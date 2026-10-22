"""改變地形高度（地形隆起／下陷、高台圖騰的升起與恢復共用）。"""

from __future__ import annotations

from dataclasses import replace

from trpg.content.maps import MAX_HEIGHT
from trpg.engine.context import Ctx
from trpg.engine.events import EventBase, TerrainChanged, UnitFell
from trpg.engine.rules.geometry import XY
from trpg.shared.types import Pos, UnitId

__all__ = ["change_height"]


def change_height(
    ctx: Ctx, xy: XY, new_height: int, source_id: UnitId | None = None
) -> list[EventBase]:
    """改變高度；站在上面的單位跟著移動（往下落差達門檻時墜落）。"""
    state = ctx.state
    tile = state.tile(*xy)
    new_height = max(0, min(MAX_HEIGHT, new_height))
    if new_height == tile.height:
        return []
    state.set_tile(*xy, replace(tile, height=new_height))
    events: list[EventBase] = [
        ctx.emit(
            TerrainChanged,
            pos=Pos(x=xy[0], y=xy[1]),
            height_before=tile.height,
            height_after=new_height,
            terrain_before=tile.terrain,
            terrain_after=tile.terrain,
        )
    ]
    drop = tile.height - new_height
    unit = state.unit_at(*xy)
    min_drop = ctx.core.fall_damage_min_drop
    if unit is not None and drop >= min_drop:
        events.append(
            ctx.emit(
                UnitFell,
                unit_id=unit.id,
                drop=drop,
                levels=drop - (min_drop - 1),
                source_id=source_id,
            )
        )
    return events
