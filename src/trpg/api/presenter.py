"""把工作階段轉成我方視角的 API 回應（Phase 3-2 4.4「戰鬥回應」）。

所有交給瀏覽器的戰鬥資料都經過這裡：

- 戰場：:func:`trpg.engine.view.project_for`（我方看得見的陷阱，沒有 ``rng_state``）。
- 事件：:func:`trpg.engine.event_filter.filter_events`（傳最新狀態，3-1 #4），並移除開場事件的
  ``seed``（種子只在 ``/log`` 匯出）。
- 步驟：對方放陷阱的 ``use_skill`` 不給目標格（與 ``skill_used`` 的過濾一致）。
"""

from __future__ import annotations

from typing import Any

from trpg.api.schemas import (
    BattleHistory,
    BattleOutcome,
    BattleResponse,
    FollowupOptionOut,
    HistoryStepOut,
    InteractOptionOut,
    PreviewOut,
    RunOptionOut,
    StepOut,
    preview_out,
)
from trpg.api.sessions import BattleSession, StepRecord
from trpg.api.telegraph import telegraph_out
from trpg.api.variants import preview_variant, variant_states
from trpg.engine.actions import Step, UseSkill
from trpg.engine.ai.commanded import ignored_orders
from trpg.engine.battle import (
    interact_direction,
    interact_options,
    legal_actions,
    run_problem,
)
from trpg.engine.copying import copy_selections
from trpg.engine.event_filter import filter_events
from trpg.engine.events import BattleStarted, EventBase
from trpg.engine.preview import Preview
from trpg.engine.results import Pending
from trpg.engine.skills.followups import followup_options
from trpg.engine.state import BattleState
from trpg.engine.view import project_for
from trpg.narrative.events import battle_started_text, describe_event
from trpg.shared.types import Pos, Team, UnitId

__all__ = [
    "VIEW_TEAM",
    "battle_response",
    "event_out",
    "history_response",
    "preview_response",
    "step_out",
    "step_view",
]

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


def history_response(session: BattleSession) -> BattleHistory:
    """到目前為止每一步的事件（我方視角；重播得到）。"""
    steps = []
    for record in session.history():
        state = record.result.state
        events = filter_events(record.result.events, state, VIEW_TEAM)
        steps.append(HistoryStepOut(events=tuple(event_out(e, state) for e in events)))
    return BattleHistory(steps=tuple(steps))


def preview_response(p: Preview, state: BattleState | None = None) -> PreviewOut:
    """預覽的公開版本，另附過濾後的模擬事件（``min``／``max``，各附中文 ``text``）。``state`` 是
    預覽前的戰場（判定戰場變奏的型態用，Phase 3-25b）。"""
    low = filter_events(p.min_events, p.min_state, VIEW_TEAM)
    high = filter_events(p.max_events, p.max_state, VIEW_TEAM)
    out = preview_out(
        p,
        tuple(event_out(e, p.min_state) for e in low),
        tuple(event_out(e, p.max_state) for e in high),
    )
    if state is None:
        return out
    return out.model_copy(update={"variant": preview_variant(state, p.action)})


def interact_options_out(state: BattleState, hero_id: UnitId) -> tuple[InteractOptionOut, ...]:
    """主角相鄰可推動物件的互動選項（含不合法的方向與原因）。"""
    hero = state.units[hero_id]
    return tuple(
        InteractOptionOut(
            object_id=obj.id,
            mode=mode,
            side=side,
            legal=problem is None,
            reason=problem,
            to_pos=_offset(obj.pos, interact_direction(hero.xy, obj.xy, mode, side)),
        )
        for obj, mode, side, problem in interact_options(state, hero)
    )


def run_option_out(state: BattleState, hero_id: UnitId) -> RunOptionOut:
    """主角跑步是否合法與原因（Phase 3-20）。"""
    problem = run_problem(state, state.units[hero_id])
    core = state.ruleset.core
    return RunOptionOut(
        legal=problem is None,
        reason=problem,
        ap_cost=core.run_ap_cost,
        move_bonus=core.run_move_bonus,
    )


def _offset(pos: Pos, direction: tuple[int, int]) -> Pos | None:
    """位移後的格子；落在地圖左／上緣之外（座標為負）時 ``None``（``Pos`` 不允許負座標）。"""
    x, y = pos.x + direction[0], pos.y + direction[1]
    return None if x < 0 or y < 0 else Pos(x=x, y=y)


def copy_options_out(state: BattleState, pending: Pending | None) -> tuple[UseSkill, ...]:
    """``copy_skill`` 暫停時，複製技能目前所有合法的選取（Phase 3C-4b）；其他時候為空。"""
    if pending is None or pending.kind != "copy_skill":
        return ()
    caster = state.units[pending.unit_id]
    return tuple(action for action, _ in copy_selections(state, caster))


def followup_options_out(
    state: BattleState, pending: Pending | None
) -> tuple[FollowupOptionOut, ...]:
    """複合技能第二段選目標暫停時（Phase 3F-4a），第二段目前所有合法的選取；其他時候為空。"""
    if pending is None or pending.kind != "followup":
        return ()
    assert pending.skill_id is not None
    caster = state.units[pending.unit_id]
    skill = state.ruleset.skill_def(pending.skill_id)
    return tuple(
        FollowupOptionOut(followup_target=target, tiles=area.tiles)
        for target, area in followup_options(state, caster, skill)
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
    legal = tuple(legal_actions(state)) if awaiting == "action" else ()
    return BattleResponse(
        battle_id=session.battle_id,
        hero_id=session.hero_id,
        awaiting=awaiting,
        initial_view=project_for(before, VIEW_TEAM),
        view=project_for(state, VIEW_TEAM),
        legal_actions=legal,
        interact_options=interact_options_out(state, session.hero_id)
        if awaiting == "action"
        else (),
        run_option=run_option_out(state, session.hero_id) if awaiting == "action" else None,
        variant_states=variant_states(state, session.hero_id, legal)
        if awaiting == "action"
        else (),
        pending=pending,
        copy_options=copy_options_out(state, pending),
        followup_options=followup_options_out(state, pending),
        orders=session.orders,
        orders_ignored=ignored_orders(state, VIEW_TEAM, session.orders),
        telegraph=telegraph_out(state, session.library, VIEW_TEAM),
        steps=tuple(step_out(r) for r in records),
        outcome=outcome,
    )
