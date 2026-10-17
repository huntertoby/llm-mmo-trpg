"""回合流程（``docs/專案計畫.md`` 5.2.1、``docs/phases/Phase1計畫.md`` 4.4）。

回合開始：AP 回復為 ``ap_per_turn + min(保留, ap_carry_max)``、移動點數回滿、
移除「到自己下回合開始」的狀態、結算持續傷害（燃燒），再結算站立表面的回合開始效果
（毒、聖光、火焰）。
回合結束：倒數型狀態 −1（歸零移除）、記錄保留的 AP。
全員行動完為一輪：``round_ended`` → 環境回合 → 勝利條件的每輪判定 → 輪數上限 →
``round_started``（反應次數重設）。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    RemoveStatusEffect,
)
from trpg.engine.environment import run_environment
from trpg.engine.events import (
    RoundEnded,
    RoundStarted,
    SkillCooldownChanged,
    StatusRemoved,
    TurnEnded,
    TurnStarted,
)
from trpg.engine.objectives import check_battle_end, check_round_end, end_battle
from trpg.engine.results import ResolveResult
from trpg.engine.state import StatusInstance, UnitState
from trpg.shared.types import Surface, UnitId

__all__ = ["advance_turn", "check_battle_end", "end_turn", "finish_resolution", "start_turn"]


def start_turn(ctx: Ctx, unit_id: UnitId) -> None:
    """開始 ``unit_id`` 的回合（可能因持續傷害而倒下，此時 ``active_unit`` 變回 ``None``）。"""
    state = ctx.state
    core = ctx.core
    unit = state.units[unit_id]
    state.active_unit = unit.id
    unit.ap = core.ap_per_turn + min(unit.ap_carry, core.ap_carry_max)
    unit.ap_carry = 0
    unit.move_points = unit.speed
    ctx.emit(
        TurnStarted,
        unit_id=unit.id,
        ap=unit.ap,
        move_points=unit.move_points,
        mana=unit.mana,
        max_mana=unit.max_mana,
    )
    _tick_cooldowns(ctx, unit)

    expiring: list[EffectBase] = []
    ticking: list[EffectBase] = []
    for status in unit.statuses:
        definition = ctx.rules.status_def(status.status_id)
        if definition.expires == "own_turn_start":
            expiring.append(
                RemoveStatusEffect(target_id=unit.id, status_id=status.status_id, reason="expired")
            )
        if definition.on_turn_start_damage is not None:
            tick = definition.on_turn_start_damage
            ticking.append(
                DamageEffect(
                    target_id=unit.id,
                    source_id=status.source_id,
                    cause="status",
                    element=tick.element,
                    dice=tick.dice,
                )
            )
    # 先移除到期狀態，再結算持續傷害（各自依狀態 ID 順序），最後是表面效果
    if expiring:
        execute(ctx, expiring)
    if ticking:
        execute(ctx, ticking)
    surface_effects = _surface_turn_start(ctx, unit)
    if surface_effects and unit.alive:
        execute(ctx, surface_effects)


def _tick_cooldowns(ctx: Ctx, unit: UnitState) -> None:
    """自己的回合開始：每個冷卻中的技能 −1（歸零移除）。"""
    for skill_id in sorted(unit.cooldowns):
        remaining = unit.cooldowns[skill_id] - 1
        if remaining <= 0:
            del unit.cooldowns[skill_id]
            remaining = 0
        else:
            unit.cooldowns[skill_id] = remaining
        ctx.emit(SkillCooldownChanged, unit_id=unit.id, skill_id=skill_id, remaining=remaining)


def _surface_turn_start(ctx: Ctx, unit: UnitState) -> list[EffectBase]:
    """站在表面上的回合開始效果（``surfaces.yaml`` 的 ``on_turn_start``）。"""
    tile = ctx.state.tile(*unit.xy)
    if tile.surface is Surface.NONE:
        return []
    on_start = ctx.rules.surface_def(tile.surface).on_turn_start
    if on_start is None:
        return []
    effects: list[EffectBase] = []
    heal = on_start.heal
    if heal is not None:
        ally = not heal.allies_only or tile.surface_team is None or tile.surface_team is unit.team
        excluded = heal.exclude_tag is not None and unit.has_tag(heal.exclude_tag)
        if ally and not excluded:
            effects.append(HealEffect(target_id=unit.id, dice=heal.dice))
    damage = on_start.damage
    if damage is not None and (damage.only_tag is None or unit.has_tag(damage.only_tag)):
        effects.append(
            DamageEffect(
                target_id=unit.id, cause="surface", element=damage.element, dice=damage.dice
            )
        )
    if on_start.apply_status is not None:
        effects.append(ApplyStatusEffect(target_id=unit.id, status_id=on_start.apply_status))
    return effects


def end_turn(ctx: Ctx) -> None:
    """結束目前行動者的回合：倒數型狀態 −1、保留 AP。"""
    state = ctx.state
    assert state.active_unit is not None
    unit = state.units[state.active_unit]
    kept: list[StatusInstance] = []
    expired: list[str] = []
    for status in unit.statuses:
        definition = ctx.rules.status_def(status.status_id)
        if definition.expires == "turn_end" and status.remaining is not None:
            remaining = status.remaining - 1
            if remaining <= 0:
                expired.append(status.status_id)
                continue
            kept.append(
                StatusInstance(
                    status_id=status.status_id, remaining=remaining, source_id=status.source_id
                )
            )
            continue
        kept.append(status)
    unit.statuses = kept
    for status_id in expired:
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=status_id, reason="expired")
    unit.ap_carry = min(unit.ap, ctx.core.ap_carry_max)
    unit.ap = 0
    unit.move_points = 0
    ctx.emit(TurnEnded, unit_id=unit.id, ap_carried=unit.ap_carry)


def _end_round(ctx: Ctx) -> bool:
    """一輪結束：環境回合與每輪勝負判定。回傳戰鬥是否已結束。"""
    state = ctx.state
    ctx.emit(RoundEnded)
    run_environment(ctx)
    if check_round_end(ctx):
        return True
    if state.max_rounds is not None and state.round >= state.max_rounds:
        end_battle(ctx, None, "round_limit")
        return True
    state.round += 1
    for unit in state.units.values():
        unit.reactions_used = 0
    ctx.emit(RoundStarted)
    return False


def advance_turn(ctx: Ctx) -> None:
    """輪到先攻順序中的下一位；必要時結束本輪（環境回合）並開始新的一輪。

    跳過在回合開始時倒下的單位。
    """
    state = ctx.state
    while not check_battle_end(ctx):
        next_pos = state.turn_pos + 1 if state.active_unit is not None else state.turn_pos
        state.active_unit = None
        if next_pos >= len(state.turn_order):
            if _end_round(ctx):
                return
            next_pos = 0
        state.turn_pos = next_pos
        start_turn(ctx, state.turn_order[next_pos])
        if state.active_unit is not None:
            check_battle_end(ctx)
            return


def finish_resolution(ctx: Ctx) -> ResolveResult:
    """一次結算的收尾：勝負判定、行動者離場時換下一位、寫回亂數狀態。"""
    if not check_battle_end(ctx) and ctx.state.active_unit is None:
        advance_turn(ctx)
    ctx.finish_rng()
    return ResolveResult(ctx.state, ctx.events, None)
