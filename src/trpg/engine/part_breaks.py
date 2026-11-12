"""頭目部位的傷害分流與破壞效果（PB-1a，``docs/design/05-戰鬥.md`` 5.12.2）。

- **分流**（:func:`damage_part`）：帶 ``part_id`` 的 ``DamageEffect`` 扣完頭目 HP、發出
  ``damage_dealt`` 之後，部位扣掉頭目實際扣掉的 HP（``hp_before − hp_after``，R2；護盾吸收、
  劍陣減半、格擋、轉移與分擔之後），發 ``part_damaged``（扣到 0 點時不發）；降到 0 發
  ``part_broken``。部位已破時不帶、照本體結算（同一動作前一下打破，R5）。
- **防禦覆寫**（R3）：打部位時命中用部位的 ``armor_bonus``、傷害用部位的 ``resist``／
  ``element_mods``（有寫的鍵才換）——以 :func:`defense_view`／:func:`element_view` 的複本計算，
  得到的數字同時扣本體與部位。
- **破壞效果**：``part_broken`` 觸發 :class:`BreakPartEffect`，依 ``on_break`` 的順序結算——
  ``seal_skill``（加進 ``sealed_skills``、發 ``skill_sealed``；正在蓄力這一招就以
  ``part_broken`` 取消）、``interrupt_charge``（有蓄力就取消）、``stat_down``（累加到
  ``part_mods``、發 ``part_stat_down``）、``control``（走一般的施加狀態：免疫、Boss 硬控轉換、
  控制遞減照常，不擲抵抗）、``stop_mechanic``（加進 ``suppressed_statuses``，身上有就移除）。
  破的那一下頭目倒下時 ``part_broken.applied`` 為假，不結算效果（T8）。

沒有 ``part_id`` 的傷害不經過這裡；不取用亂數。
"""

from __future__ import annotations

from trpg.content.parts import (
    BossPart,
    ControlBreak,
    InterruptChargeBreak,
    PartBreakEffect,
    SealSkillBreak,
    StatDownBreak,
    StopMechanicBreak,
)
from trpg.content.skills import CHARGING
from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    BreakPartEffect,
    CancelChargeEffect,
    EffectBase,
    RemoveStatusEffect,
)
from trpg.engine.effects.queue import handler_for, register_effect
from trpg.engine.events import EventBase, PartBroken, PartDamaged, PartStatDown, SkillSealed
from trpg.engine.state import UnitState
from trpg.engine.triggers import register_trigger
from trpg.shared.types import UnitId

__all__ = [
    "DAMAGE_DEALT",
    "damage_part",
    "defense_view",
    "element_view",
    "live_part",
    "part_of",
]

PERMILLE = 1000
DAMAGE_DEALT = "damage_dealt"
"""``stat_down`` 的造成傷害倍率（‰，相乘；其他項是降低量，相加）。"""


def part_of(unit: UnitState, part_id: str | None) -> BossPart | None:
    """``unit`` 的部位 ``part_id``（沒有時為 ``None``）。"""
    if part_id is None:
        return None
    return next((p for p in unit.parts if p.id == part_id), None)


def live_part(unit: UnitState, part_id: str | None) -> BossPart | None:
    """還沒破的部位 ``part_id``；已破或不存在時為 ``None``（傷害照本體結算）。"""
    part = part_of(unit, part_id)
    return None if part is None or part.id in unit.broken_parts else part


def defense_view(unit: UnitState, part_id: str | None) -> UnitState:
    """命中判定用的目標（R3）：打還沒破、有寫 ``armor_bonus`` 的部位時是換掉護甲的複本，否則是
    ``unit`` 本身。複本只能讀，不能拿去結算效果。"""
    part = live_part(unit, part_id)
    if part is None or part.armor_bonus is None:
        return unit
    view = unit.clone()
    view.armor_bonus = part.armor_bonus
    return view


def element_view(unit: UnitState, part_id: str | None) -> UnitState:
    """元素修正用的目標（R3）：打還沒破、有寫 ``resist``／``element_mods`` 的部位時是覆寫了那些鍵的
    複本，否則是 ``unit`` 本身。"""
    part = live_part(unit, part_id)
    if part is None or (part.resist is None and part.element_mods is None):
        return unit
    view = unit.clone()
    if part.resist is not None:
        view.resist = {**unit.resist, **part.resist}
    if part.element_mods is not None:
        view.element_mods = {**unit.element_mods, **part.element_mods}
    return view


