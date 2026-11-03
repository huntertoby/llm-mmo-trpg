"""編年史：影子循環賽的最終排名（Phase 5F-4b；玩法 PM 2026-11-03 代決）。

- 循環賽全部場次跑完時，把最終排名（名次、名字、build 名〔武器・種族〕、勝負和、同分比較用的數字）
  寫進 ``<世界資料夾>/chronicle/league.json``（``trpg-chronicle-league/1``）。
- 這是紀念類（#91，:mod:`trpg.server.season_policy`）：季末保留；同一季重算（規則改了整個重跑）時
  取代那一季的那一筆。循環賽凍結的報名（build 快照）照樣是數值類、季末清掉——編年史只留名字與
  build 名。
- 季末紀錄（Phase 5F-5）：``<世界資料夾>/chronicle/seasons.json``（``trpg-chronicle-seasons/1``）。
  季末重置時寫：上季每個角色的編年史文字（打過的精英、完成的事件）與名字、外觀（下季建角色可以
  沿用），以及配方的首位發現者。紀念類。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import DollLook
from trpg.content.races import RaceLook
from trpg.world.layout import CHRONICLE_DIR, LEAGUE_CHRONICLE_FILE, SEASON_CHRONICLE_FILE
from trpg.world.save import write_atomic

__all__ = [
    "CHRONICLE_DIR",
    "LEAGUE_CHRONICLE_FORMAT",
    "RACE_DOLL_FIELDS",
    "SEASON_CHRONICLE_FILE",
    "SEASON_CHRONICLE_FORMAT",
    "ChronicleHero",
    "LeagueChronicle",
    "LeagueChronicleRank",
    "LeagueChronicleSeason",
    "LeagueChronicleStore",
    "RecipeDiscovery",
    "SeasonChronicle",
    "SeasonChronicleEntry",
    "SeasonChronicleStore",
    "legacy_doll",
]

LEAGUE_CHRONICLE_FORMAT: Final = "trpg-chronicle-league/1"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LeagueChronicleRank(_Model):
    """編年史裡的一列最終排名。"""

    rank: int = Field(ge=1)
    account: str
    name: str
    """報名時的角色名。"""
    build_zh: str
    """build 名（影子的定位：武器・種族）。"""
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    draws: int = Field(ge=0)
    hp_permille_total: int = Field(ge=0)
    """所有場次己方剩餘 HP 比例（‰）的合計（同勝場時比這個，6.8 BAL-12a）。"""
    rounds_total: int = Field(ge=0)
    """所有場次的總輪數（再同分時少的勝）。"""
    tied: bool = False
    """和別人同名次（獎金平分）。"""


class LeagueChronicleSeason(_Model):
    """一季循環賽的最終排名。"""

    season_id: str
    finished_at: int = Field(ge=0)
    matches: int = Field(ge=0)
    ranks: tuple[LeagueChronicleRank, ...]


class LeagueChronicle(_Model):
    """``chronicle/league.json``。"""

    format: Literal["trpg-chronicle-league/1"] = LEAGUE_CHRONICLE_FORMAT
    seasons: tuple[LeagueChronicleSeason, ...] = ()


class LeagueChronicleStore:
    """``<root>/chronicle/league.json`` 的讀寫（檔案不存在＝沒有紀錄）。"""

    def __init__(self, root: Path) -> None:
        self.path = root / CHRONICLE_DIR / LEAGUE_CHRONICLE_FILE
        self._lock = threading.Lock()

    def load(self) -> LeagueChronicle:
        if not self.path.is_file():
            return LeagueChronicle()
        return LeagueChronicle.model_validate_json(self.path.read_text(encoding="utf-8"))

    def season(self, season_id: str) -> LeagueChronicleSeason | None:
        return next((s for s in self.load().seasons if s.season_id == season_id), None)

    def write(self, season: LeagueChronicleSeason) -> None:
        """寫入（同一季的舊紀錄被取代；依賽季 ID 排序）。"""
        with self._lock:
            kept = [s for s in self.load().seasons if s.season_id != season.season_id]
            seasons = tuple(sorted([*kept, season], key=lambda s: s.season_id))
            data = LeagueChronicle(seasons=seasons).model_dump(mode="json")
            write_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


# ---------------------------------------------------------------------------
# 季末紀錄（Phase 5F-5）
# ---------------------------------------------------------------------------

SEASON_CHRONICLE_FORMAT: Final = "trpg-chronicle-seasons/1"


class ChronicleHero(_Model):
    """上季的一個角色：編年史文字＋下季可以沿用的名字與外觀（5F-5，玩法 PM 2026-11-03 代決）。"""

    character_id: str
    account_id: str | None = None
    """角色的帳號（沒有帳號的開發模式角色＝``None``）。"""
    name: str
    """角色名（玩家文字；顯示時當資料）。"""
    race: str | None = None
    """上季的種族。種族不算外觀（5F-5c，玩法 PM 2026-11-03 代決）：下季建角色時當預設，
    可以免費改。"""
    doll: DollLook | None = None
    """紙娃娃外觀（下季建角色沿用；種族改了時，跟著種族的部件改回預設，:func:`legacy_doll`）。"""
    level: int | None = None
    """季末的等級（5F-5c；舊紀錄沒有＝``None``）。"""
    elites: tuple[str, ...] = ()
    """擊倒過的精英（中文名，依精英種類 ID 排序；來自 ``CharacterState.elite_kills``；5F-5c 起
    不含區域 Boss）。"""
    bosses: tuple[str, ...] = ()
    """打倒過的 Boss（5F-5c：區域 Boss 的中文名，再加賽季 Boss）。"""
    first_kills: tuple[str, ...] = ()
    """這一季的全服首殺（5F-5c；目標中文名，依日誌序號）。"""
    chapters: tuple[str, ...] = ()
    """完成的主線章節（5F-5c；任務名）。"""
    events: tuple[str, ...] = ()
    """完成的事件（「誰：想要什麼」，依骨架 ID 排序；來自
    ``CharacterState.finished_skeletons``）。"""
    recipes: tuple[str, ...] = ()
    """首位發現的配方（5F-5c；配方名，依配方碼）。"""
    league_rank: int | None = None
    """影子循環賽的最終名次（5F-5c；沒參加＝``None``）。"""
    text_zh: str
    """編年史的一行文字（模板在 ``world/season.yaml`` 的 ``chronicle``，5F-5c）。"""


class RecipeDiscovery(_Model):
    """配方的首位發現者（``RecipeRecord`` 的紀念類欄位；配方內容季末清掉）。"""

    code: str
    name_zh: str
    discoverer: str
    discoverer_name: str
    discovered_at: int = Field(ge=0)
    season_id: str


class SeasonChronicleEntry(_Model):
    """一季的季末紀錄。"""

    season_id: str
    name_zh: str
    """季名（「第一季」）。"""
    started_at: int = Field(ge=0)
    reset_at: int = Field(ge=0)
    """季末重置的時間（UTC 秒）。"""
    next_season_id: str
    heroes: tuple[ChronicleHero, ...] = ()
    """依角色 ID 排序。"""
    recipes: tuple[RecipeDiscovery, ...] = ()
    """依配方碼排序。"""


class SeasonChronicle(_Model):
    """``chronicle/seasons.json``。"""

    format: Literal["trpg-chronicle-seasons/1"] = SEASON_CHRONICLE_FORMAT
    seasons: tuple[SeasonChronicleEntry, ...] = ()


class SeasonChronicleStore:
    """``<root>/chronicle/seasons.json`` 的讀寫（檔案不存在＝沒有紀錄）。"""

    def __init__(self, root: Path) -> None:
        self.path = root / CHRONICLE_DIR / SEASON_CHRONICLE_FILE
        self._lock = threading.Lock()

    def load(self) -> SeasonChronicle:
        if not self.path.is_file():
            return SeasonChronicle()
        return SeasonChronicle.model_validate_json(self.path.read_text(encoding="utf-8"))

    def season(self, season_id: str) -> SeasonChronicleEntry | None:
        return next((s for s in self.load().seasons if s.season_id == season_id), None)

    def add(self, entry: SeasonChronicleEntry) -> bool:
        """加一季（同一季已有就不覆寫：季末重置中斷後重跑，不會用半套資料蓋掉）。回傳有沒有寫。"""
        with self._lock:
            current = self.load()
            if any(s.season_id == entry.season_id for s in current.seasons):
                return False
            seasons = tuple(sorted([*current.seasons, entry], key=lambda s: s.reset_at))
            data = SeasonChronicle(seasons=seasons).model_dump(mode="json", exclude_none=True)
            write_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
            return True

    def heroes(self) -> tuple[tuple[SeasonChronicleEntry, ChronicleHero], ...]:
        """所有上季角色（新的季在前）。"""
        seasons = sorted(self.load().seasons, key=lambda s: s.reset_at, reverse=True)
        return tuple((s, h) for s in seasons for h in s.heroes)


RACE_DOLL_FIELDS: Final[tuple[str, ...]] = ("skin", "hair", "hair_color", "eyes", "skull")
"""紙娃娃裡跟著種族的部件（Phase 5F-5c）：膚色、髮型、髮色、眼睛、骷髏（前端畫圖時這些也會被種族的
預設外觀蓋過，``client/src/render/appearance.ts``）。裝備、褲子、飾邊、主手材質與外光不跟種族。"""


def legacy_doll(
    doll: DollLook,
    *,
    legacy_race: str | None,
    race: str | None,
    base: DollLook | None,
    race_look: RaceLook | None = None,
) -> DollLook | None:
    """沿用上季的紙娃娃（5F-5c；5F-3c 玩法 PM 2026-11-03 代決）：種族沒改＝原樣；改了＝
    :data:`RACE_DOLL_FIELDS` 每一項，目前的值新種族也有就保留，沒有才換成新角色範本的預設
    （``base``；範本沒有紙娃娃＝整個用預設 ``None``）。

    「新種族也有」＝等於新角色範本的預設值，或等於新種族外觀（``race_look``，``races.yaml`` 的
    ``look``）同名欄位的值；種族外觀沒有的欄位（``skull``）只比範本。種族目前每一項只有一個值、
    沒有可選清單，所以這是最保守的判斷（5F-3c 待 PM 決定）。"""
    if race == legacy_race:
        return doll
    if base is None:
        return None
    update: dict[str, object] = {}
    for name in RACE_DOLL_FIELDS:
        current = getattr(doll, name)
        allowed = [getattr(base, name)]
        if race_look is not None and name in RaceLook.model_fields:
            allowed.append(getattr(race_look, name))
        if current not in allowed:
            update[name] = getattr(base, name)
    return doll.model_copy(update=update)
