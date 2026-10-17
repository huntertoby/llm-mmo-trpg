"""回合流程、勝負判定（``docs/專案計畫.md`` 5.2.1、``docs/phases/Phase1計畫.md`` 4.4）。

回合開始：AP 回復為 ``ap_per_turn + min(保留, ap_carry_max)``、移動點數回滿、
移除「到自己下回合開始」的狀態、結算持續傷害（燃燒）。
回合結束：倒數型狀態 −1（歸零移除）、記錄保留的 AP。
全員行動完為一輪；超過 ``max_rounds`` 時以平手結束（Phase 1B 在輪與輪之間執行環境回合）。
"""

from __future__ import annotations

from typing import Literal

from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect, EffectBase, RemoveStatusEffect
from trpg.engine.events import (
    BattleEnded,
    RoundEnded,
    RoundStarted,
    StatusRemoved,
    TurnEnded,
    TurnStarted,
)
from trpg.engine.results import ResolveResult
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId

__all__ = ["advance_turn", "check_battle_end", "end_turn", "finish_resolution", "start_turn"]


def check_battle_end(ctx: Ctx) -> bool:
    """全滅判定：只剩一方（或雙方皆無）存活單位時結束戰鬥。回傳戰鬥是否已結束。"""
    state = ctx.state
    if state.ended:
        return True
    teams = sorted({u.team for u in state.living_units()})
    if len(teams) >= 2:  # noqa: PLR2004 - 雙方
        return False
    winner = teams[0] if teams else None
    _end_battle(ctx, winner, "eliminate")
    return True


def _end_battle(ctx: Ctx, winner: Team | None, reason: Literal["eliminate", "round_limit"]) -> None:
    state = ctx.state
    state.ended = True
    state.winner = winner
    state.end_reason = reason
    state.active_unit = None
    ctx.emit(BattleEnded, winner=winner, reason=reason)


def start_turn(ctx: Ctx, unit_id: UnitId) -> None:
    """開始 ``unit_id`` 的回合（可能因持續傷害而倒下，此時 ``active_unit`` 變回 ``None``）。"""
    state = ctx.state
    core = ctx.core
    unit = state.units[unit_id]
    state.active_unit = unit.id
    unit.ap = core.ap_per_turn + min(unit.ap_carry, core.ap_carry_max)
    unit.ap_carry = 0
    unit.move_points = unit.speed
    ctx.emit(TurnStarted, unit_id=unit.id, ap=unit.ap, move_points=unit.move_points)

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
    # 先移除到期狀態，再結算持續傷害（各自依狀態 ID 順序）
    if expiring:
        execute(ctx, expiring)
    if ticking:
        execute(ctx, ticking)


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


def advance_turn(ctx: Ctx) -> None:
    """輪到先攻順序中的下一位；必要時開始新的一輪。跳過在回合開始時倒下的單位。"""
    state = ctx.state
    while not check_battle_end(ctx):
        next_pos = state.turn_pos + 1 if state.active_unit is not None else state.turn_pos
        state.active_unit = None
        if next_pos >= len(state.turn_order):
            ctx.emit(RoundEnded)
            if state.max_rounds is not None and state.round >= state.max_rounds:
                _end_battle(ctx, None, "round_limit")
                return
            state.round += 1
            ctx.emit(RoundStarted)
            next_pos = 0
        state.turn_pos = next_pos
        start_turn(ctx, state.turn_order[next_pos])
        if state.active_unit is not None:
            check_battle_end(ctx)
            return


def finish_resolution(ctx: Ctx) -> ResolveResult:
    """一次結算的收尾：勝負判定、行動者倒下時換下一位、寫回亂數狀態。"""
    if not check_battle_end(ctx) and ctx.state.active_unit is None:
        advance_turn(ctx)
    ctx.finish_rng()
    return ResolveResult(ctx.state, ctx.events, None)
