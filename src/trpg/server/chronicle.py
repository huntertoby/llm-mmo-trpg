"""編年史：影子循環賽的最終排名（Phase 5F-4b；玩法 PM 2026-11-03 代決）。

- 循環賽全部場次跑完時，把最終排名（名次、名字、build 名〔武器・種族〕、勝負和、同分比較用的數字）
  寫進 ``<世界資料夾>/chronicle/league.json``（``trpg-chronicle-league/1``）。
- 這是紀念類（#91，:mod:`trpg.server.season_policy`）：季末保留；同一季重算（規則改了整個重跑）時
  取代那一季的那一筆。循環賽凍結的報名（build 快照）照樣是數值類、季末清掉——編年史只留名字與
  build 名。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.world.save import write_atomic

__all__ = [
    "CHRONICLE_DIR",
    "LEAGUE_CHRONICLE_FORMAT",
    "LeagueChronicle",
    "LeagueChronicleRank",
    "LeagueChronicleSeason",
    "LeagueChronicleStore",
]

LEAGUE_CHRONICLE_FORMAT: Final = "trpg-chronicle-league/1"
CHRONICLE_DIR: Final = "chronicle"


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
        self.path = root / CHRONICLE_DIR / "league.json"
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
