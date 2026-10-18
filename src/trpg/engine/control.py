"""施加狀態的抵抗判定、控制遞減與 Boss 硬控轉換（Phase 2B-1，``docs/phases/Phase2B計畫.md``
3.2–3.4；``docs/design/06-技能.md`` 6.6、6.10）。

由 **技能或動作** 對敵方施加帶 ``save_attr`` 的狀態時：

1. Boss 轉換：帶 ``boss`` 標籤的單位被施加 ``control_group: hard`` 的狀態時，改為施加
   ``boss_control_conversion`` 中對照的狀態（持續時間沿用原效果），發出 ``status_converted``。
2. 抵抗判定：攻方用技能的 ``scaling_attr``、守方用（轉換後）狀態的 ``save_attr``，沿用
   ``maneuvers.contest`` 的比例公式（``d20 + 比例修正 + 熟練 ≥ hit_target``）；守方正處於該控制類別
   的遞減期間時，守方屬性值 ×``control_dr_resist_permille``（無條件捨去）。失敗則不施加，
   發出 ``status_resisted``。
3. 成功施加後的遞減記錄由 :func:`trpg.engine.effects.handlers.apply_status` 負責（所有來源一致）。

對友方或自己施加的狀態、表面與環境造成的狀態不擲抵抗（仍會做 Boss 轉換）。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from trpg.engine.context import Ctx
from trpg.engine.effects.models import ApplyStatusEffect
from trpg.engine.events import StatusConverted, StatusResisted, StatusSaveRolled
from trpg.engine.rules.combat import PERMILLE, is_hit
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Attribute

__all__ = ["StatusPlan", "control_dr_active", "plan_status", "status_effect", "status_save_chance"]

BOSS_TAG = "boss"


@dataclass(frozen=True, slots=True)
class StatusPlan:
    """對 ``target`` 施加 ``original_id`` 時實際會發生的事（不擲骰）。

    ``status_id``：Boss 轉換之後實際施加的狀態；``save_attr`` 為 ``None`` 表示命中即施加。
    ``defense_value``：守方抵抗用的屬性值（已含遞減）；``diminished``：遞減是否生效。
    """

    original_id: str
    status_id: str
    save_attr: Attribute | None
    defense_value: int
    diminished: bool

    @property
    def converted(self) -> bool:
        return self.status_id != self.original_id


def control_dr_active(state: BattleState, unit: UnitState, group: str) -> bool:
    """``unit`` 對控制類別 ``group`` 是否正處於遞減期間（含記錄的最後一輪）。"""
    return unit.control_dr.get(group, -1) >= state.round


def plan_status(state: BattleState, target: UnitState, status_id: str) -> StatusPlan:
    """Boss 轉換、抵抗屬性與遞減後的守方屬性值（純函式，供結算與預覽共用）。"""
    rules = state.ruleset
    definition = rules.status_def(status_id)
    final = status_id
    if definition.control_group == "hard" and target.has_tag(BOSS_TAG):
        final = rules.core.boss_control_conversion.get(status_id, status_id)
        definition = rules.status_def(final)
    attr = definition.save_attr
    if attr is None:
        return StatusPlan(status_id, final, None, 0, False)
    value = target.attributes[attr]
    group = definition.control_group
    diminished = group is not None and control_dr_active(state, target, group)
    if diminished:
        value = value * rules.core.control_dr_resist_permille // PERMILLE
    return StatusPlan(status_id, final, attr, max(1, value), diminished)


def _modifier(
    state: BattleState, caster: UnitState, attack_attr: Attribute, plan: StatusPlan
) -> int:
    return state.ruleset.hit_table.modifier(caster.attributes[attack_attr], plan.defense_value)


def status_save_chance(
    state: BattleState, caster: UnitState, attack_attr: Attribute, plan: StatusPlan
) -> Fraction:
    """攻方成功（狀態會被施加）的機率：窮舉 d20（自然 1 失敗、自然 20 成功）。
    沒有 ``save_attr`` 的狀態為 1。"""
    if plan.save_attr is None:
        return Fraction(1)
    core = state.ruleset.core
    bonus = _modifier(state, caster, attack_attr, plan) + core.proficiency
    wins = sum(1 for n in range(1, 21) if is_hit(n, n + bonus, core.hit_target))
    return Fraction(wins, 20)


def status_effect(
    ctx: Ctx,
    *,
    caster: UnitState,
    target: UnitState,
    status_id: str,
    duration: int | None,
    attack_attr: Attribute,
    skill_id: str | None = None,
) -> ApplyStatusEffect | None:
    """技能對 ``target`` 施加狀態：轉換、抵抗判定，回傳要入列的效果（被抵抗時為 ``None``）。

    預覽：抵抗判定是分歧點——``min`` 視為抵抗成功（不施加）、``max`` 視為失敗（施加）。
    """
    state = ctx.state
    plan = plan_status(state, target, status_id)
    if plan.converted and duration is None:
        duration = state.ruleset.status_def(status_id).duration  # 持續時間沿用原效果
    if plan.converted:
        ctx.emit(
            StatusConverted,
            target_id=target.id,
            from_status=plan.original_id,
            to_status=plan.status_id,
            source_id=caster.id,
        )
    effect = ApplyStatusEffect(
        source_id=caster.id, target_id=target.id, status_id=plan.status_id, duration=duration
    )
    if plan.save_attr is None or target.team is caster.team:
        return effect
    core = ctx.core
    modifier = _modifier(state, caster, attack_attr, plan)
    if ctx.preview is None:
        natural = ctx.rng.d20()
    else:
        ctx.mark_branch()
        natural = 20 if ctx.preview == "max" else 1
    total = natural + modifier + core.proficiency
    applied = is_hit(natural, total, core.hit_target)
    ctx.emit(
        StatusSaveRolled,
        attacker_id=caster.id,
        target_id=target.id,
        status_id=plan.status_id,
        attack_attr=attack_attr,
        attack_value=caster.attributes[attack_attr],
        save_attr=plan.save_attr,
        defense_value=plan.defense_value,
        diminished=plan.diminished,
        natural=natural,
        modifier=modifier,
        proficiency=core.proficiency,
        total=total,
        target_number=core.hit_target,
        applied=applied,
        skill_id=skill_id,
    )
    if not applied:
        ctx.emit(StatusResisted, target_id=target.id, status_id=plan.status_id, source_id=caster.id)
        return None
    return effect
