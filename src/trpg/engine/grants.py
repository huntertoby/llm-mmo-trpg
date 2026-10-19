"""暫時獲得技能（Phase 3D-8c，``grant_skill``，``docs/design/06-技能.md`` 6.20）。

目標（施放者自己或友方）的技能列暫時多出一個技能，不佔技能欄位。狀態存在
:attr:`~trpg.engine.state.UnitState.granted_skills`（可序列化、可重播）：技能 ID 與剩餘輪數。

- 持續輪數在 **目標自己的回合結束時** 倒數（:func:`expire_granted_skills`），歸零就消失，並清除
  該技能的冷卻與使用次數紀錄（下次再獲得是全新的）。
- 同一個被給的技能不疊加：重新施放只把剩餘輪數刷新成這次的 ``duration``。
- 目標原本就裝備了該技能時不結算（``effect_fizzled``，原因 ``already_equipped``）。
- 被給的技能照它自己的規則使用（AP、法力、冷卻、武器需求）；:attr:`UnitState.all_skills` 是引擎各處
  列舉「可以使用的技能」的依據。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import EffectFizzled, SkillGranted, SkillGrantExpired
from trpg.engine.state import GrantedSkill, UnitState

__all__ = ["expire_granted_skills", "grant_skill", "granted_remaining"]


def granted_remaining(unit: UnitState, skill_id: str) -> int | None:
    """``skill_id`` 作為暫時獲得的技能還剩幾輪；不是暫時獲得的為 ``None``。"""
    for granted in unit.granted_skills:
        if granted.skill_id == skill_id:
            return granted.remaining
    return None


def grant_skill(
    ctx: Ctx, caster: UnitState, target: UnitState, skill_id: str, duration: int
) -> bool:
    """讓 ``target`` 暫時獲得 ``skill_id`` ``duration`` 輪；回傳是否結算（目標原本就裝備了該技能時
    發出 ``effect_fizzled`` 並回傳 ``False``）。已經暫時擁有時只刷新剩餘輪數。"""
    if skill_id in target.skills:
        ctx.emit(
            EffectFizzled, effect_kind="grant_skill", pos=target.pos, reason="already_equipped"
        )
        return False
    refreshed = granted_remaining(target, skill_id) is not None
    kept = [g for g in target.granted_skills if g.skill_id != skill_id]
    if refreshed:  # 保持原本的順序：就地換成新的剩餘輪數
        target.granted_skills = tuple(
            GrantedSkill(skill_id, duration) if g.skill_id == skill_id else g
            for g in target.granted_skills
        )
    else:
        target.granted_skills = (*kept, GrantedSkill(skill_id, duration))
    ctx.emit(
        SkillGranted,
        unit_id=target.id,
        source_id=caster.id,
        skill_id=skill_id,
        duration=duration,
        refreshed=refreshed,
    )
    return True


def expire_granted_skills(ctx: Ctx, unit: UnitState) -> None:
    """``unit`` 的回合結束：暫時獲得的技能剩餘輪數 −1（依獲得順序），歸零的消失，並清除冷卻與
    使用次數紀錄。"""
    if not unit.granted_skills:
        return
    kept: list[GrantedSkill] = []
    for granted in unit.granted_skills:
        if granted.remaining > 1:
            kept.append(GrantedSkill(granted.skill_id, granted.remaining - 1))
            continue
        unit.cooldowns.pop(granted.skill_id, None)
        unit.skill_uses.pop(granted.skill_id, None)
        ctx.emit(SkillGrantExpired, unit_id=unit.id, skill_id=granted.skill_id)
    unit.granted_skills = tuple(kept)
