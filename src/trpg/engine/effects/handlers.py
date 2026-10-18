"""單位效果的處理器：damage、heal、move_unit、apply_status、remove_status，以及共用的
「抵達一格」邏輯 :func:`arrive`（墜落、致命地形、表面、撤離）。"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    MoveUnitEffect,
    RemoveStatusEffect,
)
from trpg.engine.effects.queue import register_effect
from trpg.engine.events import (
    CheckRolled,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    Healed,
    MoveBlocked,
    MoveMode,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    SurfaceEntered,
    UnitFell,
    UnitMoved,
)
from trpg.engine.lifecycle import down_unit, escape_unit
from trpg.engine.rules.combat import PERMILLE, PPM, element_modifier_ppm
from trpg.engine.rules.movement import is_deadly
from trpg.engine.rules.statuses import (
    boss_converted_status,
    damage_dealt_permille,
    damage_taken_permille,
    healing_received_permille,
)
from trpg.engine.state import BattleState, StatusInstance, UnitState
from trpg.shared.types import Element, Pos, Surface, Team, UnitId

__all__ = ["ability_modifier", "apply_status", "arrive", "enter_surface", "weather_permille"]


def weather_permille(state: BattleState, element: Element) -> int:
    """天氣對 ``element`` 傷害的倍率（‰），例如下雨時火焰 700、雷電 1200。"""
    weather = state.weather
    if weather is None:
        return PERMILLE
    return PERMILLE + weather.element_damage_permille.get(element, 0)


def ability_modifier(ctx: Ctx, value: int) -> int:
    """檢定的屬性修正：``(屬性 − ability_mod_base) // ability_mod_divisor``。"""
    return (value - ctx.core.ability_mod_base) // ctx.core.ability_mod_divisor


@register_effect("damage")
def _damage(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, DamageEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    rolls: tuple[int, ...] = ()
    mod_ppm = PPM
    weather = PERMILLE
    base_amount: int | None = None
    status_ppm = PPM
    if effect.mode == "lethal":
        amount = unit.hp
    elif effect.mode == "percent_max_hp":
        amount = max(unit.max_hp * effect.permille // PERMILLE, effect.min_damage)
    else:
        if effect.dice is not None:
            count = effect.dice.count * (2 if effect.crit else 1)
            rolls = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(count))
        raw_permille = (sum(rolls) + effect.flat) * PERMILLE + effect.scaled_permille
        if effect.apply_element_mod:
            mod_ppm = element_modifier_ppm(unit, effect.element, ctx.rules)
        if effect.apply_weather:
            weather = weather_permille(ctx.state, effect.element)
        dealt = PERMILLE
        source = None if effect.source_id is None else ctx.state.units.get(effect.source_id)
        if effect.cause == "attack" and source is not None:
            dealt = damage_dealt_permille(ctx.rules, source)  # 虛弱
        status_ppm = dealt * damage_taken_permille(ctx.rules, unit)  # 易傷；千分比 × 千分比
        amount = max(
            raw_permille
            * mod_ppm
            * weather
            * effect.multiplier_permille
            * status_ppm
            // (PERMILLE * PPM * PERMILLE * PERMILLE * PPM),
            effect.min_damage,
        )
        base_amount = max(
            raw_permille * weather * dealt // (PERMILLE * PERMILLE * PERMILLE), effect.min_damage
        )
    hp_before = unit.hp
    unit.hp = max(0, unit.hp - amount)
    events: list[EventBase] = [
        ctx.emit(
            DamageDealt,
            target_id=unit.id,
            source_id=effect.source_id,
            cause=effect.cause,
            element=effect.element,
            rolls=rolls,
            crit=effect.crit,
            element_mod_ppm=mod_ppm,
            amount=amount,
            hp_before=hp_before,
            hp_after=unit.hp,
            pos=unit.pos,
            weather_permille=weather,
            multiplier_permille=effect.multiplier_permille,
            base_amount=base_amount,
            status_ppm=status_ppm,
        )
    ]
    if unit.hp <= 0:
        events.extend(down_unit(ctx, unit))
    return events


@register_effect("heal")
def _heal(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, HealEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    rolls: tuple[int, ...] = ()
    if effect.dice is not None:
        rolls = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(effect.dice.count))
    received = healing_received_permille(ctx.rules, unit)  # 中毒
    amount = max(
        0,
        ((sum(rolls) + effect.flat) * PERMILLE + effect.scaled_permille)
        * received
        // (PERMILLE * PERMILLE),
    )
    hp_before = unit.hp
    unit.hp = min(unit.max_hp, unit.hp + amount)
    return [
        ctx.emit(
            Healed,
            target_id=unit.id,
            source_id=effect.source_id,
            rolls=rolls,
            amount=unit.hp - hp_before,
            hp_before=hp_before,
            hp_after=unit.hp,
            received_permille=received,
        )
    ]


def arrive(
    ctx: Ctx,
    unit: UnitState,
    dest: tuple[int, int],
    mode: MoveMode,
    cost: int = 0,
    *,
    source_id: UnitId | None = None,
) -> list[EventBase]:
    """把單位移到 ``dest`` 並結算抵達的後果（不檢查合法性與阻擋）。

    - ``source_id``：強制位移的推擊者；墜落與致命地形的傷害帶上這個來源（走進去時為 ``None``）。
    - ``walk``／``forced`` 往下落差達 ``fall_damage_min_drop`` 時墜落（``unit_fell``）。
    - 落入致命地形：``entered_deadly_terrain``（之後由觸發表處理死亡或精英傳送）。
    - 進入有 ``on_enter`` 的表面：``surface_entered``（套用狀態）；有檢定時擲骰
      （``check_rolled``，失敗的狀態由觸發表套用）。
    - 撤離勝利條件下，我方單位抵達出口格即離開戰場（``unit_escaped``）。
    """
    state = ctx.state
    from_pos = unit.pos
    drop = state.tile(from_pos.x, from_pos.y).height - state.tile(*dest).height
    unit.pos = Pos(x=dest[0], y=dest[1])
    events: list[EventBase] = [
        ctx.emit(
            UnitMoved, unit_id=unit.id, from_pos=from_pos, to_pos=unit.pos, mode=mode, cost=cost
        )
    ]
    min_drop = ctx.core.fall_damage_min_drop
    if mode != "teleport" and drop >= min_drop:
        levels = drop - (min_drop - 1)
        events.append(
            ctx.emit(UnitFell, unit_id=unit.id, drop=drop, levels=levels, source_id=source_id)
        )
    if is_deadly(state, dest):
        terrain = state.tile(*dest).terrain
        events.append(
            ctx.emit(
                EnteredDeadlyTerrain,
                unit_id=unit.id,
                pos=unit.pos,
                terrain=terrain,
                source_id=source_id,
            )
        )
        return events
    objective = state.objective
    if objective.kind == "escape" and unit.team is Team.ALLY and dest in objective.tiles:
        events.extend(escape_unit(ctx, unit))
        return events
    events.extend(enter_surface(ctx, unit))
    return events


def enter_surface(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """``unit`` 所在格表面的進入效果：``surface_entered``（套用狀態），有檢定時擲骰
    （``check_rolled``）。走進表面、被推進表面，以及表面出現在腳下時都會呼叫。"""
    surface = ctx.state.tile(*unit.xy).surface
    if surface is Surface.NONE:
        return []
    definition = ctx.rules.surface_def(surface)
    if definition.on_enter is None:
        return []
    events: list[EventBase] = [
        ctx.emit(SurfaceEntered, unit_id=unit.id, pos=unit.pos, surface=surface)
    ]
    check = definition.on_enter.check
    if check is not None:
        roll = ctx.check_d20()
        modifier = ability_modifier(ctx, unit.attributes[check.attr])
        total = roll + modifier
        events.append(
            ctx.emit(
                CheckRolled,
                unit_id=unit.id,
                reason=f"surface:{surface.value}",
                attr=check.attr,
                roll=roll,
                modifier=modifier,
                total=total,
                dc=check.dc,
                success=total >= check.dc,
                fail_status=check.fail_status,
            )
        )
    return events


@register_effect("move_unit")
def _move_unit(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, MoveUnitEffect)
    state = ctx.state
    unit = state.units.get(effect.unit_id)
    if unit is None or not unit.alive:
        return []
    dx, dy = effect.dest
    dest = Pos(x=max(dx, 0), y=max(dy, 0))
    if not state.in_bounds(dx, dy):
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="out_of_bounds")]
    occupant = state.unit_at(dx, dy)
    if occupant is not None and occupant.id != unit.id and effect.mode != "walk":
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="occupied")]
    return arrive(ctx, unit, (dx, dy), effect.mode, effect.cost)


