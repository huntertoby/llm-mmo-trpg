"""BAL-13c（#77）：連鎖形狀的預算倍率依連鎖衰減後的期望總份量校正（只降不升）。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import library

OLD_PER_JUMP = 250
"""BAL-13c 之前每跳 +250‰（＝每多一個目標的期望份量 0.25，沒有衰減）。"""


def _expected(jumps: int) -> int:
    core = library().ruleset.core
    total = Fraction(1000)
    for hop in range(1, jumps + 1):
        potency = max(1000 - hop * core.chain_falloff_permille, core.chain_floor_permille)
        total += Fraction(OLD_PER_JUMP * potency, 1000)
    return int(total + Fraction(1, 2))  # 四捨五入


def test_chain_shape_multiplier_follows_the_falloff() -> None:
    budget = library().ruleset.shapes.by_id()["chain"].budget
    for jumps in (1, 2, 3):
        value = budget.permille_for({"jumps": jumps})
        assert value == _expected(jumps), jumps
        assert value <= 1000 + OLD_PER_JUMP * jumps  # 只降不升
