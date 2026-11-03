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
    "SealKeyGainedEvent",
    "SeasonBossAction",
    "SeasonBossChallengedEvent",
    "SeasonBossClearedEvent",
    "SeasonBossFailedEvent",
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
    """打贏了懸賞陣容，但當天的懸賞已經被別人搶下：拿小獎（9.6.3；任務幣另有
    ``currency_gained``）。"""

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


# ---------------------------------------------------------------------------
# 5F-3 賽季 Boss（規則在 trpg.world.season_boss）
# ---------------------------------------------------------------------------


class SeasonBossAction(_Model):
    """挑戰賽季 Boss（Phase 5F-3；09 9.7、#87、#100）：在城鎮出發，扣這個帳號今天的 1 次挑戰，
    產生 Boss 的遭遇（種子由伺服器的賽季種子衍生）；之後照一般遭遇開戰或撤退（撤退不退次數）。"""

    kind: Literal["season_boss"] = "season_boss"


class SealKeyGainedEvent(_Model):
    """拿到 1 把封印鑰匙（19.6.2）：``source`` 是來源 ID；``keys`` 是個人鑰匙數，``world_keys`` 是
    全服累積數。"""

    kind: Literal["seal_key_gained"] = "seal_key_gained"
    source: str
    name_zh: str
    keys: int
    world_keys: int


class SeasonBossChallengedEvent(_Model):
    """開始挑戰賽季 Boss：這個帳號今天第 ``attempt`` 次、還剩 ``attempts_left`` 次。"""

    kind: Literal["season_boss_challenged"] = "season_boss_challenged"
    boss: str = Field(pattern=ID_PATTERN)
    attempt: int
    attempts_left: int


class SeasonBossClearedEvent(_Model):
    """打倒賽季 Boss（#87 通關評分、#101 首殺）：``first``＝這一季第一個；``survivors``／``allies``
    是存活與出場的我方人數（主角＋傭兵）；``no_down``＝我方沒有人倒下過。"""

    kind: Literal["season_boss_cleared"] = "season_boss_cleared"
    boss: str = Field(pattern=ID_PATTERN)
    name_zh: str
    first: bool
    score: int
    rounds: int
    survivors: int
    allies: int
    no_down: bool
    title_zh: str


class SeasonBossFailedEvent(_Model):
    """挑戰賽季 Boss 失敗（只扣次數，#98）。"""

    kind: Literal["season_boss_failed"] = "season_boss_failed"
    boss: str = Field(pattern=ID_PATTERN)
