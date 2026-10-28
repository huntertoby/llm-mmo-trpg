"""地形原語：建立表面、吹送表面、清除表面、破壞物件、建立障礙物、刻印、抬高與降低地形。

每個作用格（:meth:`~trpg.engine.skills.cast.Cast.tiles`，效果層級的條件對每格分別判斷）各產生
一個效果。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.engine.effects.models import (
    ClearSurfaceEffect,
    CreateObstacleEffect,
    CreateSurfaceEffect,
    DestroyObjectEffect,
    EffectBase,
    InscribeEffect,
    LowerTerrainEffect,
    RaiseTerrainEffect,
)
from trpg.engine.events import EffectFizzled
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.wind import blow_effect

if TYPE_CHECKING:
    from trpg.content.skills import EffectSpec
    from trpg.engine.skills.cast import Cast
    from trpg.engine.skills.targeting import ResolvedEffect

__all__ = ["HANDLERS"]


def create_surface(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    batch: list[EffectBase] = []
    duration = spec.duration
    bonus = attribute_perk(cast.ctx.rules, cast.caster, "surface_duration")  # 智力（3H-1）
    if bonus and spec.surface is not None:
        base = (
            duration if duration is not None else cast.ctx.rules.surface_def(spec.surface).duration
        )
        duration = None if base is None else base + bonus  # 永久的表面不變
    for xy in cast.tiles(effect.affects, spec.condition):
        assert spec.surface is not None
        batch.append(
            CreateSurfaceEffect(
                source_id=cast.caster.id,
                pos=xy,
                surface=spec.surface,
                duration=duration,
                team=cast.caster.team,
            )
        )
    return batch


def blow_surface(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """吹送（Phase 3-54a）：影響格的表面整片往風向平移 ``distance`` 格（見 trpg.engine.wind）。"""
    assert spec.distance is not None
    tiles = cast.tiles(effect.affects, spec.condition)
    blow = blow_effect(cast.area, cast.caster.xy, tiles, spec.distance, cast.caster.id)
    return [] if blow is None else [blow]


def clear_surface(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """清除表面（Phase 3-54c）：省略 ``surface`` 時清 ``core.clear_surfaces``（煙霧與毒）。"""
    surfaces = cast.ctx.rules.core.clear_surfaces if spec.surface is None else (spec.surface,)
    tiles = cast.tiles(effect.affects, spec.condition)
    if not tiles:
        return []
    return [ClearSurfaceEffect(source_id=cast.caster.id, tiles=tuple(tiles), surfaces=surfaces)]


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
    """符文只刻在影響的格子（``affects: tiles``，玩法 PM 2026-10-24）；其他對象不靜默失敗，
    發出 ``effect_fizzled``（``inscribe_needs_tiles``）。驗證器本來就會擋，這裡處理讀入的舊技能。"""
    if effect.affects != "tiles":
        cast.ctx.emit(
            EffectFizzled, effect_kind="inscribe", pos=None, reason="inscribe_needs_tiles"
        )
        return []
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
    "blow_surface": blow_surface,
    "clear_surface": clear_surface,
    "create_surface": create_surface,
    "destroy_object": destroy_object,
    "create_obstacle": create_obstacle,
    "inscribe": inscribe,
    "raise_terrain": raise_terrain,
    "lower_terrain": lower_terrain,
}
