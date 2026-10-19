"""環境回合、環境預告、天氣與地圖事件（``docs/專案計畫.md`` 5.7）。

每輪全員行動完後執行一次環境回合（:func:`run_environment`），依序：

1. **著火的物件**：剩餘回合 −1，歸零時摧毀（木橋斷裂時格上單位墜落）。
2. **表面持續回合 −1**：歸零時變成 ``expires_to``（例如冰融化成水）。
3. **火勢蔓延**：環境回合開始時的每一格火焰，蔓延到四方向相鄰、可燃（``flammable`` 表面或
   未著火的 ``flammable`` 物件）的格子（以火焰觸及該格，依互動表點燃或引爆）。
3a. **持續區域**（Phase 3D-5）：施放者不在場而到期的區域消失；移動型區域前進
   （:func:`trpg.engine.zones.move_zones`）。
4. **天氣**：下雨時隨機產生水窪。
5. **地圖事件**：本輪結束時的 ``spawn_units``／``terrain_change``。

環境回合的亂數來自 :func:`environment_rng`（由種子與輪數衍生，與玩家動作消耗的亂數無關），
因此 :func:`telegraph` 在狀態複本上執行同一段邏輯即可得到與實際完全一致的預告。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.maps import MapEvent, SpawnUnitsEvent
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ChangeTileEffect,
    CreateSurfaceEffect,
    DestroyObjectEffect,
    EffectBase,
    ElementTouchEffect,
    SpawnUnitEffect,
)
from trpg.engine.effects.world import set_surface
from trpg.engine.events import (
    DamageDealt,
    EnvironmentEnded,
    EnvironmentStarted,
    Event,
    EventBase,
    MapEventTriggered,
    ObjectDestroyed,
    ObjectExploded,
    ObjectIgnited,
    SurfaceChanged,
    TerrainChanged,
    UnitDowned,
    UnitSpawned,
    ZoneExpired,
    ZoneMoved,
)
from trpg.engine.rule_changes import expire_orphan_summons
from trpg.engine.rules.geometry import XY, neighbors4
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.state import BattleState
from trpg.engine.zones import move_zones
from trpg.shared.rng import Rng
from trpg.shared.types import Element, ObjectId, Pos, Surface, UnitId

__all__ = [
    "Telegraph",
    "TelegraphChange",
    "environment_rng",
    "run_environment",
    "telegraph",
]


def environment_rng(state: BattleState) -> Rng:
    """第 ``state.round`` 輪環境回合的亂數（由種子與輪數衍生，不受玩家動作影響）。"""
    return Rng(state.seed).fork(f"environment:{state.round}")


def _all_tiles(state: BattleState) -> list[XY]:
    return [(x, y) for y in range(state.height) for x in range(state.width)]


def _flammable(state: BattleState, xy: XY) -> bool:
    tile = state.tile(*xy)
    if tile.surface is not Surface.NONE and state.ruleset.surface_def(tile.surface).flammable:
        return True
    obj = state.object_at(*xy)
    return (
        obj is not None
        and obj.burning is None
        and "flammable" in state.ruleset.object_def(obj.kind).tags
    )


def run_environment(ctx: Ctx) -> None:
    """執行一次環境回合（見模組說明）。在 ``RoundEnded`` 之後、下一輪開始之前呼叫。"""
    state = ctx.state
    saved = ctx.rng
    if ctx.preview is None:
        ctx.rng = environment_rng(state)
    try:
        ctx.emit(EnvironmentStarted)
        tiles = _all_tiles(state)
        fires = [xy for xy in tiles if state.tile(*xy).surface is Surface.FIRE]
        _burn_objects(ctx)
        _tick_surfaces(ctx, tiles)
        _spread_fire(ctx, fires)
        move_zones(ctx)  # 持續區域：到期與移動型的前進（Phase 3D-5）
        expire_orphan_summons(ctx)  # 召喚者不在場的分身到期（Phase 3D-6）
        _weather(ctx, tiles)
        _map_events(ctx)
        ctx.emit(EnvironmentEnded)
    finally:
        ctx.rng = saved


def _burn_objects(ctx: Ctx) -> None:
    destroy: list[EffectBase] = []
    for obj in ctx.state.objects_sorted():
        if obj.burning is None:
            continue
        obj.burning -= 1
        if obj.burning <= 0:
            destroy.append(
                DestroyObjectEffect(object_id=obj.id, cause="burned", source_id=obj.burn_source)
            )
    if destroy:
        execute(ctx, destroy)


def _tick_surfaces(ctx: Ctx, tiles: list[XY]) -> None:
    state = ctx.state
    for xy in tiles:
        tile = state.tile(*xy)
        if tile.surface is Surface.NONE or tile.surface_remaining is None:
            continue
        remaining = tile.surface_remaining - 1
        if remaining > 0:
            state.set_tile(*xy, replace(tile, surface_remaining=remaining))
            continue
        after = ctx.rules.surface_def(tile.surface).expires_to
        set_surface(ctx, xy, after, cause="expired")
    # 到期後變成的表面若有進入效果，站在上面的單位立即觸發（Phase 1C 決定 #6）
    execute(ctx, [])


def _spread_fire(ctx: Ctx, fires: list[XY]) -> None:
    state = ctx.state
    targets: set[XY] = set()
    for xy in fires:
        for nxt in neighbors4(state, xy):
            if state.tile(*nxt).surface is not Surface.FIRE and _flammable(state, nxt):
                targets.add(nxt)
    if targets:
        ordered = sorted(targets, key=lambda p: (p[1], p[0]))
        execute(ctx, [ElementTouchEffect(pos=xy, element=Element.FIRE) for xy in ordered])


def _weather(ctx: Ctx, tiles: list[XY]) -> None:
    state = ctx.state
    weather = state.weather
    if weather is None or weather.puddles_per_round <= 0:
        return
    candidates = [
        xy
        for xy in tiles
        if state.tile(*xy).surface is Surface.NONE
        and state.tile(*xy).object_id is None
        and is_standable(state, xy)
        and not is_deadly(state, xy)
    ]
    chosen: list[XY] = []
    for _ in range(weather.puddles_per_round):
        if not candidates:
            break
        chosen.append(candidates.pop(ctx.rng.randint(0, len(candidates) - 1)))
    if chosen:
        execute(
            ctx,
            [CreateSurfaceEffect(pos=xy, surface=Surface.WATER, cause="weather") for xy in chosen],
        )


def _map_events(ctx: Ctx) -> None:
    state = ctx.state
    for index, event in enumerate(state.map_events):
        if event.round != state.round:
            continue
        ctx.emit(MapEventTriggered, index=index, kind=event.kind)
        execute(ctx, _event_effects(event))


def _event_effects(event: MapEvent) -> list[EffectBase]:
    if isinstance(event, SpawnUnitsEvent):
        return [SpawnUnitEffect(pos=u.at, template_id=u.template, team=u.team) for u in event.units]
    return [
        ChangeTileEffect(pos=t.at, height=t.height, terrain=t.terrain, surface=t.surface)
        for t in event.tiles
    ]


# ---------------------------------------------------------------------------
# 預告
# ---------------------------------------------------------------------------

type ChangeKind = Literal[
    "surface",
    "terrain",
    "object_destroyed",
    "object_ignited",
    "object_exploded",
    "unit_spawned",
    "unit_damaged",
    "unit_downed",
    "zone_moved",
    "zone_expired",
]


class TelegraphChange(BaseModel):
    """預告的一項變化（由模擬事件整理而成，方便顯示在地圖上）。

    持續區域（Phase 3D-5）：``zone_moved`` 的 ``tiles`` 是區域前進後的格子、``before`` 是方向；
    ``zone_expired`` 的 ``tiles`` 是消失前的格子、``before`` 是消失原因；兩者的 ``after`` 都是區域
    技能 ID、``amount`` 是區域編號。一個區域在一次環境回合只列一項（``speed`` 2 時取最後的位置）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ChangeKind
    pos: Pos | None = None
    before: str | None = None
    after: str | None = None
    object_id: ObjectId | None = None
    unit_id: UnitId | None = None
    amount: int | None = None
    tiles: tuple[Pos, ...] = ()


