"""吹送（Phase 3-54a ``blow_surface``，``docs/design/06-技能.md`` 6.33，#56）的效果處理器。

一次結算整片：

1. 拿起：``tiles`` 中表面在 ``core.wind.blow_surfaces`` 裡的格子，記下表面、剩餘回合、陣營與
   建立者，原格的表面移除（原因 ``blow``）。
2. 落點：每片沿自己的風向一格一格前進最多 ``distance`` 格，下一格「擋風」（:func:`wind_blocked`：
   地圖外、表面不能存在的牆壁與致命地形、``blocks_move`` 物件、比目前高）就停在目前的格子；
   單位不阻擋。
3. 放下：依風向由前往後（同一位置依 ``(y, x)``）放下，落點先查互動表（同產生表面），帶元素的表面
   落在物件上照常觸及；剩餘回合、陣營、建立者保留（永久的表面仍是永久）。多片落在同一格時後放的
   與先放的照互動表結算。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.engine.context import Ctx
from trpg.engine.effects.models import BlowSurfaceEffect, EffectBase
from trpg.engine.effects.queue import register_effect
from trpg.engine.effects.world import place_surface, set_surface, surface_allowed
from trpg.engine.events import EventBase, SurfaceBlown
from trpg.engine.state import BattleState
from trpg.shared.types import Pos, Surface, Team, UnitId

__all__ = ["wind_blocked"]

type XY = tuple[int, int]

BLOW_CAUSE = "blow"


def wind_blocked(state: BattleState, cur: XY, nxt: XY) -> bool:
    """被風吹動的表面（吹送、元素擴散）能不能從 ``cur`` 前進到 ``nxt``：地圖外、表面不能存在的格子
    （牆壁、致命地形）、``blocks_move`` 物件、比 ``cur`` 高的格子擋風。"""
    if not state.in_bounds(*nxt) or not surface_allowed(state, nxt):
        return True
    if state.object_has_tag(*nxt, "blocks_move"):
        return True
    return state.tile(*nxt).height > state.tile(*cur).height


@dataclass(frozen=True, slots=True)
class _Piece:
    origin: XY
    dest: XY
    direction: XY
    surface: Surface
    remaining: int | None
    team: Team | None
    creator: UnitId | None


def _destination(state: BattleState, start: XY, direction: XY, distance: int) -> XY:
    cur = start
    for _ in range(distance):
        nxt = (cur[0] + direction[0], cur[1] + direction[1])
        if wind_blocked(state, cur, nxt):
            break
        cur = nxt
    return cur


def _front_first(piece: _Piece) -> tuple[int, int, int]:
    """原本在風向最前面的先放（原格沿風向的投影由大到小），同一投影依原格的 ``(y, x)``。"""
    (x, y), (dx, dy) = piece.origin, piece.direction
    return (-(x * dx + y * dy), y, x)


@register_effect("blow_surface")
def _blow_surface(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, BlowSurfaceEffect)
    state = ctx.state
    blowable = set(ctx.core.wind.blow_surfaces)
    pieces: list[_Piece] = []
    for xy, direction in sorted(
        zip(effect.tiles, effect.directions, strict=True), key=lambda p: (p[0][1], p[0][0])
    ):
        if not state.in_bounds(*xy):
            continue
        tile = state.tile(*xy)
        if tile.surface not in blowable:
            continue
        pieces.append(
            _Piece(
                origin=xy,
                dest=_destination(state, xy, direction, effect.distance),
                direction=direction,
                surface=tile.surface,
                remaining=tile.surface_remaining,
                team=tile.surface_team,
                creator=tile.surface_creator,
            )
        )
    events: list[EventBase] = []
    for piece in pieces:  # 先全部拿起，落點才不會被還沒移動的表面影響
        events += set_surface(ctx, piece.origin, Surface.NONE, cause=BLOW_CAUSE, depth=effect.depth)
    for piece in sorted(pieces, key=_front_first):
        events.append(
            ctx.emit(
                SurfaceBlown,
                source_id=effect.source_id,
                from_pos=Pos(x=piece.origin[0], y=piece.origin[1]),
                to_pos=Pos(x=piece.dest[0], y=piece.dest[1]),
                surface=piece.surface,
                direction=piece.direction,
            )
        )
        events += place_surface(
            ctx,
            piece.dest,
            piece.surface,
            cause=BLOW_CAUSE,
            duration=piece.remaining,
            team=piece.team,
            creator=piece.creator,
            depth=effect.depth,
            permanent=True,
        )
    return events
