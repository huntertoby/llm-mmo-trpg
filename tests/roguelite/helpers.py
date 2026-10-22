"""roguelite 測試共用：內容庫與幾個已知結果的一輪（AI 代打）。"""

from __future__ import annotations

from functools import cache

from tests.engine.helpers import library
from trpg.roguelite import RunState, auto_play, new_run

__all__ = ["VICTORY", "full_run", "library"]

VICTORY = ("build_fire", 1)
"""AI 代打會打完整輪（含兩次營火與 Boss）的 build 與種子（目前內容與數值下）。"""


@cache
def full_run(build: str, seed: int) -> RunState:
    """AI 代打一整輪的最後狀態（快取；``RunState`` 不可變）。"""
    run, battle = auto_play(library(), new_run(library(), build, seed))
    assert battle is None
    return run
