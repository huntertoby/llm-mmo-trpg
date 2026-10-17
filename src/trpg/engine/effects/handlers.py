"""Phase 1A 的效果處理器：damage、heal、move_unit、apply_status、remove_status。"""

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
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    Healed,
    MoveBlocked,
    StatusApplied,
    StatusRemoved,
    UnitFell,
    UnitMoved,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.rules.combat import PERMILLE, PPM, element_modifier_ppm
from trpg.engine.rules.movement import is_deadly
from trpg.engine.state import StatusInstance
from trpg.shared.types import Pos

__all__: list[str] = []


@register_effect("damage")
def _damage(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, DamageEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or unit.downed:
        return []
    rolls: tuple[int, ...] = ()
    mod_ppm = PPM
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
        amount = max(raw_permille * mod_ppm // (PERMILLE * PPM), effect.min_damage)
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
        )
    ]
    if unit.hp <= 0:
        events.extend(down_unit(ctx, unit))
    return events


@register_effect("heal")
def _heal(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, HealEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or unit.downed:
        return []
    rolls: tuple[int, ...] = ()
    if effect.dice is not None:
        rolls = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(effect.dice.count))
    amount = max(0, sum(rolls) + effect.flat)
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
        )
    ]


@register_effect("move_unit")
def _move_unit(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, MoveUnitEffect)
    state = ctx.state
    unit = state.units.get(effect.unit_id)
    if unit is None or unit.downed:
        return []
    dx, dy = effect.dest
    dest = Pos(x=max(dx, 0), y=max(dy, 0))
    if not state.in_bounds(dx, dy):
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="out_of_bounds")]
    occupant = state.unit_at(dx, dy)
    if occupant is not None and occupant.id != unit.id and effect.mode != "walk":
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="occupied")]
    from_pos = unit.pos
    drop = state.tile(from_pos.x, from_pos.y).height - state.tile(dx, dy).height
    unit.pos = dest
    events: list[EventBase] = [
        ctx.emit(
            UnitMoved,
            unit_id=unit.id,
            from_pos=from_pos,
            to_pos=dest,
            mode=effect.mode,
            cost=effect.cost,
        )
    ]
    min_drop = ctx.core.fall_damage_min_drop
    if effect.mode != "teleport" and drop >= min_drop:
        levels = drop - (min_drop - 1)
        events.append(ctx.emit(UnitFell, unit_id=unit.id, drop=drop, levels=levels))
    if is_deadly(state, (dx, dy)):
        events.append(
            ctx.emit(
                EnteredDeadlyTerrain, unit_id=unit.id, pos=dest, terrain=state.tile(dx, dy).terrain
            )
        )
    return events


@register_effect("apply_status")
def _apply_status(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ApplyStatusEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or unit.downed:
        return []
    definition = ctx.rules.status_def(effect.status_id)
    duration = effect.duration if effect.duration is not None else definition.duration
    existing = unit.get_status(effect.status_id)
    instance = StatusInstance(
        status_id=effect.status_id, remaining=duration, source_id=effect.source_id
    )
    # 目前只有 refresh：重複施加時以新的持續時間取代，不疊加
    others = [s for s in unit.statuses if s.status_id != effect.status_id]
    unit.statuses = sorted([*others, instance], key=lambda s: s.status_id)
    return [
        ctx.emit(
            StatusApplied,
            target_id=unit.id,
            status_id=effect.status_id,
            duration=duration,
            refreshed=existing is not None,
            source_id=effect.source_id,
        )
    ]


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
