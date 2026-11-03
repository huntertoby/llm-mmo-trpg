"""配方＝基礎配方＋重骰序列（Phase 5D-3b；08 8.20／#33）：重骰與指定記進配方，配方碼打造照序列重現、
費用照付、結果和原裝備相同；首位發現者也套到帶序列的配方；舊配方碼照常可讀。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.item_gen import affix_choices
from trpg.content.library import ContentLibrary
from trpg.world.crafting import fingerprint, plan_craft, recipe_code, variant_print
from trpg.world.crafting_actions import (
    AffixChangedEvent,
    CraftAction,
    GearCraftedEvent,
    ImbueAction,
    RerollAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, GearMod, RecipeStep, WorldState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]
SMITHY = "smithy_mist_ferry"
ENCHANTER = "enchanter_mist_ferry"
COARSE = "item_coarse_material"
MIST = "item_mist_crystal"
ESSENCE = "item_essence"


def _rich(make_char: MakeChar, character_id: str = "alice") -> CharacterState:
    bag = {COARSE: 20, MIST: 5, ESSENCE: 20}
    return make_char(character_id, gold=5000, quest_coins=20, level=5, bag=bag)


def _step(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: object
) -> StepResult:
    return world_step(library, world, char, action, NOON)  # type: ignore[arg-type]


def _changed(result: StepResult) -> AffixChangedEvent:
    return next(e for e in result.events if isinstance(e, AffixChangedEvent))


def _crafted(result: StepResult) -> GearCraftedEvent:
    return next(e for e in result.events if isinstance(e, GearCraftedEvent))


def _modded(
    library: ContentLibrary, make_char: MakeChar
) -> tuple[WorldState, CharacterState, list[AffixChangedEvent]]:
    """alice 打一條史詩項鍊，重骰最後一條兩次、再指定第 1 條以外的一條。"""
    craft = CraftAction(
        station=SMITHY,
        slot_type="neck",
        rarity="epic",
        affix="affix_kw_burn_duration",
        grade=COARSE,
        materials=(MIST,),
    )
    result = _step(library, make_world(), _rich(make_char), craft)
    world, char = result.world, result.char
    item = char.gear[-1]
    last = len(item.affixes) - 1
    events: list[AffixChangedEvent] = []
    for _ in range(2):
        result = _step(
            library, world, char, RerollAction(station=ENCHANTER, item=item.id, index=last)
        )
        world, char = result.world, result.char
        events.append(_changed(result))
    current = next(g for g in char.gear if g.id == item.id)
    target = affix_choices(library, current, last)[0][0].id
    imbue = ImbueAction(station=ENCHANTER, item=item.id, index=last, affix=target)
    result = _step(library, world, char, imbue)
    events.append(_changed(result))
    return result.world, result.char, events


def _same(a: object, b: object) -> bool:
    return a.model_copy(update={"id": "x"}) == b.model_copy(update={"id": "x"})  # type: ignore[attr-defined]


def test_reroll_records_variant_and_discoverer(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world, char, events = _modded(library, make_char)
    item = char.gear[-1]
    mod = char.gear_mods[item.id]
    assert [s.affix is None for s in mod.steps] == [True, True, False]
    assert mod.traceable and mod.variant == events[-1].code
    assert all(e.code is not None and e.discovered for e in events)
    assert len({e.code for e in events}) == 3  # 每一步都是一份新配方
    record = world.recipe_of(mod.variant)  # type: ignore[arg-type]
    assert record is not None and record.base == mod.recipe and record.steps == mod.steps
    assert record.discoverer == "alice" and record.name_zh == item.name_zh
    assert mod.variant == recipe_code(variant_print(mod.fingerprint, mod.steps))
    assert world.recipe_of(mod.recipe) is not None  # type: ignore[arg-type]


def test_variant_code_reproduces_item(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char, _ = _modded(library, make_char)
    original = char.gear[-1]
    code = char.gear_mods[original.id].variant
    assert code is not None
    bob = _rich(make_char, "bob")
    action = CraftAction(station=SMITHY, code=code.upper())
    plan = plan_craft(library, world, bob, action)
    result = _step(library, world, bob, action)
    copy = result.char.gear[-1]
    assert _same(copy, original)
    assert copy.id == f"item_craft_{code}_1"
    event = _crafted(result)
    assert event.code == code and not event.discovered and event.discoverer_name
    assert result.world == world  # 已知配方，世界不變
    # 費用照付：基礎打造＋重骰 20、40＋指定（第 3 次改動）；精華 1＋1＋3
    base = plan_craft(library, world, bob, CraftAction(station=SMITHY, code=plan.base_code))
    rules = library.world_crafting
    assert rules is not None
    assert plan.gold == base.gold + 20 + 40 + rules.imbue.gold(2)
    assert plan.spent[ESSENCE] == 2 * rules.reroll.essence + rules.imbue.essence
    assert result.char.bag[ESSENCE] == 20 - plan.spent[ESSENCE]
    assert result.char.gold == bob.gold - plan.gold
    mod = result.char.gear_mods[copy.id]
    assert mod == char.gear_mods[original.id]  # 指紋、基礎碼、序列、帶序列的碼都一樣
    # 確定性：同輸入同結果
    assert _step(library, world, bob, action) == result


def test_variant_further_reroll_new_discoverer(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world, char, _ = _modded(library, make_char)
    code = char.gear_mods[char.gear[-1].id].variant
    result = _step(library, world, _rich(make_char, "bob"), CraftAction(station=SMITHY, code=code))
    copy = result.char.gear[-1]
    again = _step(
        library, result.world, result.char, RerollAction(station=ENCHANTER, item=copy.id, index=0)
    )
    event = _changed(again)
    assert event.discovered and event.code not in {code, None}
    assert again.world.recipe_of(event.code).discoverer == "bob"  # type: ignore[arg-type,union-attr]
    # 照第 4 步的序列再打一次（alice 打）→ 同一件
    third = _step(library, again.world, char, CraftAction(station=SMITHY, code=event.code))
    assert _same(third.char.gear[-1], again.char.gear[-1])


def test_base_code_still_works(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char, _ = _modded(library, make_char)
    mod = char.gear_mods[char.gear[-1].id]
    assert mod.recipe is not None
    result = _step(
        library, world, _rich(make_char, "bob"), CraftAction(station=SMITHY, code=mod.recipe)
    )
    record = world.recipe_of(mod.recipe)
    assert record is not None and record.steps == () and record.base is None
    assert result.char.gear_mods[result.char.gear[-1].id].steps == ()
    plan = plan_craft(library, world, char, CraftAction(station=SMITHY, code=mod.recipe))
    assert plan.code == recipe_code(fingerprint(plan.recipe))  # 舊格式的碼不變


def test_old_format_mod_does_not_make_code(library: ContentLibrary, make_char: MakeChar) -> None:
    """5D-3 的舊紀錄只有 rerolls（沒有序列）：還能重骰，但不產生配方碼。"""
    world, char, _ = _modded(library, make_char)
    item = char.gear[-1]
    mod = char.gear_mods[item.id]
    old = GearMod(fingerprint=mod.fingerprint, recipe=mod.recipe, rerolls=(0,))
    char = char.model_copy(update={"gear_mods": {**char.gear_mods, item.id: old}})
    result = _step(library, world, char, RerollAction(station=ENCHANTER, item=item.id, index=0))
    event = _changed(result)
    assert event.code is None and not event.discovered
    assert result.world == world
    assert result.char.gear_mods[item.id].variant is None


def test_variant_record_round_trips(library: ContentLibrary, make_char: MakeChar) -> None:
    world, _, _ = _modded(library, make_char)
    assert WorldState.model_validate_json(world.model_dump_json()) == world
    step = RecipeStep.model_validate({"index": 1})
    assert step.affix is None


def test_variant_missing_essence_keeps_state(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char, _ = _modded(library, make_char)
    code = char.gear_mods[char.gear[-1].id].variant
    poor = _rich(make_char, "bob").model_copy(update={"bag": {COARSE: 20, MIST: 5, ESSENCE: 1}})
    with pytest.raises(WorldActionError, match="材料不夠"):
        _step(library, world, poor, CraftAction(station=SMITHY, code=code))
