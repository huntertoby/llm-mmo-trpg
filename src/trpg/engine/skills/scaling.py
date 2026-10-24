"""技能的縮放值與專精加成（Phase 2H-2，``docs/phases/Phase2H計畫.md`` 第 4 節）。

- :func:`skill_scaling_value`：技能讀取縮放屬性值的 **唯一入口**。有第二縮放屬性時為兩個有效
  屬性的平均（整數，無條件捨去，各占 50%），否則為原屬性的有效屬性。**武器技（``category:
  weapon``）改看施放者手上武器的縮放值**（Phase 3H-6，玩法決定 #45：技能自己的 ``scaling_attr``
  對武器技不生效；雙屬性武器照 ``attr_mode`` 取較高／取平均）。
- :func:`skill_scaling_attr`：對抗判定（擊倒、位移、狀態抵抗）用的單一屬性；武器技為武器的主屬性。
- :func:`mastery_active`：專精加成是否生效——施放者 ``scaling_attr`` 的 **基礎屬性**（單位範本的
  屬性，不含狀態加值）不低於自己所有基礎屬性（並列也算）。用基礎屬性是讓配點決定專精，不受
  戰鬥中增益影響。
- :func:`mastery_reach_bonus`、:func:`mastery_duration_bonus`：專精的實際加成（0 或 1）。
"""

from __future__ import annotations

from trpg.content.library import Ruleset
from trpg.content.skills import SkillDef
from trpg.engine.rules.statuses import base_attribute, effective_attribute
from trpg.engine.state import UnitState
from trpg.shared.types import Attribute

__all__ = [
    "mastery_active",
    "mastery_duration_bonus",
    "mastery_reach_bonus",
    "skill_scale_attr",
    "skill_scaling_attr",
    "skill_scaling_value",
]

MASTERY_BONUS = 1
"""專精加成的大小（施放距離 +1／狀態持續 +1）。"""


def skill_scaling_value(rules: Ruleset, unit: UnitState, skill: SkillDef) -> int:
    """技能縮放屬性的值。武器技看手上武器（含雙屬性取法）；其他為技能自己的：雙屬性為兩個有效
    屬性的平均（無條件捨去），否則為主屬性的有效屬性。"""

    def get(attr: Attribute) -> int:
        return effective_attribute(rules, unit, attr)

    return skill.scaling_value(get, unit.weapon)


def skill_scaling_attr(unit: UnitState, skill: SkillDef) -> Attribute:
    """對抗判定用的屬性（和目標同屬性比）：武器技為手上武器的主屬性，其他為 ``scaling_attr``。"""
    return skill.contest_attr(unit.weapon)


def skill_scale_attr(unit: UnitState, skill: SkillDef) -> Attribute | None:
    """傷害組成顯示用的縮放屬性：只有單一屬性時回傳它，雙屬性（平均或較高）為 ``None``。武器技看
    手上武器。"""
    if skill.category == "weapon":
        weapon = unit.weapon
        single = weapon.secondary_scaling_attr is None and skill.secondary_scaling_attr is None
        return weapon.scaling_attr if single else None
    return skill.scaling_attr if skill.secondary_scaling_attr is None else None


def mastery_active(unit: UnitState, skill: SkillDef) -> bool:
    """技能有 ``mastery`` 且施放者的縮放屬性基礎屬性是自己所有屬性中最高（含並列）；武器技看
    武器的縮放值（雙屬性取較高／取平均後，仍不低於自己最高的基礎屬性）。"""
    if skill.mastery is None:
        return False
    mine = skill.mastery_value(lambda attr: base_attribute(unit, attr), unit.weapon)
    return all(mine >= base_attribute(unit, attr) for attr in Attribute)


def mastery_reach_bonus(unit: UnitState, skill: SkillDef) -> int:
    """``mastery: range`` 生效時施放距離 +1，否則 0。"""
    return MASTERY_BONUS if skill.mastery == "range" and mastery_active(unit, skill) else 0


def mastery_duration_bonus(unit: UnitState, skill: SkillDef) -> int:
    """``mastery: duration`` 生效時狀態持續 +1，否則 0。"""
    return MASTERY_BONUS if skill.mastery == "duration" and mastery_active(unit, skill) else 0
