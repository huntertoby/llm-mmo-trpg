"""``set_reaction_mode`` 與反應規則的 ``off``／``prompt`` 模式（Phase 3-4b 6.6）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template
from trpg.engine import (
    BattleState,
    Decision,
    Move,
    SetReactionMode,
    legal_actions,
    resolve,
    resume,
)
from trpg.engine.battle import reaction_mode_problem
from trpg.engine.events import ReactionDeclined, ReactionModeSet, ReactionTriggered
from trpg.engine.view import project_for
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _state(active: str = "unit_0001") -> BattleState:
    m = make_map("000000\n000000", ally=[(1, 0)], enemy=[(2, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 0), "hero_fighter"),
            spawn(Team.ENEMY, (2, 0), template("bandit", max_hp=300, reactions=[])),
        ],
    )
    return give_turn(state, active)


def _set(state: BattleState, mode: str) -> BattleState:
    action = SetReactionMode(unit_id=U1, reaction="opportunity_attack", mode=mode)  # type: ignore[arg-type]
    return resolve(state, action).state


def _walk_away(state: BattleState) -> list:  # type: ignore[type-arg]
    s = give_turn(state, "unit_0002")
    return resolve(s, Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0)))).events


def test_set_reaction_mode_costs_nothing_and_keeps_the_turn() -> None:
    state = _state()
    result = resolve(state, SetReactionMode(unit_id=U1, reaction="block", mode="off"))
    after = result.state
    assert [type(e) for e in result.events] == [ReactionModeSet]
    assert after.active_unit == U1 and after.units[U1].ap == state.units[U1].ap
    modes = {r.reaction: r.mode for r in after.units[U1].reactions}
    assert modes["block"] == "off" and modes["opportunity_attack"] == "auto"
    assert state.units[U1].reactions != after.units[U1].reactions  # 原狀態不變（純函式）
    assert not any(isinstance(a, SetReactionMode) for a in legal_actions(after))


def test_off_mode_does_not_trigger() -> None:
    assert any(isinstance(e, ReactionTriggered) for e in _walk_away(_state()))
    events = _walk_away(_set(_state(), "off"))
    assert not any(isinstance(e, ReactionTriggered | ReactionDeclined) for e in events)


@pytest.mark.parametrize("accept", [True, False])
def test_prompt_mode_pauses_and_resumes(accept: bool) -> None:
    state = give_turn(_set(_state(), "prompt"), "unit_0002")
    paused = resolve(state, Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0))))
    assert paused.pending is not None and paused.pending.reaction == "opportunity_attack"
    resumed = resume(paused.state, Decision(unit_id=U1, accept=accept))
    kinds = {type(e) for e in resumed.events}
    assert (ReactionTriggered in kinds) is accept and (ReactionDeclined in kinds) is not accept


def test_back_to_auto_restores_the_trigger() -> None:
    state = _set(_set(_state(), "off"), "auto")
    assert any(isinstance(e, ReactionTriggered) for e in _walk_away(state))


def test_rejected_when_not_own_turn_or_unknown_rule_or_paused() -> None:
    other = _state("unit_0002")
    with pytest.raises(IllegalActionError, match="不是"):
        resolve(other, SetReactionMode(unit_id=U1, reaction="block", mode="off"))
    with pytest.raises(IllegalActionError, match="沒有反應規則"):
        resolve(_state(), SetReactionMode(unit_id=U1, reaction="no_such", mode="off"))
    assert reaction_mode_problem(_state().units[U1], "block") is None
    paused = resolve(
        give_turn(_set(_state(), "prompt"), "unit_0002"),
        Move(unit_id=U2, path=(P(2, 0), P(3, 0))),
    ).state
    with pytest.raises(IllegalActionError, match="結算暫停中"):
        resolve(paused, SetReactionMode(unit_id=U1, reaction="block", mode="off"))


def test_view_lists_rules_for_own_team_only() -> None:
    state = _set(_state(), "prompt")
    ally = {u.id: u for u in project_for(state, Team.ALLY).units}
    enemy = {u.id: u for u in project_for(state, Team.ENEMY).units}
    rules = {r.reaction: r for r in ally[U1].reaction_rules}
    assert rules["opportunity_attack"].mode == "prompt"
    assert rules["block"].stamina_cost > 0 and rules["block"].trigger_zh
    assert enemy[U1].reaction_rules == ()


def test_reaction_available_false_when_every_rule_is_off() -> None:
    state = _state()
    for rule in state.units[U1].reactions:
        state = _set_rule(state, rule.reaction, "off")
    assert not project_for(state, Team.ALLY).units[0].reaction_available


def _set_rule(state: BattleState, reaction: str, mode: str) -> BattleState:
    action = SetReactionMode(unit_id=U1, reaction=reaction, mode=mode)  # type: ignore[arg-type]
    return resolve(state, action).state