def damage_part(
    ctx: Ctx, unit: UnitState, part_id: str | None, hp_before: int, source_id: UnitId | None
) -> list[EventBase]:
    """``unit`` 這一下扣完 HP（``hp_before`` → ``unit.hp``）之後，部位扣同樣的數字（見模組說明）。
    要在 ``damage_dealt`` 之後、倒下之前呼叫。"""
    part = live_part(unit, part_id)
    dealt = hp_before - unit.hp
    if part is None or dealt <= 0:
        return []
    before = unit.part_hp.get(part.id, 0)
    after = max(0, before - dealt)
    unit.part_hp[part.id] = after
    events: list[EventBase] = [
        ctx.emit(
            PartDamaged,
            target_id=unit.id,
            part_id=part.id,
            name_zh=part.name_zh,
            amount=before - after,
            hp_before=before,
            hp_after=after,
        )
    ]
    if after > 0:
        return events
    unit.broken_parts = (*unit.broken_parts, part.id)
    events.append(
        ctx.emit(
            PartBroken,
            target_id=unit.id,
            part_id=part.id,
            name_zh=part.name_zh,
            effects=tuple(e.type for e in part.on_break),
            applied=unit.hp > 0,
            text_zh=part.break_text_zh,
            source_id=source_id,
        )
    )
    return events


@register_trigger("part_broken")
def _break_on_broken(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, PartBroken)
    unit = ctx.state.units.get(event.target_id)
    if not event.applied or unit is None or not unit.alive:
        return []
    return [
        BreakPartEffect(
            depth=depth, target_id=event.target_id, part_id=event.part_id, source_id=event.source_id
        )
    ]


@register_effect("break_part")
def _break_part(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, BreakPartEffect)
    unit = ctx.state.units.get(effect.target_id)
    part = None if unit is None else part_of(unit, effect.part_id)
    if unit is None or part is None or not unit.alive:
        return []
    events: list[EventBase] = []
    for spec in part.on_break:
        events += _apply_break(ctx, unit, part, spec, effect.source_id)
    return events


def _apply_break(
    ctx: Ctx, unit: UnitState, part: BossPart, spec: PartBreakEffect, source_id: UnitId | None
) -> list[EventBase]:
    match spec:
        case SealSkillBreak():
            return _seal(ctx, unit, part, spec)
        case InterruptChargeBreak():
            return _interrupt(ctx, unit) if unit.has_status(CHARGING) else []
        case StatDownBreak():
            return _stat_down(ctx, unit, part, spec)
        case ControlBreak():
            apply = ApplyStatusEffect(
                target_id=unit.id,
                status_id=spec.status,
                duration=spec.duration,
                source_id=source_id,
            )
            return handler_for("apply_status")(ctx, apply)
        case StopMechanicBreak():
            return _stop(ctx, unit, spec.status)


def _seal(ctx: Ctx, unit: UnitState, part: BossPart, spec: SealSkillBreak) -> list[EventBase]:
    if spec.skill not in unit.sealed_skills:
        unit.sealed_skills = (*unit.sealed_skills, spec.skill)
    events: list[EventBase] = [
        ctx.emit(SkillSealed, unit_id=unit.id, skill_id=spec.skill, part_id=part.id)
    ]
    charging = unit.get_status(CHARGING)
    if charging is not None and charging.skill_id == spec.skill:
        events += _interrupt(ctx, unit)
    return events


def _interrupt(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """以既有的 ``cancel_charge`` 取消蓄力（``followup_cancelled``，原因 ``part_broken``）。"""
    cancel = CancelChargeEffect(unit_id=unit.id, reason="part_broken")
    return handler_for("cancel_charge")(ctx, cancel)


def _stat_down(ctx: Ctx, unit: UnitState, part: BossPart, spec: StatDownBreak) -> list[EventBase]:
    mods = unit.part_mods
    if spec.stat == DAMAGE_DEALT:
        total = mods.get(DAMAGE_DEALT, PERMILLE) * spec.amount // PERMILLE
    else:
        total = mods.get(spec.stat, 0) + spec.amount
    mods[spec.stat] = total
    return [
        ctx.emit(
            PartStatDown,
            unit_id=unit.id,
            part_id=part.id,
            stat=spec.stat,
            amount=spec.amount,
            total=total,
        )
    ]


def _stop(ctx: Ctx, unit: UnitState, status_id: str) -> list[EventBase]:
    if status_id not in unit.suppressed_statuses:
        unit.suppressed_statuses = (*unit.suppressed_statuses, status_id)
    if not unit.has_status(status_id):
        return []
    remove = RemoveStatusEffect(target_id=unit.id, status_id=status_id, reason="removed")
    return handler_for("remove_status")(ctx, remove)
