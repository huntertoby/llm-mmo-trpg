"""賽季的週次（Phase 5D-R1，從 :mod:`trpg.world.social` 移來）。

一週幾天在世界規則（``content/world/rules.yaml`` 的 ``week_days``，預設 7）；週次以早上 6 點刷新的
日子算（:func:`~trpg.world.calendar.day_of`），賽季開始那天是第 0 週。酒館的本週傳聞與商店的
每週限量共用。

純函式：不讀時間（``now`` 由呼叫者傳入）。
"""

from __future__ import annotations

from typing import Final

from trpg.content.library import ContentLibrary
from trpg.world.calendar import day_of
from trpg.world.state import WorldState

__all__ = ["FIRST_SEASON_ID", "week_days", "week_of"]

FIRST_SEASON_ID: Final = "s1"
"""第一季（測試季）的賽季 ID（09 9.7）。新世界從這一季開始；沒有 ``season_id`` 的舊紀錄
（首殺）都在這一季寫下（Phase 5D-R2）。"""


NO_RULES_WEEK_DAYS: Final = 7
"""沒有世界規則（只有測試的精簡內容庫）時一週的天數。HC-4d 起 ``WorldRules.week_days`` 沒有程式
預設值，這個值要和 ``world/rules.yaml`` 的 ``week_days`` 相同
（``tests/world/test_rule_defaults_hc4d.py`` 對照）。"""


def week_days(library: ContentLibrary) -> int:
    """一週幾天；內容庫沒有世界規則時用 :data:`NO_RULES_WEEK_DAYS`。"""
    rules = library.world_rules
    return NO_RULES_WEEK_DAYS if rules is None else rules.week_days


def week_of(library: ContentLibrary, world: WorldState, now: int) -> int:
    """賽季開始以來的第幾週（0 起；早上 6 點刷新的日子）。"""
    days = day_of(library, now) - day_of(library, world.season_start)
    return max(0, days) // week_days(library)
