"""編年史、上季角色與季末重置的 API 型別與組裝（Phase 5F-5；``docs/phases/Phase5計畫.md`` 40.5）。

- ``GET /api/world/chronicle``：所有人可看的編年史（每季：上季角色的紀錄文字、首位發現的配方、
  循環賽最終排名、首殺、賽季 Boss 評分榜前幾名）。角色名、配方名是玩家文字，前端當資料顯示。
- ``GET /api/world/legacy``：自己帳號上季的角色（下季建角色沿用名字與外觀）。
- ``POST /api/world/season/reset``：管理者的季末重置（回 :class:`~trpg.server.season_reset.
  SeasonResetReport`）。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.account_schemas import TitlesOf, no_titles
from trpg.content.library import ContentLibrary
from trpg.server.chronicle import (
    ChronicleHero,
    LeagueChronicleSeason,
    SeasonChronicleEntry,
)
from trpg.server.first_kills import FirstKill
from trpg.server.season_boss_board import BossBoardEntry
from trpg.server.season_reset import season_name_zh
from trpg.shared.rng import MASK64

__all__ = [
    "BOARD_TOP",
    "ChronicleBoardView",
    "ChronicleHeroView",
    "ChronicleKillView",
    "ChronicleRankView",
    "ChronicleRecipeView",
    "ChronicleSeasonView",
    "ChronicleTitles",
    "ChronicleView",
    "LegacyHeroView",
    "SeasonResetRequest",
    "SeasonVerifyRequest",
    "chronicle_view",
    "legacy_view",
]

BOARD_TOP: Final = 5
"""編年史每季列評分榜前幾名。"""


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


@dataclass(frozen=True)
class ChronicleTitles:
    """編年史名字旁的帳號稱號（5F-3c）：依角色 ID 或帳號 ID 查；預設不顯示（沒有帳號）。"""

    of_character: TitlesOf = no_titles
    of_account: TitlesOf = no_titles


_TITLES_DOC: Final = "這名玩家帳號的紀念稱號（5F-3c；名字旁顯示，目前的帳號稱號）。"


class ChronicleHeroView(_ApiModel):
    name: str
    text_zh: str
    titles: list[str] = Field(default_factory=list, description=_TITLES_DOC)


class ChronicleRecipeView(_ApiModel):
    name_zh: str
    discoverer_name: str


class ChronicleKillView(_ApiModel):
    kind: str
    target_name_zh: str
    name: str
    titles: list[str] = Field(default_factory=list, description=_TITLES_DOC)


class ChronicleRankView(_ApiModel):
    rank: int
    name: str
    build_zh: str
    wins: int
    losses: int
    draws: int
    tied: bool
    titles: list[str] = Field(default_factory=list, description=_TITLES_DOC)


class ChronicleBoardView(_ApiModel):
    name: str
    score: int
    rounds: int
    title_zh: str
    titles: list[str] = Field(default_factory=list, description=_TITLES_DOC)


class ChronicleSeasonView(_ApiModel):
    season_id: str
    name_zh: str
    current: bool
    """目前這一季（還沒季末重置：只有首殺、評分榜、循環賽排名）。"""
    started_at: int | None
    reset_at: int | None
    heroes: list[ChronicleHeroView]
    recipes: list[ChronicleRecipeView]
    first_kills: list[ChronicleKillView]
    league: list[ChronicleRankView]
    boss_board: list[ChronicleBoardView]


class ChronicleView(_ApiModel):
    current_season: str
    seasons: list[ChronicleSeasonView]
    """新的季在前；沒有任何紀錄的季不列。"""


class LegacyHeroView(_ApiModel):
    """可以沿用的上季角色。"""

    character_id: str
    season_id: str
    season_name_zh: str
    name: str
    race: str | None
    race_name_zh: str | None
    text_zh: str


class SeasonResetRequest(_ApiModel):
    """季末重置（管理者）。``dry_run`` 預設 ``true``：只列出會清什麼、留什麼。"""

    start_date: dt.date
    """新一季的開賽日（當地日期，刷新時刻開賽）。"""
    season_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$", max_length=32)
    """新一季的 ID；省略＝``s<N+1>``。"""
    seed: int | None = Field(default=None, ge=0, le=MASK64)
    """新一季的種子；省略＝由舊種子＋新季 ID 推。"""
    force: bool = False
    """賽季還沒結束、循環賽沒跑完也重置。"""
    dry_run: bool = True
    confirm_season: str | None = None
    """真的執行時必須等於目前的季 ID。"""


class SeasonVerifyRequest(_ApiModel):
    """從封存重播查證一筆首殺或一場循環賽（5F-5c；舊季讀唯讀封存，目前這一季讀世界資料夾）。"""

    kind: Literal["first_kill", "league_match"]
    season_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=32)
    target: str | None = Field(default=None, max_length=80)
    """``first_kill``：首殺的目標（精英種類或賽季 Boss ID）。"""
    match_id: str | None = Field(default=None, max_length=80)
    """``league_match``：循環賽的場次 ID。"""


def _season_view(
    season_id: str,
    current: str,
    *,
    entry: SeasonChronicleEntry | None,
    league: LeagueChronicleSeason | None,
    kills: list[FirstKill],
    board: list[BossBoardEntry],
    titles: ChronicleTitles,
) -> ChronicleSeasonView:
    return ChronicleSeasonView(
        season_id=season_id,
        name_zh=season_name_zh(season_id),
        current=season_id == current,
        started_at=None if entry is None else entry.started_at,
        reset_at=None if entry is None else entry.reset_at,
        heroes=[]
        if entry is None
        else [
            ChronicleHeroView(
                name=h.name,
                text_zh=h.text_zh,
                titles=list(
                    titles.of_character(h.character_id)
                    if h.account_id is None
                    else titles.of_account(h.account_id)
                ),
            )
            for h in entry.heroes
        ],
        recipes=[]
        if entry is None
        else [
            ChronicleRecipeView(name_zh=r.name_zh, discoverer_name=r.discoverer_name)
            for r in entry.recipes
        ],
        first_kills=[
            ChronicleKillView(
                kind=k.kind,
                target_name_zh=k.target_name_zh,
                name=k.name,
                titles=list(titles.of_character(k.character_id)),
            )
            for k in kills
        ],
        league=[]
        if league is None
        else [
            ChronicleRankView(
                rank=r.rank,
                name=r.name,
                build_zh=r.build_zh,
                wins=r.wins,
                losses=r.losses,
                draws=r.draws,
                tied=r.tied,
                titles=list(titles.of_account(r.account)),
            )
            for r in league.ranks
        ],
        boss_board=[
            ChronicleBoardView(
                name=b.name,
                score=b.score,
                rounds=b.rounds,
                title_zh=b.title_zh,
                titles=list(titles.of_character(b.character_id)),
            )
            for b in board[:BOARD_TOP]
        ],
    )


def chronicle_view(
    current: str,
    seasons: tuple[SeasonChronicleEntry, ...],
    leagues: tuple[LeagueChronicleSeason, ...],
    kills: tuple[FirstKill, ...],
    board: tuple[BossBoardEntry, ...],
    *,
    titles: ChronicleTitles | None = None,
) -> ChronicleView:
    """編年史：季末紀錄的季（依重置時間，新的在前），再加上還沒重置但已有紀錄的季（目前這一季）。
    ``titles``：名字旁的帳號稱號（5F-3c；省略＝不顯示）。"""
    found = ChronicleTitles() if titles is None else titles
    entries = {s.season_id: s for s in seasons}
    league_by = {s.season_id: s for s in leagues}
    order = [s.season_id for s in sorted(seasons, key=lambda s: s.reset_at, reverse=True)]
    others = sorted(
        ({k.season_id for k in kills} | {b.season_id for b in board} | set(league_by)) - set(order)
    )
    ids = [current] if current in others else []
    ids += [s for s in reversed(others) if s != current] + order
    views = [
        _season_view(
            sid,
            current,
            entry=entries.get(sid),
            league=league_by.get(sid),
            kills=[k for k in kills if k.season_id == sid],
            board=[b for b in board if b.season_id == sid],
            titles=found,
        )
        for sid in ids
    ]
    return ChronicleView(current_season=current, seasons=views)


def legacy_view(
    library: ContentLibrary, found: tuple[tuple[SeasonChronicleEntry, ChronicleHero], ...]
) -> list[LegacyHeroView]:
    def race_name(race: str | None) -> str | None:
        if race is None:
            return None
        try:
            return library.ruleset.race_def(race).name_zh
        except KeyError:
            return race

    return [
        LegacyHeroView(
            character_id=hero.character_id,
            season_id=season.season_id,
            season_name_zh=season.name_zh,
            name=hero.name,
            race=hero.race,
            race_name_zh=race_name(hero.race),
            text_zh=hero.text_zh,
        )
        for season, hero in found
    ]
