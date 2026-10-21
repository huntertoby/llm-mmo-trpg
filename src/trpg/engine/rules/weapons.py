"""武器參數的純計算（Phase 3-24a2；命中、暴擊與傷害的修正都讀 ``content/weapons.yaml`` 的參數）。

只看單位與距離、不改狀態，所以命中判定（:mod:`trpg.engine.rules.combat`）、預覽與 AI 可以共用：

- 站定 ``steady``：本回合還沒主動移動時，普攻命中加成與暴擊範圍擴大；
- 距離修正 ``range_mod``：依攻擊距離的命中修正與傷害千分比。
"""

from __future__ import annotations

from trpg.engine.state import UnitState

__all__ = ["crit_range_cut", "range_damage_permille", "weapon_hit_bonus"]

PERMILLE = 1000


def _steady_active(unit: UnitState) -> bool:
    return unit.weapon.steady is not None and not unit.moved_this_turn


def crit_range_cut(unit: UnitState) -> int:
    """站定時普攻暴擊範圍擴大的點數（自然骰門檻降低多少）；沒有站定或沒有此特性時 0。"""
    steady = unit.weapon.steady
    return steady.crit_range if steady is not None and _steady_active(unit) else 0


def weapon_hit_bonus(unit: UnitState, distance: int) -> int:
    """普攻的武器命中加值：站定的命中加成 ＋ 距離修正（貼臉為負）。"""
    steady = unit.weapon.steady
    bonus = steady.hit if steady is not None and _steady_active(unit) else 0
    return bonus + sum(m.hit for m in unit.weapon.range_mod if m.covers(distance))


def range_damage_permille(unit: UnitState, distance: int) -> int:
    """普攻傷害的距離修正（‰；多條重疊時相乘，每步無條件捨去；沒有修正時 1000）。"""
    value = PERMILLE
    for mod in unit.weapon.range_mod:
        if mod.covers(distance):
            value = value * mod.damage_permille // PERMILLE
    return value
