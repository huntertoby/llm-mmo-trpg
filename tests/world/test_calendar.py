"""賽季日曆（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.3）。"""

from __future__ import annotations

import datetime as dt

from tests.world.helpers import NOON, make_world, with_rules
from trpg.content.library import ContentLibrary
from trpg.world.calendar import (
    day_of,
    day_start,
    local_date,
    next_refresh,
    season_day,
    season_start_at,
    season_status,
)
from trpg.world.clock import next_refresh_at, refresh_day

DAY = 24 * 3600


def test_default_calendar_matches_clock_constants(library: ContentLibrary) -> None:
    for now in (NOON, NOON + 7 * 3600, NOON - 7 * 3600, NOON + 18 * 3600):
        assert day_of(library, now) == refresh_day(now)
        assert next_refresh(library, now) == next_refresh_at(now)


def test_other_time_zone_and_hour(library: ContentLibrary) -> None:
    utc = with_rules(library, calendar={"utc_offset_minutes": 0, "refresh_hour": 0})
    midnight = 1_793_577_600  # 2026-11-02 00:00 UTC
    assert local_date(day_of(utc, midnight)) == dt.date(2026, 11, 2)
    assert day_of(utc, midnight - 1) == day_of(utc, midnight) - 1
    assert next_refresh(utc, midnight) == midnight + DAY
    assert day_start(utc, day_of(utc, midnight)) == midnight


def test_season_start_from_date(library: ContentLibrary) -> None:
    start = season_start_at(library, dt.date(2026, 11, 10))
    assert dt.datetime.fromtimestamp(start, tz=dt.UTC).hour == 22  # 台北 06:00＝UTC 22:00（前一天）
    assert local_date(day_of(library, start)) == dt.date(2026, 11, 10)
    assert day_of(library, start - 1) == day_of(library, start) - 1


def test_season_day_and_status(library: ContentLibrary) -> None:
    world = make_world()
    assert season_day(library, world, NOON) == 1
    assert season_day(library, world, NOON + 13 * DAY) == 14
    assert season_status(library, world, NOON) == "running"
    assert season_status(library, world, NOON + 14 * DAY) == "ended"
    assert season_status(library, world, NOON - 60) == "upcoming"
    assert season_day(library, world, NOON - DAY) == 1
