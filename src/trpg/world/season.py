"""賽季的週次（Phase 5D-R1，從 :mod:`trpg.world.social` 移來）。

一週幾天在世界規則（``content/world/rules.yaml`` 的 ``week_days``，預設 7）；週次以早上 6 點刷新的
日子算（:func:`~trpg.world.clock.refresh_day`），賽季開始那天是第 0 週。酒館的本週傳聞與商店的
每週限量共用。

純函式：不讀時間（``now`` 由呼叫者傳入）。
"""

from __future__ import annotations

from typing import Final

from trpg.content.library import ContentLibrary
from trpg.content.world_rules import DEFAULT_WEEK_DAYS
from trpg.world.clock import refresh_day
from trpg.world.state import WorldState

__all__ = ["FIRST_SEASON_ID", "week_days", "week_of"]

FIRST_SEASON_ID: Final = "s1"
"""第一季（測試季）的賽季 ID（09 9.7）。新世界從這一季開始；沒有 ``season_id`` 的舊紀錄
（首殺）都在這一季寫下（Phase 5D-R2）。"""


def week_days(library: ContentLibrary) -> int:
    """一週幾天；內容庫沒有世界規則時用預設值。"""
    rules = library.world_rules
    return DEFAULT_WEEK_DAYS if rules is None else rules.week_days


def week_of(library: ContentLibrary, world: WorldState, now: int) -> int:
    """賽季開始以來的第幾週（0 起；早上 6 點刷新的日子）。"""
    days = refresh_day(now) - refresh_day(world.season_start)
    return max(0, days) // week_days(library)
