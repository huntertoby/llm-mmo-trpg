"""E6-b2 第 3 項：招牌的 API 欄位（裝備卡、角色面板）與勾選的合法性檢查。

用測試內容：幾條現有詞條標上招牌（``tests/roguelite/signature_helpers.py``）。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.roguelite.helpers import library as run_library
from tests.roguelite.signature_helpers import (
    GRAPPLE,
    GUARD,
    OVERWATCH,
    RULE_FIRE,
    RULE_MOVE,
    SMOKE,
    gear_item,
    sig_library,
)
from tests.world.helpers import NOON, hero, make_world, without_fields
from trpg.api.gear import item_info
from trpg.api.gear_signature import SIGNATURE_FULL_ZH, SIGNATURE_SHORT_ZH, signature_panel
from trpg.api.run_presenter import gear_candidate, hero_out
from trpg.api.world_economy_view import inventory_view
from trpg.content.library import ContentLibrary
from trpg.engine.view import RULE_LIMITED_ZH, SIGNATURE_LIMITED_ZH
from trpg.roguelite import ChoiceError, RunState, apply_choice, new_keyword_run
from trpg.roguelite.gear import chosen_problems, set_gear_chosen
from trpg.roguelite.state import GearChosenChoice
from trpg.world.economy_actions import GearChosenAction
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState
from trpg.world.step import new_character, world_step

LONG = SIGNATURE_LIMITED_ZH.format(n=3)
SHORT = SIGNATURE_SHORT_ZH.format(n=3)

FOUR = {
    "body": gear_item("b", "body", GUARD),
    "head": gear_item("x", "head", OVERWATCH),
    "hands": gear_item("h", "hands", GRAPPLE),
    "neck": gear_item("n", "neck", SMOKE),
}


def _run(lib: ContentLibrary, **equipment: object) -> RunState:
    run = new_keyword_run(lib, "one_handed_sword", ("ignite", "prone"), 3)
    return run.model_copy(update={"equipment": dict(equipment)})


@pytest.fixture
def lib() -> ContentLibrary:
    return sig_library(run_library())


# ---------------------------------------------------------------------------
# 勾選的合法性
# ---------------------------------------------------------------------------


def test_more_than_three_signatures_is_rejected(lib: ContentLibrary) -> None:
    run = _run(lib, **FOUR)
    four = (f"body:{GUARD}", f"head:{OVERWATCH}", f"hands:{GRAPPLE}", f"neck:{SMOKE}")
    assert any("最多勾 3 個" in p for p in chosen_problems(lib, run, four))
    with pytest.raises(ChoiceError):
        apply_choice(lib, run, GearChosenChoice(chosen=four))


def test_two_rules_are_rejected(lib: ContentLibrary) -> None:
    run = _run(
        lib,
        body=gear_item("b", "body", RULE_MOVE, legendary=True),
        neck=gear_item("n", "neck", RULE_FIRE, legendary=True),
    )
    two = (f"body:{RULE_MOVE}", f"neck:{RULE_FIRE}")
    assert any("最多勾 1 條" in p for p in chosen_problems(lib, run, two))
    with pytest.raises(ChoiceError):
        set_gear_chosen(lib, run, two)


def test_picks_must_be_worn_signatures(lib: ContentLibrary) -> None:
    run = _run(lib, **FOUR)
    for bad in (f"feet:{GRAPPLE}", f"hands:{SMOKE}", "hands:affix_attr_str", "nonsense"):
        assert chosen_problems(lib, run, (bad,)), bad
    assert chosen_problems(lib, run, (f"neck:{SMOKE}", f"neck:{SMOKE}")) == ["勾選重複"]


def test_valid_picks_are_saved_in_slot_order(lib: ContentLibrary) -> None:
    run = _run(lib, **FOUR)
    picks = (f"neck:{SMOKE}", f"head:{OVERWATCH}", f"body:{GUARD}")
    done = apply_choice(lib, run, GearChosenChoice(chosen=picks))
    assert done.gear_chosen == (f"head:{OVERWATCH}", f"body:{GUARD}", f"neck:{SMOKE}")
    assert done.node == run.node  # 不推進節點
    panel = signature_panel(lib, done)
    assert panel is not None
    assert [r.affix_id for r in panel.rows if not r.active] == [GRAPPLE]


# ---------------------------------------------------------------------------
# 角色面板與裝備卡的欄位
# ---------------------------------------------------------------------------


def test_panel_rows_counts_and_short_grey_text(lib: ContentLibrary) -> None:
    panel = signature_panel(lib, _run(lib, **FOUR))
    assert panel is not None
    assert [r.slot for r in panel.rows] == ["head", "body", "hands", "neck"]  # 欄位固定順序
    assert panel.active == 3 and panel.cap == 3 and not panel.has_rule
    assert panel.count_zh == "生效 3／3"
    assert panel.full_zh == SIGNATURE_FULL_ZH.format(n=3)
    greyed = [r for r in panel.rows if not r.active]
    assert [(r.slot, r.off_zh) for r in greyed] == [("neck", SHORT)]
    hands = next(r for r in panel.rows if r.slot == "hands")
    assert hands.kind == "action" and hands.kind_zh == "新動作" and hands.name_zh == "鉤爪"
    assert hands.counted and not hands.rule and hands.key == f"hands:{GRAPPLE}"


def test_panel_rule_conflict_text_and_rule_count(lib: ContentLibrary) -> None:
    run = _run(
        lib,
        body=gear_item("b", "body", RULE_MOVE, legendary=True),
        neck=gear_item("n", "neck", RULE_FIRE, legendary=True),
    )
    panel = signature_panel(lib, run)
    assert panel is not None and panel.has_rule
    assert panel.count_zh == "生效 1／3・改寫規則 1／1"
    neck = next(r for r in panel.rows if r.slot == "neck")
    assert neck.rule and not neck.active and neck.off_zh == RULE_LIMITED_ZH.format(slot="身體")


def test_no_signature_means_no_panel_and_plain_lines() -> None:
    lib = run_library()
    run = _run(lib)
    assert signature_panel(lib, run) is None
    hero = hero_out(lib, run)
    assert hero.signatures is None
    for slot in hero.equipment:
        for line in slot.item.affixes if slot.item is not None else ():
            assert line.signature is None and line.off_zh is None


def test_item_lines_carry_kind_label_and_name(lib: ContentLibrary) -> None:
    info = item_info(lib, gear_item("h", "hands", GRAPPLE))
    line = info.affixes[0]
    assert line.signature == "action" and line.signature_zh == "招牌・新動作"
    assert line.signature_name_zh == "鉤爪" and line.off_zh is None
    legend = item_info(lib, gear_item("n", "neck", RULE_FIRE, legendary=True)).affixes[0]
    assert legend.signature == "rule" and legend.signature_zh == "獨特效果・改寫規則"


def test_worn_and_candidate_cards_use_the_long_grey_text(lib: ContentLibrary) -> None:
    run = _run(lib, **FOUR)
    hero = hero_out(lib, run)
    neck = next(s for s in hero.equipment if s.slot == "neck")
    assert neck.item is not None and neck.item.affixes[0].off_zh == LONG
    three = {k: v for k, v in FOUR.items() if k != "hands"}
    cand = gear_candidate(lib, _run(lib, **three), gear_item("h", "hands", GRAPPLE))
    assert cand.item.affixes[0].off_zh == LONG  # 換上之後是第 4 個：新穿上的標灰
    assert hero.signatures is not None and hero.signatures.chosen == ()


# ---------------------------------------------------------------------------
# 大世界：穿戴中的勾選與背包滿時的小標
# ---------------------------------------------------------------------------


MakeChar = Callable[..., CharacterState]


@pytest.fixture
def make_char(content_library: ContentLibrary) -> MakeChar:
    """同 ``tests/world/conftest.py`` 的 ``make_char``（沒有實地地圖、在城鎮）。"""
    base = without_fields(content_library)

    def factory(**updates: object) -> CharacterState:
        char = new_character(base, "alice", hero(base), region="cloud_ridge")
        return char.model_copy(update=updates)

    return factory


def test_world_gear_chosen_action_saves_and_validates(
    content_library: ContentLibrary, make_char: MakeChar
) -> None:
    wlib = sig_library(without_fields(content_library))
    char = make_char(equipment=dict(FOUR))
    picks = (f"head:{OVERWATCH}", f"hands:{GRAPPLE}", f"neck:{SMOKE}")
    done = world_step(wlib, make_world(), char, GearChosenAction(chosen=picks), NOON).char
    assert done.gear_chosen == picks
    inv = inventory_view(wlib, done, in_battle=False)
    assert inv is not None and inv.signatures is not None
    assert [r.slot for r in inv.signatures.rows if not r.active] == ["body"]
    four = (*picks, f"body:{GUARD}")
    with pytest.raises(WorldActionError):
        world_step(wlib, make_world(), char, GearChosenAction(chosen=four), NOON)


def test_world_bag_rows_mark_signature_gear(
    content_library: ContentLibrary, make_char: MakeChar
) -> None:
    wlib = sig_library(without_fields(content_library))
    char = make_char(gear=(gear_item("h", "hands", GRAPPLE), gear_item("p", "hands")))
    inv = inventory_view(wlib, char, in_battle=False)
    assert inv is not None
    marks = {b.item: b.signature for b in inv.bag if b.gear}
    assert marks == {"h": "action", "p": None}
