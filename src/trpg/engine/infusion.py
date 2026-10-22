"""召喚物的灌注關鍵字（Phase 3-33b，``docs/design/06-技能.md`` 6.29.1）。

召喚技能施放時可選一個 **施放者持有、且在 ``core.summon_infusions`` 對照表中** 的關鍵字
（``UseSkill.infusion``）；召喚物的普攻命中後附加對照表指定的狀態或震退。

- **持有的關鍵字**：施放者裝備中的技能製造或利用的關鍵字（:meth:`Ruleset.skill_keywords`），依技能
  順序、不重複。
- **可選的關鍵字**（:func:`infusion_options`）：持有的關鍵字中有對照的。沒有任何可選時，召喚技能
  不能帶 ``infusion``，召喚物也沒有灌注。
- **預設**：玩家省略 ``infusion`` 時取第一個可選的（:func:`default_infusion`）；AI 依召喚物定位
  （近戰或遠程）挑對照表 ``roles`` 偏好的（:func:`preferred_infusion`）。
"""

from __future__ import annotations

from trpg.content.battle import UnitTemplate
from trpg.content.rules import SummonInfusion
from trpg.content.skills import SUMMON, SkillDef
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError

__all__ = [
    "active_infusions",
    "active_keywords",
    "check_infusion",
    "default_infusion",
    "held_keywords",
    "infusion_options",
    "infusion_problem",
    "is_summon_skill",
    "preferred_infusion",
    "summon_template_ids",
    "template_of",
]


def is_summon_skill(skill: SkillDef) -> bool:
    return any(e.type == SUMMON for e in skill.effects)


def summon_template_ids(skill: SkillDef) -> tuple[str, ...]:
    """技能召喚的範本 ID（依效果順序）。"""
    return tuple(e.unit for e in skill.effects if e.type == SUMMON and e.unit is not None)


def held_keywords(state: BattleState, owner: UnitState) -> tuple[str, ...]:
    """``owner`` 持有的關鍵字：裝備中技能製造或利用的關鍵字（依技能順序，不重複）。"""
    found: dict[str, None] = {}
    for skill_id in owner.skills:
        try:
            skill = state.ruleset.skill_def(skill_id)
        except KeyError:
            continue
        for keyword in state.ruleset.skill_keywords(skill).all():
            found.setdefault(keyword)
    return tuple(found)


def infusion_options(state: BattleState, owner: UnitState) -> tuple[str, ...]:
    """``owner`` 可以灌注的關鍵字：持有、且在 ``summon_infusions`` 對照表中。"""
    table = state.ruleset.core.summon_infusions
    return tuple(k for k in held_keywords(state, owner) if k in table)


def default_infusion(state: BattleState, owner: UnitState) -> str | None:
    """玩家省略 ``infusion`` 時的預設：第一個可選的關鍵字（沒有可選的時 ``None``）。"""
    options = infusion_options(state, owner)
    return options[0] if options else None


def preferred_infusion(state: BattleState, owner: UnitState, template_id: str) -> str | None:
    """AI 的挑法：對照表 ``roles`` 含召喚物定位（武器射程 1 為近戰，否則遠程）的第一個可選關鍵字；
    沒有符合的就取預設。"""
    options = infusion_options(state, owner)
    if not options:
        return None
    try:
        role = "melee" if state.ruleset.summon_def(template_id).weapon.range <= 1 else "ranged"
    except KeyError:
        return options[0]
    table = state.ruleset.core.summon_infusions
    return next((k for k in options if role in table[k].roles), options[0])


def infusion_problem(
    state: BattleState, owner: UnitState, skill: SkillDef, requested: str | None
) -> str | None:
    """動作帶的 ``infusion`` 不合法的原因（中文）；合法或沒有帶時 ``None``。"""
    if requested is None:
        return None
    if not is_summon_skill(skill):
        return f"只有召喚技能可以指定 infusion：{skill.name_zh}"
    if requested not in infusion_options(state, owner):
        return f"不能灌注關鍵字 {requested}：施放者沒有持有，或它沒有對應的灌注效果"
    return None


def check_infusion(
    state: BattleState, owner: UnitState, skill: SkillDef, requested: str | None
) -> None:
    problem = infusion_problem(state, owner, skill, requested)
    if problem is not None:
        raise IllegalActionError(problem)


def template_of(state: BattleState, unit: UnitState) -> UnitTemplate | None:
    """召喚物的範本（不是召喚物或範本不在規則包時 ``None``）。"""
    if not unit.is_summon:
        return None
    try:
        return state.ruleset.summon_def(unit.template_id).template
    except KeyError:
        return None


def active_keywords(state: BattleState, unit: UnitState) -> tuple[str, ...]:
    """召喚物生效的灌注關鍵字（Phase 3-33e1）：範本固有的在前，施放時選的在後；不在對照表中的略過、
    不重複。"""
    template = template_of(state, unit)
    table = state.ruleset.core.summon_infusions
    found: dict[str, None] = {}
    for keyword in (template.innate if template else None, unit.infusion):
        if keyword is not None and keyword in table:
            found.setdefault(keyword)
    return tuple(found)


def active_infusions(state: BattleState, unit: UnitState) -> tuple[SummonInfusion, ...]:
    """:func:`active_keywords` 在對照表中的效果。"""
    table = state.ruleset.core.summon_infusions
    return tuple(table[k] for k in active_keywords(state, unit))