def apply_status(ctx: Ctx, effect: ApplyStatusEffect) -> list[EventBase]:
    """施加狀態（重複施加時刷新持續時間，不疊加）。"""
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    events: list[EventBase] = []
    status_id = effect.status_id
    duration = effect.duration
    if duration is None:
        duration = ctx.rules.status_def(status_id).duration  # 轉換後持續時間沿用原效果
    converted = boss_converted_status(ctx.rules, unit, status_id)
    if converted != status_id:  # Boss 硬控轉換：所有來源一致（技能路徑已先轉換，這裡不會再轉）
        events.append(
            ctx.emit(
                StatusConverted,
                target_id=unit.id,
                from_status=status_id,
                to_status=converted,
                source_id=effect.source_id,
            )
        )
        status_id = converted
    definition = ctx.rules.status_def(status_id)
    existing = unit.get_status(status_id)
    instance = StatusInstance(status_id=status_id, remaining=duration, source_id=effect.source_id)
    # 目前只有 refresh：重複施加時以新的持續時間取代，不疊加
    others = [s for s in unit.statuses if s.status_id != status_id]
    unit.statuses = sorted([*others, instance], key=lambda s: s.status_id)
    if definition.control_group is not None:  # 控制遞減：同類別在 R + control_dr_rounds 輪結束前
        unit.control_dr[definition.control_group] = ctx.state.round + ctx.core.control_dr_rounds
    events.append(
        ctx.emit(
            StatusApplied,
            target_id=unit.id,
            status_id=status_id,
            duration=duration,
            refreshed=existing is not None,
            source_id=effect.source_id,
        )
    )
    return events


@register_effect("apply_status")
def _apply_status(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ApplyStatusEffect)
    return apply_status(ctx, effect)


@register_effect("remove_status")
def _remove_status(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, RemoveStatusEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.has_status(effect.status_id):
        return []
    unit.statuses = [s for s in unit.statuses if s.status_id != effect.status_id]
    return [
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=effect.status_id, reason=effect.reason)
    ]
