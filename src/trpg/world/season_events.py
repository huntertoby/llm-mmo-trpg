"""賽季日程的世界事件（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.6）。

放在獨立模組，由 :mod:`trpg.world.actions` 併進 ``WorldEvent`` 聯集（不匯入 ``actions``，避免
循環）。規則在 :mod:`trpg.world.season_board`。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN

__all__ = [
    "BountyClaimedEvent",
    "BountyMissedEvent",
    "DailyGoalDoneEvent",
    "WorldEventProgressEvent",
    "WorldEventResolvedEvent",
    "WorldEventStartedEvent",
    "WorldEventTargetEvent",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorldEventStartedEvent(_Model):
    """世界事件開始（換日；#103）。"""

    kind: Literal["world_event_started"] = "world_event_started"
    event: str = Field(pattern=ID_PATTERN)
    day: int
    target: int


class WorldEventTargetEvent(_Model):
    """世界事件的門檻依前一天上線人數調整（換日；Q14）。``players`` 為 ``None``＝沒有前一天的
    資料。"""

    kind: Literal["world_event_target"] = "world_event_target"
    event: str = Field(pattern=ID_PATTERN)
    day: int
    players: int | None
    target: int


class WorldEventProgressEvent(_Model):
    """這一步讓世界事件的全服進度前進。"""

    kind: Literal["world_event_progress"] = "world_event_progress"
    event: str = Field(pattern=ID_PATTERN)
    added: int
    progress: int
    target: int


class WorldEventResolvedEvent(_Model):
    """世界事件成功（達到門檻）或失敗（結束日過了）；``flags``、``level_bonus`` 是寫回世界的
    效果。"""

    kind: Literal["world_event_resolved"] = "world_event_resolved"
    event: str = Field(pattern=ID_PATTERN)
    outcome: Literal["succeeded", "failed"]
    progress: int
    target: int
    flags: tuple[str, ...] = ()
    level_bonus: dict[str, int] = Field(default_factory=dict)
    """區域 → 這次加的建議等級。"""


class BountyClaimedEvent(_Model):
    """搶下當天的懸賞（09 9.7「先搶先贏」）：任務幣另有 ``currency_gained``；``xp`` 是補到懸賞份數
    多給的經驗。"""

    kind: Literal["bounty_claimed"] = "bounty_claimed"
    bounty: str = Field(pattern=ID_PATTERN)
    coins: int = 0
    xp: int = 0


class BountyMissedEvent(_Model):
    """打贏了懸賞陣容，但當天的懸賞已經被別人搶下：拿小獎（9.6.3；任務幣另有 ``currency_gained``）。"""

    kind: Literal["bounty_missed"] = "bounty_missed"
    bounty: str = Field(pattern=ID_PATTERN)
    claimed_by: str
    """搶下的角色名。"""
    coins: int = 0
    """小獎的任務幣（5F-1b）。"""


class DailyGoalDoneEvent(_Model):
    """完成一條今日目標（#99；任務幣另有 ``currency_gained``）。"""

    kind: Literal["daily_goal_done"] = "daily_goal_done"
    goal: str = Field(pattern=ID_PATTERN)
    coins: int = 0
