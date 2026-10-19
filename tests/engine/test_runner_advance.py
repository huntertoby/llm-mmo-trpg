"""共用推進迴圈 ``advance``（``run_battle`` 與網頁 API；Phase 3-2 4.2）與 ``CommandedAI.issue``。"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.actions import Step
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.orders import OrderSet, UseEnvironment
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.events import EventBase
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.runner import StepLimitExceeded, StopCondition, advance, replay, run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.engine.state import BattleState, state_to_json
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.lineup import default_lineup


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _setup(library: ContentLibrary) -> BattleSetup:
    allies, enemies = default_lineup(library, "open_plain")
    return build_setup(library, "open_plain", allies, enemies, max_rounds=30)


def test_advancing_in_pieces_equals_run_battle(library: ContentLibrary) -> None:
    setup = _setup(library)
    whole = run_battle(setup, 7, UtilityAI(library.ai_profiles))
    opening = begin_battle(setup, 7)
    policy = UtilityAI(library.ai_profiles)
    events: list[EventBase] = list(opening.events)

    def record(_step: Step | None, result: ResolveResult) -> None:
        events.extend(result.events)

    def ally_turn(state: BattleState, pending: Pending | None) -> bool:
        unit = state.active
        return pending is None and unit is not None and unit.team is Team.ALLY

    state, pending = opening.state, opening.pending
    steps: list[Step] = []
    pieces = 0
    while not state.ended:
        state, pending, more = advance(state, pending, policy, on_step=record, stop=ally_turn)
        steps.extend(more)
        if state.ended:
            break
        # 停在我方回合：再走一步（停止條件第二次才成立）
        state, pending, one = advance(state, pending, policy, on_step=record, stop=_once())
        steps.extend(one)
        pieces += 1
    assert pieces > 1
    assert steps == whole.actions
    assert state_to_json(state) == state_to_json(whole.state)
    assert [e.seq for e in events] == [e.seq for e in whole.events]
    assert state_to_json(replay(setup, 7, steps).state) == state_to_json(whole.state)


def _once() -> StopCondition:
    calls = {"n": 0}

    def stop(_state: BattleState, _pending: Pending | None) -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    return stop


def test_the_step_limit_is_a_trpg_error(library: ContentLibrary) -> None:
    opening = begin_battle(_setup(library), 7)
    with pytest.raises(StepLimitExceeded, match="超過 0 個動作") as info:
        advance(opening.state, None, UtilityAI(library.ai_profiles), max_actions=0)
    assert isinstance(info.value, TrpgError)


def test_issued_orders_take_effect_and_are_logged(library: ContentLibrary) -> None:
    state = begin_battle(_setup(library), 7).state
    ai = CommandedAI(UtilityAI(library.ai_profiles), {})
    assert ai.current_orders(Team.ALLY) == OrderSet()
    orders = OrderSet(team_orders=(UseEnvironment(),))
    record = ai.issue(state, Team.ALLY, orders)
    assert record.round == state.round and record.team is Team.ALLY and record.ignored == ()
    assert ai.current_orders(Team.ALLY) == orders
    assert ai.order_log == [record]
    ally = next(u for u in state.units_sorted() if u.team is Team.ALLY)
    assert ai.ai.orders is not None
    assert ai.ai.orders(state, ally.id) == (UseEnvironment(),)
