"""疾病擴散（SK-2，#166，06 6.31、6.38 第 5 點）。

``contagion`` 原語把目標身上現有的燃燒、流血、中毒（``core.contagion_statuses``）標成會擴散
（``StatusInstance.contagious``）。帶著會擴散狀態的單位倒下（``unit_downed``）時，這些狀態以剩餘回合
傳給 ``core.contagion_radius`` 格內（單位距離，量到最近佔格）的 1 個同陣營存活單位；候選依單位 ID
排序，只有 1 個時不取亂數，多個時用戰鬥亂數 ``choice`` 挑 1 個。每次倒下最多傳 1 次、**只傳一種**
（SK-2b，玩法交接 4.1.28 第 3 點）：剩餘回合最多的那種（永久算最多），一樣多時照
``core.contagion_statuses`` 的順序（燃燒 > 流血 > 中毒）。傳過去的狀態照樣會擴散（可以連鎖）。沒有
會擴散的狀態時直接返回、不取亂數（既有戰鬥逐字不變）。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.effects.models import ApplyStatusEffect, EffectBase
from trpg.engine.events import DiseaseSpread, EventBase, UnitDowned
from trpg.engine.rules.footprint import unit_dist
from trpg.engine.state import StatusInstance, UnitState
from trpg.engine.triggers import register_trigger

__all__ = ["contagious_statuses", "spread_pick"]


def contagious_statuses(ctx: Ctx, unit: UnitState) -> list[StatusInstance]:
    """``unit`` 身上會擴散的狀態（依狀態 ID 排序）。"""
    kinds = ctx.core.contagion_statuses
    return sorted(
        (s for s in unit.statuses if s.contagious and s.status_id in kinds),
        key=lambda s: s.status_id,
    )


def spread_pick(ctx: Ctx, spreading: list[StatusInstance]) -> StatusInstance:
    """一次倒下要傳的那一種：剩餘回合最多（永久最多），一樣多時照 ``core.contagion_statuses`` 的
    順序。"""
    order = ctx.core.contagion_statuses

    def key(s: StatusInstance) -> tuple[int, int, int]:
        permanent = 1 if s.remaining is None else 0
        return (-permanent, -(s.remaining or 0), order.index(s.status_id))

    return min(spreading, key=key)


@register_trigger("unit_downed")
def _spread_on_downed(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    assert isinstance(event, UnitDowned)
    fallen = ctx.state.units[event.unit_id]
    spreading = contagious_statuses(ctx, fallen)
    if not spreading:
        return []
    radius = ctx.core.contagion_radius
    candidates = sorted(
        (
            u
            for u in ctx.state.living_units()
            if u.team is fallen.team and u.id != fallen.id and unit_dist(u, fallen) <= radius
        ),
        key=lambda u: u.id,
    )
    if not candidates:
        return []
    target = candidates[0] if len(candidates) == 1 else ctx.rng.choice(candidates)
    picked = spread_pick(ctx, spreading)
    ctx.emit(DiseaseSpread, from_id=fallen.id, to_id=target.id, status_ids=(picked.status_id,))
    return [
        ApplyStatusEffect(
            depth=depth,
            target_id=target.id,
            status_id=picked.status_id,
            duration=picked.remaining,
            source_id=picked.source_id,
            magnitude_permille=picked.magnitude_permille,
            contagious=True,
        )
    ]
