"""回合流程（``docs/專案計畫.md`` 5.2.1、``docs/phases/Phase1計畫.md`` 4.4）。

回合開始：AP 回復為 ``ap_per_turn + min(保留, ap_carry_max)``、移動點數回滿、
移除「到自己下回合開始」的狀態、結算持續傷害（燃燒），再結算站立表面的回合開始效果
（毒、聖光、火焰）。
回合結束：倒數型狀態 −1（歸零移除）、記錄保留的 AP、到期的召喚物（Phase 3D-4a）與持續區域
（Phase 3D-5）消失。回合開始時站在持續區域內的效果在表面效果之後結算。
全員行動完為一輪：``round_ended`` → 環境回合 → 勝利條件的每輪判定 → 輪數上限 →
``round_started``（反應次數重設）。
"""

from __future__ import annotations

from trpg.content.skills import CHARGING
from trpg.engine.activations import expire_activations
from trpg.engine.context import Ctx
from trpg.engine.delayed import release_at_turn_start
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
    TurnSkipped,
    TurnStarted,
)
from trpg.engine.gear import gear_turn_start
from trpg.engine.grants import expire_granted_skills
from trpg.engine.objectives import check_battle_end, check_round_end, end_battle
from trpg.engine.results import ResolveResult
from trpg.engine.rewrites import ap_cap
from trpg.engine.rules.movement import is_flying
from trpg.engine.rules.statuses import ap_penalty, move_points_for_turn, skip_turn_status
from trpg.engine.skill_infusion import release_infusion
from trpg.engine.skill_triggers import (
    collect_turn_end,
    collect_turn_start,
    reset_round_counts,
    settle,
)
from trpg.engine.stacks import expire_stacks
from trpg.engine.state import StatusInstance, UnitState
from trpg.engine.summons import (
    detonate_if_adjacent,
    expire_summons,
    pulse_summon,
    pulse_totem,
    summon_inert,
)
from trpg.engine.traps import detect_traps, tick_traps
from trpg.engine.zones import expire_zones_at_turn_end, zones_turn_start
from trpg.shared.types import Surface, UnitId

__all__ = [
    "advance_turn",
    "check_battle_end",
    "end_turn",
    "finish_resolution",
    "skip_turn_if_stunned",
    "start_turn",
]


