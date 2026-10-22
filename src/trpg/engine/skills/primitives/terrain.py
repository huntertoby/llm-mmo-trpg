"""地形原語：建立表面、破壞物件、建立障礙物、刻印、抬高與降低地形。

每個作用格（:meth:`~trpg.engine.skills.cast.Cast.tiles`，效果層級的條件對每格分別判斷）各產生
一個效果。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.engine.effects.models import (
    CreateObstacleEffect,
    CreateSurfaceEffect,
    DestroyObjectEffect,
    EffectBase,
    InscribeEffect,
    LowerTerrainEffect,
    RaiseTerrainEffect,
)
from trpg.engine.skills.primitives.base import Handler

if TYPE_CHECKING:
    from trpg.content.skills import EffectSpec
    from trpg.engine.skills.cast import Cast
    from trpg.engine.skills.targeting import ResolvedEffect

__all__ = ["HANDLERS"]


def create_surface(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    batch: list[EffectBase] = []
    for xy in cast.tiles(effect.affects, spec.condition):
        assert spec.surface is not None
        batch.append(
            CreateSurfaceEffect(
                source_id=cast.caster.id,
                pos=xy,
                surface=spec.surface,
                duration=spec.duration,
                team=cast.caster.team,
            )
        )
    return batch


def destroy_object(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """影響格中帶 ``breakable`` 標籤的物件直接摧毀。"""
    state, rules = cast.ctx.state, cast.ctx.rules
    batch: list[EffectBase] = []
    for xy in cast.tiles(effect.affects, spec.condition):
        obj = state.object_at(*xy)
        if obj is not None and "breakable" in rules.object_def(obj.kind).tags:
            batch.append(DestroyObjectEffect(source_id=cast.caster.id, object_id=obj.id))
    return batch


def create_obstacle(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    batch: list[EffectBase] = []
    for xy in cast.tiles(effect.affects, spec.condition):
        assert spec.object is not None
        batch.append(
            CreateObstacleEffect(
                source_id=cast.caster.id, pos=xy, object_kind=spec.object, duration=spec.duration
            )
        )
    return batch


def inscribe(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    return [
        InscribeEffect(
            source_id=cast.caster.id,
            pos=xy,
            team=cast.caster.team,
            element=spec.element,
            tag=spec.tag,
            duration=spec.duration,
        )
        for xy in cast.tiles(effect.affects, spec.condition)
    ]


def raise_terrain(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    return [
        RaiseTerrainEffect(source_id=cast.caster.id, pos=xy, amount=spec.amount or 1)
        for xy in cast.tiles(effect.affects, spec.condition)
    ]


def lower_terrain(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    return [
        LowerTerrainEffect(source_id=cast.caster.id, pos=xy, amount=spec.amount or 1)
        for xy in cast.tiles(effect.affects, spec.condition)
    ]


HANDLERS: dict[str, Handler] = {
    "create_surface": create_surface,
    "destroy_object": destroy_object,
    "create_obstacle": create_obstacle,
    "inscribe": inscribe,
    "raise_terrain": raise_terrain,
    "lower_terrain": lower_terrain,
}
