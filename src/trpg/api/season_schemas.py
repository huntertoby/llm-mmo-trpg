"""公告板（賽季日程、今日目標、懸賞、世界事件、共享地點狀態）的 API 格式（Phase 5F-1；
``docs/phases/Phase5計畫.md`` 35.7）。

全部由後端算好（前端不寫規則）；地點名稱已套過隱藏地點的提示語（5C-3f）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = [
    "BoardBountyView",
    "BoardClearedView",
    "BoardGoalView",
    "BoardMilestoneView",
    "BoardWorldEventView",
    "SeasonBoardView",
    "SeasonInfoView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BoardMilestoneView(_ApiModel):
    day: int
    name_zh: str


class SeasonInfoView(_ApiModel):
    """賽季第幾天與日程（09 9.7）。"""

    day: int
    days: int
    status: Literal["upcoming", "running", "ended"]
    status_zh: str
    """例「賽季第 3 天／共 14 天」「開賽前」「本季已結束」。"""
    phase_zh: str | None = None
    """這段日程的名稱與說明（例「霧中裂痕：主線第 1～2 章、雲嶺…」）。"""
    upcoming: tuple[BoardMilestoneView, ...] = ()
    """之後的時間點（今天起，依天數）。"""
    next_refresh_at: int
    """下一次每日刷新的 UTC 秒數。"""
    next_refresh_zh: str
    """例「每天 06:00 刷新」。"""


class BoardGoalView(_ApiModel):
    """一條今日目標（#99）與這個角色的進度。"""

    goal: str
    text_zh: str
    progress: int
    count: int
    done: bool
    coins: int


class BoardBountyView(_ApiModel):
    """一張今天的懸賞（18.7.4；先搶先贏）。"""

    bounty: str
    name_zh: str
    location_zh: str
    """地點名（看的人還沒發現的隱藏地點用提示語）。"""
    level: int
    coins: int
    open: bool
    claimed_by: str | None = None
    """搶下的角色名（還沒被搶＝``None``）。"""
    status_zh: str
    """例「懸賞中」「已被 小美 搶下」「你搶下了」。"""


class BoardWorldEventView(_ApiModel):
    """一個世界事件的全服進度（#103）。"""

    event: str
    name_zh: str
    text_zh: str
    status: Literal["pending", "active", "succeeded", "failed"]
    status_zh: str
    progress: int
    target: int
    permille: int
    """進度 ‰（0～1000；進度條用）。"""
    days_zh: str
    """例「第 1～3 天」。"""
    target_note_zh: str | None = None
    """門檻怎麼來的（例「依昨天 4 位冒險者調整」）。"""


class BoardClearedView(_ApiModel):
    """所有人看到的已清空地點（9.6.7 #15）。"""

    location_zh: str
    respawn_at: int


class SeasonBoardView(_ApiModel):
    """城鎮公告板的整份資料。"""

    season: SeasonInfoView
    goals: tuple[BoardGoalView, ...] = ()
    goals_note_zh: str | None = None
    """例「新手期：教學目標」。"""
    bounties: tuple[BoardBountyView, ...] = ()
    world_events: tuple[BoardWorldEventView, ...] = ()
    cleared: tuple[BoardClearedView, ...] = ()
    level_bonus_zh: tuple[str, ...] = ()
    """世界事件失敗的建議等級加成（例「灰燼荒原：建議等級 +1」）。"""
