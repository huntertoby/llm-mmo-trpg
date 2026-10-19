"""依陣營過濾事件（Phase 3-1）：事件紀錄是全知的，交給某一方玩家前先過濾。

規則（以小函式註冊在 ``_RULES``，沒有註冊的事件類型所有人可見）：

- ``TrapPlaced``、``TrapExpired``：只給放置者陣營；``TrapRevealed``（Phase 3D-8a）：只給揭露者陣營。
- 放置陷阱技能的 ``SkillUsed``：其他陣營看到的版本 ``tiles`` 為空（回傳替換後的複本），
  「誰用了哪個技能」照樣看得到。
- 由隱藏陷阱引起的 ``TriggerLimitReached``（陷阱超過觸發深度上限而留在原地）：只給放置者陣營。
- ``TrapTriggered`` 與之後的效果事件：所有人可見（陷阱已曝光）。

過濾後的清單保留每個事件原本的 ``seq``，所以會跳號（被隱藏的事件不在清單中），這是預期的；
``seq`` 只保證遞增，客戶端不可假設連續。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from trpg.engine.events import (
    EventBase,
    SkillUsed,
    TrapExpired,
    TrapPlaced,
    TrapRevealed,
    TriggerLimitReached,
)
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

__all__ = ["event_visible_to", "filter_events", "view_of_event"]

type _Rule = Callable[[Any, BattleState, Team], EventBase | None]
"""回傳 ``team`` 看到的版本（``None`` 表示看不到）。"""


def _team_of(state: BattleState, unit_id: UnitId) -> Team:
    return state.units[unit_id].team


def _owner_only_by_team(event: TrapPlaced, _state: BattleState, team: Team) -> EventBase | None:
    return event if event.team is team else None


def _revealer_only(event: TrapRevealed, _state: BattleState, team: Team) -> EventBase | None:
    return event if event.team is team else None


def _owner_only_by_unit(
    event: TrapExpired | TriggerLimitReached, state: BattleState, team: Team
) -> EventBase | None:
    owner = event.owner_id if isinstance(event, TrapExpired) else event.unit_id
    return event if _team_of(state, owner) is team else None


def _trap_skill_used(event: SkillUsed, state: BattleState, team: Team) -> EventBase | None:
    if _team_of(state, event.unit_id) is team or not event.tiles:
        return event
    if state.ruleset.skill_def(event.skill_id).trap is None:
        return event
    return event.model_copy(update={"tiles": ()})


def _trigger_limit(event: TriggerLimitReached, state: BattleState, team: Team) -> EventBase | None:
    if state.ruleset.skill_def(event.skill_id).trap is None:
        return event  # 被動與反應技的深度上限：所有人可見
    return _owner_only_by_unit(event, state, team)


_RULES: dict[type[EventBase], _Rule] = {
    TrapPlaced: _owner_only_by_team,
    TrapExpired: _owner_only_by_unit,
    TrapRevealed: _revealer_only,
    SkillUsed: _trap_skill_used,
    TriggerLimitReached: _trigger_limit,
}


def view_of_event(event: EventBase, state: BattleState, team: Team) -> EventBase | None:
    """``team`` 看到的 ``event``（可能是替換後的複本）；看不到時為 ``None``。

    ``state`` 只用來查單位陣營與技能類型（任何一個同場戰鬥的狀態都可以）。
    """
    rule = _RULES.get(type(event))
    return event if rule is None else rule(event, state, team)


def event_visible_to(event: EventBase, state: BattleState, team: Team) -> bool:
    """``team`` 看不看得到 ``event``（被遮蔽部分欄位的事件仍算看得到）。"""
    return view_of_event(event, state, team) is not None


def filter_events(events: Iterable[EventBase], state: BattleState, team: Team) -> list[EventBase]:
    """``team`` 看得到的事件（依原順序，必要時替換成遮蔽後的複本）；``seq`` 保留原值。"""
    out: list[EventBase] = []
    for event in events:
        seen = view_of_event(event, state, team)
        if seen is not None:
            out.append(seen)
    return out
