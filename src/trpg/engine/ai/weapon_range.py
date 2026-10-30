"""近距離武器的站位（BAL-5 B19；權重在 ``content/ai_profiles.yaml`` 的 ``weapon_ai:``）。

武器資料的距離修正（``range_mod`` 的 ``damage_permille``）決定「最佳距離」：普攻傷害千分比最高的
最近距離。最佳距離不超過 ``keep_distance`` 的半徑（2 格）的武器（例如霰彈槍，1 格 100%、2 格 75%、
3 格 50%、4 格 25%）叫做「近距離武器」，位置價值因此改成：

- ``close_range``：站位能打到的敵人中，距離傷害千分比最高的那一個 × ``close_range`` ÷ 1000（越靠近
  最佳距離越高）；
- ``keep_distance``（保持距離）只計算比最佳距離更近的敵人（霰彈槍的最佳距離是 1，所以不扣分）。

沒有距離傷害修正、或最佳距離在 2 格外（火槍的遠距加成）的武器完全不受影響。不寫死武器 ID。
"""

from __future__ import annotations

from trpg.content.battle import WeaponDef

__all__ = ["best_distance", "damage_permille_at", "is_close_range", "is_far_range"]

_PERMILLE = 1000


def damage_permille_at(weapon: WeaponDef, distance: int) -> int:
    """武器在 ``distance`` 格的普攻傷害千分比（與 ``range_damage_permille`` 相同的算法）。"""
    value = _PERMILLE
    for mod in weapon.range_mod:
        if mod.covers(distance):
            value = value * mod.damage_permille // _PERMILLE
    return value


def best_distance(weapon: WeaponDef) -> int | None:
    """傷害千分比最高的最近距離（1～射程）；沒有距離傷害修正時 ``None``。"""
    if not any(m.damage_permille != _PERMILLE for m in weapon.range_mod):
        return None
    reach = max(weapon.range, 1)
    return max(range(1, reach + 1), key=lambda d: (damage_permille_at(weapon, d), -d))


def is_close_range(weapon: WeaponDef, keep_radius: int) -> bool:
    """近距離武器：非近戰、最佳距離不超過 ``keep_radius``、而且最佳距離比射程近（有遞減）。"""
    if weapon.is_melee:
        return False
    best = best_distance(weapon)
    return best is not None and best <= keep_radius and best < weapon.range


def is_far_range(weapon: WeaponDef, keep_radius: int) -> bool:
    """遠距加成武器（BAL-8）：非近戰、最佳距離超過 ``keep_radius``、該距離傷害高於基準（火槍）。"""
    if weapon.is_melee:
        return False
    best = best_distance(weapon)
    return best is not None and best > keep_radius and damage_permille_at(weapon, best) > _PERMILLE
