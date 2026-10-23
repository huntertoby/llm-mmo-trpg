"""事件 → 效果的觸發對照表。

``register_trigger("unit_fell")`` 註冊一個函式：收到該類事件時回傳要入列的新效果
（``depth`` 由佇列傳入）。Phase 1B 的元素 × 標籤互動、反應規則、Phase 2 的被動與詞條
都以同樣方式掛上。

Phase 1A 的觸發：

- ``unit_fell`` → 墜落傷害（最大 HP × 每層千分比，上限 ``fall_damage_cap_permille``，
  不套用元素修正）。
- ``collided`` → 撞擊傷害（Phase 3C-3a）：被推的單位、撞到的單位、撞到的 ``breakable`` 物件，
  每少走 1 格各受一次 ``collision_damage_dice``（物理、不加屬性），歸給位移的來源單位。
- ``object_toppled`` → 推倒（Phase 3C-5a）：壓到的單位各受 ``topple_damage_dice``（物理）並倒地、
  壓到的 ``breakable`` 物件受同樣傷害，歸給推的人。
- ``entered_deadly_terrain`` → 一般單位直接死亡；帶 ``elite`` 標籤者受最大 HP ×
  ``deadly_terrain_elite_permille`` 傷害，並傳送到最近的安全格。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    DamageObjectEffect,
    EffectBase,
    MoveUnitEffect,
)
from trpg.engine.events import (
    Collided,
    EnteredDeadlyTerrain,
    EventBase,
    ObjectToppled,
    UnitFell,
    WallToppled,
)
from trpg.engine.ids import ELITE_TAG, PRONE
from trpg.engine.rules.landing import nearest_free
from trpg.engine.rules.perks import attribute_perk
from trpg.shared.types import ObjectId, UnitId

__all__ = ["ELITE_TAG", "TriggerFn", "effects_for", "register_trigger"]


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
    safe = nearest_free(ctx.state, (event.pos.x, event.pos.y), mover=unit.id)
    if safe is not None:
        effects.append(MoveUnitEffect(depth=depth, unit_id=unit.id, dest=safe, mode="teleport"))
    return effects


def _collision_flats(ctx: Ctx, event: Collided, victims: list[UnitId]) -> dict[UnitId, int]:
    """每次撞擊對各受害者的固定傷害修正：位移來源的 ``collision_dealt`` 減去受害者自己的
    ``collision_taken``（屬性常駐數值，Phase 3H-1）。"""
    units = ctx.state.units
    source = None if event.source_id is None else units.get(event.source_id)
    dealt = 0 if source is None else attribute_perk(ctx.rules, source, "collision_dealt")
    return {
        v: dealt - (attribute_perk(ctx.rules, units[v], "collision_taken") if v in units else 0)
        for v in victims
    }


@register_trigger("collided")
def _collision_damage(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, Collided)
    dice = event.dice or ctx.core.collision_damage_dice
    effects: list[EffectBase] = []
    victims = [event.unit_id] + ([] if event.other_id is None else [event.other_id])
    flats = _collision_flats(ctx, event, victims)  # 力量的常駐數值（3H-1）
    for _ in range(event.shortfall):
        effects.extend(
            DamageEffect(
                depth=depth,
                source_id=event.source_id,
                target_id=victim,
                cause="collision",
                dice=dice,
                flat=flats[victim],
            )
            for victim in victims
        )
        if event.object_id is not None and _breakable(ctx, event.object_id):
            effects.append(
                DamageObjectEffect(
                    depth=depth,
                    source_id=event.source_id,
                    object_id=event.object_id,
                    dice=dice,
                    cause="collision",
                )
            )
    return effects


@register_trigger("object_toppled")
def _topple_damage(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, ObjectToppled)
    dice = ctx.core.topple_damage_dice
    effects: list[EffectBase] = []
    for victim in event.units:
        effects.append(
            DamageEffect(
                depth=depth,
                source_id=event.source_id,
                target_id=victim,
                cause="topple",
                dice=dice,
            )
        )
        effects.append(
            ApplyStatusEffect(
                depth=depth, source_id=event.source_id, target_id=victim, status_id=PRONE
            )
        )
    effects.extend(
        DamageObjectEffect(
            depth=depth, source_id=event.source_id, object_id=oid, dice=dice, cause="topple"
        )
        for oid in event.objects
        if _breakable(ctx, oid)
    )
    return effects


@register_trigger("wall_toppled")
def _wall_topple_damage(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    """土牆倒下（3-33e2a）：壓到的單位與物件照物件推倒的規則受傷，單位並倒地。"""
    assert isinstance(event, WallToppled)
    dice = ctx.core.topple_damage_dice
    effects: list[EffectBase] = []
    for victim in event.units:
        effects.append(
            DamageEffect(
                depth=depth,
                source_id=event.source_id,
                target_id=victim,
                cause="topple",
                dice=dice,
            )
        )
        effects.append(
            ApplyStatusEffect(
                depth=depth, source_id=event.source_id, target_id=victim, status_id=PRONE
            )
        )
    effects.extend(
        DamageObjectEffect(
            depth=depth, source_id=event.source_id, object_id=oid, dice=dice, cause="topple"
        )
        for oid in event.objects
        if _breakable(ctx, oid)
    )
    return effects


def _breakable(ctx: Ctx, object_id: ObjectId) -> bool:
    obj = ctx.state.objects.get(object_id)
    return (
        obj is not None and not obj.destroyed and "breakable" in ctx.rules.object_def(obj.kind).tags
    )
