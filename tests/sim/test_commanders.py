"""腳本指揮官與可 pickle 的 policy factory（Phase 2C-2 4.4；2C-1 待決 #9）。"""

from __future__ import annotations

import pickle

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn
from trpg.engine.ai.orders import FocusTarget, HoldPosition, Protect, UseEnvironment
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId
from trpg.sim.batch import map_spec, run_batch, run_batches
from trpg.sim.commanders import (
    COMMANDER_FACTORIES,
    COMMANDER_IDS,
    CommandedPolicyFactory,
    FocusLowestHp,
    HoldStart,
    ProtectWeakest,
    UseEnv,
)

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))


def _state() -> BattleState:
    m = make_map("\n".join(["0" * 8] * 4), ally=[(0, 1)], enemy=[(7, 1)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 1), "hero_fighter"),
            spawn(Team.ALLY, (0, 2), "hero_archer"),
            spawn(Team.ENEMY, (7, 1), "bandit"),
            spawn(Team.ENEMY, (7, 2), "bandit_archer"),
        ],
    )
    return give_turn(state, U1)


def test_focus_lowest_hp_picks_the_weakest_visible_enemy() -> None:
    state = _state()
    state.units[U4].hp = 3
    orders = FocusLowestHp()(state, Team.ALLY)
    assert orders is not None and orders.team_orders == (FocusTarget(target=U4),)
    state.units[U4].hp = 0
    state.units[U4].downed = True
    orders = FocusLowestHp()(state, Team.ALLY)
    assert orders is not None and orders.team_orders == (FocusTarget(target=U3),)
    # 敵方看我方：HP 最低的是 U2（弓手）
    state.units[U2].hp = 1
    enemy_view = FocusLowestHp()(state, Team.ENEMY)
    assert enemy_view is not None and enemy_view.team_orders == (FocusTarget(target=U2),)


def test_protect_weakest_picks_the_lowest_hp_ratio_ally() -> None:
    state = _state()
    state.units[U2].hp = 4
    orders = ProtectWeakest()(state, Team.ALLY)
    assert orders is not None and orders.team_orders == (Protect(ward=U2),)
    state.units[U4].downed = True  # 敵方只剩一人：沒有可保護的友方
    state.units[U4].hp = 0
    empty = ProtectWeakest()(state, Team.ENEMY)
    assert empty is not None and empty.empty


def test_hold_start_remembers_the_first_positions() -> None:
    state = _state()
    commander = HoldStart()
    first = commander(state, Team.ALLY)
    assert first is not None
    assert first.unit_orders == {
        U1: (HoldPosition(at=(0, 1), radius=1),),
        U2: (HoldPosition(at=(0, 2), radius=1),),
    }
    moved = state.clone()
    moved.units[U1].pos = moved.units[U1].pos.model_copy(update={"x": 4})
    second = commander(moved, Team.ALLY)
    assert second is not None and second.unit_orders[U1] == first.unit_orders[U1]
    moved.units[U2].downed = True
    third = commander(moved, Team.ALLY)
    assert third is not None and set(third.unit_orders) == {U1}


def test_use_env_orders_the_whole_team() -> None:
    orders = UseEnv()(_state(), Team.ENEMY)
    assert orders is not None and orders.team_orders == (UseEnvironment(),)


def test_registry_and_pickling() -> None:
    assert set(COMMANDER_IDS) == {"focus_lowest_hp", "protect_weakest", "hold_start", "use_env"}
    factory = CommandedPolicyFactory(library().ai_profiles, "hold_start", "focus_lowest_hp")
    restored = pickle.loads(pickle.dumps(factory))
    assert restored == factory
    first, second = factory(), factory()
    assert first is not second  # 每場新建
    for commander_id in COMMANDER_FACTORIES:
        assert pickle.loads(pickle.dumps(COMMANDER_FACTORIES[commander_id]))
    with pytest.raises(ValueError, match="未知的指揮官"):
        CommandedPolicyFactory(library().ai_profiles, "nope")


def test_commanded_batch_is_deterministic_and_jobs_independent() -> None:
    lib = library()
    spec = map_spec(lib, "oil_depot", range(3), enemy_commander="focus_lowest_hp")
    assert isinstance(spec.policy_factory, CommandedPolicyFactory)
    one = run_batch(spec)
    again = run_batch(spec)
    parallel = run_batches([spec], jobs=2)[0]
    assert one == again == parallel
    assert all(a.kind != "exception" for a in one.anomalies)


def test_commanders_change_the_battle() -> None:
    """指揮官確實影響結果（同一種子、不同指揮官 → 動作不同）。"""
    lib = library()
    plain = run_batch(map_spec(lib, "swamp", range(6)))
    commanded = run_batch(map_spec(lib, "swamp", range(6), enemy_commander="focus_lowest_hp"))
    assert plain != commanded
