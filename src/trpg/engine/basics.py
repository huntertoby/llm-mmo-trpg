"""基本動作：守護、換位、瞄準（Phase 3-21a，玩法 #24；``docs/design/05-戰鬥.md`` 5.2.2）。

- **守護**（``Defend``）：沿用防禦（防禦值 +25%、到自己下回合開始），可選相鄰隊友；轉移承受的結算
  在 :func:`trpg.engine.reactions.try_intercept`，這裡只放合法性與設定；
- **換位**（``Swap``）：與相鄰我方單位互換位置（沿用 ``swap_units``；不觸發藉機攻擊，朝向不變）；
- **瞄準**（``Aim``）：下一次需要擲命中的攻擊命中加值，用掉或回合結束時失效。

所有數值在 ``core.yaml``。
"""

from __future__ import annotations

from trpg.engine.actions import Action, Aim, Defend, Swap
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, SwapUnitsEffect
from trpg.engine.events import GuardSet, UnitAimed
from trpg.engine.ids import DEFENDING
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.statuses import is_rooted, skip_turn_status
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import UnitId

__all__ = [
    "adjacent_allies",
    "aim_problem",
    "do_aim",
    "do_defend",
    "do_swap",
    "guard_problem",
    "swap_problem",
]


def adjacent_allies(state: BattleState, unit: UnitState) -> list[UnitState]:
    """與 ``unit`` 相鄰的我方單位（含召喚物；不含自己；依單位 ID）。"""
    return [
        other
        for other in state.units_sorted()
        if other.id != unit.id
        and other.alive
        and other.team is unit.team
        and manhattan(other.xy, unit.xy) == 1
    ]


def _ally_problem(state: BattleState, unit: UnitState, ally_id: UnitId | None) -> str | None:
    ally = None if ally_id is None else state.units.get(ally_id)
    if ally is None or not ally.alive:
        return f"找不到目標：{ally_id}"
    if ally.id == unit.id:
        return "不能指定自己（守護自己請不指定目標）"
    if ally.team is not unit.team:
        return f"{ally.name_zh} 不是隊友"
    if manhattan(ally.xy, unit.xy) != 1:
        return f"{ally.name_zh} 不在相鄰格"
    return None


def guard_problem(state: BattleState, unit: UnitState, ally_id: UnitId | None) -> str | None:
    """守護（含守護自己）不合法的原因；合法時 ``None``。順序：AP、已守護、隊友是否合法。"""
    cost = state.ruleset.core.defend_ap_cost
    if unit.ap < cost:
        return f"AP 不足：需要 {cost}，剩餘 {unit.ap}"
    if unit.has_status(DEFENDING):
        return "已處於守護姿態"
    if ally_id is None:
        return None
    return _ally_problem(state, unit, ally_id)


def do_defend(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Defend)
    problem = guard_problem(ctx.state, unit, action.target_id)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= ctx.core.defend_ap_cost
    execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=DEFENDING, source_id=unit.id)])
    if action.target_id is not None:
        unit.guarding_id = action.target_id
        ctx.emit(GuardSet, unit_id=unit.id, ally_id=action.target_id)


def guard_covers(ctx: Ctx, guardian: UnitState, target: UnitState) -> bool:
    """``guardian`` 現在能不能替 ``target`` 承受一次單體攻擊（守護中、仍相鄰、本輪次數未滿、
    沒有被暈眩等讓他不能行動的狀態）。"""
    return (
        guardian.guarding_id == target.id
        and guardian.has_status(DEFENDING)
        and guardian.id != target.id
        and guardian.alive
        and guardian.guard_transfers < ctx.core.guard_transfers_per_round
        and manhattan(guardian.xy, target.xy) == 1
        and skip_turn_status(ctx.rules, guardian) is None
    )


def swap_problem(state: BattleState, unit: UnitState, ally_id: UnitId) -> str | None:
    """換位不合法的原因：AP、對象、任一方不能移動（定身、速度 0）、高低差會墜落。"""
    core = state.ruleset.core
    if unit.ap < core.swap_ap_cost:
        return f"AP 不足：需要 {core.swap_ap_cost}，剩餘 {unit.ap}"
    problem = _ally_problem(state, unit, ally_id)
    if problem is not None:
        return problem
    ally = state.units[ally_id]
    for mover in (unit, ally):
        if is_rooted(state.ruleset, mover):
            return f"{mover.name_zh} 被定身，不能換位"
        if mover.speed == 0:
            return f"{mover.name_zh} 不能移動，不能換位"
    drop = abs(state.tile(*unit.xy).height - state.tile(*ally.xy).height)
    if drop >= core.fall_damage_min_drop:
        return "高低差太大，不能換位"
    return None


def do_swap(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Swap)
    problem = swap_problem(ctx.state, unit, action.target_id)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= ctx.core.swap_ap_cost
    execute(
        ctx,
        [SwapUnitsEffect(source_id=unit.id, unit_id=unit.id, other_id=action.target_id)],
    )


def aim_problem(state: BattleState, unit: UnitState) -> str | None:
    """瞄準不合法的原因：已經瞄準了（不疊加）、AP 不足。"""
    if unit.aimed:
        return "已經瞄準了"
    cost = state.ruleset.core.aim_ap_cost
    if unit.ap < cost:
        return f"AP 不足：需要 {cost}，剩餘 {unit.ap}"
    return None


def do_aim(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Aim)
    problem = aim_problem(ctx.state, unit)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= ctx.core.aim_ap_cost
    unit.aimed = True
    ctx.emit(UnitAimed, unit_id=unit.id, bonus=ctx.core.aim_hit_bonus)
