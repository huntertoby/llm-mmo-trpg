"""技能等級的結算（Phase 3-26a，06 6.28；參數在 ``content/skill_growth.yaml``）。

技能等級是單位技能資料的一部分（``UnitState.skill_levels``，開戰時由範本帶入、戰鬥中不變）：

- **2 級、4 級（3、5 級沿用前一級）**：效果加成（:func:`level_multiplier`，整數千分比）。套用在
  技能的傷害（:func:`~trpg.engine.skills.targeting.damage_parameters`）、治療與護盾的倍率上，無條件
  捨去由各效果結算時的整數除法完成。
- **5 級小特性**（:func:`level_trait`）：技能的形狀有可增加的範圍就範圍 +1（不超過形狀的最大值，即
  6.6 的範圍上限），否則冷卻 −1（原冷卻至少 ``trait_min_cooldown``）；都做不到就沒有小特性。由
  :func:`leveled_skill` 在施放前複製出變形後的技能，所以合法動作、預覽與實際結算彼此一致。

只有主動技能有等級效果。這個模組只讀狀態。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from trpg.content.skills import ShapeSpec, SkillDef

if TYPE_CHECKING:
    from trpg.content.library import Ruleset
    from trpg.engine.state import UnitState

__all__ = [
    "grow_shape",
    "level_multiplier",
    "level_trait",
    "leveled_skill",
    "skill_level",
]

type Trait = Literal["area", "cooldown"]

_GROWABLE = ("size", "radius")
"""範圍 +1 能加的形狀參數（``cross``、``square3`` 只有 ``range``，大小固定）。"""


def skill_level(unit: UnitState, skill_id: str) -> int:
    """``unit`` 的技能 ``skill_id`` 的等級（沒有記錄為 1）。"""
    return unit.skill_levels.get(skill_id, 1)


def level_multiplier(rules: Ruleset, unit: UnitState, skill: SkillDef) -> int:
    """技能等級的效果倍率（‰，1000 ＝ 不變）；只有主動技能、等級 ≥ 2 才有加成。"""
    if skill.kind != "active" or not unit.skill_levels:
        return 1000
    level = skill_level(unit, skill.id)
    return 1000 if level <= 1 else rules.skill_growth.multiplier_permille(level)


def grow_shape(rules: Ruleset, shape: ShapeSpec, delta: int) -> ShapeSpec:
    """``shape`` 的第一個可增加的大小參數（``size``、``radius``）加 ``delta``（不超過最大值）。"""
    params = rules.shape_def(shape.type).params
    for name in _GROWABLE:
        value = getattr(shape, name)
        if name in params and isinstance(value, int):
            return shape.model_copy(update={name: min(value + delta, params[name].max)})
    return shape


def _can_grow(rules: Ruleset, shape: ShapeSpec) -> bool:
    params = rules.shape_def(shape.type).params
    for name in _GROWABLE:
        value = getattr(shape, name)
        if name in params and isinstance(value, int):
            return value < params[name].max
    return False


def level_trait(rules: Ruleset, skill: SkillDef) -> Trait | None:
    """5 級小特性會是哪一種（``area`` 範圍 +1、``cooldown`` 冷卻 −1）；做不到時 ``None``。

    複合技能（有第二段）與陷阱的形狀不變形（與修正規則的保守做法一致），只看冷卻。"""
    if skill.kind != "active":
        return None
    growth = rules.skill_growth
    if skill.followup is None and skill.trap is None and _can_grow(rules, skill.shape):
        return "area"
    cooldown = skill.cost.cooldown
    if cooldown is not None and cooldown >= growth.trait_min_cooldown:
        return "cooldown"
    return None


def leveled_skill(rules: Ruleset, unit: UnitState, skill: SkillDef) -> SkillDef:
    """施放者的技能等級套用 5 級小特性後的技能；沒有成立時回傳原技能（同一個物件）。"""
    if skill.kind != "active" or not unit.skill_levels:
        return skill
    growth = rules.skill_growth
    if skill_level(unit, skill.id) < growth.trait_level:
        return skill
    trait = level_trait(rules, skill)
    if trait == "area":
        return skill.model_copy(
            update={"shape": grow_shape(rules, skill.shape, growth.trait_area_delta)}
        )
    if trait == "cooldown":
        assert skill.cost.cooldown is not None
        cost = skill.cost.model_copy(
            update={"cooldown": skill.cost.cooldown - growth.trait_cooldown_delta}
        )
        return skill.model_copy(update={"cost": cost})
    return skill
