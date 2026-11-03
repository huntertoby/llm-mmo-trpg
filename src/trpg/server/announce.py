"""Discord 公告的資料與文字（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.6）。

- :func:`daily_digest`：讀世界存檔（**唯讀**）算出今日公告要的數字。今日目標、世界事件全服進度走
  接口（:class:`DailyGoalsSource`、:class:`WorldEventSource`；``None``＝沒有資料，模板寫「尚未
  開放」；代決 5E3-2）；5F-1 的真資料是 :class:`SeasonAnnouncements`，``AnnouncementSource`` 有
  內容庫時預設接上。
- 文字一律走模板（``content/world/announcements.yaml``；5E-4 再預產 LLM 文字）。
- 玩家文字（角色名）一律當資料：:func:`safe_text` 中和 Discord 提及、換行換空白、截長度。
- :class:`AnnouncementSource`：Bot（另一個程序）用它取公告文字；只讀世界資料夾，不寫。

時間由呼叫者傳入（伺服器時鐘）；刷新日照 :func:`trpg.world.clock.refresh_day`。
"""

from __future__ import annotations

import datetime as dt
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from pydantic import model_validator

from trpg.content.library import ContentLibrary
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.schemas import ContentModel
from trpg.roguelite.save import default_save_dir
from trpg.server.first_kills import FIRST_KILLS_FILE, FirstKill, load_first_kills
from trpg.world.calendar import day_of
from trpg.world.calendar import season_day as calendar_season_day
from trpg.world.clock import refresh_day
from trpg.world.save import loads_log, loads_world
from trpg.world.season_board import daily_goals_for, players_on, roll_season
from trpg.world.season_boss import boss_def, boss_status, status_note_zh
from trpg.world.state import WorldState

__all__ = [
    "BOT_STATE_FILE",
    "AnnouncementSource",
    "AnnouncementTemplates",
    "DailyDigest",
    "DailyGoal",
    "DailyGoalsSource",
    "SeasonAnnouncements",
    "WorldEventProgress",
    "WorldEventSource",
    "daily_digest",
    "default_bot_state_path",
    "load_templates",
    "location_name",
    "region_name",
    "render_daily",
    "render_first_kill",
    "safe_text",
]

TEMPLATE_PATH: Final = Path("world") / "announcements.yaml"
BOT_STATE_FILE: Final = Path("bot") / "announce_state.json"
NAME_LIMIT: Final = 40
ZERO_WIDTH: Final = "\u200b"

TEMPLATE_VARS: Final[Mapping[str, frozenset[str]]] = {
    "daily": frozenset(
        {
            "date",
            "season_day",
            "active_yesterday",
            "threads",
            "cleared",
            "first_kills",
            "goals",
            "events",
            "season_boss",
            "public_url",
        }
    ),
    "goals_none": frozenset(),
    "goal_line": frozenset({"text"}),
    "events_none": frozenset(),
    "event_line": frozenset({"name", "progress", "target"}),
    "public_url_line": frozenset({"public_url"}),
    "first_kill": frozenset({"name", "target"}),
    "season_boss_line": frozenset({"name", "status", "note"}),
    "season_boss_first_kill": frozenset({"name", "target"}),
}
"""每個模板可用的變數（用到別的 → 載入錯誤）。"""


class AnnouncementTemplates(ContentModel):
    """``content/world/announcements.yaml``。"""

    daily: str
    goals_none: str
    goal_line: str
    events_none: str
    event_line: str
    public_url_line: str
    first_kill: str
    season_boss_line: str = ""
    """今日公告的賽季 Boss 一行（Phase 5F-3；空＝不寫）。"""
    season_boss_first_kill: str = ""
    """賽季 Boss 首殺的公告（Phase 5F-3；空＝用 ``first_kill``）。"""

    @model_validator(mode="after")
    def _known_variables(self) -> AnnouncementTemplates:
        for field, allowed in TEMPLATE_VARS.items():
            template = string.Template(getattr(self, field))
            if not template.is_valid():
                raise ValueError(f"模板 {field} 的 $ 寫法不合法")
            unknown = sorted(set(template.get_identifiers()) - allowed)
            if unknown:
                raise ValueError(f"模板 {field} 用到不認得的變數：{'、'.join(unknown)}")
        return self


def load_templates(content_dir: Path | None = None) -> AnnouncementTemplates:
    root = default_content_dir() if content_dir is None else content_dir
    return load_content_file(root / TEMPLATE_PATH, AnnouncementTemplates)


