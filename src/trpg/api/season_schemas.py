"""公告板（賽季日程、今日目標、懸賞、世界事件、共享地點狀態）的 API 格式（Phase 5F-1；
``docs/phases/Phase5計畫.md`` 35.7）。

全部由後端算好（前端不寫規則）；地點名稱已套過隱藏地點的提示語（5C-3f）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = [
    "BoardBossEntryView",
    "BoardBountyView",
    "BoardClearedView",
    "BoardGoalView",
    "BoardMilestoneView",
    "BoardPhaseView",
    "BoardSeasonBossView",
    "BoardWorldEventView",
    "SeasonBoardView",
    "SeasonInfoView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


MilestoneKind = Literal["story_skill", "boss_unlock", "league", "other"]
"""時間點的種類（PNL-1b；決定時間軸釘的圖示）：劇情技能、頭目解鎖、循環賽、其他。"""


class BoardMilestoneView(_ApiModel):
    day: int
    name_zh: str
    id: str = ""
    """時間點 ID（PNL-1b）。"""
    kind: MilestoneKind = "other"
    """主要種類（PNL-1b；``kinds`` 的第一個）。"""
    kinds: tuple[MilestoneKind, ...] = ()
    """這個時間點涉及的全部種類（PNL-1b；例：第 10 天「頭目強制解鎖；主線第 3 章的劇情技能」
    ＝頭目解鎖＋劇情技能）。"""


class BoardPhaseView(_ApiModel):
    """一段日程（PNL-1b；``content/world/season.yaml`` 的 ``schedule``）。"""

    id: str
    name_zh: str
    text_zh: str = ""
    start_day: int
    end_day: int


class SeasonInfoView(_ApiModel):
    """賽季第幾天與日程（09 9.7）。"""

    day: int
    days: int
    status: Literal["upcoming", "running", "ended"]
    status_zh: str
    """例「賽季第 3 天／共 14 天」「開賽前」「本季已結束」。"""
    phase_zh: str | None = None
    """這段日程的名稱與說明（例「霧中裂痕：主線第 1～2 章、雲嶺…」）。"""
    phase: BoardPhaseView | None = None
    """今天所在的那段日程（PNL-1b；名稱與說明分開；賽季進行中才有）。"""
    phases: tuple[BoardPhaseView, ...] = ()
    """全部日程（PNL-1b；依天數；時間軸的階段列）。"""
    upcoming: tuple[BoardMilestoneView, ...] = ()
    """之後的時間點（今天起，依天數）。"""
    milestones: tuple[BoardMilestoneView, ...] = ()
    """全部時間點（PNL-1b；含已過的，依天數；時間軸的釘與完整日程）。"""
    next_refresh_at: int
    """下一次每日刷新的 UTC 秒數。"""
    next_refresh_zh: str
    """例「每天 06:00 刷新」。"""
    refresh_time_zh: str = ""
    """每日刷新的當地時刻（PNL-1b；例「06:00」，懸賞「每天 06:00 換一批」）。"""


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
    """例「懸賞中」「已被 小美 搶下」「你搶下了」（PNL-1b 起不含括號說明，移到
    ``status_note_zh``）。"""
    status_note_zh: str | None = None
    """狀態的補充說明（PNL-1b；例「今天第一次交手打倒仍有小獎：任務幣 1」；說明卡用）。"""


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
    start_day: int = 0
    """第幾天開始（PNL-1b；時間軸的世界事件列）。"""
    end_day: int = 0
    """第幾天結束（含）。"""
    region: str | None = None
    """事件的目標區域（PNL-1b；紋章圖示；沒有區域＝``None``，例：封印共鳴）。"""
    target_note_zh: str | None = None
    """門檻怎麼來的（例「依昨天 4 位冒險者調整」）。"""


class BoardClearedView(_ApiModel):
    """所有人看到的已清空地點（9.6.7 #15）。"""

    location_zh: str
    respawn_at: int


class BoardBossEntryView(_ApiModel):
    """評分榜的一名（Phase 5F-3；#87）。"""

    rank: int
    name: str
    score: int
    rounds: int
    survivors: int
    allies: int
    no_down: bool
    location_zh: str
    """出發挑戰的地點（看的人還沒發現的隱藏地點用提示語，5C-3f）。"""
    mine: bool
    at: int
    titles: tuple[str, ...] = ()
    """這名玩家帳號的紀念稱號（5F-3c；名字旁顯示）。"""


class BoardSeasonBossView(_ApiModel):
    """賽季 Boss 區塊（Phase 5F-3；09 9.7、#87、#100、#101）。"""

    boss: str
    name_zh: str
    status: Literal["sealed", "announced", "open", "closed"]
    status_zh: str
    note_zh: str | None = None
    """例「11 月 10 日 06:00 解鎖」「開放到 11 月 13 日 06:00」。"""
    announce_at: int
    unlock_at: int
    close_at: int
    world_keys: int
    """全服累積的封印鑰匙。"""
    keys_target: int | None = None
    """封印共鳴的門檻（事件還沒開始＝``None``）。"""
    my_keys: int
    keys_required: int
    attempts_left: int
    """這個帳號今天還剩幾次。"""
    daily_attempts: int
    can_challenge: bool
    problem_zh: str | None = None
    """不能挑戰的原因。"""
    first_kill_zh: str | None = None
    first_kill_titles: tuple[str, ...] = ()
    """首殺玩家帳號的紀念稱號（5F-3c；沒有首殺＝空）。"""
    title_zh: str
    board: tuple[BoardBossEntryView, ...] = ()
    """通關評分榜（前 10 名）。"""


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
    """世界事件失敗的建議等級加成（例「灰燼荒原：建議等級 +1」）與商店價格加成（Phase 5F-5b，例
    「鐵娘的廢鐵攤：買價 +20%」）。"""
    season_boss: BoardSeasonBossView | None = None
    """賽季 Boss（Phase 5F-3；沒有賽季 Boss 時 ``None``）。"""
