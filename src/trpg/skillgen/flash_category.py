"""閃現的類別判定（Phase 3W-1，``docs/design/06-技能.md`` 6.34；3W-R2 從 ``flash.py`` 拆出）：
輔助技、模板適用的技能種類、這一次可以出（或指定）的類別。資料在 ``content/flash_templates.yaml``。
"""

from __future__ import annotations

from trpg.content.flash_templates import FlashCategory, FlashTable, FlashTemplate
from trpg.content.skills import SkillDef

__all__ = [
    "allowed_categories",
    "is_support_skill",
    "template_kinds",
]


def is_support_skill(skill: SkillDef, table: FlashTable) -> bool:
    """輔助技（「輔助」類用）：沒有傷害類效果，而且有治療、護盾或作用於友方的效果（原語分類在
    ``flash_templates.yaml`` 的 ``support``）。"""
    rule = table.support
    if any(e.type in rule.harm_effects for e in skill.effects):
        return False
    helps = any(e.type in rule.help_effects for e in skill.effects)
    buffs = any(e.type in rule.ally_effects and e.affects == "allies" for e in skill.effects)
    return helps or buffs


def template_kinds(table: FlashTable, template: FlashTemplate) -> tuple[str, ...]:
    """小變化模板可以用在哪些技能種類（模板自己的 ``kinds``，沒寫時用類別的）。"""
    if template.kinds is not None:
        return template.kinds
    return table.category(template.category).kinds


def _category_ok(table: FlashTable, category: FlashCategory, skill: SkillDef) -> bool:
    return skill.kind in category.kinds and (
        not category.support_only or is_support_skill(skill, table)
    )


def allowed_categories(table: FlashTable, skill: SkillDef, *, major: bool) -> tuple[str, ...]:
    """這招這一次可以出（或指定）的類別（資料順序）。"""
    categories = table.stage_categories("major" if major else "minor")
    return tuple(c.id for c in categories if _category_ok(table, c, skill))
