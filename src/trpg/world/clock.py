"""世界時鐘（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.3）。

- 遊戲內一天＝現實 30 分鐘（``docs/專案計畫.md`` 3.1、09 9.6.9）。
- 每區天氣每半天（現實 15 分鐘）換一次（09 9.6.10 #104）。
- 每日刷新：現實早上 6 點（Asia/Taipei，3.1）。時區用固定 +8 小時位移，不讀系統時區資料（2.1）。

全部是純函式：時間 ``now`` 是 UTC 秒數整數，由呼叫端（API 層）讀時鐘後傳入；本模組不讀時間。

遊戲日以 Unix 紀元對齊（代決 5A2-2）：台北 06:00＝UTC 22:00＝79200 秒，是 1800 的倍數，所以每天的
刷新點一定是某個遊戲日的開頭。遊戲日從遊戲內 06:00 開始，前半（06:00～18:00）是白天、後半是夜晚。
"""

from __future__ import annotations

from typing import Final, Literal

__all__ = [
    "GAME_DAY_SECONDS",
    "REAL_DAY_SECONDS",
    "REFRESH_HOUR",
    "UTC_OFFSET_SECONDS",
    "WEATHER_PERIOD_SECONDS",
    "DayPhase",
    "day_phase",
    "day_start_at",
    "game_clock",
    "game_day_index",
    "half_day_index",
    "next_refresh_at",
    "refresh_day",
]

type DayPhase = Literal["day", "night"]

GAME_DAY_SECONDS: Final = 30 * 60
"""遊戲內一天的現實秒數（3.1「遊戲內一天＝現實 30 分鐘」）。"""
WEATHER_PERIOD_SECONDS: Final = GAME_DAY_SECONDS // 2
"""天氣更換週期（#104「遊戲內每半天（現實 15 分鐘）換一次」）。"""
UTC_OFFSET_SECONDS: Final = 8 * 3600
"""Asia/Taipei 的固定位移（沒有日光節約時間）。"""
REFRESH_HOUR: Final = 6
"""每日刷新的當地時刻（3.1「每天早上 6 點」）。"""
REAL_DAY_SECONDS: Final = 24 * 3600

_GAME_DAY_START_MINUTE: Final = 6 * 60
"""遊戲日開頭是遊戲內 06:00。"""
_MINUTES_PER_DAY: Final = 24 * 60


def _check(now: int) -> int:
    if isinstance(now, bool) or not isinstance(now, int):
        raise TypeError(f"now 必須是 int（UTC 秒數），收到 {type(now).__name__}")
    if now < 0:
        raise ValueError(f"now 不可為負，收到 {now}")
    return now


def game_day_index(now: int) -> int:
    """從 Unix 紀元起的第幾個遊戲日。"""
    return _check(now) // GAME_DAY_SECONDS


def half_day_index(now: int) -> int:
    """從 Unix 紀元起的第幾個半天（天氣週期）。"""
    return _check(now) // WEATHER_PERIOD_SECONDS


def day_phase(now: int) -> DayPhase:
    """白天（遊戲日前半）或夜晚（後半）。"""
    return "day" if half_day_index(now) % 2 == 0 else "night"


def game_clock(now: int) -> tuple[int, int]:
    """遊戲內時刻 ``(時, 分)``；遊戲日從 06:00 開始。"""
    offset = _check(now) % GAME_DAY_SECONDS
    minute = (_GAME_DAY_START_MINUTE + offset * _MINUTES_PER_DAY // GAME_DAY_SECONDS) % (
        _MINUTES_PER_DAY
    )
    return divmod(minute, 60)


def _offset(utc_offset_minutes: int | None) -> int:
    return UTC_OFFSET_SECONDS if utc_offset_minutes is None else utc_offset_minutes * 60


def refresh_day(
    now: int, *, utc_offset_minutes: int | None = None, refresh_hour: int = REFRESH_HOUR
) -> int:
    """以當地早上 6 點為界的「第幾天」（每日一次的判定、懸賞、今日目標用）。

    時區與刷新時刻預設是台北 6 點；世界規則的 ``calendar`` 可以換（Phase 5F-1，
    :mod:`trpg.world.calendar`）。"""
    shifted = _check(now) + _offset(utc_offset_minutes) - refresh_hour * 3600
    return shifted // REAL_DAY_SECONDS


def day_start_at(
    day: int, *, utc_offset_minutes: int | None = None, refresh_hour: int = REFRESH_HOUR
) -> int:
    """刷新日 ``day`` 開始（當地刷新時刻）的 UTC 秒數。"""
    return day * REAL_DAY_SECONDS - _offset(utc_offset_minutes) + refresh_hour * 3600


def next_refresh_at(
    now: int, *, utc_offset_minutes: int | None = None, refresh_hour: int = REFRESH_HOUR
) -> int:
    """下一次每日刷新的 UTC 秒數（嚴格大於 ``now``）。"""
    day = refresh_day(now, utc_offset_minutes=utc_offset_minutes, refresh_hour=refresh_hour)
    return day_start_at(day + 1, utc_offset_minutes=utc_offset_minutes, refresh_hour=refresh_hour)
