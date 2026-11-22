"""HC-4d：沒有世界規則時的備用值要和內容檔相同（HC-7 起合成載入層的一份，見
``test_rule_defaults_hc7.py``）；時段表和世界時鐘一致。"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.world.clock import GAME_DAY_SECONDS, day_phase, game_clock


def test_day_parts_match_world_clock(library: ContentLibrary) -> None:
    """時段表的白天開始（早）、夜晚開始（晚）和世界時鐘一致：遊戲日開頭是 ``morning`` 點、白天；
    過了半天是 ``evening`` 點、夜晚（世界時鐘的白天／夜晚不讀這張表，所以在這裡對照）。"""
    rules = library.world_rules
    assert rules is not None
    parts = rules.day_parts
    start = GAME_DAY_SECONDS * 1000  # 任一個遊戲日的開頭
    half = GAME_DAY_SECONDS // 2
    assert game_clock(start) == (parts.morning, 0)
    assert day_phase(start) == "day"
    assert day_phase(start + half - 1) == "day"
    assert game_clock(start + half) == (parts.evening, 0)
    assert day_phase(start + half) == "night"
    assert day_phase(start + GAME_DAY_SECONDS - 1) == "night"
    hours = {game_clock(start + s)[0] for s in range(0, half)}
    assert parts.noon in hours  # 午在白天裡
    night = {game_clock(start + half + s)[0] for s in range(0, half)}
    assert parts.night in night  # 夜在夜晚裡
