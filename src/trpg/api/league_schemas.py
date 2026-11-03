"""影子循環賽的 API 格式（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.7）。

全部由後端算好（前端不寫規則）；排行榜是給別人看的，地點名已套過隱藏地點的提示語（5C-3f）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.api.schemas import BattleResponse
from trpg.api.world_party_schemas import AiChoiceView

__all__ = [
    "LeagueAllocationView",
    "LeagueEntryView",
    "LeagueMatchView",
    "LeagueReplayResponse",
    "LeagueRunView",
    "LeagueStandingView",
    "LeagueStatus",
    "LeagueView",
]

type LeagueStatus = Literal["none", "signup", "closed", "running", "done"]
"""沒有循環賽／報名中／已截止（還沒開跑）／進行中／已結束。"""


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LeagueEntryView(_ApiModel):
    """看的人的帳號報名的角色。"""

    character_id: str
    name: str
    ai: str | None
    ai_zh: str
    """打法名稱（「預設」＝自己影子的預設打法）。"""
    this_character: bool
    """報名的就是現在這個角色。"""
    allocation: dict[str, int] | None = None
    """（5F-4b）報名時自己配的屬性點（``None``＝照自動配點）。"""


class LeagueAllocationView(_ApiModel):
    """（5F-4b，#32）報名時的免費重新配點：拉到等級上限後全部可配的點（已分配的＋未分配的＋升到
    上限多出的）。前端用既有的配點元件；不配＝照 ``auto``。"""

    base: dict[str, int]
    """重新分配前的屬性（目前的屬性扣掉已分配的點）。"""
    points: int
    """可以分配的點數（總和必須剛好等於這個）。"""
    auto: dict[str, int]
    """不自己配時的配點（已分配的不動＋新增的點補到主屬性）。"""


class LeagueStandingView(_ApiModel):
    """排行榜的一列（代決 5F4-7、5F4-8）。"""

    rank: int | None
    """名次（同分同名次）；還沒開跑＝``None``。"""
    name: str
    level: int
    """對戰時的等級（拉到上限）。"""
    role_zh: str
    """定位：武器・種族。"""
    place_zh: str
    """報名時所在的地點（看的人還沒發現的隱藏地點用提示語，5C-3f）。"""
    wins: int
    losses: int
    draws: int
    played: int
    mine: bool
    """看的人自己的帳號。"""
    hp_permille_total: int = 0
    """（5F-4b）所有場次己方剩餘 HP 比例（‰）合計（同勝場時比這個，6.8 BAL-12a）。"""
    rounds_total: int = 0
    """（5F-4b）總輪數（再同分時少的勝）。"""
    tied: bool = False
    """（5F-4b）和別人同名次（三項都相同，獎金平分）。"""


class LeagueMatchView(_ApiModel):
    id: str
    ally_name: str
    """先手、站我方起始區的那位。"""
    enemy_name: str
    map_zh: str
    seed_index: int
    status: Literal["pending", "done", "error"]
    result_zh: str
    """例「阿霧勝（12 輪）」「和局（30 輪）」「尚未進行」「出錯：…」。"""
    mine: bool
    replayable: bool
    replay_problem_zh: str | None = None
    """（5F-4b）不能重播的原因（例「規則已變、不能重播」）；能重播或還沒打＝``None``。"""


class LeagueView(_ApiModel):
    """``GET /api/world/characters/{id}/league``。"""

    status: LeagueStatus
    status_zh: str
    season_day: int
    signup_close_day: int
    maps_zh: tuple[str, ...]
    per_pair: int
    """每對組合打幾場（地圖 × 種子 × 交換先後手）。"""
    rules_zh: str
    """一行規則說明（拉到等級上限、1 對 1、雙方都由 AI 操作）。"""
    entry: LeagueEntryView | None
    can_enter: bool
    enter_problem_zh: str | None
    can_withdraw: bool
    ai_choices: tuple[AiChoiceView, ...]
    entrants: int
    standings: tuple[LeagueStandingView, ...]
    matches: tuple[LeagueMatchView, ...]
    """這一頁的場次（自己帳號的場次在前，其他依編號；5F-4b 分頁）。"""
    done: int
    total: int
    champion_zh: str | None
    """全部跑完後的冠軍（同分都列，註明平分獎金）。"""
    page: int = 1
    """（5F-4b）場次列表的第幾頁（1 起）。"""
    pages: int = 1
    """（5F-4b）場次列表共幾頁（至少 1）。"""
    page_size: int = 20
    allocation: LeagueAllocationView | None = None
    """（5F-4b）這個角色報名時可以重新配點的資料（不能報名、這一季沒有循環賽時 ``None``）。"""
    stale_zh: str | None = None
    """（5F-4b）賽程是用舊規則跑的：「規則已變、不能重播」＋管理者重新開跑會整個重跑的說明。"""
    reruns: int = 0
    """（5F-4b）因為規則改了整個重跑過幾次。"""


class LeagueRunView(_ApiModel):
    """``POST /api/world/league/run``（管理者）。"""

    started: bool
    """這次有開一條背景執行緒（已經在跑時為 ``False``）。"""
    done: int
    total: int


class LeagueReplayResponse(_ApiModel):
    """``POST …/league/matches/{match_id}/replay``：從開場播到結束的戰鬥（既有戰鬥畫面）。"""

    title_zh: str
    battle: BattleResponse
    verified: bool
    """依紀錄的步驟重播出的最終狀態和紀錄裡存的一致。"""
    outcome_zh: str
    """（5F-4b）結束面板的中性勝負文字：「某某 勝」或「和局」。"""
