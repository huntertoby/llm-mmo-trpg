"""落點與最近空格（Phase 3E-2f）：``landing_problem``、``nearest_free`` 的每種阻擋原因與排序。"""

from __future__ import annotations

from dataclasses import replace

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle
from trpg.engine import BattleState
from trpg.engine.rules.landing import LandingBlock, landing_problem, nearest_free
from trpg.shared.types import Pos


def _state() -> BattleState:
    skill = make_skill(
        SID,
        {"type": "single", "range": 4},
        [{"type": "heal", "dice": "1d4", "affects": "allies"}],
    )
    return battle(skill, [(6, 6)], allies=[(4, 3)])  # U1 (3,3)、U2 (4,3)、U3 (6,6)


def _terrain(state: BattleState, xy: tuple[int, int], terrain: str) -> None:
    state.set_tile(*xy, replace(state.tile(*xy), terrain=terrain))


def test_landing_problem_reports_each_block() -> None:
    state = _state()
    assert landing_problem(state, (-1, 0)) is LandingBlock.OUT_OF_BOUNDS
    assert landing_problem(state, (state.width, 0)) is LandingBlock.OUT_OF_BOUNDS
    assert landing_problem(state, (0, 0)) is None
    _terrain(state, (0, 0), "wall")
    assert landing_problem(state, (0, 0)) is LandingBlock.NOT_STANDABLE
    _terrain(state, (1, 0), "chasm")
    assert landing_problem(state, (1, 0)) is LandingBlock.NOT_STANDABLE  # 致命地形也不能站
    assert landing_problem(state, state.units[U2].xy) is LandingBlock.OCCUPIED


def test_the_mover_may_stay_on_its_own_tile() -> None:
    state = _state()
    here = state.units[U1].xy
    assert landing_problem(state, here) is LandingBlock.OCCUPIED
    assert landing_problem(state, here, mover=U1) is None
    assert landing_problem(state, state.units[U2].xy, mover=U1) is LandingBlock.OCCUPIED


def test_objects_block_only_when_asked() -> None:
    skill = make_skill(SID, {"type": "self"}, [{"type": "heal", "dice": "1d4"}])
    state = battle(skill, [(6, 6)], objects=((0, 1, "grass"),))  # 草叢：不擋移動
    assert landing_problem(state, (0, 1)) is None
    assert landing_problem(state, (0, 1), clear_of_objects=True) is LandingBlock.OBJECT


def test_nearest_free_orders_by_distance_then_y_then_x() -> None:
    state = _state()
    origin = state.units[U2].xy  # (4, 3) 被 U2 占著
    assert nearest_free(state, origin) == (4, 2)  # 距離 1：y 較小者先
    _terrain(state, (4, 2), "wall")
    assert nearest_free(state, origin) == (5, 3)  # (3,3) 被 U1 占住：(5,3)、(4,4) 同距，y 小者先
    state.units[U1].pos = Pos(x=0, y=0)
    assert nearest_free(state, origin) == (3, 3)  # (3,3)、(5,3) 同 y：x 小者先
    assert nearest_free(state, origin, mover=U2) == origin


def test_nearest_free_respects_the_radius() -> None:
    state = _state()
    taken = state.units[U1].xy
    assert nearest_free(state, taken, radius=0) is None
    assert nearest_free(state, taken, radius=0, mover=U1) == taken
    assert nearest_free(state, taken, radius=1) == (3, 2)
