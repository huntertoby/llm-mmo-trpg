"""持續區域（Phase 3D-5，``docs/design/06-技能.md`` 6.16 G、``docs/phases/Phase3D計畫.md`` 5）。

- **建立**：原語 ``zone``（技能唯一的效果）在技能形狀的格子上建立區域（:func:`create_zone`），
  快照施放者的有效屬性；同一施放者超過 ``zone_limit_per_owner`` 時最舊的消失。
- **錨點**：``tile`` 固定在施放時的格子；``caster`` 跟隨施放者（每次施放者移動就以新位置重新展開
  形狀，:func:`zone_cells`）；``moving`` 每次環境回合沿施放方向前進 ``speed`` 格（一次一格，
  :func:`move_zones`），走到牆壁或地圖外的格子消失，全部消失時區域消失（``blocked``）。
- **結算**：單位 **進入** 區域時（``when: enter``／``both``）或 **回合開始時** 站在區域內時
  （``turn_start``／``both``），依 ``affects`` 判斷敵我，對他結算 ``effects``（自動命中，狀態照常
  擲抵抗；:func:`~trpg.engine.skills.casting.use_zone_effects`），觸發深度 +1，所以命中後的
  被動（``on_damaged`` 等）照常觸發。「進入」＝單位的位置從區域外變成區域內：單位移動（走路、
  推擊、傳送、交換都算）、區域建立、移動型區域前進、跟隨型區域隨施放者移動都會造成；在區域內移動、
  站著不動都不算，所以同一次進入只結算一次。進入在效果佇列清空時（表面與陷阱之後）結算。
  區域不是表面：進入區域不會觸發 ``on_enter_surface``。
- **表面**：有 ``surface`` 時，區域新覆蓋的格子留下該表面（建立者為施放者）。
- **消失**：施放者在 ``expires_round``（施放輪 ＋ ``duration``）那一輪（或之後）的回合結束時
  （:func:`expire_zones_at_turn_end`）；施放者不在場時在那一輪的環境回合（:func:`move_zones`）；
  跟隨型在施放者倒下、撤離或消失時（:func:`remove_caster_zones_of`）。
- 區域對雙方都看得見（不像陷阱）；狀態放在 :attr:`BattleState.zones`，可序列化、可重播。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.content.skills import EffectSpec, SkillDef
from trpg.engine.context import Ctx
from trpg.engine.effects.models import CreateSurfaceEffect
from trpg.engine.effects.queue import execute
from trpg.engine.events import (
    EventBase,
    ZoneCreated,
    ZoneExpanded,
    ZoneExpired,
    ZoneExpiryReason,
    ZoneMoved,
)
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skills import shapes
from trpg.engine.state import UnitState, ZoneState
from trpg.engine.zone_triggers import (
    affects_team,
    caster_cells,
    find_zone,
    flush_zone_entries,
    next_zone_cells,
    sorted_cells,
    step_cells,
    zone_cells,
    zone_elements,
    zone_is_harmful,
    zone_spec,
    zone_when,
    zones_at,
    zones_turn_start,
)
from trpg.shared.types import Attribute, Pos, UnitId

__all__ = [
    "affects_team",
    "create_zone",
    "expand_zone",
    "expire_zones_at_turn_end",
    "flush_zone_entries",
    "move_zones",
    "next_zone_cells",
    "note_unit_moved",
    "remove_caster_zones_of",
    "zone_cells",
    "zone_elements",
    "zone_is_harmful",
    "zone_spec",
    "zones_at",
    "zones_turn_start",
]


def create_zone(  # noqa: PLR0917
    ctx: Ctx,
    caster: UnitState,
    skill: SkillDef,
    spec: EffectSpec,
    tiles: tuple[XY, ...],
    direction: XY | None,
) -> None:
    """``caster`` 以 ``skill`` 的 ``zone`` 效果在 ``tiles``（技能的影響範圍）建立區域；``direction``
    是方向型形狀的前進向量（移動型區域用）。"""
    state = ctx.state
    owned = [z for z in state.zones if z.owner_id == caster.id]
    while len(owned) >= ctx.core.zone_limit_per_owner:
        _remove(ctx, owned.pop(0), "limit")
    assert spec.anchor is not None and spec.duration is not None and spec.when is not None
    name = None
    if direction is not None:
        name = next(k for k, v in shapes.DIRECTIONS.items() if v == direction)
    caster_anchor = spec.anchor == "caster"
    zone = ZoneState(
        id=state.next_zone_id,
        owner_id=caster.id,
        team=caster.team,
        skill_id=skill.id,
        anchor=spec.anchor,
        cells=() if caster_anchor else tuple(Pos(x=x, y=y) for x, y in sorted_cells(tiles)),
        expires_round=state.round
        + spec.duration
        + attribute_perk(ctx.rules, caster, "surface_duration"),  # 智力（3H-1）
        attributes=tuple(
            (attr, effective_attribute(ctx.rules, caster, attr)) for attr in Attribute
        ),
        direction=name if spec.anchor == "moving" else None,
        speed=spec.speed or 0,
        shape=skill.shape.type,
        radius=skill.shape.radius,
    )
    state.next_zone_id += 1
    state.zones = [*state.zones, zone]
    cells = zone_cells(state, zone)
    assert spec.affects in ("enemies", "allies", "all")
    ctx.emit(
        ZoneCreated,
        zone_id=zone.id,
        owner_id=caster.id,
        skill_id=skill.id,
        anchor=zone.anchor,
        when=spec.when,
        affects=spec.affects,
        cells=tuple(Pos(x=x, y=y) for x, y in cells),
        expires_round=zone.expires_round,
        direction=zone.direction,
        speed=zone.speed,
        surface=spec.surface,
    )
    _covered(ctx, zone, cells, ())


def _covered(
    ctx: Ctx,
    zone: ZoneState,
    new: tuple[XY, ...],
    old: tuple[XY, ...],
    *,
    exclude: UnitId | None = None,
) -> None:
    """區域覆蓋了新的格子 ``new``（之前是 ``old``）：留下表面、記下新進入區域的單位（``exclude``
    除外：跟隨型區域的施放者相對於區域不動，不算進入），然後結算。"""
    state = ctx.state
    before = set(old)
    fresh = [xy for xy in new if xy not in before]
    if not fresh:
        return
    spec = zone_spec(state, zone)
    if zone_when(state, zone) != "turn_start":
        for xy in fresh:
            unit = state.unit_at(*xy)
            if unit is not None and unit.id != exclude and affects_team(state, zone, unit.team):
                ctx.zone_entries.append((zone.id, unit.id))
    surfaces = []
    if spec.surface is not None:
        surfaces = [
            CreateSurfaceEffect(
                pos=(x, y),
                surface=spec.surface,
                team=zone.team,
                source_id=zone.owner_id,
                cause="zone",
            )
            for x, y in fresh
        ]
    execute(ctx, surfaces)


def _remove(ctx: Ctx, zone: ZoneState, reason: ZoneExpiryReason) -> EventBase:
    cells = zone_cells(ctx.state, zone)
    ctx.state.zones = [z for z in ctx.state.zones if z.id != zone.id]
    return ctx.emit(
        ZoneExpired,
        zone_id=zone.id,
        owner_id=zone.owner_id,
        skill_id=zone.skill_id,
        reason=reason,
        cells=tuple(Pos(x=x, y=y) for x, y in cells),
    )


def expire_zones_at_turn_end(ctx: Ctx, owner: UnitState) -> None:
    """``owner`` 的回合結束：他的到期（``expires_round`` ≤ 目前輪數）區域消失。"""
    for zone in [z for z in ctx.state.zones if z.owner_id == owner.id]:
        if zone.expires_round <= ctx.state.round:
            _remove(ctx, zone, "timeout")


def remove_caster_zones_of(ctx: Ctx, owner_id: UnitId) -> list[EventBase]:
    """施放者離場（倒下、撤離、召喚物消失）：他的跟隨型區域消失；其他區域保留到期。"""
    return [
        _remove(ctx, zone, "owner_gone")
        for zone in list(ctx.state.zones)
        if zone.owner_id == owner_id and zone.anchor == "caster"
    ]


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------


def move_zones(ctx: Ctx) -> None:
    """環境回合（火勢蔓延之後）：到期而施放者不在場的區域消失，移動型區域依 ``id`` 前進 ``speed``
    格（一次一格；每一格都結算新進入的單位與表面）。"""
    state = ctx.state
    for zone in list(state.zones):
        if zone.expires_round <= state.round:
            _remove(ctx, zone, "timeout")
    for moving in [z for z in state.zones if z.anchor == "moving"]:
        for _ in range(moving.speed):
            current = find_zone(state, moving.id)
            if current is None or current.direction is None:
                break
            _advance(ctx, current, current.direction)


def _advance(ctx: Ctx, zone: ZoneState, direction: str) -> None:
    state = ctx.state
    old = zone_cells(state, zone)
    new = step_cells(state, old, direction)
    if not new:
        _remove(ctx, zone, "blocked")
        return
    moved = replace(zone, cells=tuple(Pos(x=x, y=y) for x, y in new))
    state.zones = [moved if z.id == zone.id else z for z in state.zones]
    ctx.emit(
        ZoneMoved,
        zone_id=zone.id,
        owner_id=zone.owner_id,
        skill_id=zone.skill_id,
        direction=direction,
        cells=moved.cells,
    )
    _covered(ctx, moved, new, old)


def expand_zone(ctx: Ctx, zone_id: int, added: tuple[XY, ...], source_id: UnitId | None) -> None:
    """元素擴散（Phase 3-54a，06 6.33）：固定或移動型區域多出 ``added`` 這些格子（已在區域裡、地圖外
    與牆壁的格子略過）；新覆蓋的格子照常留下表面、上面的單位算進入。跟隨型區域的格子由施放者位置
    決定，不擴大。"""
    state = ctx.state
    zone = find_zone(state, zone_id)
    if zone is None or zone.anchor == "caster":
        return
    old = zone_cells(state, zone)
    fresh = [xy for xy in sorted_cells(added) if xy not in old and shapes.in_play(state, xy)]
    if not fresh:
        return
    new = sorted_cells([*old, *fresh])
    grown = replace(zone, cells=tuple(Pos(x=x, y=y) for x, y in new))
    state.zones = [grown if z.id == zone.id else z for z in state.zones]
    ctx.emit(
        ZoneExpanded,
        zone_id=zone.id,
        owner_id=zone.owner_id,
        skill_id=zone.skill_id,
        source_id=source_id,
        added=tuple(Pos(x=x, y=y) for x, y in fresh),
        cells=grown.cells,
    )
    _covered(ctx, grown, new, old)


def note_unit_moved(ctx: Ctx, unit: UnitState, before: XY, after: XY) -> None:
    """單位從 ``before`` 移到 ``after``（:func:`~trpg.engine.effects.handlers.arrive`）：進入了別的
    區域就記下；他自己的跟隨型區域跟著移動（新覆蓋的格子留下表面、上面的單位算進入）。"""
    state = ctx.state
    if not state.zones or before == after:
        return
    for zone in list(state.zones):
        if zone.anchor == "caster" and zone.owner_id == unit.id:
            old = caster_cells(state, zone, before)
            _covered(ctx, zone, zone_cells(state, zone), old, exclude=unit.id)
            continue
        cells = zone_cells(state, zone)
        if (
            after in cells
            and before not in cells
            and zone_when(state, zone) != "turn_start"
            and affects_team(state, zone, unit.team)
        ):
            ctx.zone_entries.append((zone.id, unit.id))


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------
