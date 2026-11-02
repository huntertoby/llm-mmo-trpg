"""世界時鐘（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.3）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from trpg.world.clock import (
    GAME_DAY_SECONDS,
    WEATHER_PERIOD_SECONDS,
    day_phase,
    game_clock,
    game_day_index,
    half_day_index,
    next_refresh_at,
    refresh_day,
)

TAIPEI = timezone(timedelta(hours=8))


def _ts(day: int, hour: int, minute: int = 0, second: int = 0) -> int:
    """2026 年 11 月 ``day`` 日的台北時間 → UTC 秒。"""
    return int(datetime(2026, 11, day, hour, minute, second, tzinfo=TAIPEI).timestamp())


def test_constants_match_design() -> None:
    assert GAME_DAY_SECONDS == 30 * 60  # 一天＝現實 30 分鐘
    assert WEATHER_PERIOD_SECONDS == 15 * 60  # 半天換天氣


def test_taipei_six_am_starts_a_game_day() -> None:
    six = _ts(2, 6, 0, 0)
    assert six % GAME_DAY_SECONDS == 0
    assert game_day_index(six) == game_day_index(six - 1) + 1
    assert game_clock(six) == (6, 0)
    assert day_phase(six) == "day"


def test_day_and_night_halves() -> None:
    start = _ts(2, 6, 0, 0)
    assert day_phase(start + WEATHER_PERIOD_SECONDS - 1) == "day"
    assert day_phase(start + WEATHER_PERIOD_SECONDS) == "night"
    assert day_phase(start + GAME_DAY_SECONDS - 1) == "night"
    assert day_phase(start + GAME_DAY_SECONDS) == "day"
    assert half_day_index(start + WEATHER_PERIOD_SECONDS) == half_day_index(start) + 1


def test_game_clock_runs_24_hours_in_30_minutes() -> None:
    start = _ts(2, 6, 0, 0)
    assert game_clock(start + WEATHER_PERIOD_SECONDS) == (18, 0)
    assert game_clock(start + 75) == (7, 0)  # 遊戲 1 小時＝現實 75 秒
    assert game_clock(start + 1350) == (0, 0)
    assert game_clock(start + GAME_DAY_SECONDS - 1)[0] == 5


def test_refresh_day_switches_at_six_taipei() -> None:
    before = _ts(2, 5, 59, 59)
    at = _ts(2, 6, 0, 0)
    assert refresh_day(at) == refresh_day(before) + 1
    assert refresh_day(_ts(3, 5, 59, 59)) == refresh_day(at)
    assert refresh_day(_ts(2, 23, 0, 0)) == refresh_day(at)


def test_next_refresh_at() -> None:
    at = _ts(2, 6, 0, 0)
    assert next_refresh_at(at - 1) == at
    assert next_refresh_at(at) == _ts(3, 6, 0, 0)
    noon = _ts(2, 12, 0, 0)
    assert datetime.fromtimestamp(next_refresh_at(noon), tz=UTC).hour == 22  # UTC 22:00


@pytest.mark.parametrize("bad", [-1, -1800])
def test_negative_time_rejected(bad: int) -> None:
    with pytest.raises(ValueError, match="不可為負"):
        game_day_index(bad)


def test_non_int_rejected() -> None:
    with pytest.raises(TypeError):
        refresh_day(1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        day_phase(True)
