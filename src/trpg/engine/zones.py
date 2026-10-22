"""持續區域（Phase 3D-5，``docs/design/06-技能.md`` 6.16 G、``docs/phases/Phase3D計畫.md`` 5）。

- **建立**：原語 ``zone``（技能唯一的效果）在技能形狀的格子上建立區域（:func:`create_zone`），
  快照施放者的有效屬性；同一施放者超過 ``zone_limit_per_owner`` 時最舊的消失。
- **錨點**：``tile`` 固定在施放時的格子；``caster`` 跟隨施放者（每次施放者移動就以新位置重新展開
  形狀，:func:`zone_cells`）；``moving`` 每次環境回合沿施放方向前進 ``speed`` 格（一次一格，
  :func:`move_zones`），走到牆壁或地圖外的格子消失，全部消失時區域消失（``blocked``）。
- **結算**：單位 **進入** 區域時（``when: enter``／``both``）或 **回合開始時** 站在區域內時
  （``turn_start``／``both``），依 ``affects`` 判斷敵我，對他結算 ``effects``（自動命中，狀態照常
  擲抵抗；:func:`~trpg.engine.skills.interpreter.use_zone_effects`），觸發深度 +1，所以命中後的
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

from trpg.content.skills import ZONE, EffectSpec, SkillDef
from trpg.engine.context import Ctx
from trpg.engine.effects.models import CreateSurfaceEffect
from trpg.engine.events import (
    EventBase,
    ZoneCreated,
    ZoneExpired,
    ZoneExpiryReason,
    ZoneMoved,
    ZoneTriggered,
)
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skill_triggers import check_trigger_depth
from trpg.engine.skills import shapes
from trpg.engine.skills.casting import use_zone_effects
from trpg.engine.state import BattleState, UnitState, ZoneState
from trpg.shared.types import Attribute, Pos, Team, UnitId

__all__ = [
    "affects_team",
    "create_zone",
    "expire_zones_at_turn_end",
    "flush_zone_entries",
    "move_zones",
    "next_zone_cells",
    "note_unit_moved",
    "remove_caster_zones_of",
    "zone_cells",
    "zone_is_harmful",
    "zone_spec",
    "zones_at",
    "zones_turn_start",
]


def _sorted(cells: set[XY] | list[XY] | tuple[XY, ...]) -> tuple[XY, ...]:
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


def _caster_cells(state: BattleState, zone: ZoneState, center: XY) -> tuple[XY, ...]:
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
    return _caster_cells(state, zone, owner.xy)


def _step(state: BattleState, cells: tuple[XY, ...], direction: str) -> tuple[XY, ...]:
    dx, dy = shapes.DIRECTIONS[direction]
    moved = [(x + dx, y + dy) for x, y in cells]
    return _sorted([c for c in moved if shapes.in_play(state, c)])


def next_zone_cells(state: BattleState, zone: ZoneState) -> tuple[XY, ...] | None:
    """移動型區域在下一次環境回合之後的格子（只看幾何，不結算；給視圖與預告用）。不會移動的區域、
    或下一次環境回合之前就會到期的區域為 ``None``。"""
    if zone.anchor != "moving" or zone.direction is None:
        return None
    if zone.expires_round <= state.round:
        return None
    cells = zone_cells(state, zone)
    for _ in range(zone.speed):
        cells = _step(state, cells, zone.direction)
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


def _when(state: BattleState, zone: ZoneState) -> str:
    when = zone_spec(state, zone).when
    assert when is not None
    return when


# ---------------------------------------------------------------------------
# 建立與消失
# ---------------------------------------------------------------------------


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
        cells=() if caster_anchor else tuple(Pos(x=x, y=y) for x, y in _sorted(tiles)),
        expires_round=state.round + spec.duration,
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
    # 延後匯入：效果佇列匯入本模組。
    from trpg.engine.effects import execute  # noqa: PLC0415

    state = ctx.state
    before = set(old)
    fresh = [xy for xy in new if xy not in before]
    if not fresh:
        return
    spec = zone_spec(state, zone)
    if _when(state, zone) != "turn_start":
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
            current = _find(state, moving.id)
            if current is None or current.direction is None:
                break
            _advance(ctx, current, current.direction)


def _find(state: BattleState, zone_id: int) -> ZoneState | None:
    return next((z for z in state.zones if z.id == zone_id), None)


def _advance(ctx: Ctx, zone: ZoneState, direction: str) -> None:
    state = ctx.state
    old = zone_cells(state, zone)
    new = _step(state, old, direction)
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


def note_unit_moved(ctx: Ctx, unit: UnitState, before: XY, after: XY) -> None:
    """單位從 ``before`` 移到 ``after``（:func:`~trpg.engine.effects.handlers.arrive`）：進入了別的
    區域就記下；他自己的跟隨型區域跟著移動（新覆蓋的格子留下表面、上面的單位算進入）。"""
    state = ctx.state
    if not state.zones or before == after:
        return
    for zone in list(state.zones):
        if zone.anchor == "caster" and zone.owner_id == unit.id:
            old = _caster_cells(state, zone, before)
            _covered(ctx, zone, zone_cells(state, zone), old, exclude=unit.id)
            continue
        cells = zone_cells(state, zone)
        if (
            after in cells
            and before not in cells
            and _when(state, zone) != "turn_start"
            and affects_team(state, zone, unit.team)
        ):
            ctx.zone_entries.append((zone.id, unit.id))


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------


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
        zone = _find(ctx.state, zone_id)
        unit = ctx.state.units.get(unit_id)
        if zone is None or unit is None or not unit.alive:
            continue
        if unit.xy in zone_cells(ctx.state, zone):
            _trigger(ctx, zone, unit, "enter")


def zones_turn_start(ctx: Ctx, unit: UnitState) -> None:
    """``unit`` 的回合開始：涵蓋他所在格、``when`` 含回合開始、``affects`` 包含他的區域依 ``id``
    結算。"""
    for zone in list(ctx.state.zones):
        if not unit.alive:
            return
        if _find(ctx.state, zone.id) is None or _when(ctx.state, zone) == "enter":
            continue
        if unit.xy in zone_cells(ctx.state, zone) and affects_team(ctx.state, zone, unit.team):
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
