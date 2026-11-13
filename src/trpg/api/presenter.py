"""把工作階段轉成我方視角的 API 回應（Phase 3-2 4.4「戰鬥回應」）。

所有交給瀏覽器的戰鬥資料都經過這裡：

- 戰場：:func:`trpg.engine.view.project_for`（我方看得見的陷阱，沒有 ``rng_state``）。
- 事件：:func:`trpg.engine.event_filter.filter_events`（傳最新狀態，3-1 #4），並移除開場事件的
  ``seed``（種子只在 ``/log`` 匯出）。
- 步驟：對方放陷阱的 ``use_skill`` 不給目標格（與 ``skill_used`` 的過濾一致）。
- 隱蔽中的敵人只藏資訊（05 5.1.2，決定 #144；:mod:`trpg.api.hidden_info`）：戰場、事件、紀錄
  文字與預覽依觀看者陣營遮住 HP、護盾、狀態。``/log`` 匯出與重播照完整狀態。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from trpg.api.condition_off import skills_off
from trpg.api.hidden_info import (
    event_hidden_fields,
    event_visible,
    hidden_unit_ids,
    mask_event_data,
    mask_outcomes,
    mask_view,
)
from trpg.api.schemas import (
    BattleHistory,
    BattleOutcome,
    BattleResponse,
    FollowupOptionOut,
    HistoryStepOut,
    InteractOptionOut,
    PartActionOut,
    PartOptionOut,
    PreviewOut,
    RunOptionOut,
    StepOut,
    preview_out,
)
from trpg.api.sessions import BattleSession, StepRecord
from trpg.api.telegraph import telegraph_out
from trpg.api.variants import preview_variant, variant_states
from trpg.content.library import ContentLibrary
from trpg.engine.actions import Action, Attack, Step, UseSkill
from trpg.engine.ai.commanded import ignored_orders
from trpg.engine.battle import (
    interact_direction,
    interact_options,
    legal_actions,
    run_problem,
)
from trpg.engine.copying import copy_selections
from trpg.engine.event_filter import filter_events
from trpg.engine.events import BattleStarted, EffectFizzled, EventBase, TurnStarted
from trpg.engine.lock_on import LOCK_BLOCKED, LOCK_CONCEALED, LOCK_LOST, lock_blocker
from trpg.engine.parts import PART_REASON_ZH, part_targets
from trpg.engine.preview import Preview
from trpg.engine.results import Pending
from trpg.engine.skills.followups import followup_options
from trpg.engine.state import BattleState
from trpg.engine.view import BattleView, UnitView, project_for
from trpg.narrative.events import battle_started_text, describe_event
from trpg.narrative.parts import break_lines_zh
from trpg.narrative.unit_traits import unit_trait_lines
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


def event_out(
    event: EventBase, state: BattleState, hidden: frozenset[UnitId] = frozenset()
) -> dict[str, Any]:
    """事件的 JSON ＋ ``text``（中文描述；沒有時不含此鍵）。開場事件不含 ``seed``。

    ``hidden``：觀看者看不到資訊的單位（:func:`trpg.api.hidden_info.hidden_unit_ids`）；這些單位的
    剩餘 HP、護盾欄位為 ``None``，描述也不寫出。"""
    data: dict[str, Any] = mask_event_data(
        event.model_dump(mode="json"), event_hidden_fields(event, hidden)
    )
    if isinstance(event, BattleStarted):
        data.pop("seed", None)
        text: str | None = battle_started_text(state, None)
    else:
        text = describe_event(event, state, hidden)
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


def traits_view(
    state: BattleState, team: Team, library: ContentLibrary, hero_id: UnitId | None
) -> BattleView:
    """:func:`~trpg.engine.view.project_for` ＋ 每個單位卡的「特性」欄
    （Phase 5A-M1b，``trpg.narrative`` 依單位範本產生；主角的招牌在技能列，不重複列）；
    隱蔽中的敵人只藏資訊（:func:`trpg.api.hidden_info.mask_view`）。"""
    view = mask_view(project_for(state, team), hidden_unit_ids(state, team))
    cache: dict[str, tuple[str, ...]] = {}
    units = tuple(
        u
        if u.id == hero_id
        else u.model_copy(
            update={
                "traits_zh": cache.setdefault(
                    u.template_id, unit_trait_lines(library, u.template_id)
                )
            }
        )
        for u in view.units
    )
    return view.model_copy(update={"units": tuple(_with_break_lines(state, u) for u in units)})


def _with_break_lines(state: BattleState, unit: UnitView) -> UnitView:
    """部位的「破掉會：……」（PB-1c；:func:`trpg.narrative.parts.break_lines_zh`）。"""
    owner = state.units.get(unit.id)
    if unit.parts is None or owner is None:
        return unit
    defs = {p.id: p for p in owner.parts}
    parts = tuple(
        p.model_copy(update={"break_lines_zh": break_lines_zh(state.ruleset, defs[p.id])})
        if p.id in defs
        else p
        for p in unit.parts
    )
    return unit.model_copy(update={"parts": parts})


def part_options_out(
    state: BattleState, legal: tuple[Action, ...]
) -> tuple[PartActionOut, ...] | None:
    """``legal`` 裡目標有部位的普攻與單體技能各自的部位選項（PB-1c；同一個動作種類、技能、目標只列
    一次）；沒有時為 ``None``。"""
    out: list[PartActionOut] = []
    seen: set[tuple[str, str | None, str]] = set()
    for action in legal:
        if not isinstance(action, (Attack, UseSkill)) or action.target_id is None:
            continue
        skill_id = action.skill_id if isinstance(action, UseSkill) else None
        key = (action.type, skill_id, action.target_id)
        if key in seen:
            continue
        targets = part_targets(state, action)
        if not targets:
            continue
        seen.add(key)
        out.append(
            PartActionOut(
                type="attack" if isinstance(action, Attack) else "use_skill",
                skill_id=skill_id,
                target_id=action.target_id,
                options=tuple(
                    PartOptionOut(
                        part_id=t.part_id,
                        name_zh=t.name_zh,
                        ok=t.ok,
                        reason_zh=None if t.reason is None else PART_REASON_ZH[t.reason],
                    )
                    for t in targets
                ),
            )
        )
    return tuple(out) if out else None


def team_events_out(
    events: Iterable[EventBase], state: BattleState, team: Team
) -> tuple[dict[str, Any], ...]:
    """``team`` 看到的事件 JSON：陷阱過濾（:func:`filter_events`）＋ 隱蔽中的敵人只藏資訊
    （以這一步之後的狀態判斷誰看不到）。"""
    hidden = hidden_unit_ids(state, team)
    out: list[dict[str, Any]] = []
    turn_of: UnitId | None = None
    for e in filter_events(events, state, team):
        if isinstance(e, TurnStarted):
            turn_of = e.unit_id
        if not event_visible(e, state, team, hidden):
            continue
        data = event_out(e, state, hidden)
        if isinstance(e, EffectFizzled) and e.reason in _LOCK_REASONS:
            data.update(_lock_fizzle_ids(state, e, turn_of, hidden))
        out.append(data)
    return tuple(out)


_LOCK_REASONS = frozenset({LOCK_LOST, LOCK_CONCEALED, LOCK_BLOCKED})
"""瞄準預告落空的原因（RG-1 ``effect_fizzled.reason``）。"""


def _lock_fizzle_ids(
    state: BattleState, e: EffectFizzled, caster_id: UnitId | None, hidden: frozenset[UnitId]
) -> dict[str, str]:
    """瞄準預告落空（RG-3 浮字）：``lock_caster_id``＝射出的人（射出在他回合開始時，取這一步
    裡最後一個 ``turn_started``）；``lock_on_blocked`` 另帶 ``lock_blocker_id``＝擋下的目標隊友
    （以這一步之後的戰場、:func:`lock_blocker` 判斷）。觀看者看不到資訊的單位不送。

    RG-3b：AF-1 起有人擋在中間時改打擋住的人，引擎發 ``lock_intercepted``（自帶 ``unit_id``＝
    射出的人、``blocker_id``），前端「被擋下」直接讀它、這裡不推算；``lock_on_blocked`` 落空只剩
    「擋住的人本身選不到」（例如 2 格外的隱蔽）這一種，引擎事件沒有擋住的人，才在這裡推算。"""
    out: dict[str, str] = {}
    caster = None if caster_id is None else state.units.get(caster_id)
    if caster is None or caster.id in hidden:
        return out
    out["lock_caster_id"] = caster.id
    if e.reason != LOCK_BLOCKED or e.pos is None:
        return out
    target = state.unit_at(e.pos.x, e.pos.y)
    blocker = None if target is None else lock_blocker(state, caster, target)
    if blocker is not None and blocker.id not in hidden:
        out["lock_blocker_id"] = blocker.id
    return out


def step_out(
    record: StepRecord, library: ContentLibrary, hero_id: UnitId, team: Team = VIEW_TEAM
) -> StepOut:
    state = record.result.state
    return StepOut(
        actor_id=None if record.step is None else record.step.unit_id,
        step=step_view(record.step, state, team),
        events=team_events_out(record.result.events, state, team),
        view=traits_view(state, team, library, hero_id),
    )


def history_response(session: BattleSession) -> BattleHistory:
    """到目前為止每一步的事件（我方視角；重播得到）。"""
    steps = []
    for record in session.history():
        state = record.result.state
        steps.append(HistoryStepOut(events=team_events_out(record.result.events, state, VIEW_TEAM)))
    return BattleHistory(steps=tuple(steps))


def preview_response(p: Preview, state: BattleState | None = None) -> PreviewOut:
    """預覽的公開版本，另附過濾後的模擬事件（``min``／``max``，各附中文 ``text``）。``state`` 是
    預覽前的戰場（判定戰場變奏的型態用，Phase 3-25b；也用來判斷隱蔽中的敵人只藏資訊，省略時
    不遮）。"""
    hidden = frozenset() if state is None else hidden_unit_ids(state, VIEW_TEAM)
    low = filter_events(p.min_events, p.min_state, VIEW_TEAM)
    high = filter_events(p.max_events, p.max_state, VIEW_TEAM)
    out = preview_out(
        p,
        tuple(
            event_out(e, p.min_state, hidden)
            for e in low
            if event_visible(e, p.min_state, VIEW_TEAM, hidden)
        ),
        tuple(
            event_out(e, p.max_state, hidden)
            for e in high
            if event_visible(e, p.max_state, VIEW_TEAM, hidden)
        ),
    )
    if hidden:
        out = out.model_copy(
            update={
                "certain": mask_outcomes(out.certain, hidden),
                "possible": mask_outcomes(out.possible, hidden),
            }
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
        initial_view=traits_view(before, VIEW_TEAM, session.library, session.hero_id),
        view=traits_view(state, VIEW_TEAM, session.library, session.hero_id),
        legal_actions=legal,
        interact_options=interact_options_out(state, session.hero_id)
        if awaiting == "action"
        else (),
        run_option=run_option_out(state, session.hero_id) if awaiting == "action" else None,
        variant_states=variant_states(state, session.hero_id, legal)
        if awaiting == "action"
        else (),
        oath_active=state.oath is not None and not state.oath.broken and not state.oath.pending,
        pending=pending,
        copy_options=copy_options_out(state, pending),
        followup_options=followup_options_out(state, pending),
        part_options=part_options_out(state, legal),
        skills_off=skills_off(state, session.hero_id),
        orders=session.orders,
        orders_ignored=ignored_orders(state, VIEW_TEAM, session.orders),
        telegraph=telegraph_out(state, session.library, VIEW_TEAM),
        steps=tuple(step_out(r, session.library, session.hero_id) for r in records),
        outcome=outcome,
    )
