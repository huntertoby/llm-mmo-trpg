"""勝利條件（全滅、撤離、守點，含失敗條件）與部署階段（6.1-10、6.1-11、6.2-4）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.maps import Objective
from trpg.engine import (
    BattleSetupError,
    BattleState,
    EndTurn,
    Move,
    build_setup,
    deploy_allies,
    deployment_tiles,
    legal_actions,
    resolve,
    start_battle,
)
from trpg.engine.effects import DamageEffect, run_effects
from trpg.engine.events import UnitEscaped
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _end_all(state: BattleState, rounds: int = 1) -> BattleState:
    target = state.round + rounds
    while state.round < target and not state.ended:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    return state


def _escape_state(*allies: tuple[int, int]) -> BattleState:
    m = make_map(
        "000000\n000000",
        objective={"kind": "escape", "rounds": 2, "tiles": [[5, 0]]},
        ally=list(allies),
        enemy=[(0, 1)],
    )
    spawns = [spawn(Team.ALLY, a, no_reactions("hero_fighter")) for a in allies]
    spawns.append(spawn(Team.ENEMY, (0, 1), no_reactions()))
    return make_state(m, spawns)


def test_escape_victory_when_all_allies_reach_exit() -> None:
    state = give_turn(_escape_state((2, 0), (1, 0)), "unit_0001")
    result = resolve(state, Move(unit_id=U1, path=(P(2, 0), P(3, 0), P(4, 0), P(5, 0))))
    assert any(isinstance(e, UnitEscaped) and e.unit_id == U1 for e in result.events)
    s = result.state
    assert s.units[U1].escaped and not s.units[U1].alive and U1 not in s.turn_order
    assert s.unit_at(5, 0) is None  # 離開戰場，出口格空出來
    assert not s.ended  # 還有一位我方在戰場上
    s = give_turn(s, "unit_0002")
    s = resolve(s, Move(unit_id=U2, path=(P(1, 0), P(2, 0), P(3, 0), P(4, 0), P(5, 0)))).state
    assert s.ended and s.winner is Team.ALLY and s.end_reason == "escaped"


def test_escape_partial_survivors_still_win() -> None:
    state = give_turn(_escape_state((4, 0), (1, 0)), "unit_0001")
    s = resolve(state, Move(unit_id=U1, path=(P(4, 0), P(5, 0)))).state
    s = run_effects(s, [DamageEffect(target_id=U2, mode="lethal")]).state
    assert s.ended and s.winner is Team.ALLY and s.end_reason == "escaped"


def test_escape_timeout_is_a_defeat() -> None:
    state = _escape_state((2, 0))
    s = _end_all(state, rounds=1)
    assert not s.ended and s.round == 2
    s = _end_all(s, rounds=1)
    assert s.ended and s.winner is Team.ENEMY and s.end_reason == "escape_failed"


def test_enemy_cannot_escape() -> None:
    state = _escape_state((0, 0))
    s = give_turn(state, "unit_0002")
    s.units[U2].pos = P(4, 1)
    s = resolve(s, Move(unit_id=U2, path=(P(4, 1), P(5, 1), P(5, 0)))).state
    assert not s.units[U2].escaped and s.units[U2].pos == P(5, 0)


def _defend_state() -> BattleState:
    m = make_map(
        "00000",
        objective={"kind": "defend", "rounds": 2, "tiles": [[2, 0]]},
        ally=[(0, 0)],
        enemy=[(4, 0)],
    )
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (4, 0), no_reactions()),
        ],
    )


def test_defend_victory_after_rounds() -> None:
    s = _end_all(_defend_state(), rounds=1)
    assert not s.ended
    s = _end_all(s, rounds=1)
    assert s.ended and s.winner is Team.ALLY and s.end_reason == "defended"


def test_defend_point_lost_at_round_end() -> None:
    state = give_turn(_defend_state(), "unit_0002")
    s = resolve(state, Move(unit_id=U2, path=(P(4, 0), P(3, 0), P(2, 0)))).state
    assert not s.ended  # 只在一輪結束時判定
    s = _end_all(s, rounds=1)
    assert s.ended and s.winner is Team.ENEMY and s.end_reason == "point_lost"


def test_eliminating_enemies_wins_in_any_mode() -> None:
    for state in (_defend_state(), _escape_state((0, 0))):
        s = run_effects(
            state, [DamageEffect(target_id=U2 if len(state.units) == 2 else U3, mode="lethal")]
        ).state
        assert s.ended and s.winner is Team.ALLY and s.end_reason == "eliminate"


def test_allies_wiped_out_is_a_defeat() -> None:
    s = run_effects(_defend_state(), [DamageEffect(target_id=U1, mode="lethal")]).state
    assert s.ended and s.winner is Team.ENEMY and s.end_reason == "eliminate"


def test_setup_objective_overrides_map() -> None:
    m = make_map("00000", ally=[(0, 0)], enemy=[(4, 0)])
    setup = make_setup(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (4, 0))])
    setup = setup.model_copy(
        update={"objective": Objective(kind="defend", rounds=1, tiles=((2, 0),))}
    )
    s = start_battle(setup, 0)
    assert s.objective.kind == "defend"
    s = _end_all(s)
    assert s.end_reason == "defended"


# ---------------------------------------------------------------------------
# 部署
# ---------------------------------------------------------------------------


def test_deploy_allies_in_start_zone() -> None:
    setup = build_setup(library(), "test_heights_8x8", ["hero_fighter", "hero_archer"], ["bandit"])
    assert deployment_tiles(setup) == [(0, 6), (1, 6), (0, 7), (1, 7)]
    deployed = deploy_allies(setup, [(1, 7)])
    state = start_battle(deployed, 1)
    assert state.units[U1].pos == P(1, 7)
    assert state.units[U2].pos == P(0, 6)  # 其餘依起始區順序自動排列（跳過已用的格子）
    auto = start_battle(setup, 1)
    assert [auto.units[u].pos for u in (U1, U2)] == [P(0, 6), P(1, 6)]


@pytest.mark.parametrize(
    ("positions", "fragment"),
    [
        ([(5, 5)], "不在我方起始區"),
        ([(0, 6), (0, 6)], "重複"),
        ([(0, 6), (1, 6), (0, 7)], "過多"),
    ],
)
def test_deploy_rejects_bad_positions(positions: list[tuple[int, int]], fragment: str) -> None:
    setup = build_setup(library(), "test_heights_8x8", ["hero_fighter", "hero_archer"], ["bandit"])
    with pytest.raises(BattleSetupError, match=fragment):
        deploy_allies(setup, positions)


def test_legal_actions_after_escape_skip_escaped_units() -> None:
    state = give_turn(_escape_state((4, 0), (0, 0)), "unit_0001")
    s = resolve(state, Move(unit_id=U1, path=(P(4, 0), P(5, 0)))).state
    assert s.active_unit is not None and s.active_unit != U1
    assert all(a.unit_id == s.active_unit for a in legal_actions(s))
