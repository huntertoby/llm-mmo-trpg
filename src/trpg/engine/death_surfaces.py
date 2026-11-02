"""倒下時留下表面（Phase 5A-M1；``docs/design/18-雲嶺內容.md`` 18.2.2 碎晶傀儡、
``docs/design/19-灰燼荒原與賽季主線.md`` 熔岩獸「熔核爆裂」）。

身上帶有 ``on_death_surface`` 狀態（``statuses.yaml``，中性、不倒數；由單位範本的
``opening_statuses`` 開場掛上）的單位倒下（``unit_downed``）時，在倒下的格子與曼哈頓距離
``radius`` 以內的格子（依 ``(y, x)``）產生表面：``create_surface``，``cause`` 為
``death_surface``，照一般產生表面的規則（互動表、致命地形與牆壁上不產生）。同一個單位帶了多個
這種狀態時依狀態順序各留一次。做法同定時炸彈的「倒下時爆炸」（:mod:`trpg.engine.bombs`）。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.effects.models import CreateSurfaceEffect, EffectBase
from trpg.engine.events import EventBase, UnitDowned
from trpg.engine.skills.shapes import radius_tiles
from trpg.engine.triggers import register_trigger

__all__ = ["DEATH_SURFACE_CAUSE"]

DEATH_SURFACE_CAUSE = "death_surface"
"""``surface_created.cause``：倒下時留下的表面。"""


@register_trigger("unit_downed")
def _surface_on_downed(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, UnitDowned)
    unit = ctx.state.units[event.unit_id]
    effects: list[EffectBase] = []
    for status in unit.statuses:
        spec = ctx.rules.status_def(status.status_id).on_death_surface
        if spec is None:
            continue
        for xy in radius_tiles(ctx.state, unit.xy, spec.radius):
            effects.append(
                CreateSurfaceEffect(
                    depth=depth,
                    source_id=unit.id,
                    pos=xy,
                    surface=spec.surface,
                    duration=spec.duration,
                    cause=DEATH_SURFACE_CAUSE,
                )
            )
    return effects
