"""技能的縮放值與專精加成（Phase 2H-2，``docs/phases/Phase2H計畫.md`` 第 4 節）。

- :func:`skill_scaling_value`：技能讀取縮放屬性值的 **唯一入口**。有第二縮放屬性時為兩個有效
  屬性的平均（整數，無條件捨去，各占 50%），否則為原屬性的有效屬性。武器技的武器傷害與武器
  命中讀武器自己的屬性，不經過這裡。
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
    "skill_scaling_value",
]

MASTERY_BONUS = 1
"""專精加成的大小（施放距離 +1／狀態持續 +1）。"""


def skill_scaling_value(rules: Ruleset, unit: UnitState, skill: SkillDef) -> int:
    """技能縮放屬性的值：雙屬性為兩個有效屬性的平均（無條件捨去），否則為主屬性的有效屬性。"""
    primary = effective_attribute(rules, unit, skill.scaling_attr)
    if skill.secondary_scaling_attr is None:
        return primary
    return (primary + effective_attribute(rules, unit, skill.secondary_scaling_attr)) // 2


def mastery_active(unit: UnitState, skill: SkillDef) -> bool:
    """技能有 ``mastery`` 且施放者的 ``scaling_attr`` 基礎屬性是自己所有屬性中最高（含並列）。"""
    if skill.mastery is None:
        return False
    mine = base_attribute(unit, skill.scaling_attr)
    return all(mine >= base_attribute(unit, attr) for attr in Attribute)


def mastery_reach_bonus(unit: UnitState, skill: SkillDef) -> int:
    """``mastery: range`` 生效時施放距離 +1，否則 0。"""
    return MASTERY_BONUS if skill.mastery == "range" and mastery_active(unit, skill) else 0


def mastery_duration_bonus(unit: UnitState, skill: SkillDef) -> int:
    """``mastery: duration`` 生效時狀態持續 +1，否則 0。"""
    return MASTERY_BONUS if skill.mastery == "duration" and mastery_active(unit, skill) else 0
