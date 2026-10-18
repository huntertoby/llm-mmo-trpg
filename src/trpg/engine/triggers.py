"""事件 → 效果的觸發對照表。

``register_trigger("unit_fell")`` 註冊一個函式：收到該類事件時回傳要入列的新效果
（``depth`` 由佇列傳入）。Phase 1B 的元素 × 標籤互動、反應規則、Phase 2 的被動與詞條
都以同樣方式掛上。

Phase 1A 的觸發：

- ``unit_fell`` → 墜落傷害（最大 HP × 每層千分比，上限 ``fall_damage_cap_permille``，
  不套用元素修正）。
- ``entered_deadly_terrain`` → 一般單位直接死亡；帶 ``elite`` 標籤者受最大 HP ×
  ``deadly_terrain_elite_permille`` 傷害，並傳送到最近的安全格。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.engine.context import Ctx
from trpg.engine.effects.models import DamageEffect, EffectBase, MoveUnitEffect
from trpg.engine.events import EnteredDeadlyTerrain, EventBase, UnitFell
from trpg.engine.rules.movement import nearest_safe_tile

__all__ = ["ELITE_TAG", "TriggerFn", "effects_for", "register_trigger"]

ELITE_TAG = "elite"

type TriggerFn = Callable[[Ctx, EventBase, int], list[EffectBase]]

_TRIGGERS: dict[str, list[TriggerFn]] = {}


def register_trigger(event_type: str) -> Callable[[TriggerFn], TriggerFn]:
    def decorator(fn: TriggerFn) -> TriggerFn:
        _TRIGGERS.setdefault(event_type, []).append(fn)
        return fn

    return decorator


def effects_for(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    """``event`` 觸發的效果（依註冊順序串接）。"""
    event_type = getattr(event, "type", "")
    result: list[EffectBase] = []
    for fn in _TRIGGERS.get(event_type, ()):
        result.extend(fn(ctx, event, depth))
    return result


@register_trigger("unit_fell")
def _fall_damage(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, UnitFell)
    core = ctx.core
    permille = min(
        event.levels * core.fall_damage_permille_per_level, core.fall_damage_cap_permille
    )
    return [
        DamageEffect(
            depth=depth,
            source_id=event.source_id,
            target_id=event.unit_id,
            cause="fall",
            mode="percent_max_hp",
            permille=permille,
            apply_element_mod=False,
        )
    ]


@register_trigger("entered_deadly_terrain")
def _deadly_terrain(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, EnteredDeadlyTerrain)
    unit = ctx.state.unit(event.unit_id)
    if not unit.has_tag(ELITE_TAG):
        return [
            DamageEffect(
                depth=depth,
                source_id=event.source_id,
                target_id=unit.id,
                cause="deadly_terrain",
                mode="lethal",
                apply_element_mod=False,
            )
        ]
    effects: list[EffectBase] = [
        DamageEffect(
            depth=depth,
            source_id=event.source_id,
            target_id=unit.id,
            cause="deadly_terrain",
            mode="percent_max_hp",
            permille=ctx.core.deadly_terrain_elite_permille,
            apply_element_mod=False,
        )
    ]
    safe = nearest_safe_tile(ctx.state, (event.pos.x, event.pos.y), unit)
    if safe is not None:
        effects.append(MoveUnitEffect(depth=depth, unit_id=unit.id, dest=safe, mode="teleport"))
    return effects
