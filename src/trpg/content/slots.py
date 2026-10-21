"""裝備欄位與物品種類（Phase 3G-G1，``docs/design/08-裝備.md`` 8.23）。

獨立成不依賴其他內容模組的小模組，讓 :mod:`trpg.content.battle`（單位範本的 ``equipment``）與
:mod:`trpg.content.equipment`（物品與詞條）都能引用而不循環匯入。
"""

from __future__ import annotations

from typing import Literal, get_args

__all__ = [
    "SLOTS",
    "SLOT_INDEX",
    "SLOT_TYPES",
    "SLOT_TYPE_OF",
    "SLOT_TYPE_ZH",
    "SLOT_ZH",
    "Slot",
    "SlotType",
]

type Slot = Literal[
    "main_hand", "off_hand", "head", "body", "hands", "feet", "neck", "ring_1", "ring_2"
]
"""裝備欄位 ID（8.23）。"""

type SlotType = Literal["weapon", "offhand", "head", "body", "hands", "feet", "neck", "ring"]
"""物品種類（``slot_type``）：決定物品能放進哪個欄位。"""

SLOTS: tuple[Slot, ...] = get_args(Slot.__value__)
"""欄位的固定順序（遞減疊加「同值依欄位固定順序」、顯示順序都用它）。"""

SLOT_INDEX: dict[str, int] = {slot: i for i, slot in enumerate(SLOTS)}

SLOT_TYPES: tuple[SlotType, ...] = get_args(SlotType.__value__)

SLOT_TYPE_OF: dict[str, SlotType] = {
    "main_hand": "weapon",
    "off_hand": "offhand",
    "head": "head",
    "body": "body",
    "hands": "hands",
    "feet": "feet",
    "neck": "neck",
    "ring_1": "ring",
    "ring_2": "ring",
}
"""每個欄位可放的物品種類。"""

SLOT_ZH: dict[str, str] = {
    "main_hand": "主手",
    "off_hand": "副手",
    "head": "頭",
    "body": "身體",
    "hands": "手",
    "feet": "腳",
    "neck": "項鍊",
    "ring_1": "戒指 1",
    "ring_2": "戒指 2",
}

SLOT_TYPE_ZH: dict[str, str] = {
    "weapon": "武器",
    "offhand": "副手",
    "head": "頭",
    "body": "身體",
    "hands": "手",
    "feet": "腳",
    "neck": "項鍊",
    "ring": "戒指",
}
