"""回合流程、AP、先攻、勝負（驗收條件 9 與 4.4 節）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import give_turn, make_map, make_setup, make_state, spawn, template
from trpg.engine import (
    Attack,
    BattleSetupError,
    BattleState,
    Defend,
    EndTurn,
    Move,
    begin_battle,
    legal_actions,
    resolve,
    start_battle,
)
from trpg.engine.events import (
    BattleEnded,
    InitiativeRolled,
    InitiativeTieBroken,
    RoundEnded,
    RoundStarted,
    StatusRemoved,
    TurnStarted,
    UnitDowned,
)
from trpg.engine.state import UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def _duel(**core: Any) -> BattleState:
    m = make_map("000\n000")
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", max_hp=999)),
            spawn(Team.ENEMY, (1, 0), template("bandit", max_hp=999)),
        ],
        **core,
    )


def _end(state: BattleState) -> BattleState:
    assert state.active_unit is not None
    return resolve(state, EndTurn(unit_id=state.active_unit)).state


def _next_turn_of(state: BattleState, unit_id: UnitId) -> BattleState:
    state = _end(state)
    while state.active_unit != unit_id:
        state = _end(state)
    return state


def _attack(state: BattleState) -> BattleState:
    assert state.active_unit is not None
    target = U2 if state.active_unit == U1 else U1
    return resolve(state, Attack(unit_id=state.active_unit, target_id=target)).state


def test_ap_per_turn_and_carry() -> None:
    state = _duel()
    first = state.active_unit
    assert first is not None
    assert state.units[first].ap == 3
    # 用 2 AP，保留 1 → 下回合 4
    s = _attack(_attack(state))
    assert s.units[first].ap == 1
    s = _next_turn_of(s, first)
    assert s.units[first].ap == 4
    # 一點都不用：最多只保留 1 → 下回合 3 + 1 = 4
    s = _next_turn_of(s, first)
    assert s.units[first].ap == 4
    # 用光 → 下回合 3
    for _ in range(4):
        s = _attack(s)
    s = _next_turn_of(s, first)
    assert s.units[first].ap == 3


def test_ap_shortage_is_rejected_with_reason() -> None:
    state = _duel()
    for _ in range(3):
        state = _attack(state)
    assert state.active_unit is not None
    with pytest.raises(IllegalActionError, match="AP 不足：需要 1，剩餘 0"):
        _attack(state)
    with pytest.raises(IllegalActionError, match="AP 不足：需要 1，剩餘 0"):
        resolve(state, Defend(unit_id=state.active_unit))
    assert all(a.type in {"move", "end_turn"} for a in legal_actions(state))


def test_ap_values_come_from_rules() -> None:
    state = _duel(ap_per_turn=5, ap_carry_max=2)
    first = state.active_unit
    assert first is not None
    assert state.units[first].ap == 5
    s = _next_turn_of(state, first)
    assert s.units[first].ap == 7


def test_not_your_turn_and_battle_over() -> None:
    state = _duel()
    other = U2 if state.active_unit == U1 else U1
    with pytest.raises(IllegalActionError, match="的回合，不是"):
        resolve(state, EndTurn(unit_id=other))
    ended = state.clone()
    ended.ended = True
    with pytest.raises(IllegalActionError, match="戰鬥已結束"):
        resolve(ended, EndTurn(unit_id=U1))
    assert legal_actions(ended) == []


def test_initiative_order_and_ties() -> None:
    """先攻：總值高者先；同值比敏捷；仍相同以戰鬥亂數決定並寫入事件（PM 決定，1B）。"""
    m = make_map("0000\n0000")
    spawns = [
        spawn(Team.ALLY, (0, 0), template("hero_fighter", attributes={"dex": 16})),
        spawn(Team.ALLY, (0, 1), template("hero_fighter", attributes={"dex": 9})),
        spawn(Team.ENEMY, (3, 0), template("bandit", attributes={"dex": 10})),
        spawn(Team.ENEMY, (3, 1), template("bandit", attributes={"dex": 10})),
        spawn(Team.ENEMY, (2, 1), template("bandit", attributes={"dex": 11})),
    ]
    setup = make_setup(m, spawns)
    saw_dex_tiebreak = False
    tie_orders: set[tuple[UnitId, ...]] = set()
    for seed in range(120):
        result = begin_battle(setup, seed)
        rolled = {e.unit_id: e for e in result.events if isinstance(e, InitiativeRolled)}
        assert [rolled[u].modifier for u in sorted(rolled)] == [3, -1, 0, 0, 0]
        for uid, ev in rolled.items():
            assert ev.total == ev.roll + ev.modifier == result.state.units[uid].initiative
        order = result.state.turn_order
        units = result.state.units

        def key(u: UnitId, units: dict[UnitId, UnitState] = units) -> tuple[int, int]:
            return (-units[u].initiative, -units[u].attributes[Attribute.DEX])

        assert order == sorted(order, key=key)  # 總值 → 敏捷（穩定排序保留亂數決定的部分）
        ties = [e for e in result.events if isinstance(e, InitiativeTieBroken)]
        for tie in ties:
            members = [u for u in order if key(u) == (-tie.total, -tie.dex)]
            assert tuple(members) == tie.order and len(members) >= 2
            tie_orders.add(tie.order)
        totals = [units[u].initiative for u in order]
        dex = [units[u].attributes[Attribute.DEX] for u in order]
        saw_dex_tiebreak = saw_dex_tiebreak or any(
            totals[i] == totals[i + 1] and dex[i] > dex[i + 1] for i in range(len(order) - 1)
        )
    assert saw_dex_tiebreak
    # 兩個敏捷 10 的盜賊同值時，兩種順序都出現過（由亂數決定，而非 ID）
    pair = {UnitId("unit_0003"), UnitId("unit_0004")}
    assert {o for o in tie_orders if set(o) == pair} == {
        (UnitId("unit_0003"), UnitId("unit_0004")),
        (UnitId("unit_0004"), UnitId("unit_0003")),
    }


def test_initiative_tie_is_deterministic() -> None:
    m = make_map("0000\n0000")
    spawns = [spawn(Team.ALLY, (0, 0)), spawn(Team.ALLY, (0, 1)), spawn(Team.ENEMY, (3, 0))]
    setup = make_setup(m, spawns)
    for seed in range(20):
        assert begin_battle(setup, seed).state.turn_order == (
            begin_battle(setup, seed).state.turn_order
        )


def test_rounds_advance_after_everyone_acts() -> None:
    state = _duel()
    assert state.round == 1
    s = _end(state)
    assert s.round == 1
    result = resolve(s, EndTurn(unit_id=s.active_unit))  # type: ignore[arg-type]
    types = [type(e) for e in result.events]
    assert RoundEnded in types and RoundStarted in types
    assert result.state.round == 2
    assert result.state.active_unit == state.active_unit


def test_round_limit_draw() -> None:
    m = make_map("000")
    setup = make_setup(
        m,
        [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (2, 0), "bandit")],
        max_rounds=2,
    )
    s = start_battle(setup, 1)
    for _ in range(4):
        s = _end(s)
    assert s.ended and s.winner is None and s.end_reason == "round_limit" and s.round == 2
    assert legal_actions(s) == []


def test_defending_expires_at_own_turn_start() -> None:
    state = _duel()
    me = state.active_unit
    assert me is not None
    s = resolve(state, Defend(unit_id=me)).state
    assert s.units[me].has_status("defending")
    s = _end(s)
    assert s.units[me].has_status("defending")  # 對方回合中仍然有效
    result = resolve(s, EndTurn(unit_id=s.active_unit))  # type: ignore[arg-type]
    assert not result.state.units[me].has_status("defending")
    started = [i for i, e in enumerate(result.events) if isinstance(e, TurnStarted)]
    removed = [i for i, e in enumerate(result.events) if isinstance(e, StatusRemoved)]
    assert started and removed and started[0] < removed[0]


def test_elimination_victory() -> None:
    m = make_map("000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", attributes={"str": 300})),
            spawn(Team.ENEMY, (1, 0), template("bandit", max_hp=1)),
        ],
    )
    state = give_turn(state, "unit_0001")
    for _ in range(3):
        if state.ended:
            break
        state = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert state.ended and state.winner is Team.ALLY and state.end_reason == "eliminate"
    assert state.active_unit is None and U2 not in state.turn_order


def test_active_unit_dying_passes_turn() -> None:
    m = make_map("2000\n0000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), "hero_fighter"),
            spawn(Team.ALLY, (0, 1), "hero_mage"),
            spawn(Team.ENEMY, (3, 1), "bandit"),
        ],
    )
    state = give_turn(state, "unit_0001")
    state.units[U1].hp = 1
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=0, y=0), Pos(x=1, y=0), Pos(x=2, y=0))))
    assert any(isinstance(e, UnitDowned) for e in result.events)
    s = result.state
    assert s.units[U1].pos == Pos(x=1, y=0)  # 倒下後不再繼續走
    assert s.active_unit is not None and s.active_unit != U1 and not s.ended
    assert any(isinstance(e, TurnStarted) for e in result.events)


def test_setup_errors() -> None:
    m = make_map("000", ".x.")
    with pytest.raises(BattleSetupError, match="雙方"):
        start_battle(make_setup(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ALLY, (2, 0))]), 0)
    with pytest.raises(BattleSetupError, match="不可站立"):
        start_battle(make_setup(m, [spawn(Team.ALLY, (1, 0)), spawn(Team.ENEMY, (2, 0))]), 0)
    with pytest.raises(BattleSetupError, match="重複"):
        start_battle(make_setup(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (0, 0))]), 0)


def test_battle_ended_event_once() -> None:
    m = make_map("000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", attributes={"str": 300})),
            spawn(Team.ENEMY, (1, 0), template("bandit", max_hp=1)),
        ],
    )
    state = give_turn(state, "unit_0001")
    events = []
    while not state.ended:
        r = resolve(state, Attack(unit_id=U1, target_id=U2))
        state = r.state
        events += r.events
    assert sum(isinstance(e, BattleEnded) for e in events) == 1
