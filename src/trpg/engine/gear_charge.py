"""裝備充能（第 7 類）的啟動（Phase 3G-G3a，``docs/design/08-裝備.md`` 8.21.2.7）。

累積層數見 :mod:`trpg.engine.gear_triggers`；這裡是 ``ActivateCharge`` 動作：花 ``cost_stacks`` 層
與 ``cost_ap`` AP，結算詞條的 ``effects``（發出 ``charge_activated``）。

- 只在自己的回合、層數與 AP 足夠時合法（前端放在行動面板的「更多動作」）。
- ``effect_target: target``：必須指定一個普攻合法的敵人（武器射程與視線，不檢查 AP）；
  ``self``：不指定目標。
- 效果歸給持有者，自動命中（沒有命中判定）；期間引起的觸發在整個動作結束後結算。
"""

from __future__ import annotations

from trpg.content.equipment import ChargeAffix
from trpg.engine.actions import Action, ActivateCharge
from trpg.engine.context import Ctx
from trpg.engine.events import ChargeActivated
from trpg.engine.gear_state import GearAffix
from trpg.engine.gear_triggers import gear_carrier
from trpg.engine.rules.combat import attack_problem
from trpg.engine.skill_triggers import holding
from trpg.engine.skills.interpreter import use_gear_effects
from trpg.engine.stacks import spend_stacks
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import UnitId

__all__ = [
    "active_charges",
    "charge_actions",
    "charge_problem",
    "do_activate_charge",
    "find_charge",
]


def active_charges(unit: UnitState) -> tuple[tuple[GearAffix, ChargeAffix], ...]:
    """持有者身上生效中的充能詞條（詞條 ID 排序）。"""
    return tuple(
        (g, g.affix) for g in unit.gear.active_affixes("charge") if isinstance(g.affix, ChargeAffix)
    )


def find_charge(unit: UnitState, affix_id: str) -> ChargeAffix | None:
    """持有者身上生效中、id 為 ``affix_id`` 的充能詞條；沒有時為 ``None``。"""
    return next((a for _, a in active_charges(unit) if a.id == affix_id), None)


def _cost_problem(unit: UnitState, affix: ChargeAffix) -> str | None:
    have = unit.stacks.get(affix.stack, 0)
    if have < affix.cost_stacks:
        return f"層數不足：需要 {affix.cost_stacks} 層，目前 {have} 層"
    if unit.ap < affix.cost_ap:
        return f"AP 不足：需要 {affix.cost_ap}，剩餘 {unit.ap}"
    return None


def charge_problem(
    state: BattleState, unit: UnitState, affix_id: str, target_id: UnitId | None
) -> str | None:
    """啟動不合法的原因（繁體中文）；合法時為 ``None``。"""
    affix = find_charge(unit, affix_id)
    if affix is None:
        return f"{unit.name_zh} 沒有這條充能詞條：{affix_id}"
    problem = _cost_problem(unit, affix)
    if problem is not None:
        return problem
    if affix.effect_target == "self":
        return "這條充能作用在自己，不能指定目標" if target_id is not None else None
    target = None if target_id is None else state.units.get(target_id)
    if target is None:
        return "必須指定一個敵方目標"
    return attack_problem(state, unit, target)


def charge_actions(state: BattleState, unit: UnitState) -> list[Action]:
    """目前能啟動的充能（詞條 ID 排序；需要目標的依目標 ID）。"""
    actions: list[Action] = []
    for _, affix in active_charges(unit):
        if _cost_problem(unit, affix) is not None:
            continue
        if affix.effect_target == "self":
            actions.append(ActivateCharge(unit_id=unit.id, affix_id=affix.id))
            continue
        actions.extend(
            ActivateCharge(unit_id=unit.id, affix_id=affix.id, target_id=t.id)
            for t in state.living_units()
            if attack_problem(state, unit, t) is None
        )
    return actions


def do_activate_charge(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, ActivateCharge)
    problem = charge_problem(ctx.state, unit, action.affix_id, action.target_id)
    if problem is not None:
        raise IllegalActionError(problem)
    affix = find_charge(unit, action.affix_id)
    assert affix is not None
    target = None if action.target_id is None else ctx.state.units[action.target_id]
    with holding(ctx):
        unit.ap -= affix.cost_ap
        ctx.emit(
            ChargeActivated,
            unit_id=unit.id,
            affix_id=affix.id,
            name_zh=affix.name_zh,
            stack_id=affix.stack,
            stacks_spent=affix.cost_stacks,
            ap_spent=affix.cost_ap,
            target_id=action.target_id,
        )
        spend_stacks(ctx, unit, affix.stack, affix.cost_stacks, source_id=unit.id)
        use_gear_effects(ctx, unit, gear_carrier(ctx.rules, unit, affix), target)
