"""報表與卡片文字共用的小格式化函式（CODE-3，整理提案 I3）。

原本散在 sim／cli／skillgen／narrative／content／api 的同名私有函式（``_pct``、``_percent``、
``_signed``、``_mean``），行為完全相同的才收進來；小數位、千分比或空輸入處理不同的保留在原模組。
純函式、確定性，不匯入其他 ``trpg`` 子套件。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

__all__ = ["exact_pct", "mean", "percent_of", "permille_pct", "ratio_pct", "signed", "signed_zh"]


def ratio_pct(value: float | Fraction) -> str:
    """比例 → 一位小數的百分比：``0.123`` → ``"12.3%"``。"""
    return f"{float(value) * 100:.1f}%"


def percent_of(num: float, den: float) -> float:
    """``num`` 佔 ``den`` 的百分比（數值，0～100）；``den`` 為 0 時回 ``0.0``。"""
    return 0.0 if den == 0 else num * 100 / den


def exact_pct(num: int, den: int) -> str:
    """整數比例 → 一位小數的百分比，以 ``Fraction`` 取到 0.1%（不經浮點）。

    ``den`` 為 0 時回 ``"—"``。
    """
    if den == 0:
        return "—"
    tenths = Fraction(num * 1000, den).__round__()
    return f"{tenths // 10}.{tenths % 10}%"


def permille_pct(permille: int) -> str:
    """千分比 → 百分比（整除時不帶小數）：``150`` → ``"15%"``、``15`` → ``"1.5%"``。"""
    return f"{permille / 10:g}%"


def signed(n: int, *, plus: str = "+", minus: str = "-") -> str:
    """帶正負號的整數；0 視為正（``"+0"``）。``minus`` 可換成全形減號 ``"−"``。"""
    return f"{plus}{n}" if n >= 0 else f"{minus}{-n}"


def mean(values: Sequence[float]) -> float:
    """平均；空序列回 ``0.0``。"""
    return sum(values) / len(values) if values else 0.0


def signed_zh(n: int) -> str:
    """同 :func:`signed`，負號用全形「−」（卡片文字）：``3`` → ``"+3"``、``-2`` → ``"−2"``。"""
    return signed(n, minus="−")
