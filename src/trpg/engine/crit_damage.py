"""暴擊傷害倍率（CR-1，``docs/design/05-戰鬥.md`` 5.4.2，#178）。

暴擊時照常擲原本的傷害骰，再多擲一組同樣顆數；多擲的那組乘（倍率 − 100%），無條件捨去
（:func:`trpg.engine.rules.combat.crit_extra_total`）。屬性加成、固定值不放大。

倍率由攻擊方在擲骰時算好，放進 :class:`~trpg.engine.effects.models.DamageEffect` 的
``crit_permille``（:func:`crit_damage_permille`）：

1. 武器基礎：普攻看攻擊用的武器（形態中是天生武器）、武器技看手上的武器，武器的
   ``crit_permille``；沒填（或法術技）照 ``core.crit_damage.base_permille``（2000‰）。單位檔另填的
   倍率在開戰時已寫進單位的武器（:meth:`~trpg.content.library.ContentLibrary.weapon_of`）。
2. 裝備數值詞條「暴擊傷害 +N%」（:func:`~trpg.engine.gear.core.gear_crit_damage_permille`；同一詞條
   開戰時已照 08 8.21.5.3 遞減）。
3. 修正技（修正型被動）的 ``crit_damage_permille``
   （:func:`~trpg.engine.modifiers.crit_damage_bonus`；同一招的複本遞減）；被動觸發等不受修正的施放不算。
4. 這招自帶的倍率（``SkillDef.crit_permille``）比基礎倍率多出的部分。

全部相加，最後套全身上下限 ``core.crit_damage.min_permille``～``max_permille``（150%～300%）。
敵我用同一套規則。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from trpg.content.battle import WeaponDef
from trpg.content.skills import SkillDef
from trpg.engine.gear.core import gear_crit_damage_permille
from trpg.engine.modifiers import Use, crit_damage_bonus
from trpg.engine.rules.forms import held_weapon
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import BattleState, UnitState

__all__ = ["crit_damage_permille", "crit_weapon"]


def crit_weapon(unit: UnitState, skill: SkillDef | None) -> WeaponDef | None:
    """決定基礎倍率的武器：普攻是 ``unit.weapon``（形態中是天生武器）、武器技是手上的武器；
    法術技不看武器（``None``）。"""
    if skill is None:
        return unit.weapon
    return held_weapon(unit) if skill.category == "weapon" else None


def crit_damage_permille(
    state: BattleState,
    unit: UnitState,
    *,
    use: Use | None = None,
    subject: Subject | None = None,
    skill: SkillDef | None = None,
) -> int:
    """``unit`` 這一次攻擊的暴擊傷害倍率（‰，已套全身上下限）。

    ``skill``：施放的技能（普攻為 ``None``）；``use``：受修正規則影響的動作（被動觸發等不受修正的
    施放為 ``None``）；``subject``：這次攻擊的目標（修正規則的條件看它）。"""
    rules = state.ruleset.core.crit_damage
    weapon = crit_weapon(unit, skill)
    own = None if weapon is None else weapon.crit_permille
    total = rules.base_permille if own is None else own
    total += gear_crit_damage_permille(unit)
    if use is not None:
        target = subject if subject is not None else Subject(unit, unit.xy)
        total += crit_damage_bonus(state, unit, use, target)
    if skill is not None and skill.crit_permille is not None:
        total += skill.crit_permille - rules.base_permille
    return max(rules.min_permille, min(rules.max_permille, total))
