"""賽季日曆（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.3）。

每日刷新的時區與當地時刻在世界規則的 ``calendar``（預設台北 6 點，``docs/專案計畫.md`` 3.1）；
所有「每天一次」的判定（感知判定、聊天好感度、懸賞、今日目標…）都用 :func:`day_of`，換時區只改資料。
賽季天數在 ``content/world/season.yaml``；開賽時間是 :attr:`WorldState.season_start`（伺服器設定的
開賽日，或第一次建立世界的當下）。

純函式：``now`` 由呼叫者傳入（UTC 秒數）。
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.world_rules import CalendarRules
from trpg.world.clock import day_start_at, next_refresh_at, refresh_day
from trpg.world.state import WorldState

__all__ = [
    "SeasonStatus",
    "calendar_of",
    "day_of",
    "day_start",
    "local_date",
    "local_time_zh",
    "next_refresh",
    "season_day",
    "season_start_at",
    "season_status",
]

type SeasonStatus = Literal["upcoming", "running", "ended"]

_EPOCH = dt.date(1970, 1, 1)


def calendar_of(library: ContentLibrary) -> CalendarRules:
    """世界規則的日曆；沒有世界規則時用預設（台北 6 點）。"""
    rules = library.world_rules
    return CalendarRules() if rules is None else rules.calendar


def day_of(library: ContentLibrary, now: int) -> int:
    """``now`` 的刷新日（以當地刷新時刻為界的第幾天）。"""
    cal = calendar_of(library)
    return refresh_day(
        now, utc_offset_minutes=cal.utc_offset_minutes, refresh_hour=cal.refresh_hour
    )


def day_start(library: ContentLibrary, day: int) -> int:
    """刷新日 ``day`` 開始的 UTC 秒數。"""
    cal = calendar_of(library)
    return day_start_at(
        day, utc_offset_minutes=cal.utc_offset_minutes, refresh_hour=cal.refresh_hour
    )


def next_refresh(library: ContentLibrary, now: int) -> int:
    """下一次每日刷新的 UTC 秒數（嚴格大於 ``now``）。"""
    cal = calendar_of(library)
    return next_refresh_at(
        now, utc_offset_minutes=cal.utc_offset_minutes, refresh_hour=cal.refresh_hour
    )


def local_date(day: int) -> dt.date:
    """刷新日 ``day`` 對應的當地日期。"""
    return _EPOCH + dt.timedelta(days=day)


def local_time_zh(library: ContentLibrary, at: int) -> str:
    """UTC 秒 → 當地時間「11 月 10 日 06:00」（時區照日曆；Phase 5F-3 賽季 Boss 的解鎖時間）。"""
    offset = calendar_of(library).utc_offset_minutes * 60
    local = dt.datetime.fromtimestamp(at + offset, tz=dt.UTC)
    return f"{local.month} 月 {local.day} 日 {local.hour:02d}:{local.minute:02d}"


def season_start_at(library: ContentLibrary, date: dt.date) -> int:
    """開賽日 ``date``（當地日期）刷新時刻的 UTC 秒數。"""
    return day_start(library, (date - _EPOCH).days)


def season_day(library: ContentLibrary, world: WorldState, now: int) -> int:
    """賽季第幾天（開賽那個刷新日＝第 1 天；開賽前也回 1）。"""
    return max(1, day_of(library, now) - day_of(library, world.season_start) + 1)


def season_status(library: ContentLibrary, world: WorldState, now: int) -> SeasonStatus:
    """開賽前、進行中或已結束（超過 ``season.yaml`` 的天數；沒有賽季資料時一直進行中）。"""
    if now < world.season_start:
        return "upcoming"
    season = library.world_season
    if season is not None and season_day(library, world, now) > season.days:
        return "ended"
    return "running"
