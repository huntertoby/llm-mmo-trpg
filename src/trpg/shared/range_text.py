"""量類骰子的顯示（X10-3b，05 5.4.1）：卡片與技能列只寫範圍（「20–160」），不寫「2d8」。

連接號一律用短橫線「–」（U+2013），和戰鬥預覽 ``client/src/battle/previewText.ts`` 的
``damageText`` 一致。
"""

from __future__ import annotations

__all__ = ["RANGE_DASH", "DiceNote", "dice_note", "range_text", "span"]

RANGE_DASH = "–"
"""範圍的連接號（U+2013）。"""


def span(count: int, sides: int, scale: int, extra: int = 0) -> tuple[int, int]:
    """``count`` 顆 ``sides`` 面骰、每點 × ``scale``，再加 ``extra``（固定值與屬性加成）的
    最小與最大值。"""
    return count * scale + extra, count * sides * scale + extra


def range_text(low: int, high: int) -> str:
    """「20–160」；兩端相同時只寫一個數。"""
    return str(low) if low == high else f"{low}{RANGE_DASH}{high}"


class DiceNote(str):
    """:func:`dice_note` 的回傳值：字串本身是「擲 2d8，每點 ×10」，另外帶著骰子本身（HC-6c，AR-X10
    待決 5：名詞表 ``/api/glossary`` 的規則句用它標出哪幾行是骰子行，前端不必比對句型）。"""

    __slots__ = ("dice_count", "dice_scale", "dice_sides")
    dice_count: int
    dice_sides: int
    dice_scale: int

    def __new__(cls, text: str, count: int, sides: int, scale: int) -> DiceNote:
        note = super().__new__(cls, text)
        note.dice_count, note.dice_sides, note.dice_scale = count, sides, scale
        return note


def dice_note(count: int, sides: int, scale: int) -> DiceNote:
    """長說明多的一行：「擲 2d8，每點 ×10」（倍率 1 時只寫「擲 2d8」）。"""
    head = f"擲 {count}d{sides}"
    return DiceNote(head if scale == 1 else f"{head}，每點 ×{scale}", count, sides, scale)
