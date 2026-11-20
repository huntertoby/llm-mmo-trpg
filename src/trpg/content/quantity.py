"""量類倍率（``quantity_scale``，05 5.4.1，#169 題 10）的共用常數（HC-2）。

量類（HP、傷害、治療、護盾、屬性、法力、耐力……）的值跟著 ``core.yaml`` 的 ``quantity_scale`` 走。
schema 欄位的護欄（``le``）在載入時拿不到內容的倍率，寫成「換算前的上限 × 最大倍率」
（:func:`quantity_cap`）：倍率 10 時和 X10-1 放寬後的上限相同，倍率 1 時照樣放得進去。
"""

from __future__ import annotations

from typing import Final, Literal, get_args

QuantityScale = Literal[1, 10]
"""``CoreRules.quantity_scale`` 可用的值。"""

MAX_QUANTITY_SCALE: Final[int] = max(get_args(QuantityScale))


def quantity_cap(old: int) -> int:
    """量類欄位的 schema 上限：換算前的上限 ``old`` × :data:`MAX_QUANTITY_SCALE`。"""
    return old * MAX_QUANTITY_SCALE
