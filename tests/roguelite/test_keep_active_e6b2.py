"""E6-b2 第 2 項：換裝時保留原本生效的招牌與改寫規則（08 8.27、8.30 第 4 點；E6-b1 待決 1）。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from tests.roguelite.signature_helpers import (
    GRAPPLE,
    GUARD,
    RANGED_BLOCK,
    RULE_FIRE,
    RULE_MOVE,
    SMOKE,
    gear_item,
    sig_library,
)
from trpg.content.library import ContentLibrary
from trpg.roguelite import RunState, new_keyword_run
from trpg.roguelite.gear import active_picks, equip, limited_gear

KEYWORDS = ("ignite", "prone")


def _run(lib: ContentLibrary, **equipment: object) -> RunState:
    run = new_keyword_run(lib, "one_handed_sword", KEYWORDS, 3)
    return run.model_copy(update={"equipment": dict(equipment)})


def _greyed(lib: ContentLibrary, run: RunState) -> list[tuple[str, str, str | None]]:
    gear = limited_gear(lib, run)
    return [(a.slot, a.affix.id, a.limited_by) for a in gear.affixes if a.limited_by is not None]


THREE = {
    "off_hand": gear_item("o", "offhand", GUARD),
    "body": gear_item("b", "body", RANGED_BLOCK),
    "neck": gear_item("n", "neck", SMOKE),
}


def test_new_fourth_signature_is_greyed_and_the_old_three_stay() -> None:
    lib = sig_library(library())
    run = _run(lib, **THREE)
    assert run.gear_chosen == () and _greyed(lib, run) == []
    done = equip(lib, run, gear_item("h", "hands", GRAPPLE))
    # 照欄位順序會標灰項鍊；保留原本生效的 3 個，新穿上的手套標灰
    assert done.gear_chosen == (
        f"off_hand:{GUARD}",
        f"body:{RANGED_BLOCK}",
        f"neck:{SMOKE}",
    )
    assert _greyed(lib, done) == [("hands", GRAPPLE, "signature")]
    without = done.model_copy(update={"gear_chosen": ()})
    assert _greyed(lib, without) == [("neck", SMOKE, "signature")]


def test_new_rule_is_greyed_and_the_old_rule_stays() -> None:
    lib = sig_library(library())
    run = _run(lib, neck=gear_item("n", "neck", RULE_FIRE, legendary=True))
    done = equip(lib, run, gear_item("b", "body", RULE_MOVE, legendary=True))
    assert done.gear_chosen == (f"neck:{RULE_FIRE}",)
    assert _greyed(lib, done) == [("body", RULE_MOVE, "rule")]
    assert active_picks(lib, done) == (f"neck:{RULE_FIRE}",)


def test_plain_rules_without_signature_also_keep_the_old_one() -> None:
    lib = library()  # 現有內容：改寫規則沒有標招牌，照樣只生效 1 條
    run = _run(lib, neck=gear_item("n", "neck", RULE_FIRE, legendary=True))
    done = equip(lib, run, gear_item("b", "body", RULE_MOVE, legendary=True))
    assert done.gear_chosen == (f"neck:{RULE_FIRE}",)
    assert _greyed(lib, done) == [("body", RULE_MOVE, "rule")]


def test_no_overflow_keeps_gear_chosen_empty() -> None:
    lib = sig_library(library())
    run = _run(lib, body=gear_item("b", "body", RANGED_BLOCK))
    done = equip(lib, run, gear_item("h", "hands", GRAPPLE))
    assert done.gear_chosen == ()
    plain = equip(library(), _run(library()), gear_item("h2", "hands"))
    assert plain.gear_chosen == ()


def test_picks_of_the_item_taken_off_are_dropped() -> None:
    lib = sig_library(library())
    run = _run(lib, **THREE).model_copy(
        update={"gear_chosen": (f"body:{RANGED_BLOCK}", f"neck:{SMOKE}")}
    )
    done = equip(lib, run, gear_item("b2", "body"))
    assert done.gear_chosen == (f"neck:{SMOKE}",)
