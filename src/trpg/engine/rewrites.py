"""改寫規則型原語（Phase 3C-4a，``docs/design/06-技能.md`` 6.3、6.6）：``grant_ap``、
``reset_cooldown``。``cheat_death`` 只是施加 ``prevents_death`` 的狀態（解譯器直接產生
``ApplyStatusEffect``），擋下致命傷害的規則在 ``trpg.engine.effects.handlers``。

規則（數值在 ``content/``）：

- ``grant_ap``：目標立刻獲得 AP，超過本回合上限（:func:`ap_cap`）的部分不保留；目標不在自己的
  回合時，AP 存進 ``ap_pending``，在它下次回合開始時加上（同樣不超過上限）。同一單位每輪最多被給
  一次，之後的給予發出 ``effect_fizzled``（``already_granted``）。
- ``extra_reaction``（Phase 3C-4b）：目標本輪的反應次數上限 +``amount``，每輪開始時歸零。
- ``reset_cooldown``：目標的冷卻歸零（``which: all`` 全部、``tag`` 只有帶該標籤的技能——含修正規則
  加上的標籤）；花源力的技能（``cost.source``）與施放的這個技能本身不重置；施放者自己不受影響。
"""

from __future__ import annotations

from trpg.content.rules import CoreRules
from trpg.content.skills import EffectSpec, SkillDef
from trpg.engine import modifiers
from trpg.engine.context import Ctx
from trpg.engine.events import ApGranted, EffectFizzled, ReactionsGranted, SkillCooldownChanged
from trpg.engine.gear.core import cap_ap_gain
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "ap_cap",
    "gear_grant_ap",
    "grant_ap",
    "grant_ap_problem",
    "grant_reactions",
    "reset_cooldowns",
    "resettable_cooldowns",
]


def ap_cap(core: CoreRules) -> int:
    """單位同時持有的 AP 上限（本回合上限）：``ap_per_turn ＋ ap_carry_max``。"""
    return core.ap_per_turn + core.ap_carry_max


def grant_ap_problem(state: BattleState, target: UnitState) -> str | None:
    """``target`` 這一輪不能再被給 AP 的原因（已經被給過）；可以時為 ``None``。"""
    if target.ap_granted_round == state.round:
        return f"{target.name_zh} 這一輪已經被給過 AP"
    return None


def grant_ap(ctx: Ctx, caster: UnitState, target: UnitState, amount: int) -> None:
    """``grant_ap`` 對 ``target`` 的結算（見模組說明）。"""
    state = ctx.state
    if grant_ap_problem(state, target) is not None:
        ctx.emit(EffectFizzled, effect_kind="grant_ap", pos=target.pos, reason="already_granted")
        return
    target.ap_granted_round = state.round
    cap = ap_cap(ctx.core)
    deferred = state.active_unit != target.id
    if deferred:
        before = target.ap_pending
        target.ap_pending = min(before + amount, cap)
        after = target.ap_pending
    else:
        before = target.ap
        target.ap = max(before, min(before + amount, cap))
        after = target.ap
    target.ap_gain_turn += after - before
    ctx.emit(
        ApGranted,
        unit_id=target.id,
        source_id=caster.id,
        amount=after - before,
        ap_after=after,
        deferred=deferred,
    )


def gear_grant_ap(ctx: Ctx, owner: UnitState, target: UnitState, amount: int) -> None:
    """裝備觸發（Phase 3G-G3a，``affix_trig_kill_ap``）回復 AP：本回合已回復的 AP（``grant_ap``、
    ``refund_ap`` 與裝備，``ap_gain_turn``）合計不超過 ``caps.ap_gain_per_round``（+1）；不在自己
    回合時存進 ``ap_pending``；不受「每輪最多被給一次」限制。沒有任何增加時發出 ``effect_fizzled``
    （``ap_gain_cap``）。"""

    state = ctx.state
    granted = cap_ap_gain(ctx.rules, target.ap_gain_turn, amount)
    cap = ap_cap(ctx.core)
    deferred = state.active_unit != target.id
    before = target.ap_pending if deferred else target.ap
    after = max(before, min(before + granted, cap))
    if after <= before:
        ctx.emit(EffectFizzled, effect_kind="grant_ap", pos=target.pos, reason="ap_gain_cap")
        return
    if deferred:
        target.ap_pending = after
    else:
        target.ap = after
    target.ap_gain_turn += after - before
    ctx.emit(
        ApGranted,
        unit_id=target.id,
        source_id=owner.id,
        amount=after - before,
        ap_after=after,
        deferred=deferred,
    )


def resettable_cooldowns(
    state: BattleState, caster: UnitState, target: UnitState, skill: SkillDef, spec: EffectSpec
) -> list[str]:
    """``reset_cooldown`` 會重置的 ``target`` 技能（依技能 ID 排序；AI 的估計也用它）。"""
    if target.id == caster.id:
        return []
    found: list[str] = []
    for skill_id in sorted(target.cooldowns):
        if target.cooldowns[skill_id] <= 0 or skill_id == skill.id:
            continue
        definition = state.ruleset.skill_def(skill_id)
        if definition.cost.source is not None:
            continue
        if spec.which == "tag" and spec.tag not in modifiers.effective_tags(
            state, target, definition
        ):
            continue
        found.append(skill_id)
    return found


def reset_cooldowns(
    ctx: Ctx, caster: UnitState, target: UnitState, skill: SkillDef, spec: EffectSpec
) -> bool:
    """``reset_cooldown`` 對 ``target`` 的結算：每個重置的技能發出 ``skill_cooldown_changed``
    （``remaining: 0``）。回傳是否重置了任何技能。"""
    reset = resettable_cooldowns(ctx.state, caster, target, skill, spec)
    for skill_id in reset:
        del target.cooldowns[skill_id]
        ctx.emit(SkillCooldownChanged, unit_id=target.id, skill_id=skill_id, remaining=0)
    return bool(reset)


def grant_reactions(ctx: Ctx, caster: UnitState, target: UnitState, amount: int) -> None:
    """``extra_reaction`` 對 ``target`` 的結算：本輪反應上限 +``amount``（可疊加，下一輪歸零）。"""
    target.extra_reactions += amount
    ctx.emit(
        ReactionsGranted,
        unit_id=target.id,
        source_id=caster.id,
        amount=amount,
        total=target.extra_reactions,
    )
