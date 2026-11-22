"""E3：地形規則「攀岩」（``flat_climb``，08 8.29 E3 第 5 點）：上 1 層當平地走、只花 1 點；攀跳
（上 2 層）照舊。走路預覽與 AI 找路都經過 ``unit_step_cost``。"""

from __future__ import annotations

from tests.engine.helpers import give_turn
from tests.engine.race_helpers import U1, race_state
from tests.engine.test_unit_rules_e2 import terrain, wear
from trpg.engine import BattleState, Move, Vault, legal_actions, resolve
from trpg.engine.path_preview import preview_path
from trpg.engine.rules.movement import path_map, unit_step_cost
from trpg.engine.rules.race import flat_climb_height
from trpg.shared.types import Pos

CLIMB = terrain("affix_t_climb", "上 1 層不多花移動", rule="flat_climb", amount=1)
# x=3 起每格高 1 層：0 1 2 3（三個 1 層台階），(3,5) 高 2 層（攀跳）
STAIRS = "\n".join(["0000000", "0000000", "0000000", "0000123", "0000000", "0002000", "0000000"])


def _state(*, climb: bool, move: int = 3, me: tuple[int, int] = (3, 3)) -> BattleState:
    state = race_state(None, foes=((0, 6),), heights=STAIRS, me=me)
    if climb:
        wear(state, {"feet": [CLIMB]})
    state = give_turn(state, U1)
    state.units[U1].move_points = move
    return state


def _path(*xys: tuple[int, int]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in xys)


def test_climb_rule_makes_one_layer_cost_one() -> None:
    plain, climber = _state(climb=False), _state(climb=True)
    assert flat_climb_height(plain.ruleset, plain.units[U1]) == 0
    assert flat_climb_height(climber.ruleset, climber.units[U1]) == 1
    assert unit_step_cost(plain, plain.units[U1], (3, 3), (4, 3)) == 2
    assert unit_step_cost(climber, climber.units[U1], (3, 3), (4, 3)) == 1
    assert unit_step_cost(climber, climber.units[U1], (4, 3), (3, 3)) == 1  # 下坡照舊


def test_two_layers_still_need_a_vault() -> None:
    climber = _state(climb=True, me=(3, 4))
    assert unit_step_cost(climber, climber.units[U1], (3, 4), (3, 5)) is None
    vaults = [a for a in legal_actions(climber) if isinstance(a, Vault)]
    assert Pos(x=3, y=5) in [a.dest for a in vaults]


def test_three_steps_up_with_three_points() -> None:
    path = _path((3, 3), (4, 3), (5, 3), (6, 3))
    walked = resolve(_state(climb=True), Move(unit_id=U1, path=path))
    assert walked.state.units[U1].xy == (6, 3)
    assert walked.state.units[U1].move_points == 0


def test_preview_and_pathing_see_the_climb() -> None:
    path = _path((3, 3), (4, 3), (5, 3), (6, 3))
    climber = preview_path(_state(climb=True), U1, path=path)
    plain = preview_path(_state(climb=False), U1, path=path)
    assert climber.reachable and climber.legal_length == 4
    assert not plain.reachable and plain.legal_length < 4
    climber_state, plain_state = _state(climb=True), _state(climb=False)
    reach = path_map(climber_state, climber_state.units[U1], 3)
    assert (6, 3) in reach.cost
    assert (6, 3) not in path_map(plain_state, plain_state.units[U1], 3).cost
