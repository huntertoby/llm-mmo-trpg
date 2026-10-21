"""撤離與守點的 AI 評分（Phase 3-22）：敵方搶點／攔截出口路線，我方朝出口、守在點附近。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from trpg.content.environment import AiProfileTable, AiWeights
from trpg.engine import Move
from trpg.engine.ai.objective import hold_guard_bonus, objective_cost
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def _weights(**over: int) -> AiWeights:
    return AiWeights(objective=8, **over)


def _profiles(**weights: int) -> AiProfileTable:
    """目前的 AI 設定；``weights`` 覆寫所有行為模式的同名權重。"""
    raw: dict[str, Any] = library().ai_profiles.model_dump(mode="json")
    for profile in raw["profiles"]:
        profile["weights"].update(weights)
    return AiProfileTable.model_validate(raw)


def _state(
    objective: dict[str, object] | None, ally: tuple[int, int], enemy: tuple[int, int]
) -> BattleState:
    rows = "\n".join("0" * 10 for _ in range(3))
    m = make_map(rows, ally=[ally], enemy=[enemy], objective=objective)
    return make_state(
        m,
        [
            spawn(Team.ALLY, ally, no_reactions("hero_fighter")),
            spawn(Team.ENEMY, enemy, no_reactions()),
        ],
    )


def _dest(state: BattleState, unit: UnitId, profiles: AiProfileTable) -> tuple[int, int]:
    """AI 這回合的移動目的地（不移動時為原地）。"""
    action = UtilityAI(profiles, override="brute")(give_turn(state, unit))
    if isinstance(action, Move):
        return action.dest.x, action.dest.y
    return state.units[unit].xy


def test_cost_is_zero_without_an_objective_or_weights() -> None:
    state = _state(None, (0, 0), (9, 2))
    assert objective_cost(state, state.units[U1], _weights(rush_exit=6)) == 0
    escape = {"kind": "escape", "rounds": 5, "tiles": [[9, 0]]}
    state = _state(escape, (0, 0), (9, 2))
    assert objective_cost(state, state.units[U2], AiWeights()) == 0  # 敵方且 intercept = 0


def test_escape_allies_head_for_the_exit_and_enemies_intercept_it() -> None:
    escape = {"kind": "escape", "rounds": 5, "tiles": [[9, 0]]}
    state = _state(escape, (3, 0), (6, 2))
    ally, enemy = state.units[U1], state.units[U2]
    w = _weights(rush_exit=6, intercept=8)
    assert objective_cost(state, ally, w) == (8 + 6) * 6
    assert objective_cost(state, enemy, w) == 8 * (3 + 2)  # 敵方不吃 objective / rush_exit


def test_defend_enemies_contest_and_allies_hold_near_the_point() -> None:
    defend = {"kind": "defend", "rounds": 5, "tiles": [[2, 1]]}
    state = _state(defend, (7, 1), (9, 1))
    w = _weights(contest=4, hold_point=10, hold_radius=2)
    assert objective_cost(state, state.units[U2], w) == (8 + 4) * 7
    assert objective_cost(state, state.units[U1], w) == 8 * 5 + 10 * (5 - 2)
    near = _state(defend, (3, 1), (9, 1))
    assert objective_cost(near, near.units[U1], w) == 8 * 1  # 半徑內不扣 hold_point


def test_hold_guard_only_near_the_point_with_a_threat() -> None:
    defend = {"kind": "defend", "rounds": 5, "tiles": [[2, 1]]}
    w = _weights(hold_guard=4, hold_radius=2)
    near = _state(defend, (3, 1), (7, 1))
    assert hold_guard_bonus(near, near.units[U1], w) == 4
    far = _state(defend, (7, 2), (9, 1))
    assert hold_guard_bonus(far, far.units[U1], w) == 0  # 離守點太遠
    calm = _state(defend, (3, 1), (9, 2))
    assert hold_guard_bonus(calm, calm.units[U1], w) == 0  # 敵人不在 6 格內
    assert hold_guard_bonus(near, near.units[U2], w) == 0  # 敵方不守
    plain = _state(None, (3, 1), (7, 1))
    assert hold_guard_bonus(plain, plain.units[U1], w) == 0  # 不是守點戰


def test_enemy_ai_moves_toward_the_exit_with_intercept_weight() -> None:
    """撤離戰：敵方在 intercept 權重下比沒有時更靠近出口（出口與我方在不同方向）。"""
    escape = {"kind": "escape", "rounds": 5, "tiles": [[9, 2]]}
    state = _state(escape, (0, 0), (9, 0))
    exit_xy = (9, 2)
    with_weight = _dest(state, U2, _profiles(intercept=8, approach=0))
    without = _dest(state, U2, _profiles(intercept=0, approach=0))
    assert manhattan(with_weight, exit_xy) < manhattan(without, exit_xy)


def test_ally_ai_moves_toward_the_exit() -> None:
    escape = {"kind": "escape", "rounds": 5, "tiles": [[0, 2]]}
    state = _state(escape, (5, 0), (9, 0))
    dest = _dest(state, U1, _profiles(rush_exit=6))
    assert manhattan(dest, (0, 2)) < manhattan((5, 0), (0, 2))


def test_defend_enemy_ai_rushes_the_point() -> None:
    defend = {"kind": "defend", "rounds": 5, "tiles": [[0, 2]]}
    state = _state(defend, (0, 0), (9, 0))
    dest = _dest(state, U2, _profiles(contest=4, approach=0))
    assert manhattan(dest, (0, 2)) < manhattan((9, 0), (0, 2))