def start_turn(ctx: Ctx, unit_id: UnitId) -> None:
    """開始 ``unit_id`` 的回合（可能因持續傷害而倒下，此時 ``active_unit`` 變回 ``None``）。"""
    state = ctx.state
    core = ctx.core
    unit = state.units[unit_id]
    state.active_unit = unit.id
    unit.ap = min(
        core.ap_per_turn + min(unit.ap_carry, core.ap_carry_max) + unit.ap_pending,
        ap_cap(core),
    )
    unit.ap = max(0, unit.ap - ap_penalty(ctx.rules, unit))  # 透支（Phase 3-50）
    unit.ap_carry = 0
    unit.moved_this_turn = False  # 連段條件的「本回合」紀錄（Phase 3D-1）
    unit.ran_this_turn = False  # 跑步每回合限 1 次（Phase 3-20）
    unit.guarding_id = None  # 守護到自己的下回合開始（Phase 3-21a）
    unit.turn_cast_tags = ()
    unit.ap_gain_turn = unit.ap_pending  # 回合外存下的 AP 算在這個回合的 AP 回復上限內（3G-G3a）
    unit.gear_turn_counts = {}  # 裝備觸發的每回合 1 次（3G-G3a）
    unit.ap_pending = 0  # grant_ap 給的、等到這個回合才加上的 AP（Phase 3C-4a）
    unit.move_points = move_points_for_turn(ctx.rules, unit)
    gained = max(0, min(unit.stamina_regen, unit.max_stamina - unit.stamina))  # 耐力回復（3H-5）
    unit.stamina += gained
    if summon_inert(state, unit):
        unit.ap = 0  # 圖騰（Phase 3D-4b）、土牆（3-33e2a）：不攻擊、不施放，只有回合開始的特性
    ctx.emit(
        TurnStarted,
        unit_id=unit.id,
        ap=unit.ap,
        move_points=unit.move_points,
        mana=unit.mana,
        max_mana=unit.max_mana,
        stamina=unit.stamina,
        max_stamina=unit.max_stamina,
        stamina_gained=gained,
    )
    _tick_cooldowns(ctx, unit)
    expire_activations(ctx, unit)  # 限時傳說到期（Phase 3D-6）
    detect_traps(ctx, unit)  # 感知的常駐數值（Phase 3H-1）

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
        if definition.on_turn_start_heal is not None:
            ticking.append(
                HealEffect(
                    target_id=unit.id,
                    source_id=status.source_id,
                    dice=definition.on_turn_start_heal.dice,
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
    _turn_start_hooks(ctx, unit)


def _turn_start_hooks(ctx: Ctx, unit: UnitState) -> None:
    """回合開始、狀態與表面效果之後：裝備的代價（3G-G1）、持續區域、陷阱倒數、圖騰、延遲段、被動的
    ``on_turn_start``，最後是召喚物身上灌注的技能（Phase 3-33d；每一步之前都確認行動者還站著）。"""
    state = ctx.state
    if unit.alive and unit.gear.bonuses:  # 裝備的代價型：回合開始失去 HP（不致死，Phase 3G-G1）
        gear_turn_start(ctx, unit)
    if unit.alive and state.zones:  # 站在持續區域內的回合開始效果（Phase 3D-5）
        zones_turn_start(ctx, unit)
    if unit.alive and state.traps:  # 放置者的陷阱倒數（Phase 2E-3）：delay 到期觸發、enter 到期消失
        tick_traps(ctx, unit)
    if unit.alive and unit.is_summon:  # 圖騰的光環（Phase 3D-4b）
        pulse_totem(ctx, unit)
        pulse_summon(ctx, unit)  # 水精等的脈動（3-33e1）
        detonate_if_adjacent(ctx, unit, "adjacent")  # 爆裂傀儡回合開始時已相鄰（3-33e2a）
    if unit.alive and unit.has_status(CHARGING):  # 延遲段（Phase 3F-4b）：釋放或失效
        release_at_turn_start(ctx, unit)
    if unit.alive:  # 被動技能 on_turn_start：在狀態與表面的回合開始效果之後
        collect_turn_start(ctx, unit)
        settle(ctx)
    if unit.alive and unit.infused_skill is not None:  # 灌注的技能（Phase 3-33d）：行動之前施放
        release_infusion(ctx, unit)
        settle(ctx)


def skip_turn_if_stunned(ctx: Ctx) -> bool:
    """行動者帶有 ``skip_turn`` 狀態（暈眩）時跳過整個回合：沒有 AP 與移動點數，發出
    ``turn_skipped``，然後照常結束回合（狀態倒數）。回傳是否跳過。

    回合開始的處理（冷卻、持續傷害）已在 :func:`start_turn` 完成；在那之中倒下者不會走到這裡。
    """
    state = ctx.state
    if state.active_unit is None:
        return False
    unit = state.units[state.active_unit]
    status_id = skip_turn_status(ctx.rules, unit)
    if status_id is None:
        return False
    unit.ap = 0
    unit.ap_carry = 0
    unit.move_points = 0
    ctx.emit(TurnSkipped, unit_id=unit.id, status_id=status_id)
    end_turn(ctx)
    return True


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
    if tile.surface is Surface.NONE or is_flying(unit):  # 會飛的單位不受地面表面影響（3-33e2b）
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
    collect_turn_end(ctx, unit)  # 被動技能 on_turn_end：在狀態倒數之前
    settle(ctx)
    if not unit.alive:
        return  # 被自己的觸發擊倒：已離開先攻順序，回合流程接著開始下一位
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
                    status_id=status.status_id,
                    remaining=remaining,
                    source_id=status.source_id,
                    amount=status.amount,
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
    unit.aimed = False  # 瞄準到回合結束失效（Phase 3-21a）
    expire_granted_skills(ctx, unit)  # 暫時獲得的技能倒數（Phase 3D-8c）
    expire_summons(ctx, unit)  # 召喚物到期：在召喚者的回合結束時消失（Phase 3D-4a）
    expire_zones_at_turn_end(ctx, unit)  # 持續區域到期：在施放者的回合結束時消失（Phase 3D-5）
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
        unit.extra_reactions = 0  # extra_reaction 到下一輪開始為止（Phase 3C-4b）
        unit.guard_transfers = 0  # 守護每輪的轉移次數（Phase 3-21a）
    reset_round_counts(iter(state.units_sorted()))
    ctx.emit(RoundStarted)
    expire_stacks(ctx)  # 到期的層數在新的一輪開始時清空（Phase 2E-3）
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
            if skip_turn_if_stunned(ctx):
                continue  # active_unit 仍是這位，下一圈取順序中的下一位
            check_battle_end(ctx)
            return


def finish_resolution(ctx: Ctx) -> ResolveResult:
    """一次結算的收尾：（尚未結算的）被動觸發、勝負判定、行動者離場時換下一位、寫回亂數狀態。"""
    settle(ctx)
    if not check_battle_end(ctx) and ctx.state.active_unit is None:
        advance_turn(ctx)
    ctx.finish_rng()
    return ResolveResult(ctx.state, ctx.events, None)
