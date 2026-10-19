"""``copy_skill``（Phase 3C-4b，``docs/phases/Phase3C計畫.md`` 7）：複製本輪最後施放的主動技能。

- 戰鬥狀態記錄 ``casts``（本輪以 ``UseSkill`` 施放過的主動技能：施放者、技能、當輪）。
- 可複製的條件（:func:`copy_source`）：本輪內「最後一個別人施放的」（不算複製者自己的）、施放者
  仍在場上而且複製者看得到它（視線）；技能本身不能是傳說、改寫規則型（含 ``copy_skill``）、陷阱
  或有層數需求的技能（保守）。
- 複製的技能由複製者重新選目標（:func:`copy_selections`），不扣法力與 AP、不進冷卻、不花源力，但
  沉默、射程、視線與技能條件都要合法（:func:`copy_free_problem`、``selections``）；不檢查
  ``weapon_req``（技能的傷害與射程照複製者自己的武器算）。
- 玩家：``UseSkill``（沒有 ``copy_cast``）→ 結算暫停（``Pending.kind == "copy_skill"``）→
  ``Decision`` 帶 ``copy_cast``（複製技能的選取）繼續；AI 與重播直接在 ``UseSkill.copy_cast``
  給出選取。
"""

from __future__ import annotations

from collections.abc import Iterator

from trpg.content.skills import COPY_SKILL, SkillDef
from trpg.engine.actions import UseSkill
from trpg.engine.rules.geometry import has_line_of_sight
from trpg.engine.rules.statuses import blocks_spells
from trpg.engine.skills.targeting import SkillArea, selections
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "copy_free_problem",
    "copy_problem",
    "copy_selections",
    "copy_source",
    "has_copy_effect",
    "uncopyable_reason",
]


def has_copy_effect(skill: SkillDef) -> bool:
    """技能是否有 ``copy_skill`` 效果（它必須是唯一的效果，見 ``SkillDef._check_copy_skill``）。"""
    return any(e.type == COPY_SKILL for e in skill.effects)


def uncopyable_reason(state: BattleState, skill: SkillDef) -> str | None:
    """技能本身不能被複製的原因（傳說、改寫規則型、非主動、陷阱、層數需求）；可以時為 ``None``。"""
    if skill.kind != "active" or skill.trap is not None:
        return f"「{skill.name_zh}」不是一般的主動技能，不能複製"
    if skill.rarity == "legendary":
        return f"「{skill.name_zh}」是傳說技能，不能複製"
    if skill.cost.stacks is not None:
        return f"「{skill.name_zh}」需要層數，不能複製"
    for effect in skill.effects:
        if state.ruleset.primitive_def(effect.type).category == "rule_rewrite":
            return f"「{skill.name_zh}」改寫了規則，不能複製"
    return None


def copy_source(state: BattleState, caster: UnitState) -> tuple[SkillDef, UnitState] | str:
    """``caster`` 現在可以複製的技能與它的施放者；不能時回傳原因（繁體中文）。"""
    last = next(
        (c for c in reversed(state.casts) if c.round == state.round and c.unit_id != caster.id),
        None,
    )
    if last is None:
        return "本輪還沒有其他單位施放過技能，沒有技能可以複製"
    origin = state.units.get(last.unit_id)
    if origin is None or not origin.alive:
        return "上一個施放技能的單位已不在場上，沒有技能可以複製"
    skill = state.ruleset.skill_def(last.skill_id)
    reason = uncopyable_reason(state, skill)
    if reason is not None:
        return reason
    if not has_line_of_sight(state, caster.xy, origin.xy):
        return f"看不到 {origin.name_zh}，無法複製「{skill.name_zh}」"
    return skill, origin


def copy_free_problem(state: BattleState, caster: UnitState, skill: SkillDef) -> str | None:
    """複製 ``skill`` 時仍要滿足的條件：沉默（法術技）；法力、AP、冷卻、次數與 ``weapon_req`` 都
    不檢查。"""
    if skill.category == "spell" and blocks_spells(state.ruleset, caster):
        return f"沉默中：不能使用法術技：{skill.name_zh}"
    return None


def copy_selections(state: BattleState, caster: UnitState) -> Iterator[tuple[UseSkill, SkillArea]]:
    """``caster`` 複製的技能目前所有合法的選取與影響範圍（確定性順序，同 ``selections``）。"""
    found = copy_source(state, caster)
    if isinstance(found, str):
        return
    skill = found[0]
    if copy_free_problem(state, caster, skill) is not None:
        return
    yield from selections(state, caster, skill)


def copy_problem(state: BattleState, caster: UnitState) -> str | None:
    """有 ``copy_skill`` 的技能目前不能施放的原因：沒有可複製的技能，或複製的技能沒有合法的選取。"""
    found = copy_source(state, caster)
    if isinstance(found, str):
        return found
    skill = found[0]
    problem = copy_free_problem(state, caster, skill)
    if problem is not None:
        return problem
    if next(selections(state, caster, skill), None) is None:
        return f"「{skill.name_zh}」目前沒有合法的目標"
    return None