def safe_text(text: str, limit: int = NAME_LIMIT) -> str:
    """玩家文字放進公告前：控制字元換空白、``@`` 後插零寬字元（``@everyone``、``<@id>`` 都不會
    提及）、截到 ``limit`` 字。"""
    cleaned = "".join(" " if not ch.isprintable() else ch for ch in text).strip()
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1] + "…"
    return cleaned.replace("@", "@" + ZERO_WIDTH)


@dataclass(frozen=True)
class DailyGoal:
    """一個今日目標（5F-1 實作來源）。"""

    text: str


@dataclass(frozen=True)
class WorldEventProgress:
    """一個世界事件的全服進度（#103；5F-1 實作來源）。"""

    name: str
    progress: int
    target: int


class DailyGoalsSource(Protocol):
    """今日目標的接口（5F-1）。"""

    def daily_goals(self, world: WorldState, now: int) -> Sequence[DailyGoal]: ...


class WorldEventSource(Protocol):
    """世界事件全服進度的接口（5F-1；門檻依前一天上線人數調整，#103）。"""

    def world_events(self, world: WorldState, now: int) -> Sequence[WorldEventProgress]: ...


@dataclass(frozen=True)
class DailyDigest:
    """今日公告的數字。``goals``／``events`` 為 ``None``＝還沒有資料來源。"""

    date: str
    season_day: int
    active_yesterday: int
    threads: int
    cleared: int
    first_kills: int
    goals: tuple[DailyGoal, ...] | None = None
    events: tuple[WorldEventProgress, ...] | None = None
    season_boss: tuple[str, str, str] | None = None
    """賽季 Boss 的（名字、狀態、說明）（Phase 5F-3；``None``＝沒有賽季 Boss）。"""


def _date_of(day: int) -> str:
    return (dt.date(1970, 1, 1) + dt.timedelta(days=day)).isoformat()


def _active_on(world_dir: Path, day: int) -> int:
    path = world_dir / "log.jsonl"
    if not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return 0
    return len({e.character_id for e in loads_log(text) if refresh_day(e.now) == day})


class SeasonAnnouncements:
    """今日目標與世界事件進度的真資料（Phase 5F-1）：實作 :class:`DailyGoalsSource`、
    :class:`WorldEventSource`。``world`` 要是換日後的世界（:func:`daily_digest` 會先換日）。"""

    def __init__(self, library: ContentLibrary) -> None:
        self.library = library

    def daily_goals(self, world: WorldState, now: int) -> Sequence[DailyGoal]:
        goals = daily_goals_for(self.library, world, day_of(self.library, now))
        return [DailyGoal(g.text_zh) for g in goals]

    def world_events(self, world: WorldState, now: int) -> Sequence[WorldEventProgress]:
        del now
        season = self.library.world_season
        if season is None:
            return []
        found: list[WorldEventProgress] = []
        for event in season.world_events:
            state = world.world_event(event.id)
            if state is None:
                continue
            suffix = {"succeeded": "（成功）", "failed": "（失敗）"}.get(state.status, "")
            found.append(WorldEventProgress(event.name_zh + suffix, state.progress, state.target))
        return found


def daily_digest(
    world_dir: Path,
    now: int,
    *,
    goals: DailyGoalsSource | None = None,
    world_events: WorldEventSource | None = None,
    library: ContentLibrary | None = None,
) -> DailyDigest | None:
    """``now`` 這個刷新日的公告數字；世界還沒建立（沒有 ``world.json``）＝``None``。

    ``library`` 有給時（5F-1）：日子照世界規則的日曆、世界先換日（只算不寫）、昨天的上線人數用
    世界狀態裡的帳號數（和世界事件門檻同一個數字；沒有紀錄時退回日誌裡的角色數）。"""
    path = world_dir / "world.json"
    if not path.is_file():
        return None
    world = loads_world(path.read_text(encoding="utf-8"))
    if library is None:
        today = refresh_day(now)
        season_day = max(1, today - refresh_day(world.season_start) + 1)
        active = _active_on(world_dir, today - 1)
    else:
        world = roll_season(library, world, now)[0]
        today = day_of(library, now)
        season_day = calendar_season_day(library, world, now)
        recorded = any(a.day == today - 1 for a in world.activity)
        active = players_on(world, today - 1) if recorded else _active_on(world_dir, today - 1)
    return DailyDigest(
        date=_date_of(today),
        season_day=season_day,
        active_yesterday=active,
        threads=len(world.threads),
        cleared=sum(1 for c in world.cleared if now < c.respawn_at),
        first_kills=sum(k.kind == "elite" for k in load_first_kills(world_dir / FIRST_KILLS_FILE)),
        goals=tuple(goals.daily_goals(world, now)) if goals is not None else None,
        events=tuple(world_events.world_events(world, now)) if world_events is not None else None,
        season_boss=None if library is None else _season_boss_line(library, world, now),
    )


