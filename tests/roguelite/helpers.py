"""roguelite 測試共用：內容庫與幾個已知結果的一輪（AI 代打）。"""

from __future__ import annotations

from dataclasses import replace
from functools import cache

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.roguelite import RunState, auto_play, new_run

__all__ = ["VICTORY", "full_library", "full_run", "library"]

VICTORY = ("build_fire", 2)
"""AI 代打會打完整輪（含兩次營火與 Boss）的 build 與種子（目前內容與數值下）。

3-33e1 技能池多了 6 招召喚技，原種子 1 不再勝利，改 6。3W-5 改成靈感點與閃現後種子 6 輸掉 Boss 戰，
改 2（種子 0～11 中勝利的有 1、2、7）。
"""


@cache
def full_library() -> ContentLibrary:
    """候選走「完整技能」三選一的內容庫（``candidates.whiteboard: false``，Phase 3W-4）。

    升級與任務三選一預設是白板（單一效果、1 階）；需要升級候選是整招技能的測試（例：LLM 來源只在
    完整技能的候選產生器使用）用這個。
    """
    lib = library()
    settings = lib.roguelite.candidates.model_copy(update={"whiteboard": False})
    return replace(lib, roguelite=lib.roguelite.model_copy(update={"candidates": settings}))


@cache
def full_run(build: str, seed: int) -> RunState:
    """AI 代打一整輪的最後狀態（快取；``RunState`` 不可變）。"""
    run, battle = auto_play(library(), new_run(library(), build, seed))
    assert battle is None
    return run
