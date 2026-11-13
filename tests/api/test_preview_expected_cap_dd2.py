"""DD-2 待決 3（開發 PM 裁定「期望 ≤ 最多」）：預覽回應的期望傷害夾在「最多」以內。

雙匕首打兩下時引擎的期望＝每下期望 × 2，沒扣「第一下打倒」與 HP 上限，會大於被 HP 擋住的最多
（DD-2 截圖：最多 18、期望 19.4）。只改 API 的顯示；引擎與 AI 的估值不動。"""

from __future__ import annotations

from fractions import Fraction

from trpg.api.schemas import _damage
from trpg.engine.preview import DamageRange


def test_expected_above_the_maximum_is_capped() -> None:
    if_hit = Fraction(228, 10)  # 每下 11.4 × 2 下
    hit = Fraction(85, 100)
    out = _damage(DamageRange(9, 18, if_hit * hit, if_hit))
    assert out is not None
    assert out.expected_if_hit_milli == 18_000
    assert out.expected_milli == 15_300  # 最多 18 × 命中 85%
    assert out.expected_milli <= out.maximum * 1000
    assert (out.minimum, out.maximum) == (9, 18)


def test_expected_within_the_maximum_is_unchanged() -> None:
    if_hit = Fraction(23, 2)
    hit = Fraction(3, 4)
    out = _damage(DamageRange(6, 16, if_hit * hit, if_hit))
    assert out is not None
    assert out.expected_if_hit_milli == 11_500
    assert out.expected_milli == 8_625


def test_expected_equal_to_the_maximum_and_zero_hit() -> None:
    out = _damage(DamageRange(4, 4, Fraction(4), Fraction(4)))
    assert out is not None and out.expected_milli == 4_000 and out.expected_if_hit_milli == 4_000
    missed = _damage(DamageRange(3, 10, Fraction(0), Fraction(0)))
    assert missed is not None and missed.expected_milli == 0
    assert _damage(None) is None
