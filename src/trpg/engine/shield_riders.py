"""護盾的附帶效果（Phase 3W-2b，``docs/design/06-技能.md`` 6.34.5 護盾類大變化）。

帶附帶效果的護盾是另一個 ``absorbs_damage`` 狀態（``statuses.yaml`` 的 ``shielded_*``），欄位見
:class:`~trpg.content.battle.StatusDef` 的 ``shield_*``：

- **反傷**（``shield_reflect``）：護盾吸收一次相鄰（近戰）攻擊時，對攻擊者反彈固定的物理傷害
  （``shield_absorbed`` 事件觸發）；
- **結束回復**（``shield_end_heal``）：護盾被打破或到期時，持有者回復固定的生命；
- **破盾造表面**（``shield_break_surface``）：護盾被打破時，在持有者自己的格子造出表面；
- **破盾施加狀態**（``shield_break_status``）：護盾被打破時，對打破它的攻擊者施加狀態；
- **破盾電擊**（``shield_break_lightning``，3W-2c）：護盾被打破時，對打破它的攻擊者造成固定的
  雷電傷害（「帶電」是雷電傷害的關鍵字，不是狀態）。

打破由 ``shield_ended``（``broken``）觸發；到期由回合結束的狀態倒數直接結算
（:func:`expiry_effects`）。
"""

from __future__ import annotations

from trpg.content.battle import StatusDef
from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CreateSurfaceEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
)
from trpg.engine.events import EventBase, ShieldAbsorbed, ShieldEnded
from trpg.engine.state import UnitState
from trpg.engine.triggers import register_trigger
from trpg.shared.types import Element

__all__ = ["end_effects", "expiry_effects"]


def end_effects(
    unit: UnitState,
    definition: StatusDef,
    *,
    broken: bool,
    breaker: UnitState | None,
    depth: int = 0,
) -> list[EffectBase]:
    """護盾結束（被打破或到期）時的效果。"""
    effects: list[EffectBase] = []
    if definition.shield_end_heal and unit.alive:
        effects.append(
            HealEffect(
                depth=depth, target_id=unit.id, source_id=unit.id, flat=definition.shield_end_heal
            )
        )
    if broken and definition.shield_break_surface is not None and unit.alive:
        effects.append(
            CreateSurfaceEffect(
                depth=depth,
                source_id=unit.id,
                pos=unit.xy,
                surface=definition.shield_break_surface,
                team=unit.team,
            )
        )
    if (
        broken
        and definition.shield_break_status is not None
        and breaker is not None
        and breaker.alive
        and breaker.team is not unit.team
    ):
        effects.append(
            ApplyStatusEffect(
                depth=depth,
                source_id=unit.id,
                target_id=breaker.id,
                status_id=definition.shield_break_status,
            )
        )
    if (
        broken
        and definition.shield_break_lightning
        and breaker is not None
        and breaker.alive
        and breaker.team is not unit.team
    ):
        effects.append(
            DamageEffect(
                depth=depth,
                source_id=unit.id,
                target_id=breaker.id,
                cause="effect",
                element=Element.LIGHTNING,
                flat=definition.shield_break_lightning,
            )
        )
    return effects


def expiry_effects(ctx: Ctx, unit: UnitState, status_id: str) -> list[EffectBase]:
    """護盾到期（回合結束的狀態倒數）時的效果：只有結束回復（沒有被打破，不造表面也不施加狀態）。"""
    definition = ctx.rules.status_def(status_id)
    if not definition.has_shield_riders:
        return []
    return end_effects(unit, definition, broken=False, breaker=None)


@register_trigger("shield_absorbed")
def _reflect(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, ShieldAbsorbed)
    definition = ctx.rules.status_def(event.status_id)
    if not definition.shield_reflect or not event.melee or event.source_id is None:
        return []
    attacker = ctx.state.units.get(event.source_id)
    if attacker is None or not attacker.alive:
        return []
    return [
        DamageEffect(
            depth=depth,
            source_id=event.unit_id,
            target_id=attacker.id,
            cause="effect",
            element=Element.PHYSICAL,
            flat=definition.shield_reflect,
        )
    ]


@register_trigger("shield_ended")
def _ended(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, ShieldEnded)
    unit = ctx.state.units.get(event.unit_id)
    if unit is None:
        return []
    breaker = None if event.breaker_id is None else ctx.state.units.get(event.breaker_id)
    return end_effects(
        unit,
        ctx.rules.status_def(event.status_id),
        broken=event.broken,
        breaker=breaker,
        depth=depth,
    )
