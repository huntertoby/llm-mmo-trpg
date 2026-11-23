"""E6-c2 第 1 項：鐵匠打造傳說（08 8.27「傳說可以打造，但材料很貴」、8.30 第 6、10、11 點）。

打造的稀有度多一個傳說：獨特效果的類型和 1 條技能強化二選一（打法比照一般打造）；部位只能選主手、
副手、身體、腳、項鍊；費用照平衡待查第 41 條的初值（``content/world/crafting.yaml``）。開關
``legendary_enabled`` 關著時不能打。沿用 E6-a2 的測試內容庫（幾條詞條標成招牌），再把傳說開關
打開。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest

from tests.world.helpers import NOON, make_world, without_fields
from tests.world.test_crafting_signature_e6a2 import with_signatures
from trpg.api.world_crafting_view import crafting_view
from trpg.content.item_budget import is_legendary, legendary_unique
from trpg.content.library import ContentLibrary
from trpg.world.crafting import build_choices, plan_craft, unique_choices
from trpg.world.crafting_actions import CraftAction, GearCraftedEvent
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]
SMITHY = "smithy_mist_ferry"
FINE = "item_fine_material"
SUPERIOR = "item_superior_material"
MIST = "item_mist_crystal"
LEGENDARY_SLOTS = ("weapon", "offhand", "body", "feet", "neck")


def with_legendary(lib: ContentLibrary, *, enabled: bool = True) -> ContentLibrary:
    assert lib.item_gen is not None
    rules = lib.item_gen.model_copy(update={"legendary_enabled": enabled})
    return dataclasses.replace(lib, item_gen=rules)


@pytest.fixture(scope="module")
def plain(content_library: ContentLibrary) -> ContentLibrary:
    return without_fields(content_library)


@pytest.fixture(scope="module")
def library(plain: ContentLibrary) -> ContentLibrary:
    """覆寫 ``tests/world/conftest.py`` 的 ``library``（``make_char`` 也跟著用這份）。"""
    return with_legendary(with_signatures(plain, enabled=False))


def _rich(make_char: MakeChar, **updates: Any) -> CharacterState:
    bag = {FINE: 20, SUPERIOR: 20, MIST: 5}
    data: dict[str, Any] = {"gold": 50000, "quest_coins": 50, "level": 8, "bag": bag}
    data.update(updates)
    return make_char("alice", **data)


def _craft(**fields: Any) -> CraftAction:
    data: dict[str, Any] = {"station": SMITHY, "slot_type": "neck", "rarity": "legendary"}
    data.update({"grade": SUPERIOR})
    data.update(fields)
    return CraftAction(**data)


def _step(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: object
) -> StepResult:
    return world_step(library, world, char, action, NOON)  # type: ignore[arg-type]


def _crafted(result: StepResult) -> GearCraftedEvent:
    return next(e for e in result.events if isinstance(e, GearCraftedEvent))


def _unique(library: ContentLibrary, item: Any) -> list[str]:
    return [r.affix for r in item.affixes if legendary_unique(library.affixes[r.affix])]


def test_unique_choices_follow_switch_and_slot(
    plain: ContentLibrary, library: ContentLibrary
) -> None:
    """開關關著時沒有傳說的類型可選；打開後只列能出傳說的五個部位上、有候選的種類（8.27 的
    順序）。"""
    off = with_legendary(with_signatures(plain, enabled=False), enabled=False)
    for slot in (*LEGENDARY_SLOTS, "head", "hands", "ring"):
        assert unique_choices(off, slot, "melee") == []
    assert unique_choices(library, "weapon", "melee") == ["action", "behavior", "rule"]
    assert unique_choices(library, "offhand") == ["action", "reaction", "rule"]
    assert unique_choices(library, "body") == ["reaction", "rule"]
    assert unique_choices(library, "feet") == ["terrain", "rule"]
    assert unique_choices(library, "neck") == ["action", "rule"]
    for slot in ("head", "hands", "ring"):
        assert unique_choices(library, slot) == []


@pytest.mark.parametrize(
    ("slot", "kind"),
    [("neck", "rule"), ("neck", "action"), ("feet", "terrain"), ("offhand", "reaction")],
)
def test_craft_legendary_with_unique_kind(
    library: ContentLibrary, make_char: MakeChar, slot: str, kind: str
) -> None:
    """指定獨特效果的類型：打出傳說，獨特效果是那一種（放最後、恰好 1 個）；配方記類型、不記詞條；
    同一份配方（配方碼）一定打出同一件（8.20）。"""
    result = _step(library, make_world(), _rich(make_char), _craft(slot_type=slot, signature=kind))
    item = result.char.gear[-1]
    assert item.rarity == "legendary" and is_legendary(item)
    uniques = _unique(library, item)
    assert uniques == [item.affixes[-1].affix]
    found = library.affixes[uniques[0]]
    assert (found.signature or ("rule" if found.category == "rule" else None)) == kind
    record = result.world.recipe_of(_crafted(result).code)
    assert record is not None
    assert record.recipe.rarity == "legendary"
    assert record.recipe.signature == kind and record.recipe.affix is None
    again = _step(
        library, result.world, _rich(make_char), CraftAction(station=SMITHY, code=record.code)
    )
    assert again.char.gear[-1].affixes == item.affixes


def test_craft_legendary_with_build_affix(library: ContentLibrary, make_char: MakeChar) -> None:
    """指定 1 條技能強化：第 1 條是那條，獨特效果照部位權重隨機。"""
    affix = build_choices(library, "neck")[0].id
    result = _step(library, make_world(), _rich(make_char), _craft(affix=affix))
    item = result.char.gear[-1]
    assert item.rarity == "legendary"
    assert item.affixes[0].affix == affix
    assert len(_unique(library, item)) == 1
    record = result.world.recipe_of(_crafted(result).code)
    assert record is not None and record.recipe.affix == affix and record.recipe.signature is None


def test_affix_and_unique_kind_are_exclusive() -> None:
    """二選一（同一般打造）：兩個都給被擋下。"""
    with pytest.raises(ValueError, match="只能選一個"):
        _craft(affix="affix_kw_burn_duration", signature="rule")


@pytest.mark.parametrize("slot", ["head", "hands", "ring"])
def test_legendary_slot_limit(library: ContentLibrary, make_char: MakeChar, slot: str) -> None:
    """部位只能選主手、副手、身體、腳、項鍊（08 8.30 第 6 點）。"""
    affix = build_choices(library, slot)[0].id
    with pytest.raises(WorldActionError, match="傳說只能打"):
        plan_craft(library, make_world(), _rich(make_char), _craft(slot_type=slot, affix=affix))


def test_unique_kind_without_candidates(library: ContentLibrary, make_char: MakeChar) -> None:
    """這個部位沒有那一種獨特效果的候選時報錯。"""
    with pytest.raises(WorldActionError, match="不能指定獨特效果類型"):
        plan_craft(library, make_world(), _rich(make_char), _craft(signature="terrain"))


def test_switch_off_rejects_legendary(plain: ContentLibrary, make_char: MakeChar) -> None:
    """開關關著（預設）時不能打傳說，配方碼也一樣。"""
    off = with_signatures(plain, enabled=False)
    affix = build_choices(off, "neck")[0].id
    with pytest.raises(WorldActionError, match="傳說打造還沒有開放"):
        plan_craft(off, make_world(), _rich(make_char), _craft(affix=affix))


def test_legendary_cost(library: ContentLibrary, make_char: MakeChar) -> None:
    """材料費用（平衡待查第 41 條初值）：金幣 40 × 物品等級、任務幣 5，另要 1 個上料（和通用料
    一起扣）。"""
    rules = library.world_crafting
    assert rules is not None
    cost = rules.craft.rarities["legendary"]
    assert (cost.gold_per_level, cost.quest_coins) == (40, 5)
    assert cost.extra == {SUPERIOR: 1}
    char = _rich(make_char)
    amount = rules.craft.grade_amount["neck"]
    plan = plan_craft(library, make_world(), char, _craft(signature="rule", item_level=6))
    assert plan.gold == 40 * 6 and plan.quest_coins == 5
    assert plan.spent == {SUPERIOR: amount + 1}
    # 通用料是精料時，上料另外扣 1 個
    fine = plan_craft(library, make_world(), char, _craft(signature="rule", grade=FINE))
    assert fine.spent == {FINE: amount, SUPERIOR: 1}
    result = _step(library, make_world(), char, _craft(signature="rule", item_level=6))
    assert result.char.gold == char.gold - 240
    assert result.char.quest_coins == char.quest_coins - 5
    assert result.char.bag.get(SUPERIOR, 0) == 20 - amount - 1
    # 上料不夠：打不了
    poor = _rich(make_char, bag={FINE: 20})
    with pytest.raises(WorldActionError):
        _step(library, make_world(), poor, _craft(signature="rule", grade=FINE))


def test_legendary_recipe_dump_has_no_new_field(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """``CraftRecipe`` 沒有加欄位：傳說配方只是稀有度不同，指定詞條時 ``signature`` 照舊不輸出。"""
    affix = build_choices(library, "neck")[0].id
    plan = plan_craft(library, make_world(), _rich(make_char), _craft(affix=affix))
    assert "signature" not in plan.recipe.model_dump(mode="json")


# ---------------------------------------------------------------------------
# 打造畫面的資料（E6-c2 第 4 項）
# ---------------------------------------------------------------------------


def test_view_lists_legendary_only_when_switch_on(
    plain: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    """開關打開：稀有度多傳說（費用寫上料、只能打五個部位），部位列獨特效果類型；關著時和原本一樣。"""
    char = _rich(make_char)
    on = crafting_view(library, make_world(), char, in_battle=False)
    assert on is not None
    rarities = {r.rarity: r for r in on.rarities}
    assert list(rarities) == ["rare", "epic", "legendary"]
    legendary = rarities["legendary"]
    assert legendary.name_zh == "傳說"
    assert legendary.cost_zh == "金幣 40 × 物品等級＋任務幣 5＋上料 ×1"
    assert legendary.slots == LEGENDARY_SLOTS
    assert rarities["rare"].slots == () and rarities["epic"].slots == ()
    by_slot = {s.slot_type: s for s in on.slots}
    assert [(o.id, o.text_zh) for o in by_slot["neck"].uniques] == [
        ("action", "獨特效果：新動作"),
        ("rule", "獨特效果：改寫規則"),
    ]
    assert by_slot["head"].uniques == ()
    off = crafting_view(
        with_legendary(with_signatures(plain, enabled=False), enabled=False),
        make_world(),
        char,
        in_battle=False,
    )
    assert off is not None
    assert [r.rarity for r in off.rarities] == ["rare", "epic"]
    assert all(s.uniques == () for s in off.slots)
    # 配方表的摘要註明指定的獨特效果類型
    done = _step(library, make_world(), char, _craft(signature="rule"))
    view = crafting_view(library, done.world, done.char, in_battle=False)
    assert view is not None
    assert view.recipes[0].summary_zh.endswith("・指定獨特效果：改寫規則")
