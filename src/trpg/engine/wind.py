"""風元素的專屬機制（Phase 3-54a，``docs/design/06-技能.md`` 6.33，玩法決定 #56）。

- **風向**（:func:`wind_direction`）：方向型形狀（直線、錐形……）為形狀的方向；中心格型為
  「施放者 → 中心格」的主要軸向；以施放者為中心（或單體）的形狀為「施放者 → 該格」的主要軸向
  （往外吹）。施放者自己所在的格子沒有風向。
- **吹送**（原語 ``blow_surface``，:func:`blow_effect`）：影響格的表面整片往風向平移，結算見
  :mod:`trpg.engine.effects.blow`。
- **元素擴散**（:func:`spread_wind`）：技能的 ``element: wind`` 傷害效果結算完後（與補上元素觸及
  同一時機），影響格中 ``core.wind.spread_surfaces`` 的表面、與涵蓋影響格且帶
  ``core.wind.spread_zone_elements`` 元素的固定／移動型區域，從每個被吹到的格子往風向擴大
  ``core.wind.spread_distance`` 格（遇到擋風的格子停下，見
  :func:`~trpg.engine.effects.blow.wind_blocked`）。擴散以結算當下的狀態為準一次算完，新長出的
  格子不會在同一次施放中再擴散。
- **風壓撞擊**：風元素技能（:func:`~trpg.content.skills.is_wind_skill`）的推擊撞擊傷害 ×
  ``core.wind.collision_permille``（在 :mod:`trpg.engine.skills.primitives.displacement`）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.blow import wind_blocked
from trpg.engine.effects.models import BlowSurfaceEffect, CreateSurfaceEffect, EffectBase
from trpg.engine.rules.geometry import XY, axis_direction
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState
from trpg.engine.zones import expand_zone, zone_cells, zone_elements
from trpg.shared.types import UnitId

__all__ = ["SPREAD_CAUSE", "blow_effect", "spread_wind", "wind_direction"]

SPREAD_CAUSE = "wind_spread"


def wind_direction(area: SkillArea, caster: XY, xy: XY) -> XY | None:
    """``xy`` 這一格的風向（見模組說明）；沒有風向時為 ``None``。"""
    if area.direction is not None:
        return area.direction
    if area.origin != caster:
        return axis_direction(area.origin[0] - caster[0], area.origin[1] - caster[1])
    return axis_direction(xy[0] - caster[0], xy[1] - caster[1])


def blow_effect(
    area: SkillArea, caster: XY, tiles: Sequence[XY], distance: int, source_id: UnitId
) -> BlowSurfaceEffect | None:
    """吹送 ``tiles``（有風向的格子）的效果；沒有任何格子有風向時為 ``None``。"""
    picked = [(xy, d) for xy in tiles if (d := wind_direction(area, caster, xy)) is not None]
    if not picked:
        return None
    return BlowSurfaceEffect(
        source_id=source_id,
        tiles=tuple(xy for xy, _ in picked),
        directions=tuple(d for _, d in picked),
        distance=distance,
    )


def _line(state: BattleState, start: XY, direction: XY, distance: int) -> list[XY]:
    cells: list[XY] = []
    cur = start
    for _ in range(distance):
        nxt = (cur[0] + direction[0], cur[1] + direction[1])
        if wind_blocked(state, cur, nxt):
            break
        cells.append(nxt)
        cur = nxt
    return cells


def _surface_spread(
    ctx: Ctx, area: SkillArea, caster: XY, tiles: Sequence[XY], distance: int
) -> list[EffectBase]:
    state, wind = ctx.state, ctx.core.wind
    batch: list[EffectBase] = []
    for xy in tiles:
        tile = state.tile(*xy)
        direction = wind_direction(area, caster, xy)
        if tile.surface not in wind.spread_surfaces or direction is None:
            continue
        batch.extend(
            CreateSurfaceEffect(
                source_id=tile.surface_creator,
                pos=cell,
                surface=tile.surface,
                duration=tile.surface_remaining,
                team=tile.surface_team,
                cause=SPREAD_CAUSE,
            )
            for cell in _line(state, xy, direction, distance)
        )
    return batch


def _zone_spread(
    ctx: Ctx, area: SkillArea, caster: XY, tiles: Sequence[XY], distance: int
) -> list[tuple[int, tuple[XY, ...]]]:
    state, wind = ctx.state, ctx.core.wind
    blown = set(tiles)
    plans: list[tuple[int, tuple[XY, ...]]] = []
    for zone in state.zones:
        if zone.anchor == "caster" or not zone_elements(state, zone) & set(
            wind.spread_zone_elements
        ):
            continue
        added: list[XY] = []
        for xy in zone_cells(state, zone):
            direction = wind_direction(area, caster, xy)
            if xy in blown and direction is not None:
                added += _line(state, xy, direction, distance)
        if added:
            plans.append((zone.id, tuple(added)))
    return plans


def spread_wind(
    ctx: Ctx,
    area: SkillArea,
    caster: XY,
    tiles: Sequence[XY],
    source_id: UnitId,
    *,
    distance: int | None = None,
) -> None:
    """元素擴散：風吹到 ``tiles``（技能的影響格）時，表面與區域往風向擴大 ``distance`` 格（技能的
    ``spread`` 參數 1 或 2；省略為 ``core.wind.spread_distance``；先表面、再依區域編號）。
    全部依結算當下的狀態先算好再執行，同一次施放不會連鎖擴散。"""
    reach = ctx.core.wind.spread_distance if distance is None else distance
    surfaces = _surface_spread(ctx, area, caster, tiles, reach)
    zones = _zone_spread(ctx, area, caster, tiles, reach)
    if surfaces:
        execute(ctx, surfaces)
    for zone_id, added in zones:
        expand_zone(ctx, zone_id, added, source_id)
