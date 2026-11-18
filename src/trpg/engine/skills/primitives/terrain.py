"""地形原語：建立表面、吹送表面、清除表面、吸收表面、破壞物件、建立障礙物、刻印、抬高與降低地形。

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
    HealEffect,
    InscribeEffect,
    LowerTerrainEffect,
    RaiseTerrainEffect,
    ShieldEffect,
)
from trpg.engine.events import EffectFizzled, SurfaceAbsorbed
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.stacks import add_stacks
from trpg.engine.wind import blow_effect
from trpg.shared.types import Element, Pos, Surface

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
                magnitude_permille=spec.magnitude_permille or 1000,  # 強度（BAL-12e）
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


def _absorb_tile(cast: Cast, effect: ResolvedEffect) -> XY:
    """吸收表面的那一格：``affects: self`` 是施放者腳下，其他是形狀選中的那一格（``self``、
    ``single``、``ground_tile`` 都只有一格；範圍外或沒有格子時退回施放者腳下）。"""
    if effect.affects == "self" or not cast.area.tiles:
        return cast.caster.xy
    return cast.area.tiles[0]


def _absorbable(cast: Cast, spec: EffectSpec, surface: Surface) -> Element | bool | None:
    """``surface`` 能不能吸：不能時 ``False``；能時回表面的元素（沒有元素為 ``None``）。"""
    if surface is Surface.NONE or (spec.surface is not None and surface is not spec.surface):
        return False
    element = cast.ctx.rules.surface_def(surface).element
    if spec.gain == "element" and element is None:
        return False  # 水、油、煙霧沒有元素，不能換成元素（SK-2 待 PM 決定：水 → 潮濕）
    return element


def absorb_surface(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """吸收表面（SK-2，06 6.38 第 4 點）：移除一格的表面，換成 ``gain`` 的收益（只給施放者）。
    沒有可吸的表面時落空（``effect_fizzled`` ``no_surface``），技能的其他效果照常。"""
    assert spec.gain is not None
    ctx, caster = cast.ctx, cast.caster
    xy = _absorb_tile(cast, effect)
    surface = ctx.state.tile(*xy).surface
    found = _absorbable(cast, spec, surface)
    pos = Pos(x=xy[0], y=xy[1])
    if found is False:
        ctx.emit(EffectFizzled, effect_kind="absorb_surface", pos=pos, reason="no_surface")
        return []
    element = found if spec.gain == "element" and isinstance(found, Element) else None
    ctx.emit(
        SurfaceAbsorbed,
        unit_id=caster.id,
        skill_id=cast.skill.id,
        pos=pos,
        surface=surface,
        gain=spec.gain,
        element=element,
    )
    batch: list[EffectBase] = [
        ClearSurfaceEffect(source_id=caster.id, tiles=(xy,), surfaces=(surface,), cause="absorb")
    ]
    if element is not None:
        cast.absorbed_element = element  # 這一招之後的傷害改成表面的元素
    elif spec.gain == "stack":
        assert spec.stack is not None and spec.amount is not None
        add_stacks(ctx, caster, spec.stack, spec.amount, source_id=caster.id)
    elif spec.gain == "heal":
        batch.append(
            HealEffect(
                target_id=caster.id,
                source_id=caster.id,
                dice=spec.dice,
                scaled_permille=cast.spell_scaled(),
                multiplier_permille=cast.heal_multiplier(self_heal=True, spec=spec),
            )
        )
    else:
        batch.append(
            ShieldEffect(
                target_id=caster.id,
                source_id=caster.id,
                dice=spec.dice,
                scaled_permille=cast.spell_scaled(),
                multiplier_permille=cast.shield_multiplier(),
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
    "absorb_surface": absorb_surface,
    "blow_surface": blow_surface,
    "clear_surface": clear_surface,
    "create_surface": create_surface,
    "destroy_object": destroy_object,
    "create_obstacle": create_obstacle,
    "inscribe": inscribe,
    "raise_terrain": raise_terrain,
    "lower_terrain": lower_terrain,
}
