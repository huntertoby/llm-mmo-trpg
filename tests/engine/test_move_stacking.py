"""途中倒地而停在友軍所在的格子時，單位滑回最近的空格（Phase 2C-3，冰湖地圖暴露的問題）。"""

from __future__ import annotations

from tests.engine.helpers import give_turn, make_map, make_state, spawn, with_rolls
from trpg.engine import BattleState, Move, resolve
from trpg.engine.events import CheckRolled, UnitMoved
from trpg.shared.types import Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def _state() -> BattleState:
    m = make_map("0000", surfaces=[(1, 0, "ice")], ally=[(0, 0), (1, 0)], enemy=[(3, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), "hero_fighter"),
            spawn(Team.ALLY, (1, 0), "hero_archer"),
            spawn(Team.ENEMY, (3, 0), "bandit"),
        ],
    )
    return give_turn(state, U1)


def test_slipping_on_ice_under_an_ally_slides_back_instead_of_stacking() -> None:
    state = with_rolls(_state(), [(20, 3)])
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=0, y=0), Pos(x=1, y=0), Pos(x=2, y=0))))
    s = result.state
    assert s.units[U1].has_status("prone")
    assert s.units[U1].pos == Pos(x=0, y=0) and s.units[U2].pos == Pos(x=1, y=0)
    positions = [u.pos for u in s.units.values()]
    assert len(positions) == len(set(positions))
    assert [e.mode for e in result.events if isinstance(e, UnitMoved)][-1] == "teleport"


def test_passing_over_an_ally_on_ice_without_slipping_is_unchanged() -> None:
    state = with_rolls(_state(), [(20, 18)])
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=0, y=0), Pos(x=1, y=0), Pos(x=2, y=0))))
    s = result.state
    assert not s.units[U1].has_status("prone") and s.units[U1].pos == Pos(x=2, y=0)
    assert [e.success for e in result.events if isinstance(e, CheckRolled)] == [True]
