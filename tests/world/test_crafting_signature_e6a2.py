"""E6-a2：鐵匠打造指定招牌類型（08 8.27「打造可以指定類型，不能指定是哪一條」、8.30）。

現有內容沒有標招牌的詞條，開關也預設關；這裡沿用 E6-a1 的測試內容庫做法（把幾條現有詞條標成招牌、
另加腳的地形規則與主手的行為改寫），再把開關打開。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from tests.content.test_signature_gen_e6a1 import TAGS, _extra
from tests.world.helpers import NOON, make_world, without_fields
from trpg.api.world_crafting_view import crafting_view
from trpg.content.item_gen import ItemGenError, affix_choices, generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.crafting import build_choices, plan_craft, signature_choices
from trpg.world.crafting_actions import (
    AffixChangedEvent,
    CraftAction,
    GearCraftedEvent,
    ImbueAction,
    RerollAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]
SMITHY = "smithy_mist_ferry"
ENCHANTER = "enchanter_mist_ferry"
COARSE = "item_coarse_material"
FINE = "item_fine_material"
SUPERIOR = "item_superior_material"
MIST = "item_mist_crystal"
ESSENCE = "item_essence"
KW_NECK = "affix_kw_burn_duration"


def with_signatures(lib: ContentLibrary, *, enabled: bool = True) -> ContentLibrary:
    affixes = dict(lib.affixes)
    for affix_id, kind in TAGS.items():
        affixes[affix_id] = affixes[affix_id].model_copy(update={"signature": kind})
    affixes.update(_extra())
    assert lib.item_gen is not None
    rules = lib.item_gen.model_copy(update={"signature_enabled": enabled})
    return dataclasses.replace(lib, affixes=dict(sorted(affixes.items())), item_gen=rules)


@pytest.fixture(scope="module")
def plain(content_library: ContentLibrary) -> ContentLibrary:
    return without_fields(content_library)


@pytest.fixture(scope="module")
def library(plain: ContentLibrary) -> ContentLibrary:
    """覆寫 ``tests/world/conftest.py`` 的 ``library``（``make_char`` 也跟著用這份）。"""
    return with_signatures(plain)


def _rich(make_char: MakeChar, **updates: Any) -> CharacterState:
    bag = {COARSE: 20, FINE: 20, SUPERIOR: 20, MIST: 5, ESSENCE: 20}
    data: dict[str, Any] = {"gold": 50000, "quest_coins": 50, "level": 8, "bag": bag}
    data.update(updates)
    return make_char("alice", **data)


def _craft(**fields: Any) -> CraftAction:
    data: dict[str, Any] = {"station": SMITHY, "slot_type": "neck", "rarity": "rare"}
    data.update({"grade": SUPERIOR})
    data.update(fields)
    return CraftAction(**data)


def _step(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: object
) -> StepResult:
    return world_step(library, world, char, action, NOON)  # type: ignore[arg-type]


def _crafted(result: StepResult) -> GearCraftedEvent:
    return next(e for e in result.events if isinstance(e, GearCraftedEvent))


def test_signature_choices_follow_switch_and_slot(
    plain: ContentLibrary, library: ContentLibrary
) -> None:
    """開關關著時沒有這個選項；打開後只列帶招牌的部位上、有候選的種類（依 8.27 的五種順序）。"""
    off = with_signatures(plain, enabled=False)
    for slot in ("weapon", "offhand", "body", "feet", "neck", "head"):
        assert signature_choices(plain, slot, "melee") == []
        assert signature_choices(off, slot, "melee") == []
    assert signature_choices(library, "weapon", "melee") == ["action", "behavior"]
    assert signature_choices(library, "offhand") == ["action", "reaction"]
    assert signature_choices(library, "body") == ["reaction"]
    assert signature_choices(library, "feet") == ["terrain"]
    assert signature_choices(library, "neck") == ["action"]
    assert signature_choices(library, "head") == []  # 頭、手、戒指不帶招牌
    assert signature_choices(library, "hands") == []


@pytest.mark.parametrize("rarity", ["rare", "epic"])
def test_craft_with_signature_kind(
    library: ContentLibrary, make_char: MakeChar, rarity: str
) -> None:
    """指定招牌類型：招牌是那一種（放最後），build 詞條照產生器原本的抽法隨機（第 1 條）。"""
    for slot, kind in (("offhand", "reaction"), ("offhand", "action"), ("feet", "terrain")):
        action = _craft(slot_type=slot, rarity=rarity, signature=kind)
        result = _step(library, make_world(), _rich(make_char), action)
        item = result.char.gear[-1]
        last = library.affixes[item.affixes[-1].affix]
        assert last.signature == kind, (slot, kind)
        assert sum(1 for r in item.affixes if library.affixes[r.affix].signature) == 1
        record = result.world.recipe_of(_crafted(result).code)
        assert record is not None
        assert record.recipe.signature == kind and record.recipe.affix is None
        # 同一份配方一定打出同一件（8.20）；配方碼照打也一樣
        again = _step(
            library,
            result.world,
            _rich(make_char),
            CraftAction(station=SMITHY, code=_crafted(result).code),
        )
        assert again.char.gear[-1].affixes == item.affixes


def test_signature_kind_build_affix_is_random(library: ContentLibrary, make_char: MakeChar) -> None:
    """選了招牌類型就不能再指定詞條：第 1 條 build 詞條由配方指紋決定，不同材料組合會不同。"""
    firsts: set[str] = set()
    for level in range(5, 9):
        result = _step(
            library,
            make_world(),
            _rich(make_char),
            _craft(slot_type="weapon", signature="action", item_level=level),
        )
        item = result.char.gear[-1]
        firsts.add(item.affixes[0].affix)
        assert library.affixes[item.affixes[-1].affix].signature == "action"
    choices = {a.id for a in build_choices(library, "weapon", "melee")}
    assert firsts <= choices  # 5 級起剩下的 40% 放得下技能強化，第 1 條是 build 詞條
    assert len(firsts) >= 2


def test_affix_and_signature_are_exclusive() -> None:
    """指定詞條和指定招牌類型二選一（8.27「打造的指定名額仍然只有 1 條」）。"""
    with pytest.raises(ValidationError, match="只能選一個"):
        _craft(affix=KW_NECK, signature="action")
    with pytest.raises(ValidationError, match="配方碼"):
        CraftAction(station=SMITHY, code="abcdef0123", signature="action")


def test_signature_kind_rejected(
    plain: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _rich(make_char)
    # 開關關著：這個選項不存在，送了也擋
    off = with_signatures(plain, enabled=False)
    with pytest.raises(WorldActionError, match="還沒有開放"):
        plan_craft(off, make_world(), char, _craft(signature="action"))
    # 頭不帶招牌
    with pytest.raises(WorldActionError, match="不帶招牌"):
        plan_craft(library, make_world(), char, _craft(slot_type="head", signature="action"))
    # 這個部位沒有這一種
    with pytest.raises(WorldActionError, match="地形規則"):
        plan_craft(library, make_world(), char, _craft(slot_type="neck", signature="terrain"))
    # 沒指定詞條也沒指定類型
    with pytest.raises(WorldActionError, match="要指定 1 條詞條"):
        plan_craft(library, make_world(), char, _craft())


def test_forced_affix_must_fit_the_rest(library: ContentLibrary, make_char: MakeChar) -> None:
    """開關打開時，指定的 build 詞條要放進招牌以外的 40%；放不下照現有規則報錯（E6-a1 待決 6）。"""
    # 3 級項鍊：預算 12、招牌 7.2、剩 4.8，放不下 8 點的技能強化
    with pytest.raises(ItemGenError, match="放不下指定的詞條"):
        generate_item(library, Rng(1), "neck", "rare", 3, forced=KW_NECK)
    with pytest.raises(WorldActionError, match="打不出來"):
        _step(library, make_world(), _rich(make_char), _craft(affix=KW_NECK, item_level=3))
    # 8 級項鍊：預算 23、剩 9.2，放得下；第 1 條是指定的詞條，招牌在最後
    result = _step(library, make_world(), _rich(make_char), _craft(affix=KW_NECK, item_level=8))
    item = result.char.gear[-1]
    assert item.affixes[0].affix == KW_NECK
    assert library.affixes[item.affixes[-1].affix].signature == "action"


def test_generator_signature_kind(library: ContentLibrary) -> None:
    for seed in range(8):
        item = generate_item(library, Rng(seed), "weapon", "epic", 6, signature_kind="behavior")
        assert library.affixes[item.affixes[-1].affix].signature == "behavior"
    with pytest.raises(ItemGenError, match="不能帶招牌"):
        generate_item(library, Rng(0), "head", "epic", 6, signature_kind="action")
    with pytest.raises(ItemGenError, match="沒有「地形規則」"):
        generate_item(library, Rng(0), "neck", "epic", 6, signature_kind="terrain")


# ---------------------------------------------------------------------------
# 附魔台重骰招牌（08 8.30 第 3、10 點）
# ---------------------------------------------------------------------------


def _offhand(library: ContentLibrary, make_char: MakeChar) -> StepResult:
    """10 級史詩副手、指定新動作：副手的新動作有 2 條（鉤爪、煙霧），招牌以外還有 1 條以上。"""
    char = _rich(make_char, level=10)
    action = _craft(slot_type="offhand", rarity="epic", signature="action", item_level=10)
    return _step(library, make_world(), char, action)


def _reroll(library: ContentLibrary, result: StepResult, item: str, index: int) -> StepResult:
    action = RerollAction(station=ENCHANTER, item=item, index=index)
    return _step(library, result.world, result.char, action)


def test_reroll_signature_stays_same_kind(library: ContentLibrary, make_char: MakeChar) -> None:
    done = _offhand(library, make_char)
    item = done.char.gear[-1]
    index = len(item.affixes) - 1
    current = item.affixes[index].affix
    options = affix_choices(library, item, index)
    assert options, "招牌要能重骰"
    assert {a.signature for a, _ in options} == {"action"}  # 只換成同一種
    assert current not in {a.id for a, _ in options}
    seen = {current}
    for _ in range(4):
        done = _reroll(library, done, item.id, index)
        new = done.char.gear[-1].affixes[index].affix
        assert library.affixes[new].signature == "action"
        seen.add(new)
    assert seen == {"affix_act_grapple", "affix_act_smoke"}


def test_reroll_signature_without_other_candidates(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """同一種只有原本那條時沒有候選（身體的新反應只有 1 條）：不能換。"""
    char = _rich(make_char, level=10)
    action = _craft(slot_type="body", rarity="epic", signature="reaction", item_level=10)
    done = _step(library, make_world(), char, action)
    item = done.char.gear[-1]
    index = len(item.affixes) - 1
    assert affix_choices(library, item, index) == []
    with pytest.raises(WorldActionError, match="不能換"):
        _reroll(library, done, item.id, index)


def test_reroll_signature_cost_shares_count(library: ContentLibrary, make_char: MakeChar) -> None:
    """費用照一般重骰，和同件其他詞條共用遞增次數（08 8.30 第 3 點）。"""
    rules = library.world_crafting
    assert rules is not None
    done = _offhand(library, make_char)
    item = done.char.gear[-1]
    assert len(item.affixes) >= 2
    last = len(item.affixes) - 1
    gold: list[int] = []
    for index in (0, last, 0, last):
        done = _reroll(library, done, item.id, index)
        gold += [e.gold_spent for e in done.events if isinstance(e, AffixChangedEvent)]
    assert gold == [rules.reroll.gold(n) for n in range(4)]
    assert gold[0] < gold[1] < gold[2] < gold[3]


def test_imbue_cannot_pick_signature(library: ContentLibrary, make_char: MakeChar) -> None:
    """附魔台的「指定」不能把招牌指定成某一條（08 8.30 第 10 點）；畫面上招牌那條沒有指定選單。"""
    done = _offhand(library, make_char)
    item = done.char.gear[-1]
    index = len(item.affixes) - 1
    other = next(a.id for a, _ in affix_choices(library, item, index))
    with pytest.raises(WorldActionError, match="不能指定"):
        _step(
            library,
            done.world,
            done.char,
            ImbueAction(station=ENCHANTER, item=item.id, index=index, affix=other),
        )
    view = crafting_view(library, done.world, done.char, in_battle=False)
    assert view is not None
    gear = next(g for g in view.gear if g.item == item.id)
    assert gear.affixes is not None
    row = gear.affixes[index]
    assert row.can_change and row.choices == ()
    assert gear.affixes[0].choices  # 一般詞條照舊可以指定
