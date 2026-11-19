"""AP 列資料（AP-2 第 5 項）：視圖的 ``ap_borrowed``（橘色菱形）、``ap_next_loss_borrowed``（下回合
紅斜線裡來自預支的）、``ap_lost_borrowed``（回合開始已扣掉裡來自預支的）。"""

from __future__ import annotations

from tests.engine.skill_helpers import U1, battle, cast
from tests.engine.test_borrow_ap_ap2 import _end_round, borrow_skill
from trpg.engine import EndTurn, resolve
from trpg.engine.state import BattleState
from trpg.engine.view import UnitView, project_for
from trpg.shared.types import Team


def _view(state: BattleState) -> UnitView:
    return {u.id: u for u in project_for(state, Team.ALLY).units}[U1]


def test_the_view_after_borrowing() -> None:
    result = cast(battle(borrow_skill(1)))
    view = _view(result.state)
    assert (view.ap_borrowed, view.ap_next_loss, view.ap_next_loss_borrowed) == (1, 1, 1)
    assert view.ap_lost == view.ap_lost_borrowed == 0


def test_the_view_on_the_next_turn() -> None:
    result = cast(battle(borrow_skill(1)))
    result.state.units[U1].ap = 0
    after, _ = _end_round(result.state)
    view = _view(after)
    assert (view.ap_borrowed, view.ap_next_loss, view.ap_next_loss_borrowed) == (0, 0, 0)
    assert view.ap_lost == view.ap_lost_borrowed == 1


def test_off_turn_shows_the_coming_loss() -> None:
    result = cast(battle(borrow_skill(2)))
    state = result.state
    state.units[U1].ap = 0
    ended = resolve(state, EndTurn(unit_id=U1)).state
    view = _view(ended)
    assert view.ap_borrowed == 0
    assert view.ap_next_loss == view.ap_next_loss_borrowed == 2
