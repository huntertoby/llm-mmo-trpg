"""賽季的週次（Phase 5D-R1，從 :mod:`trpg.world.social` 移來）。

一週幾天在世界規則（``content/world/rules.yaml`` 的 ``week_days``，預設 7）；週次以早上 6 點刷新的
日子算（:func:`~trpg.world.calendar.day_of`），賽季開始那天是第 0 週。酒館的本週傳聞與商店的
每週限量共用。

純函式：不讀時間（``now`` 由呼叫者傳入）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.world_rules import DEFAULT_WEEK_DAYS
from trpg.world.calendar import day_of
from trpg.world.state import WorldState

__all__ = ["week_days", "week_of"]


def week_days(library: ContentLibrary) -> int:
    """一週幾天；內容庫沒有世界規則時用預設值。"""
    rules = library.world_rules
    return DEFAULT_WEEK_DAYS if rules is None else rules.week_days


def week_of(library: ContentLibrary, world: WorldState, now: int) -> int:
    """賽季開始以來的第幾週（0 起；早上 6 點刷新的日子）。"""
    days = day_of(library, now) - day_of(library, world.season_start)
    return max(0, days) // week_days(library)
