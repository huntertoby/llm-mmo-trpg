"""入門武器、起始武器的卡片多寫的一行（Phase OB-6，#150 第 1 點與第 9 點「重選的邊界」；21 21.5
「OB-6 補充」）。

- 入門期（``opening.stage == "starter"``）手上的入門武器（``range.starters`` 該大類那把）：
  :data:`STARTER_WEAPON_ZH`（玩法 PM 定稿「OB-6 字串」）。
- 正式選定之後、還有重選資格（:func:`trpg.world.opening_reselect.reselect_window_problem`）時，起始
  武器本體（拿在手上、主手欄或背包，:func:`trpg.world.opening_reselect.starter_item_id`）：
  :func:`reselect_weapon_zh`。

只讀狀態；畫面照這裡給的字顯示，前端不寫死武器 ID。
"""

from __future__ import annotations

from typing import Final

from trpg.content.library import ContentLibrary
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.opening_reselect import reselect_window_problem, starter_item_id, weapon_item_id
from trpg.world.state import CharacterState

__all__ = ["STARTER_WEAPON_ZH", "opening_gear_note", "reselect_weapon_zh"]

STARTER_WEAPON_ZH: Final = "入門配備是借的，正式選定時會換成你自己的。不能賣、寄、分解。"


def reselect_weapon_zh() -> str:
    """起始武器卡片那一行（還能重選時才顯示；等級讀規則常數）。"""
    return f"{OPENING_END_LEVEL} 級前重選的話，這把會被收回。"


def opening_gear_note(library: ContentLibrary, char: CharacterState, item_id: str) -> str | None:
    """``item_id`` 這件（穿戴中的一欄或背包裡的裝備）卡片上要多寫的一行；沒有＝``None``。"""
    opening = char.opening
    if opening is None:
        return None
    if opening.stage == "starter":
        newcomer = library.world_newcomer
        arena = None if newcomer is None else newcomer.range
        starter = None
        if arena is not None and opening.weapon_class is not None:
            starter = arena.starters.get(opening.weapon_class)
        if starter is None or item_id != weapon_item_id(library, char, starter):
            return None
        return STARTER_WEAPON_ZH
    if opening.stage != "chosen" or reselect_window_problem(char) is not None:
        return None
    return reselect_weapon_zh() if item_id == starter_item_id(library, char) else None
