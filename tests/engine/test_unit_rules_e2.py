"""E2：單位規則表（種族與裝備共用，08 8.29，#175）。

用測試內容：``affixes.yaml`` 沒有地形規則詞條，這裡臨時組。涵蓋：裝備地形規則生效、和種族或另一件
裝備重複的五種判法（開關完全涵蓋、開關有新參數、開關部分重疊、數值同參數、數值不同參數）、
裝備移動加成合計上限、角色面板的標灰與重疊說明。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from pydantic import TypeAdapter

from tests.engine.race_helpers import U1, of, race_state
from trpg.content.equipment import (
    AffixDef,
    EquippedAffix,
    EquippedItem,
    ItemDef,
    Loadout,
)
from trpg.content.slots import SLOT_TYPE_OF
from trpg.engine import BattleState, Move, resolve
from trpg.engine.events import StatusApplied
from trpg.engine.gear.core import build_gear
from trpg.engine.rules.race import (
    burn_immune,
    rule_move_bonus,
    slip_immune,
    surface_move_bonus,
    weather_move_bonus,
)
from trpg.engine.rules.statuses import move_points_for_turn
from trpg.engine.rules.unit_rules import (
    classify_sources,
    gear_move_room,
    rule_sources,
    terrain_notes,
)
from trpg.engine.state import UnitState
from trpg.engine.view import AffixLineView, project_for
from trpg.shared.types import Pos, Surface, Team

_ADAPTER: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)
_EVERY = tuple(dict.fromkeys(SLOT_TYPE_OF.values()))


def terrain(affix_id: str, name_zh: str, **params: Any) -> EquippedAffix:
    """測試用地形規則詞條。"""
    data = {"id": affix_id, "name_zh": name_zh, "category": "terrain", "slots": _EVERY, **params}
    return EquippedAffix(affix=_ADAPTER.validate_python(data))


def move_stat(amount: int) -> EquippedAffix:
    data = {
        "id": "affix_t_move",
        "name_zh": "移動 +{n}",
        "category": "stat",
        "stat": "move",
        "slots": _EVERY,
        "value": {"min": 1, "max": 2},
    }
    return EquippedAffix(affix=_ADAPTER.validate_python(data), value=amount)


FIRE_WALK = ("affix_t_fire_walk", "火焰表面不會讓你燃燒")


def loadout(slots: Mapping[str, Sequence[EquippedAffix]]) -> Loadout:
    order = list(SLOT_TYPE_OF)
    items: list[EquippedItem] = []
    for slot in sorted(slots, key=order.index):
        slot_type = SLOT_TYPE_OF[slot]
        affixes = tuple(slots[slot])
        item = ItemDef.model_validate(
            {
                "id": f"item_t_{slot}",
                "name_zh": f"測試{slot}",
                "slot_type": slot_type,
                "weapon": "one_handed_sword" if slot_type == "weapon" else None,
                "affixes": [{"affix": a.affix.id, "value": a.value} for a in affixes],
            }
        )
        items.append(EquippedItem(slot=slot, item=item, affixes=affixes))  # type: ignore[arg-type]
    return Loadout(items=tuple(items))


def wear(state: BattleState, slots: Mapping[str, Sequence[EquippedAffix]]) -> UnitState:
    """U1 穿上 ``slots``（只換裝備狀態；地形規則在戰鬥中查詢，不必重建單位）。"""
    unit = replace(state.units[U1], gear=build_gear(loadout(slots), state.ruleset.equipment))
    state.units[U1] = unit
    return unit


def lines(state: BattleState) -> dict[str, AffixLineView]:
    view = project_for(state, Team.ALLY)
    me = next(u for u in view.units if u.id == U1)
    return {f"{s.slot}:{a.affix_id}": a for s in me.equipment for a in s.affixes}


# ---------------------------------------------------------------------------
# 裝備地形規則生效
# ---------------------------------------------------------------------------


def _burns_walking_into_fire(gear: Mapping[str, Sequence[EquippedAffix]]) -> bool:
    state = race_state(None, foes=((6, 6),), surfaces=[(4, 3, "fire")])
    wear(state, gear)
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=4, y=3))))
    return any(e.target_id == U1 and e.status_id == "burning" for e in of(result, StatusApplied))


def test_equipment_terrain_rule_takes_effect() -> None:
    boots = terrain(*FIRE_WALK, rule="burn_immunity_on", surfaces=["fire"])
    state = race_state(None)
    assert not burn_immune(state.ruleset, state.units[U1], Surface.FIRE)
    unit = wear(state, {"feet": [boots]})
    assert burn_immune(state.ruleset, unit, Surface.FIRE)
    assert not burn_immune(state.ruleset, unit, Surface.POISON)
    assert _burns_walking_into_fire({})
    assert not _burns_walking_into_fire({"feet": [boots]})


def test_without_terrain_affix_the_sources_are_just_the_race() -> None:
    state = race_state("fiend")
    sources = rule_sources(state.ruleset, state.units[U1])
    assert len(sources) == 1 and sources[0].from_race
    assert terrain_notes(state.ruleset, state.units[U1]) == {}


# ---------------------------------------------------------------------------
# 重複的五種判法（判斷在 classify_sources）
# ---------------------------------------------------------------------------


def test_switch_rule_fully_covered_by_race_is_greyed() -> None:
    state = race_state("dwarf")
    wear(
        state,
        {"feet": [terrain("affix_t_ice", "冰上不滑倒", rule="slip_immunity", surfaces=["ice"])]},
    )
    overlap = classify_sources(rule_sources(state.ruleset, state.units[U1]))[1]
    assert overlap.full
    line = lines(state)["feet:affix_t_ice"]
    assert not line.active
    assert line.weight_permille == 0
    assert line.duplicate_of == "種族被動「穩健步伐」"
    assert line.overlap_zh is None


def test_switch_rule_with_new_param_adds_it() -> None:
    state = race_state("dwarf")
    unit = wear(
        state,
        {"feet": [terrain("affix_t_wet", "水上不滑倒", rule="slip_immunity", surfaces=["water"])]},
    )
    overlap = classify_sources(rule_sources(state.ruleset, unit))[1]
    assert overlap.covered == () and not overlap.full
    assert slip_immune(state.ruleset, unit, Surface.ICE)
    assert slip_immune(state.ruleset, unit, Surface.WATER)
    line = lines(state)["feet:affix_t_wet"]
    assert line.active and line.duplicate_of is None and line.overlap_zh is None


def test_switch_rule_partial_overlap_stays_active_with_note() -> None:
    state = race_state("dwarf")
    both = terrain(
        "affix_t_both", "冰上水上不滑倒", rule="slip_immunity", surfaces=["ice", "water"]
    )
    unit = wear(state, {"feet": [both]})
    overlap = classify_sources(rule_sources(state.ruleset, unit))[1]
    assert [k for k, _ in overlap.covered] == ["ice"] and not overlap.full
    assert slip_immune(state.ruleset, unit, Surface.WATER)
    line = lines(state)["feet:affix_t_both"]
    assert line.active
    assert line.overlap_zh == "冰的部分和種族重複"


def test_numeric_rule_with_same_params_is_greyed_and_does_not_stack() -> None:
    state = race_state("scalefolk")
    boots = terrain(
        "affix_t_swim",
        "站在水或冰上，移動 +1",
        rule="surface_move_bonus",
        surfaces=["water", "ice"],
        amount=1,
    )
    unit = wear(state, {"feet": [boots]})
    assert classify_sources(rule_sources(state.ruleset, unit))[1].full
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 1  # 鱗族穿水上靴仍是 +1
    line = lines(state)["feet:affix_t_swim"]
    assert not line.active and line.duplicate_of == "種族被動「流線身形」"


def test_numeric_rule_with_different_params_still_counts() -> None:
    state = race_state("scalefolk")
    boots = terrain(
        "affix_t_oil", "站在油上，移動 +1", rule="surface_move_bonus", surfaces=["oil"], amount=1
    )
    unit = wear(state, {"feet": [boots]})
    overlap = classify_sources(rule_sources(state.ruleset, unit))[1]
    assert overlap.covered == ()
    assert surface_move_bonus(state.ruleset, unit, Surface.OIL) == 1
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 1
    assert lines(state)["feet:affix_t_oil"].active


def test_two_pieces_of_gear_with_the_same_rule_grey_the_later_slot() -> None:
    state = race_state(None)
    fire = {"rule": "burn_immunity_on", "surfaces": ["fire"]}
    wear(
        state,
        {
            "body": [terrain("affix_t_fire_a", "火焰表面不會讓你燃燒", **fire)],
            "feet": [terrain("affix_t_fire_b", "走在火上不燃燒", **fire)],
        },
    )
    shown = lines(state)
    assert shown["body:affix_t_fire_a"].active
    feet = shown["feet:affix_t_fire_b"]
    assert not feet.active
    assert feet.duplicate_of == "身體的火焰表面不會讓你燃燒"


# ---------------------------------------------------------------------------
# 裝備的移動加成合計上限（8.21.5.3）
# ---------------------------------------------------------------------------


def _water_boots() -> EquippedAffix:
    return terrain(
        "affix_t_water_step",
        "站在水上，移動 +1",
        rule="surface_move_bonus",
        surfaces=["water"],
        amount=1,
    )


def _rain_cloak() -> EquippedAffix:
    return terrain(
        "affix_t_rain_step", "下雨時移動 +1", rule="weather_move_bonus", weathers=["rain"], amount=1
    )


def test_gear_terrain_move_bonus_counts_toward_the_gear_move_cap() -> None:
    state = race_state(None)
    unit = wear(state, {"feet": [_water_boots()], "body": [move_stat(2)]})
    assert gear_move_room(state.ruleset, unit) == 0
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 0
    assert rule_move_bonus(state.ruleset, unit, None, Surface.WATER) == 0


def test_two_gear_move_rules_share_the_remaining_room() -> None:
    state = race_state(None)
    unit = wear(state, {"feet": [_water_boots()], "body": [_rain_cloak()], "head": [move_stat(1)]})
    assert gear_move_room(state.ruleset, unit) == 1
    assert weather_move_bonus(state.ruleset, unit, "rain") == 1
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 1
    assert rule_move_bonus(state.ruleset, unit, "rain", Surface.WATER) == 1
    base = move_points_for_turn(state.ruleset, unit)
    assert move_points_for_turn(state.ruleset, unit, "rain", Surface.WATER) == base + 1


def test_race_move_bonus_is_not_capped_by_gear() -> None:
    state = race_state("seafolk")
    unit = wear(state, {"feet": [_water_boots()], "body": [move_stat(2)]})
    assert rule_move_bonus(state.ruleset, unit, "rain", Surface.WATER) == 1  # 種族 +1、靴子 0


def test_gear_move_rule_without_other_move_gets_its_amount() -> None:
    state = race_state(None)
    unit = wear(state, {"feet": [_water_boots()]})
    assert rule_move_bonus(state.ruleset, unit, None, Surface.WATER) == 1
    assert rule_move_bonus(state.ruleset, unit, None, None) == 0
