"""E3：地形規則「每一步留下表面」（霜行，08 8.29 E3 第 1～4 點）。

用測試內容：``affixes.yaml`` 沒有地形規則詞條，這裡臨時組（同 E2 的測試）。涵蓋：步行留冰的格子
（起點與途經、不含停下的那一格）、事件順序、冰記下是誰的、已有表面的格子不動、隊友格不留、到期直接
消失、持有者踩自己的冰不滑而別人會滑、別人造的冰持有者照樣滑、衝刺與直線衝撞也留、跳躍與被推不留、
表面被換掉時標記清掉、預覽與 AI 的滑倒估計、重播的確定性。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import give_turn, library, with_rolls
from tests.engine.race_helpers import U1, end_turn, of, race_state
from tests.engine.test_charge_through import PRONE_HIT
from tests.engine.test_charge_through import arena as charge_arena
from tests.engine.test_charge_through import skill as charge_through_skill
from tests.engine.test_self_moves import DASH, HIT, always, arena, charge_skill, use
from tests.engine.test_unit_rules_e2 import loadout, terrain, wear
from trpg.engine import BattleState, Move, UseSkill, Vault, resolve
from trpg.engine.effects import run_effects
from trpg.engine.effects.models import CreateSurfaceEffect, PushEffect
from trpg.engine.events import CheckRolled, SurfaceChanged, UnitMoved
from trpg.engine.ice_slide import path_slide_risks
from trpg.engine.path_preview import preview_path
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.engine.state import state_from_json, state_to_json
from trpg.shared.types import Pos, Surface, Team, UnitId

U2, U3 = UnitId("unit_0002"), UnitId("unit_0003")
FROST = terrain(
    "affix_t_frost", "走過的格子結 1 回合冰", rule="trail_surface", surfaces=["ice"], duration=1
)
FAIL = [(20, 1)]


def _frost(state: BattleState, unit: UnitId = U1) -> BattleState:
    if unit == U1:
        wear(state, {"feet": [FROST]})
    return state


def _path(*xys: tuple[int, int]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in xys)


def _walk(state: BattleState, *xys: tuple[int, int], unit: UnitId = U1) -> Any:
    return resolve(state, Move(unit_id=unit, path=_path(*xys)))


def _ice(state: BattleState) -> dict[tuple[int, int], UnitId | None]:
    return {
        (x, y): state.tile(x, y).surface_trail
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is Surface.ICE
    }


# ---------------------------------------------------------------------------
# 留下的格子與事件
# ---------------------------------------------------------------------------


def test_walk_leaves_ice_on_start_and_passed_tiles_not_the_stop() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    result = _walk(state, (3, 3), (4, 3), (5, 3), (5, 4))
    after = result.state
    assert _ice(after) == {(3, 3): U1, (4, 3): U1, (5, 3): U1}
    tile = after.tile(3, 3)
    assert (tile.surface_remaining, tile.surface_creator, tile.surface_team) == (1, U1, Team.ALLY)
    assert after.units[U1].xy == (5, 4)


def test_without_the_rule_nothing_is_left() -> None:
    state = race_state(None, foes=((6, 6),))
    result = _walk(state, (3, 3), (4, 3), (5, 3))
    assert _ice(result.state) == {}
    assert not of(result, SurfaceChanged)


def test_event_order_each_step_then_the_tile_left() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    result = _walk(state, (3, 3), (4, 3), (5, 3))
    seq = [
        (type(e).__name__, getattr(e, "to_pos", None) or getattr(e, "pos", None))
        for e in result.events
        if isinstance(e, (UnitMoved, SurfaceChanged))
    ]
    assert seq == [
        ("UnitMoved", Pos(x=4, y=3)),
        ("SurfaceChanged", Pos(x=3, y=3)),
        ("UnitMoved", Pos(x=5, y=3)),
        ("SurfaceChanged", Pos(x=4, y=3)),
    ]
    changed = of(result, SurfaceChanged)
    assert all(
        (c.before, c.after, c.cause, c.remaining) == (Surface.NONE, Surface.ICE, "trail", 1)
        for c in changed
    )


def test_trail_owner_is_not_serialized_when_empty() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    before = state_to_json(state)
    assert "surface_trail" not in before
    after = _walk(state, (3, 3), (4, 3)).state
    text = state_to_json(after)
    assert '"surface_trail":"unit_0001"' in text.replace(" ", "")
    assert state_from_json(text).tile(3, 3).surface_trail == U1


def test_tiles_with_a_surface_stay_as_they_are() -> None:
    state = _frost(race_state(None, foes=((6, 6),), surfaces=[(4, 3, "water"), (5, 3, "oil")]))
    result = _walk(state, (3, 3), (4, 3), (5, 3), (6, 3))
    after = result.state
    assert after.tile(4, 3).surface is Surface.WATER  # 不結冰、不觸發互動
    assert after.tile(5, 3).surface is Surface.OIL
    assert after.tile(4, 3).surface_trail is None
    assert _ice(after) == {(3, 3): U1}
    assert [c.pos for c in of(result, SurfaceChanged)] == [Pos(x=3, y=3)]


def test_no_ice_under_an_ally_walked_through() -> None:
    state = _frost(race_state(None, foes=((6, 6),), allies=((4, 3),)))
    result = _walk(state, (3, 3), (4, 3), (5, 3), (6, 3))
    assert _ice(result.state) == {(3, 3): U1, (5, 3): U1}


def test_trail_ice_vanishes_when_it_expires_instead_of_turning_to_water() -> None:
    state = _frost(race_state(None, foes=((6, 6),), surfaces=[(0, 0, "ice")]))
    # 對照：一般的冰（技能產生、持續 1）到期變成水
    state = run_effects(
        state, [CreateSurfaceEffect(pos=(1, 0), surface=Surface.ICE, duration=1)]
    ).state
    state = _walk(state, (3, 3), (4, 3)).state
    start_round = state.round
    while state.round == start_round:
        state = end_turn(state).state
    assert state.tile(3, 3).surface is Surface.NONE
    assert state.tile(3, 3).surface_trail is None
    assert state.tile(1, 0).surface is Surface.WATER


# ---------------------------------------------------------------------------
# 滑倒：自己的冰不滑、別人照常
# ---------------------------------------------------------------------------


def _slide_checks(result: Any, unit: UnitId) -> list[CheckRolled]:
    return [e for e in of(result, CheckRolled) if e.unit_id == unit and e.slide]


def test_owner_does_not_slip_on_own_trail_ice() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state  # (3,3)、(4,3) 結冰
    state = give_turn(state, U1)
    state.units[U1].move_points = 6
    result = _walk(with_rolls(state, FAIL), (5, 3), (4, 3), (3, 3), (2, 3))
    assert not _slide_checks(result, U1)
    assert result.state.units[U1].xy == (2, 3)
    assert not result.state.units[U1].has_status("prone")


def test_others_slip_on_the_trail_ice() -> None:
    state = _frost(race_state(None, foes=((4, 5),)))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state  # (3,3)、(4,3) 結冰
    foe = next(u.id for u in state.units.values() if u.team is Team.ENEMY)
    state = give_turn(state, foe)
    result = _walk(with_rolls(state, FAIL), (4, 5), (4, 4), (4, 3), (3, 3), unit=foe)
    assert len(_slide_checks(result, foe)) == 1
    assert result.state.units[foe].has_status("prone")


def test_owner_slips_on_ice_made_by_others() -> None:
    state = _frost(race_state(None, foes=((6, 6),), surfaces=[(4, 3, "ice")]))
    result = _walk(with_rolls(state, FAIL), (3, 3), (4, 3), (5, 3))
    assert len(_slide_checks(result, U1)) == 1


def test_own_trail_then_others_ice_rolls_on_the_others_ice() -> None:
    state = _frost(race_state(None, foes=((6, 6),), surfaces=[(2, 3, "ice")]))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state  # (3,3)、(4,3) 是自己的冰
    state = give_turn(state, U1)
    state.units[U1].move_points = 6
    result = _walk(with_rolls(state, [(20, 20)]), (5, 3), (4, 3), (3, 3), (2, 3), (1, 3))
    checks = _slide_checks(result, U1)
    assert len(checks) == 1  # 只在 (2,3) 別人的冰上擲
    assert result.state.units[U1].xy == (1, 3)


def test_pushed_onto_own_trail_ice_does_not_roll() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state
    pushed = run_effects(
        with_rolls(state, FAIL), [PushEffect(target_id=U1, direction=(-1, 0), distance=1)]
    )
    assert pushed.state.units[U1].xy == (4, 3)
    assert not [e for e in of(pushed, CheckRolled) if e.unit_id == U1]
    assert not pushed.state.units[U1].has_status("prone")


def test_replacing_the_surface_clears_the_trail_mark() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    state = _walk(state, (3, 3), (4, 3)).state
    state = run_effects(
        state, [CreateSurfaceEffect(pos=(3, 3), surface=Surface.ICE, duration=3)]
    ).state
    assert state.tile(3, 3).surface is Surface.ICE
    assert state.tile(3, 3).surface_trail is None  # 別人的冰：持有者照常檢定、到期變水


# ---------------------------------------------------------------------------
# 哪些移動算：衝刺、直線衝撞算；被推、跳躍不算
# ---------------------------------------------------------------------------


def test_dash_skill_leaves_ice(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena(charge_skill(DASH, HIT))
    wear(state, {"feet": [FROST]})
    result = use(state, "skill_t_move", target_id=U2)
    assert result.state.units[U1].xy == (3, 3)
    assert _ice(result.state) == {(0, 3): U1, (1, 3): U1, (2, 3): U1}


def test_charge_through_leaves_ice(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = charge_arena(charge_through_skill(PRONE_HIT))
    wear(state, {"feet": [FROST]})
    result = resolve(
        state, UseSkill(unit_id=U1, skill_id="skill_t_charge", target_pos=Pos(x=3, y=3))
    )
    assert result.state.units[U1].xy == (3, 3)
    assert _ice(result.state) == {(0, 3): U1, (1, 3): U1, (2, 3): U1}


def test_being_pushed_leaves_no_ice() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    pushed = run_effects(state, [PushEffect(target_id=U1, direction=(1, 0), distance=2)])
    assert pushed.state.units[U1].xy == (5, 3)
    assert _ice(pushed.state) == {}


def test_vault_leaves_no_ice() -> None:
    heights = "\n".join(
        ["0000000", "0000000", "0000000", "0002000", "0000000", "0000000", "0000000"]
    )
    state = _frost(race_state(None, foes=((6, 6),), me=(2, 3), heights=heights))
    result = resolve(state, Vault(unit_id=U1, dest=Pos(x=3, y=3)))
    assert result.state.units[U1].xy == (3, 3)
    assert _ice(result.state) == {}


# ---------------------------------------------------------------------------
# 預覽、AI、確定性
# ---------------------------------------------------------------------------


def test_preview_shows_trail_ice_and_marks_it_no_slip_for_the_owner() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state
    state = give_turn(state, U1)
    state.units[U1].move_points = 6
    p = preview_path(state, U1, path=_path((5, 3), (4, 3), (3, 3), (2, 3)))
    assert [s.surface for s in p.steps if s.pos in ((4, 3), (3, 3))] == [Surface.ICE] * 2
    (run,) = p.slip_runs
    assert run.immune and (run.start, run.end) == (1, 2)
    assert p.stop == (2, 3)


def test_preview_for_someone_else_shows_the_slip_risk() -> None:
    state = _frost(race_state(None, foes=((4, 5),)))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state
    foe = next(u.id for u in state.units.values() if u.team is Team.ENEMY)
    state = give_turn(state, foe)
    p = preview_path(state, foe, path=_path((4, 5), (4, 4), (4, 3)))
    (run,) = p.slip_runs
    assert not run.immune and run.status_id == "prone"


def test_ai_slide_risk_sees_trail_ice_for_others_only() -> None:
    state = _frost(race_state(None, foes=((4, 5),)))
    state = _walk(state, (3, 3), (4, 3), (5, 3)).state
    foe = state.units[next(u.id for u in state.units.values() if u.team is Team.ENEMY)]
    assert path_slide_risks(state, foe, ((4, 5), (4, 4), (4, 3)))
    me = state.units[U1]
    assert not path_slide_risks(state, me, ((5, 3), (4, 3), (3, 3)))


def _frost_setup() -> BattleSetup:
    """英雄穿三種新地形規則（霜行、攀岩、表面傷害免疫）。"""
    lib = library()
    setup = build_setup(lib, "open_plain", ["hero_fighter"], ["bandit", "bandit"])
    hero = setup.units[0]
    climb = terrain("affix_t_climb", "上 1 層不多花移動", rule="flat_climb", amount=1)
    proof = terrain(
        "affix_t_poison_proof",
        "毒表面不會傷害你",
        rule="surface_damage_immunity",
        surfaces=["poison"],
    )
    gear = loadout({"feet": [FROST], "body": [climb], "head": [proof]})
    hero = hero.model_copy(update={"equipment": gear})
    return setup.model_copy(update={"units": (hero, *setup.units[1:])})


def test_battle_with_the_new_terrain_rules_replays_identically() -> None:
    setup = _frost_setup()
    first = run_battle(setup, 3)
    assert any(isinstance(e, SurfaceChanged) and e.cause == "trail" for e in first.events)
    second = run_battle(setup, 3)
    dump = [e.model_dump() for e in first.events]
    assert dump == [e.model_dump() for e in second.events]
    again = replay(setup, 3, first.actions)
    assert [e.model_dump() for e in again.events] == dump
    assert state_to_json(again.state) == state_to_json(first.state)
