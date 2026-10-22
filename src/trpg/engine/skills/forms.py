"""帶戰場變奏的技能的選取列舉（Phase 3-25a，``docs/phases/Phase3計畫.md`` 33 PM 決定 #4）。

候選目標 ＝ 各型態候選的聯集；某個選取合法 ⇔ 它的目標點選出的型態（:func:`chosen_variant`）
就是列出它的那個型態，而且該型態接受它（:func:`~trpg.engine.skills.targeting.selections`）。
所以射程變奏只在條件成立時放寬（例：居高 +2 只對比自己低的目標點有效）。施放時解譯器以同一個
規則選型態再檢查選取，兩邊一致。

沒有變奏的技能直接用 :func:`~trpg.engine.skills.targeting.selections`（結果完全不變）。
"""

from __future__ import annotations

from collections.abc import Iterator

from trpg.content.skills import SkillDef
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.skills.targeting import SkillArea, selections
from trpg.engine.state import BattleState, UnitState
from trpg.engine.variants import chosen_variant, possible_variants, target_point

__all__ = ["has_skill_selection", "skill_selections"]


def skill_selections(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> Iterator[tuple[UseSkill, SkillArea]]:
    """``skill``（基礎型態，已套用等級與修正：:func:`~trpg.engine.modifiers.acting_skill`）所有
    型態的合法選取與影響範圍（確定性順序：依型態的資料順序、基礎型態最後，各型態內照
    :func:`selections` 的順序）。"""
    base = state.ruleset.skill_def(skill.id)
    if not base.variants:
        yield from selections(state, caster, skill)
        return
    for variant_id in possible_variants(state, caster, base):
        if variant_id is None:
            form = skill
        else:
            form = modifiers.shaped_skill(state, caster, base.variant_form(variant_id))
        for action, area in selections(state, caster, form):
            chosen = chosen_variant(state, caster, base, target_point(state, action))
            if (None if chosen is None else chosen.id) == variant_id:
                yield action, area


def has_skill_selection(state: BattleState, caster: UnitState, skill: SkillDef) -> bool:
    """:func:`skill_selections` 至少有一個（不建立完整列表）。"""
    return next(skill_selections(state, caster, skill), None) is not None