_BOSS_STATUS_ZH: Final = {
    "sealed": "封印中",
    "announced": "即將解鎖",
    "open": "已解鎖",
    "closed": "本季挑戰已結束",
}


def _season_boss_line(
    library: ContentLibrary, world: WorldState, now: int
) -> tuple[str, str, str] | None:
    """今日公告的賽季 Boss：封印中、即將解鎖（解鎖前 24 小時公告，09 9.7）、已解鎖、已結束。"""
    boss = boss_def(library)
    status = boss_status(library, world, now)
    if boss is None or status is None:
        return None
    return boss.name_zh, _BOSS_STATUS_ZH[status], status_note_zh(library, world, now) or ""


def _sub(template: str, **values: object) -> str:
    return string.Template(template).safe_substitute({k: str(v) for k, v in values.items()})


def render_daily(
    templates: AnnouncementTemplates, digest: DailyDigest, *, public_url: str = ""
) -> str:
    if digest.goals:
        goals = "\n".join(_sub(templates.goal_line, text=safe_text(g.text)) for g in digest.goals)
    else:
        goals = templates.goals_none
    if digest.events:
        events = "\n".join(
            _sub(
                templates.event_line,
                name=safe_text(e.name),
                progress=e.progress,
                target=e.target,
            )
            for e in digest.events
        )
    else:
        events = templates.events_none
    url = _sub(templates.public_url_line, public_url=public_url) if public_url else ""
    boss = ""
    if digest.season_boss is not None and templates.season_boss_line:
        name, status, note = digest.season_boss
        boss = _sub(templates.season_boss_line, name=name, status=status, note=note)
    return _sub(
        templates.daily,
        date=digest.date,
        season_day=digest.season_day,
        active_yesterday=digest.active_yesterday,
        threads=digest.threads,
        cleared=digest.cleared,
        first_kills=digest.first_kills,
        goals=goals,
        events=events,
        season_boss=boss,
        public_url=url,
    )


def region_name(library: ContentLibrary, region: str) -> str:
    regions = library.regions.region_by_id() if library.regions is not None else {}
    found = regions.get(region)
    return found.name_zh if found is not None else region


def location_name(library: ContentLibrary, region: str, location: str) -> str:
    world_map = library.world_maps.get(region)
    found = world_map.location_by_id().get(location) if world_map is not None else None
    return found.name_zh if found is not None else location


def render_first_kill(
    templates: AnnouncementTemplates, kill: FirstKill, library: ContentLibrary | None = None
) -> str:
    """首殺公告只說「誰打倒了什麼」，不說地點（5E-3b，玩法 PM 代決、9.6.10）：模板只認
    ``$name``、``$target``，寫了 ``$location``／``$region`` 會載入錯誤。``library`` 留著相容。"""
    del library
    template = templates.first_kill
    if kill.kind == "season_boss" and templates.season_boss_first_kill:  # 5F-3
        template = templates.season_boss_first_kill
    return _sub(template, name=safe_text(kill.name), target=kill.target_name_zh)


def default_bot_state_path(save_dir: Path | None = None) -> Path:
    """Bot 的公告狀態檔：``<存檔資料夾>/bot/announce_state.json``。"""
    return (save_dir if save_dir is not None else default_save_dir()) / BOT_STATE_FILE


class AnnouncementSource:
    """Bot 取公告文字的地方（只讀世界資料夾）。"""

    def __init__(
        self,
        world_dir: Path | None = None,
        *,
        templates: AnnouncementTemplates | None = None,
        library: ContentLibrary | None = None,
        public_url: str = "",
        goals: DailyGoalsSource | None = None,
        world_events: WorldEventSource | None = None,
    ) -> None:
        self.world_dir = world_dir if world_dir is not None else default_save_dir() / "world"
        self.templates = templates if templates is not None else load_templates()
        self.library = library
        self.public_url = public_url
        season = None if library is None else SeasonAnnouncements(library)  # 5F-1 預設接上
        self.goals = goals if goals is not None else season
        self.world_events = world_events if world_events is not None else season

    def daily_text(self, now: int) -> str | None:
        """今日公告；世界還沒建立＝``None``（不貼）。"""
        digest = daily_digest(
            self.world_dir,
            now,
            goals=self.goals,
            world_events=self.world_events,
            library=self.library,
        )
        if digest is None:
            return None
        return render_daily(self.templates, digest, public_url=self.public_url)

    def first_kills(self) -> tuple[FirstKill, ...]:
        return load_first_kills(self.world_dir / FIRST_KILLS_FILE)

    def first_kill_text(self, kill: FirstKill) -> str:
        return render_first_kill(self.templates, kill, self.library)
