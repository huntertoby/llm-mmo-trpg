"""``copy_skill`` 的來源與條件判定（Phase R3 自 :mod:`trpg.engine.copying` 抽出；只讀狀態）。

不依賴技能選取（:mod:`trpg.engine.skills.targeting`），所以 targeting 的施放檢查可以直接匯入；
需要列舉選取的 :func:`~trpg.engine.copying.copy_selections` 與
:func:`~trpg.engine.skills.targeting.copy_problem` 在上層。:mod:`trpg.engine.copying` 照舊轉出
本模組的函式。
"""

from __future__ import annotations

from trpg.content.skills import COPY_SKILL, SkillDef
from trpg.engine.rules.forms import is_spell_for_silence
from trpg.engine.rules.geometry import has_line_of_sight
from trpg.engine.rules.statuses import blocks_spells
from trpg.engine.state import BattleState, UnitState

__all__ = ["copy_free_problem", "copy_source", "has_copy_effect", "uncopyable_reason"]


def has_copy_effect(skill: SkillDef) -> bool:
    """技能是否有 ``copy_skill`` 效果（它必須是唯一的效果，見 ``SkillDef._check_copy_skill``）。"""
    return any(e.type == COPY_SKILL for e in skill.effects)


def uncopyable_reason(state: BattleState, skill: SkillDef) -> str | None:
    """技能本身不能被複製的原因（傳說、改寫規則型、非主動、陷阱、敵人專用、層數需求、帶變奏）。"""
    checks = (
        (skill.kind != "active" or skill.trap is not None, "不是一般的主動技能"),
        (skill.enemy_only, "是敵人專用的技能"),  # 5F-R1（06 6.35）：戰鬥中暫時複製也不行
        (skill.rarity == "legendary", "是傳說技能"),
        (skill.cost.stacks is not None, "需要層數"),
        # 紀錄只存技能 ID，看不出當時施放的是哪個型態，保守地不複製（3E-2a）
        (bool(skill.variants), "帶有戰場變奏"),
        (
            any(
                state.ruleset.primitive_def(e.type).category == "rule_rewrite"
                for e in skill.effects
            ),
            "改寫了規則",
        ),
    )
    for failed, why in checks:
        if failed:
            return f"「{skill.name_zh}」{why}，不能複製"
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
    if is_spell_for_silence(state.ruleset, skill) and blocks_spells(state.ruleset, caster):
        return f"沉默中：不能使用法術技：{skill.name_zh}"
    return None
