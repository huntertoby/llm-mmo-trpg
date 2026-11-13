"""持續區域的查詢與進入／回合開始的觸發結算（Phase R3 自 :mod:`trpg.engine.zones` 抽出）。

這裡的函式只讀區域、或經 :func:`~trpg.engine.skills.casting.use_zone_effects` 結算區域效果，
不直接使用效果佇列；效果佇列（:mod:`trpg.engine.effects.queue`）清空時呼叫
:func:`flush_zone_entries`，所以可以在模組頂端匯入本模組。建立、移動、擴張區域（要留下表面，
會結算效果）留在 :mod:`trpg.engine.zones`，該模組也照舊轉出本模組的公開名稱。
"""

from __future__ import annotations

from trpg.content.skills import ZONE, EffectSpec
from trpg.engine.context import Ctx
from trpg.engine.events import ZoneTriggered
from trpg.engine.rules.footprint import touches
from trpg.engine.rules.geometry import XY
from trpg.engine.skill_triggers import check_trigger_depth
from trpg.engine.skills import shapes
from trpg.engine.skills.casting import use_zone_effects
from trpg.engine.state import BattleState, UnitState, ZoneState
from trpg.shared.types import Element, Team, UnitId

__all__ = [
    "affects_team",
    "caster_cells",
    "find_zone",
    "flush_zone_entries",
    "next_zone_cells",
    "sorted_cells",
    "step_cells",
    "zone_cells",
    "zone_elements",
    "zone_is_harmful",
    "zone_spec",
    "zone_when",
    "zones_at",
    "zones_turn_start",
]


def sorted_cells(cells: set[XY] | list[XY] | tuple[XY, ...]) -> tuple[XY, ...]:
    return tuple(sorted(set(cells), key=lambda p: (p[1], p[0])))


def zone_spec(state: BattleState, zone: ZoneState) -> EffectSpec:
    """區域技能唯一的 ``zone`` 效果。"""
    spec = state.ruleset.skill_def(zone.skill_id).effects[0]
    assert spec.type == ZONE
    return spec


def zone_is_harmful(state: BattleState, spec: EffectSpec) -> bool:
    """區域的效果含傷害或有害狀態（AI 避開、網頁顏色）。"""
    for sub in spec.effects or ():
        if sub.type == "damage":
            return True
        if (
            sub.type == "apply_status"
            and sub.status is not None
            and not state.ruleset.status_def(sub.status).beneficial
        ):
            return True
    return False


def zone_elements(state: BattleState, zone: ZoneState) -> frozenset[Element]:
    """區域帶的元素（元素擴散用，Phase 3-54a）：區域效果中傷害的元素，加上區域留下的表面的元素。"""
    spec = zone_spec(state, zone)
    found = {sub.element for sub in spec.effects or () if sub.type == "damage" and sub.element}
    if spec.surface is not None:
        element = state.ruleset.surface_def(spec.surface).element
        if element is not None:
            found.add(element)
    return frozenset(found)


def caster_cells(state: BattleState, zone: ZoneState, center: XY) -> tuple[XY, ...]:
    if zone.shape == "self":
        return (center,) if shapes.in_play(state, center) else ()
    radius = zone.radius or 1
    if zone.shape == "ring":
        return shapes.ring_tiles(state, center, radius)
    return shapes.radius_tiles(state, center, radius)


def zone_cells(state: BattleState, zone: ZoneState) -> tuple[XY, ...]:
    """區域目前的格子（依 ``(y, x)`` 排序）。跟隨型以施放者目前的位置展開；施放者不在場時為空。"""
    if zone.anchor != "caster":
        return tuple((p.x, p.y) for p in zone.cells)
    owner = state.units.get(zone.owner_id)
    if owner is None or not owner.alive:
        return ()
    return caster_cells(state, zone, owner.xy)


def step_cells(state: BattleState, cells: tuple[XY, ...], direction: str) -> tuple[XY, ...]:
    dx, dy = shapes.DIRECTIONS[direction]
    moved = [(x + dx, y + dy) for x, y in cells]
    return sorted_cells([c for c in moved if shapes.in_play(state, c)])


def next_zone_cells(state: BattleState, zone: ZoneState) -> tuple[XY, ...] | None:
    """移動型區域在下一次環境回合之後的格子（只看幾何，不結算；給視圖與預告用）。不會移動的區域、
    或下一次環境回合之前就會到期的區域為 ``None``。"""
    if zone.anchor != "moving" or zone.direction is None:
        return None
    if zone.expires_round <= state.round:
        return None
    cells = zone_cells(state, zone)
    for _ in range(zone.speed):
        cells = step_cells(state, cells, zone.direction)
    return cells


def affects_team(state: BattleState, zone: ZoneState, team: Team) -> bool:
    """區域的 ``affects`` 是否包含 ``team`` 的單位。"""
    affects = zone_spec(state, zone).affects
    if affects == "all":
        return True
    same = team is zone.team
    return same if affects == "allies" else not same


def zones_at(state: BattleState, xy: XY) -> list[ZoneState]:
    """涵蓋 ``xy`` 的區域（依 ``id``）。"""
    return [z for z in state.zones if xy in zone_cells(state, z)]


def zone_when(state: BattleState, zone: ZoneState) -> str:
    when = zone_spec(state, zone).when
    assert when is not None
    return when


# ---------------------------------------------------------------------------
# 建立與消失
# ---------------------------------------------------------------------------


def find_zone(state: BattleState, zone_id: int) -> ZoneState | None:
    return next((z for z in state.zones if z.id == zone_id), None)


def flush_zone_entries(ctx: Ctx) -> None:
    """結算記下的區域進入（依記錄順序，同一區域與單位只結算一次）：單位仍存活、區域仍在、單位仍在
    區域內才結算。"""
    entries = ctx.zone_entries
    ctx.zone_entries = []
    seen: set[tuple[int, UnitId]] = set()
    for zone_id, unit_id in entries:
        if (zone_id, unit_id) in seen:
            continue
        seen.add((zone_id, unit_id))
        zone = find_zone(ctx.state, zone_id)
        unit = ctx.state.units.get(unit_id)
        if zone is None or unit is None or not unit.alive:
            continue
        if touches(unit, zone_cells(ctx.state, zone)):
            _trigger(ctx, zone, unit, "enter")


def zones_turn_start(ctx: Ctx, unit: UnitState) -> None:
    """``unit`` 的回合開始：涵蓋他所在格、``when`` 含回合開始、``affects`` 包含他的區域依 ``id``
    結算。"""
    for zone in list(ctx.state.zones):
        if not unit.alive:
            return
        if find_zone(ctx.state, zone.id) is None or zone_when(ctx.state, zone) == "enter":
            continue
        if touches(unit, zone_cells(ctx.state, zone)) and affects_team(ctx.state, zone, unit.team):
            _trigger(ctx, zone, unit, "turn_start")


def _trigger(ctx: Ctx, zone: ZoneState, unit: UnitState, cause: str) -> None:
    """區域對 ``unit`` 結算效果：深度檢查（超過 ``max_trigger_depth`` 時不結算）、事件、效果。"""
    depth = ctx.trigger_depth + 1
    if not check_trigger_depth(ctx, zone.owner_id, zone.skill_id, depth):
        return
    ctx.emit(
        ZoneTriggered,
        zone_id=zone.id,
        owner_id=zone.owner_id,
        skill_id=zone.skill_id,
        unit_id=unit.id,
        cause=cause,
        trigger_depth=depth,
    )
    use_zone_effects(ctx, zone, unit, depth=depth)
