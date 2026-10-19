"""把工作階段轉成我方視角的 API 回應（Phase 3-2 4.4「戰鬥回應」）。

所有交給瀏覽器的戰鬥資料都經過這裡：

- 戰場：:func:`trpg.engine.view.project_for`（我方看得見的陷阱，沒有 ``rng_state``）。
- 事件：:func:`trpg.engine.event_filter.filter_events`（傳最新狀態，3-1 #4），並移除開場事件的
  ``seed``（種子只在 ``/log`` 匯出）。
- 步驟：對方放陷阱的 ``use_skill`` 不給目標格（與 ``skill_used`` 的過濾一致）。
"""

from __future__ import annotations

from typing import Any

from trpg.api.schemas import BattleOutcome, BattleResponse, StepOut
from trpg.api.sessions import BattleSession, StepRecord
from trpg.engine.actions import Step, UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.event_filter import filter_events
from trpg.engine.events import BattleStarted, EventBase
from trpg.engine.state import BattleState
from trpg.engine.view import project_for
from trpg.narrative.events import battle_started_text, describe_event
from trpg.shared.types import Team

__all__ = ["VIEW_TEAM", "battle_response", "event_out", "step_out", "step_view"]

VIEW_TEAM = Team.ALLY
"""網頁玩家的陣營。"""


def event_out(event: EventBase, state: BattleState) -> dict[str, Any]:
    """事件的 JSON ＋ ``text``（中文描述；沒有時不含此鍵）。開場事件不含 ``seed``。"""
    data: dict[str, Any] = event.model_dump(mode="json")
    if isinstance(event, BattleStarted):
        data.pop("seed", None)
        text: str | None = battle_started_text(state, None)
    else:
        text = describe_event(event, state)
    if text is not None:
        data["text"] = text
    return data


def step_view(step: Step | None, state: BattleState, team: Team) -> Step | None:
    """``team`` 看得到的步驟：其他陣營放陷阱的技能不給目標（格子、方向、目標單位）。"""
    if not isinstance(step, UseSkill):
        return step
    actor = state.units.get(step.unit_id)
    if actor is None or actor.team is team:
        return step
    if state.ruleset.skill_def(step.skill_id).trap is None:
        return step
    return step.model_copy(
        update={"target_pos": None, "direction": None, "target_id": None, "target_object_id": None}
    )


def step_out(record: StepRecord, team: Team = VIEW_TEAM) -> StepOut:
    state = record.result.state
    events = filter_events(record.result.events, state, team)
    return StepOut(
        actor_id=None if record.step is None else record.step.unit_id,
        step=step_view(record.step, state, team),
        events=tuple(event_out(e, state) for e in events),
        view=project_for(state, team),
    )


def battle_response(
    session: BattleSession,
    records: list[StepRecord],
    before: BattleState | None = None,
) -> BattleResponse:
    """``before`` 是本次請求開始推進前的狀態（``initial_view`` 的來源）；建立戰鬥時省略，
    取開場那一步（``records[0]``）的狀態；沒有推進時為目前狀態。"""
    state = session.state
    awaiting = session.awaiting
    pending = session.pending if awaiting == "decision" else None
    if before is None:
        before = records[0].result.state if records else state
    outcome = (
        BattleOutcome(winner=state.winner, end_reason=state.end_reason, round=state.round)
        if state.ended
        else None
    )
    return BattleResponse(
        battle_id=session.battle_id,
        hero_id=session.hero_id,
        awaiting=awaiting,
        initial_view=project_for(before, VIEW_TEAM),
        view=project_for(state, VIEW_TEAM),
        legal_actions=tuple(legal_actions(state)) if awaiting == "action" else (),
        pending=pending,
        orders=session.orders,
        steps=tuple(step_out(r) for r in records),
        outcome=outcome,
    )
