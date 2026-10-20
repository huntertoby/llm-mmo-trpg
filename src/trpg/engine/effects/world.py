"""Phase 1B 的環境效果處理器：push、create_surface、damage_object、destroy_object、
raise_terrain、lower_terrain、create_obstacle、spawn_unit，以及互動表使用的
element_touch、explode、ignite_object、change_tile。

處理器只修改狀態並產生事件；後續的連鎖（爆炸波及、點燃、雷電擴散……）由
:mod:`trpg.engine.interactions` 的觸發函式依互動表產生。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from trpg.content.maps import MAX_HEIGHT
from trpg.content.rule_changes import PUSH_ANY_OBJECT
from trpg.engine.activations import moves_object
from trpg.engine.context import Ctx
from trpg.engine.effects.handlers import arrive, weather_permille
from trpg.engine.effects.models import (
    ChangeTileEffect,
    CreateObstacleEffect,
    CreateSurfaceEffect,
    DamageObjectEffect,
    DestroyObjectEffect,
    EffectBase,
    ElementTouchEffect,
    ExplodeEffect,
    HurlObjectEffect,
    IgniteObjectEffect,
    LowerTerrainEffect,
    PushEffect,
    RaiseTerrainEffect,
    SpawnUnitEffect,
)
from trpg.engine.effects.queue import register_effect
from trpg.engine.events import (
    Collided,
    CollisionObstacle,
    EffectFizzled,
    ElementTouched,
    EnteredDeadlyTerrain,
    EventBase,
    MoveBlocked,
    ObjectCreated,
    ObjectDamaged,
    ObjectDestroyCause,
    ObjectDestroyed,
    ObjectExploded,
    ObjectHurled,
    ObjectIgnited,
    ObjectMoved,
    ObjectToppled,
    PushResisted,
    RuleChangeTriggered,
    SurfaceChanged,
    TerrainChanged,
    UnitFell,
    UnitSpawned,
)
from trpg.engine.lifecycle import make_unit
from trpg.engine.rules.combat import PERMILLE
from trpg.engine.rules.facing import facing_toward_enemies
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.state import BattleState, ObjectState, UnitState
from trpg.shared.types import ObjectId, Pos, Surface, Team, UnitId

__all__ = [
    "ToppleLine",
    "change_height",
    "creation_result",
    "hurl_landing",
    "object_push_block",
    "push_distance",
    "remove_object",
    "set_surface",
    "topple_line",
    "unit_push_block",
]

STEADFAST = "steadfast"
TOPPLABLE = "topplable"

type HurlOutcome = Literal["exploded", "shattered", "placed", "lost"]

type XY = tuple[int, int]


def _pos(xy: XY) -> Pos:
    return Pos(x=xy[0], y=xy[1])


# ---------------------------------------------------------------------------
# 表面
# ---------------------------------------------------------------------------


def set_surface(
    ctx: Ctx,
    xy: XY,
    surface: Surface,
    *,
    cause: str,
    duration: int | None = None,
    team: Team | None = None,
    creator: UnitId | None = None,
    use_default_duration: bool = True,
    depth: int = 0,
) -> list[EventBase]:
    """把 ``xy`` 的表面設為 ``surface``（不查互動表）。

    持續回合：``duration`` 優先；否則 ``use_default_duration`` 時用表面定義的預設值（``None`` 為
    永久）。表面與持續時間都沒有改變時不產生事件。

    表面種類改變且新表面有進入效果時，若有單位站在這一格，記錄到 ``ctx.surface_entries``，
    由效果佇列在清空前觸發（``depth`` 為造成改變的效果深度）。
    """
    state = ctx.state
    tile = state.tile(*xy)
    if surface is Surface.NONE:
        remaining = None
        team = None
        creator = None
    elif duration is not None:
        remaining = duration
    else:
        remaining = ctx.rules.surface_def(surface).duration if use_default_duration else None
    if (
        tile.surface is surface
        and tile.surface_remaining == remaining
        and tile.surface_team == team
        and tile.surface_creator == creator
    ):
        return []
    before = tile.surface
    state.set_tile(
        *xy,
        replace(
            tile,
            surface=surface,
            surface_remaining=remaining,
            surface_team=team,
            surface_creator=creator,
        ),
    )
    if before is surface:
        return []  # 只刷新持續時間
    if surface is not Surface.NONE and ctx.rules.surface_def(surface).on_enter is not None:
        unit = state.unit_at(*xy)
        if unit is not None:
            # 表面出現在單位腳下：效果佇列清空前依單位 ID 觸發進入效果（Phase 1C 決定 #6）
            ctx.surface_entries.append((unit.id, xy, depth))
    return [
        ctx.emit(
            SurfaceChanged,
            pos=_pos(xy),
            before=before,
            after=surface,
            remaining=remaining,
            cause=cause,
        )
    ]


def creation_result(state: BattleState, xy: XY, surface: Surface) -> tuple[Surface | None, str]:
    """在 ``xy`` 產生 ``surface`` 的結果（查互動表的 ``surface_created`` 規則）。

    回傳 ``(最終表面, 原因)``；最終表面為 ``None`` 表示保持原狀（``keep``）。
    """
    current = state.tile(*xy).surface
    for rule in state.ruleset.interactions.rules:
        if rule.trigger != "surface_created" or rule.surface_created is not surface:
            continue
        if rule.target != "surface" or rule.surface is not current:
            continue
        outcome = rule.then[0]
        if outcome.op == "keep":
            return None, f"interaction:{rule.id}"
        if outcome.op == "set_surface":
            return outcome.surface, f"interaction:{rule.id}"
    return surface, "effect"


def _surface_allowed(state: BattleState, xy: XY) -> bool:
    """致命地形上（沒有木橋）與牆壁（不可進入、非致命的地形）上不能有表面。"""
    if is_deadly(state, xy):
        return False
    terrain = state.ruleset.terrain_def(state.tile(*xy).terrain)
    return terrain.walkable or terrain.deadly


@register_effect("create_surface")
def _create_surface(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, CreateSurfaceEffect)
    state = ctx.state
    xy = effect.pos
    if not state.in_bounds(*xy):
        return [_fizzle(ctx, effect.kind, xy, "out_of_bounds")]
    if not _surface_allowed(state, xy):
        reason = "deadly_terrain" if is_deadly(state, xy) else "solid_terrain"
        return [_fizzle(ctx, effect.kind, xy, reason)]
    final: Surface | None = effect.surface
    cause = effect.cause
    if effect.react:
        final, rule_cause = creation_result(state, xy, effect.surface)
        if rule_cause != "effect":
            cause = rule_cause
    if final is None:
        return []
    duration = effect.duration if final is effect.surface else None
    events = set_surface(
        ctx,
        xy,
        final,
        cause=cause,
        duration=duration,
        team=effect.team,
        creator=effect.source_id,
        depth=effect.depth,
    )
    element = ctx.rules.surface_def(final).element if final is not Surface.NONE else None
    if (
        effect.react
        and final is effect.surface
        and element is not None
        and state.tile(*xy).object_id is not None
    ):
        events.append(
            ctx.emit(
                ElementTouched,
                pos=_pos(xy),
                element=element,
                source_id=effect.source_id,
                direction=None,
                push_distance=0,
                damage=0,
                objects_only=True,
            )
        )
    return events


def _fizzle(ctx: Ctx, kind: str, xy: XY | None, reason: str) -> EventBase:
    pos = None if xy is None or xy[0] < 0 or xy[1] < 0 else _pos(xy)
    return ctx.emit(EffectFizzled, effect_kind=kind, pos=pos, reason=reason)


@register_effect("element_touch")
def _element_touch(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ElementTouchEffect)
    if not ctx.state.in_bounds(*effect.pos):
        return []
    return [
        ctx.emit(
            ElementTouched,
            pos=_pos(effect.pos),
            element=effect.element,
            source_id=effect.source_id,
            direction=effect.direction,
            push_distance=effect.push_distance,
            damage=effect.damage,
            objects_only=effect.objects_only,
            tile_only=effect.tile_only,
        )
    ]


# ---------------------------------------------------------------------------
# 物件
# ---------------------------------------------------------------------------


def _live_object(state: BattleState, object_id: ObjectId) -> ObjectState | None:
    obj = state.objects.get(object_id)
    return None if obj is None or obj.destroyed else obj


@register_effect("damage_object")
def _damage_object(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, DamageObjectEffect)
    obj = _live_object(ctx.state, effect.object_id)
    if obj is None or obj.hp is None:
        return []
    rolls: tuple[int, ...] = ()
    if effect.dice is not None:
        rolls = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(effect.dice.count))
    raw_permille = (sum(rolls) + effect.flat) * PERMILLE + effect.scaled_permille
    weather = weather_permille(ctx.state, effect.element)
    amount = max(
        raw_permille * weather * effect.multiplier_permille // (PERMILLE * PERMILLE * PERMILLE),
        effect.min_damage,
    )
    hp_before = obj.hp
    obj.hp = max(0, obj.hp - amount)
    return [
        ctx.emit(
            ObjectDamaged,
            object_id=obj.id,
            pos=obj.pos,
            source_id=effect.source_id,
            cause=effect.cause,
            element=effect.element,
            rolls=rolls,
            amount=amount,
            hp_before=hp_before,
            hp_after=obj.hp,
        )
    ]


def remove_object(
    ctx: Ctx,
    obj: ObjectState,
    cause: ObjectDestroyCause,
    set_terrain: str | None = None,
    source_id: UnitId | None = None,
) -> list[EventBase]:
    """摧毀物件；之後若該格變成致命地形，清除表面並讓格上的單位落入（來源為 ``source_id``）。"""
    state = ctx.state
    obj.destroyed = True
    xy = obj.xy
    tile = state.tile(*xy)
    events: list[EventBase] = []
    if set_terrain is not None and set_terrain != tile.terrain:
        state.set_tile(*xy, replace(tile, object_id=None, terrain=set_terrain))
        events.append(
            ctx.emit(
                TerrainChanged,
                pos=obj.pos,
                height_before=tile.height,
                height_after=tile.height,
                terrain_before=tile.terrain,
                terrain_after=set_terrain,
            )
        )
    else:
        state.set_tile(*xy, replace(tile, object_id=None))
    events.append(
        ctx.emit(ObjectDestroyed, object_id=obj.id, kind=obj.kind, pos=obj.pos, cause=cause)
    )
    if is_deadly(state, xy):
        events.extend(set_surface(ctx, xy, Surface.NONE, cause="fell"))
        unit = state.unit_at(*xy)
        if unit is not None:
            terrain = state.tile(*xy).terrain
            events.append(
                ctx.emit(
                    EnteredDeadlyTerrain,
                    unit_id=unit.id,
                    pos=unit.pos,
                    terrain=terrain,
                    source_id=source_id,
                )
            )
    return events


@register_effect("destroy_object")
def _destroy_object(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, DestroyObjectEffect)
    obj = _live_object(ctx.state, effect.object_id)
    if obj is None:
        return []
    return remove_object(ctx, obj, effect.cause, effect.set_terrain, effect.source_id)


@register_effect("explode")
def _explode(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ExplodeEffect)
    obj = _live_object(ctx.state, effect.object_id)
    if obj is None:
        return []
    explosion = ctx.rules.object_def(obj.kind).explosion
    if explosion is None:
        return []
    events: list[EventBase] = [
        ctx.emit(
            ObjectExploded,
            object_id=obj.id,
            pos=obj.pos,
            radius=explosion.radius,
            source_id=effect.source_id,
        )
    ]
    events.extend(remove_object(ctx, obj, "explosion", source_id=effect.source_id))
    return events


@register_effect("ignite_object")
def _ignite_object(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, IgniteObjectEffect)
    obj = _live_object(ctx.state, effect.object_id)
    if obj is None or obj.burning is not None:
        return []
    obj.burning = ctx.core.burning_object_rounds
    obj.burn_source = effect.source_id
    return [ctx.emit(ObjectIgnited, object_id=obj.id, pos=obj.pos, rounds=obj.burning)]


@register_effect("create_obstacle")
def _create_obstacle(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, CreateObstacleEffect)
    state = ctx.state
    xy = effect.pos
    if not state.in_bounds(*xy):
        return [_fizzle(ctx, effect.kind, xy, "out_of_bounds")]
    if state.tile(*xy).object_id is not None or state.unit_at(*xy) is not None:
        return [_fizzle(ctx, effect.kind, xy, "occupied")]
    if not is_standable(state, xy):
        return [_fizzle(ctx, effect.kind, xy, "not_standable")]
    return [_new_object(ctx, xy, effect.object_kind)]


def _new_object(ctx: Ctx, xy: XY, kind: str) -> EventBase:
    """在 ``xy`` 放一個新的 ``kind`` 物件（呼叫端已確認放得下），回傳 ``object_created``。"""
    state = ctx.state
    definition = ctx.rules.object_def(kind)
    oid = ObjectId(f"obj_{len(state.objects) + 1:04d}")
    state.objects[oid] = ObjectState(
        id=oid, kind=definition.id, pos=_pos(xy), hp=definition.max_hp, max_hp=definition.max_hp
    )
    state.set_tile(*xy, replace(state.tile(*xy), object_id=oid))
    return ctx.emit(ObjectCreated, object_id=oid, kind=definition.id, pos=_pos(xy))


# ---------------------------------------------------------------------------
# 推擊
# ---------------------------------------------------------------------------


@register_effect("push")
def _push(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, PushEffect)
    if effect.target_id is not None:
        return _push_unit(ctx, effect, effect.target_id)
    if effect.object_id is not None:
        return _push_object(ctx, effect, effect.object_id)
    return []


def _push_unit(ctx: Ctx, effect: PushEffect, unit_id: UnitId) -> list[EventBase]:
    state = ctx.state
    unit = state.units.get(unit_id)
    if unit is None or not unit.alive:
        return []
    events: list[EventBase] = []
    distance = push_distance(state, unit, effect.distance)
    if unit.has_tag(STEADFAST) and distance != effect.distance:
        events.append(
            ctx.emit(PushResisted, unit_id=unit.id, requested=effect.distance, distance=distance)
        )
    dx, dy = effect.direction
    for step in range(distance):
        nxt = (unit.pos.x + dx, unit.pos.y + dy)
        reason = unit_push_block(state, unit.xy, nxt, unit.id)
        if reason is not None:
            to_pos = Pos(x=max(nxt[0], 0), y=max(nxt[1], 0))
            events.append(
                ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=to_pos, reason=reason, forced=True)
            )
            events.append(_collide(ctx, effect, unit, nxt, reason, shortfall=distance - step))
            break
        moved = arrive(ctx, unit, nxt, "forced", source_id=effect.source_id)
        events.extend(moved)
        if not unit.alive or any(isinstance(e, EnteredDeadlyTerrain) for e in moved):
            return events  # 墜落、致命地形造成的停下不算撞擊（多推的部分也不算）
    if effect.extra_collisions > 0 and unit.alive:
        events.append(
            ctx.emit(
                Collided,
                unit_id=unit.id,
                obstacle="excess",
                shortfall=effect.extra_collisions,
                pos=unit.pos,
                source_id=effect.source_id,
                dice=effect.collision_dice,
            )
        )
    return events


_COLLISION_OBSTACLES: dict[str, CollisionObstacle] = {
    "out_of_bounds": "edge",
    "occupied": "unit",
    "too_high": "wall",
}


def _collide(
    ctx: Ctx, effect: PushEffect, unit: UnitState, blocked: XY, reason: str, *, shortfall: int
) -> EventBase:
    """推擊被障礙擋下：少走 ``shortfall`` 格的撞擊（傷害由 :mod:`trpg.engine.triggers` 結算）。"""
    state = ctx.state
    obstacle = _COLLISION_OBSTACLES.get(reason)
    other = state.unit_at(*blocked) if obstacle == "unit" else None
    object_id: ObjectId | None = None
    if obstacle is None:  # ``obstacle``：blocks_move 物件，否則是不可走的地形
        if state.object_has_tag(*blocked, "blocks_move"):
            obstacle, object_id = "object", state.tile(*blocked).object_id
        else:
            obstacle = "wall"
    return ctx.emit(
        Collided,
        unit_id=unit.id,
        obstacle=obstacle,
        shortfall=shortfall,
        pos=Pos(x=max(blocked[0], 0), y=max(blocked[1], 0)),
        source_id=effect.source_id,
        other_id=None if other is None else other.id,
        object_id=object_id,
        dice=effect.collision_dice,
    )


def push_distance(state: BattleState, unit: UnitState, requested: int) -> int:
    """單位實際被推的格數：帶 ``steadfast`` 標籤者 × ``steadfast_push_permille``（無條件捨去）。

    技能的推擊效果（Phase 2）遇到 0 格時只是不移動；基本動作 ``Shove`` 遇到 0 格時不合法。
    """
    if unit.has_tag(STEADFAST):
        return requested * state.ruleset.core.steadfast_push_permille // PERMILLE
    return requested


def unit_push_block(state: BattleState, cur: XY, nxt: XY, unit_id: UnitId) -> str | None:
    """單位從 ``cur`` 被推向 ``nxt`` 時的阻擋原因（``out_of_bounds``／``occupied``／
    ``obstacle``／``too_high``）；可以推過去時回傳 ``None``（致命地形不阻擋）。"""
    if not state.in_bounds(*nxt):
        return "out_of_bounds"
    other = state.unit_at(*nxt)
    if other is not None and other.id != unit_id:
        return "occupied"
    if state.object_has_tag(*nxt, "blocks_move"):
        return "obstacle"
    if not is_standable(state, nxt) and not is_deadly(state, nxt):
        return "obstacle"  # 牆壁等不可站立、非致命的地形
    if state.tile(*nxt).height > state.tile(*cur).height:
        return "too_high"
    return None


def _push_object(ctx: Ctx, effect: PushEffect, object_id: ObjectId) -> list[EventBase]:
    state = ctx.state
    obj = _live_object(state, object_id)
    if obj is None:
        return []
    tags = ctx.rules.object_def(obj.kind).tags
    if TOPPLABLE in tags:  # 推倒（Phase 3C-5a）：不移動，往推的方向倒下
        return _topple(ctx, obj, effect.direction, effect.source_id)
    events: list[EventBase] = []
    if "pushable" not in tags:
        change = moves_object(state, effect.source_id, tags)  # 規則改變「移山」（Phase 3D-6）
        if change is None:
            return []
        assert effect.source_id is not None
        events.append(
            ctx.emit(
                RuleChangeTriggered,
                unit_id=effect.source_id,
                skill_id=change.skill.id,
                rule=change.rule.id,
                kind=PUSH_ANY_OBJECT,
                object_id=obj.id,
            )
        )
    dx, dy = effect.direction
    for _ in range(effect.distance):
        cur = obj.xy
        nxt = (cur[0] + dx, cur[1] + dy)
        reason = object_push_block(state, cur, nxt)
        if reason is not None:
            events.append(_fizzle(ctx, "push", nxt, reason))
            break
        state.set_tile(*cur, replace(state.tile(*cur), object_id=None))
        obj.pos = _pos(nxt)
        state.set_tile(*nxt, replace(state.tile(*nxt), object_id=obj.id))
        events.append(
            ctx.emit(
                ObjectMoved, object_id=obj.id, from_pos=_pos(cur), to_pos=obj.pos, how=effect.how
            )
        )
        if is_deadly(state, nxt):
            events.extend(remove_object(ctx, obj, "fell", source_id=effect.source_id))
            break
    return events


def object_push_block(state: BattleState, cur: XY, nxt: XY) -> str | None:
    """物件從 ``cur`` 被推向 ``nxt`` 時的阻擋原因；可以推過去時回傳 ``None``。"""
    if not state.in_bounds(*nxt):
        return "out_of_bounds"
    if state.tile(*nxt).object_id is not None:
        return "obstacle"
    if state.unit_at(*nxt) is not None:
        return "occupied"
    if not is_standable(state, nxt) and not is_deadly(state, nxt):
        return "obstacle"  # 牆壁等不可站立、非致命的地形
    if state.tile(*nxt).height > state.tile(*cur).height:
        return "too_high"
    return None


# ---------------------------------------------------------------------------
# 推倒（Phase 3C-5a）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToppleLine:
    """``topplable`` 物件往某方向倒下時壓住的範圍（:func:`topple_line`）。

    - ``tiles``：壓住的格子（依序；地圖外與不可走的地形已跳過，被非破壞物件擋住時只到它之前）。
    - ``units``／``objects``：壓到的單位與 ``breakable`` 物件（依壓到的順序）。
    - ``rubble``：產生倒塌物的格子——原格與 ``tiles`` 中最後一個放得下的（沒有單位與其他物件、
      可站立）；都放不下時為 ``None``。
    """

    tiles: tuple[XY, ...]
    units: tuple[UnitId, ...]
    objects: tuple[ObjectId, ...]
    rubble: XY | None


def topple_line(state: BattleState, obj: ObjectState, direction: XY) -> ToppleLine:
    """物件 ``obj`` 往 ``direction`` 倒下時壓住的範圍（只讀狀態；預覽與介面也用這個）。

    從物件的下一格起最多 ``topple_length`` 格：地圖外、牆壁等不可走的地形與致命地形跳過；有
    ``breakable`` 物件的格子照壓（物件受傷）；不阻擋移動的非破壞物件（草叢）不影響；其他物件
    （阻擋移動又不能破壞，例如倒塌物）擋住倒下，停在它之前。
    """
    dx, dy = direction
    tiles: list[XY] = []
    units: list[UnitId] = []
    objects: list[ObjectId] = []
    for step in range(1, state.ruleset.core.topple_length + 1):
        xy = (obj.pos.x + dx * step, obj.pos.y + dy * step)
        if not state.in_bounds(*xy) or is_deadly(state, xy) or not _walkable(state, xy):
            continue
        other = state.object_at(*xy)
        if other is not None:
            tags = state.object_def(other).tags
            if "breakable" in tags:
                objects.append(other.id)
            elif "blocks_move" in tags:
                break
        unit = state.unit_at(*xy)
        if unit is not None:
            units.append(unit.id)
        tiles.append(xy)
    rubble = next(
        (xy for xy in reversed([obj.xy, *tiles]) if _rubble_fits(state, xy, obj)),
        None,
    )
    return ToppleLine(tuple(tiles), tuple(units), tuple(objects), rubble)


def _walkable(state: BattleState, xy: XY) -> bool:
    """地形本身可以進入（不看物件與單位）。"""
    return state.ruleset.terrain_def(state.tile(*xy).terrain).walkable


def _rubble_fits(state: BattleState, xy: XY, toppled: ObjectState) -> bool:
    """倒塌物放得下：沒有單位、沒有其他物件（被推倒的物件自己的格子算空的）、可站立的地形。"""
    if state.unit_at(*xy) is not None:
        return False
    other = state.object_at(*xy)
    if other is not None and other.id != toppled.id:
        return False
    return _walkable(state, xy) and not is_deadly(state, xy)


def _topple(ctx: Ctx, obj: ObjectState, direction: XY, source_id: UnitId | None) -> list[EventBase]:
    """推倒：發出 ``object_toppled``（傷害與倒地由 :mod:`trpg.engine.triggers` 結算）、移除原物件、
    在 ``rubble`` 產生倒塌物。"""
    state = ctx.state
    line = topple_line(state, obj, direction)
    events: list[EventBase] = [
        ctx.emit(
            ObjectToppled,
            object_id=obj.id,
            kind=obj.kind,
            pos=obj.pos,
            direction=direction,
            tiles=tuple(_pos(xy) for xy in line.tiles),
            units=line.units,
            objects=line.objects,
            rubble_pos=None if line.rubble is None else _pos(line.rubble),
            source_id=source_id,
        )
    ]
    events.extend(remove_object(ctx, obj, "toppled", source_id=source_id))
    if line.rubble is not None:
        events.append(_new_object(ctx, line.rubble, ctx.core.topple_rubble_object))
    return events


# ---------------------------------------------------------------------------
# 投擲物件（Phase 3C-5a）
# ---------------------------------------------------------------------------


def hurl_landing(state: BattleState, dest: XY) -> XY | None:
    """非破壞物件被丟到 ``dest`` 後停下的格子：``dest`` 本身或 ``hurl_scatter_radius`` 內最近的空格
    （沒有單位與物件、可站立、非致命；同距離依 ``(y, x)``）；``dest`` 是致命地形或附近沒有空格時
    為 ``None``（物件摧毀）。"""
    if is_deadly(state, dest):
        return None
    radius = state.ruleset.core.hurl_scatter_radius
    cells = sorted(
        (abs(x - dest[0]) + abs(y - dest[1]), y, x)
        for y in range(dest[1] - radius, dest[1] + radius + 1)
        for x in range(dest[0] - radius, dest[0] + radius + 1)
        if abs(x - dest[0]) + abs(y - dest[1]) <= radius and state.in_bounds(x, y)
    )
    for _, y, x in cells:
        xy = (x, y)
        free = state.tile(*xy).object_id is None and state.unit_at(*xy) is None
        if free and is_standable(state, xy) and not is_deadly(state, xy):
            return xy
    return None


@register_effect("hurl_object")
def _hurl_object(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    """物件從原格舉起、落在 ``dest``：``explosive`` 只有在技能帶火元素或落點有火焰時才爆炸；
    其他 ``breakable`` 碎掉（有 ``spill`` 的漏出表面，由 ``object_destroyed`` 觸發表處理）、其他放在
    落點或附近的空格（:func:`hurl_landing`），沒有空格就摧毀。"""
    assert isinstance(effect, HurlObjectEffect)
    state = ctx.state
    obj = _live_object(state, effect.object_id)
    if obj is None:
        return [_fizzle(ctx, effect.kind, effect.dest, "no_object")]
    definition = ctx.rules.object_def(obj.kind)
    start, dest = obj.pos, _pos(effect.dest)
    state.set_tile(*obj.xy, replace(state.tile(*obj.xy), object_id=None))
    landing = None
    lit = effect.ignite or state.tile(*effect.dest).surface is Surface.FIRE
    if definition.explosion is not None and "explosive" in definition.tags and lit:
        outcome: HurlOutcome = "exploded"
    elif "breakable" in definition.tags:
        outcome = "shattered"
    else:
        landing = hurl_landing(state, effect.dest)
        outcome = "lost" if landing is None else "placed"
    if landing is not None:
        obj.pos = _pos(landing)
        state.set_tile(*landing, replace(state.tile(*landing), object_id=obj.id))
    else:
        obj.pos, obj.destroyed = dest, True
    events: list[EventBase] = [
        ctx.emit(
            ObjectHurled,
            object_id=obj.id,
            kind=obj.kind,
            from_pos=start,
            to_pos=dest,
            source_id=effect.source_id,
            outcome=outcome,
            placed_pos=None if landing is None else obj.pos,
        )
    ]
    if outcome == "exploded":
        assert definition.explosion is not None
        events.append(
            ctx.emit(
                ObjectExploded,
                object_id=obj.id,
                pos=dest,
                radius=definition.explosion.radius,
                source_id=effect.source_id,
            )
        )
    if landing is None:
        cause: ObjectDestroyCause = "hurled"
        if outcome == "exploded":
            cause = "explosion"
        elif is_deadly(state, effect.dest):
            cause = "fell"
        events.append(
            ctx.emit(ObjectDestroyed, object_id=obj.id, kind=obj.kind, pos=dest, cause=cause)
        )
    return events


# ---------------------------------------------------------------------------
# 地形
# ---------------------------------------------------------------------------


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
            pos=_pos(xy),
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


@register_effect("raise_terrain")
def _raise_terrain(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, RaiseTerrainEffect)
    if not ctx.state.in_bounds(*effect.pos):
        return []
    return change_height(
        ctx, effect.pos, ctx.state.tile(*effect.pos).height + effect.amount, effect.source_id
    )


@register_effect("lower_terrain")
def _lower_terrain(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, LowerTerrainEffect)
    if not ctx.state.in_bounds(*effect.pos):
        return []
    return change_height(
        ctx, effect.pos, ctx.state.tile(*effect.pos).height - effect.amount, effect.source_id
    )


@register_effect("change_tile")
def _change_tile(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ChangeTileEffect)
    state = ctx.state
    xy = effect.pos
    events: list[EventBase] = []
    if effect.height is not None:
        events.extend(change_height(ctx, xy, effect.height))
    if effect.terrain is not None:
        tile = state.tile(*xy)
        if tile.terrain != effect.terrain:
            state.set_tile(*xy, replace(tile, terrain=effect.terrain))
            events.append(
                ctx.emit(
                    TerrainChanged,
                    pos=_pos(xy),
                    height_before=tile.height,
                    height_after=tile.height,
                    terrain_before=tile.terrain,
                    terrain_after=effect.terrain,
                )
            )
            if is_deadly(state, xy):
                events.extend(set_surface(ctx, xy, Surface.NONE, cause="terrain"))
                unit = state.unit_at(*xy)
                if unit is not None:
                    events.append(
                        ctx.emit(
                            EnteredDeadlyTerrain,
                            unit_id=unit.id,
                            pos=unit.pos,
                            terrain=effect.terrain,
                        )
                    )
    if effect.surface is not None and _surface_allowed(state, xy):
        final, cause = creation_result(state, xy, effect.surface)
        if final is not None:
            events.extend(
                set_surface(
                    ctx,
                    xy,
                    final,
                    cause="map_event" if cause == "effect" else cause,
                    use_default_duration=False,
                    depth=effect.depth,
                )
            )
    return events


# ---------------------------------------------------------------------------
# 產生單位
# ---------------------------------------------------------------------------


@register_effect("spawn_unit")
def _spawn_unit(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, SpawnUnitEffect)
    state = ctx.state
    spawn = state.spawn_templates.get(effect.template_id)
    if spawn is None:
        return [_fizzle(ctx, effect.kind, effect.pos, f"unknown_template:{effect.template_id}")]
    xy: XY | None = effect.pos
    if (
        xy is None
        or not state.in_bounds(*xy)
        or not is_standable(state, xy)
        or is_deadly(state, xy)
        or state.unit_at(*xy) is not None
    ):
        origin = effect.pos if state.in_bounds(*effect.pos) else (0, 0)
        xy = _free_tile(state, origin)
    if xy is None:
        return [_fizzle(ctx, effect.kind, effect.pos, "no_space")]
    uid = UnitId(f"unit_{len(state.units) + 1:04d}")
    same = sum(1 for u in state.units.values() if u.template_id == spawn.template.id)
    name = spawn.template.name_zh + str(same + 1)
    unit = make_unit(
        uid,
        template=spawn.template,
        weapon=spawn.weapon,
        team=effect.team,
        pos=_pos(xy),
        name=name,
        rules=ctx.rules,
        facing=facing_toward_enemies(state, xy, effect.team),  # 援軍面向敵人（Phase 3D-8d）
    )
    state.units[uid] = unit
    state.turn_order.append(uid)
    return [
        ctx.emit(
            UnitSpawned, unit_id=uid, template_id=spawn.template.id, team=effect.team, pos=_pos(xy)
        )
    ]


def _free_tile(state: BattleState, origin: XY) -> XY | None:
    occupied = set(state.occupancy())
    best: tuple[int, int, int] | None = None
    for y in range(state.height):
        for x in range(state.width):
            if (x, y) in occupied or not is_standable(state, (x, y)) or is_deadly(state, (x, y)):
                continue
            key = (abs(origin[0] - x) + abs(origin[1] - y), y, x)
            if best is None or key < best:
                best = key
    return None if best is None else (best[2], best[1])