class Telegraph(BaseModel):
    """下一次環境回合將發生的所有變化。

    - ``events``：在狀態複本上模擬環境回合得到的事件（與實際環境回合的事件除 ``seq`` 外相同，
      前提是環境回合之前狀態不再改變）。
    - ``changes``：由事件整理的變化清單。
    - ``burning``：目前著火的物件與「還能撐幾次環境回合」。
    - ``upcoming``：再下一輪結束時的地圖事件（提前一輪預告）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    round: int
    events: list[Event]
    changes: tuple[TelegraphChange, ...]
    burning: tuple[tuple[ObjectId, int], ...]
    upcoming: tuple[MapEvent, ...]


def _changes(events: list[EventBase]) -> list[TelegraphChange]:
    def convert(e: EventBase) -> TelegraphChange | None:  # noqa: PLR0911
        if isinstance(e, SurfaceChanged):
            return TelegraphChange(
                kind="surface", pos=e.pos, before=e.before.value, after=e.after.value
            )
        if isinstance(e, TerrainChanged):
            return TelegraphChange(
                kind="terrain",
                pos=e.pos,
                before=f"{e.terrain_before}:{e.height_before}",
                after=f"{e.terrain_after}:{e.height_after}",
            )
        if isinstance(e, ObjectDestroyed):
            return TelegraphChange(kind="object_destroyed", pos=e.pos, object_id=e.object_id)
        if isinstance(e, ObjectIgnited):
            return TelegraphChange(kind="object_ignited", pos=e.pos, object_id=e.object_id)
        if isinstance(e, ObjectExploded):
            return TelegraphChange(kind="object_exploded", pos=e.pos, object_id=e.object_id)
        if isinstance(e, UnitSpawned):
            return TelegraphChange(
                kind="unit_spawned", pos=e.pos, unit_id=e.unit_id, after=e.template_id
            )
        if isinstance(e, DamageDealt):
            return TelegraphChange(
                kind="unit_damaged",
                pos=e.pos,
                unit_id=e.target_id,
                amount=e.amount - e.absorbed,
            )
        if isinstance(e, UnitDowned):
            return TelegraphChange(kind="unit_downed", unit_id=e.unit_id)
        return _zone_change(e)

    changes = [c for e in events if (c := convert(e)) is not None]
    last_move = {c.amount: i for i, c in enumerate(changes) if c.kind == "zone_moved"}
    return [c for i, c in enumerate(changes) if c.kind != "zone_moved" or last_move[c.amount] == i]


def _zone_change(e: EventBase) -> TelegraphChange | None:
    """持續區域的預告（Phase 3D-5）：前進後的位置與消失。"""
    if isinstance(e, ZoneMoved):
        return TelegraphChange(
            kind="zone_moved",
            tiles=e.cells,
            before=e.direction,
            after=e.skill_id,
            amount=e.zone_id,
        )
    if isinstance(e, ZoneExpired):
        return TelegraphChange(
            kind="zone_expired",
            tiles=e.cells,
            before=e.reason,
            after=e.skill_id,
            amount=e.zone_id,
        )
    return None


def telegraph(state: BattleState) -> Telegraph:
    """預告下一次環境回合（本輪結束時）的變化：在狀態複本上執行 :func:`run_environment`。"""
    burning = tuple((o.id, o.burning) for o in state.objects_sorted() if o.burning is not None)
    upcoming = tuple(e for e in state.map_events if e.round == state.round + 1)
    if state.ended:
        return Telegraph(
            round=state.round, events=[], changes=(), burning=burning, upcoming=upcoming
        )
    ctx = Ctx(state.clone())
    run_environment(ctx)
    return Telegraph(
        round=state.round,
        events=ctx.events,  # type: ignore[arg-type]
        changes=tuple(_changes(ctx.events)),
        burning=burning,
        upcoming=upcoming,
    )
