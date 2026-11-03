"""實地地圖上看得見的敵人（Phase 6C-1；``docs/phases/Phase6計畫.md`` 0.4 Q4、Q5、Q8，21.4、21.10）。

- **敵群**：室外圖的每個 ``spawns`` 是一隊敵人。陣容照 ``group``（遭遇變化、懸賞照舊優先，
  :func:`~trpg.world.encounters.roll_lineup`），種子由「這一趟」（:class:`FieldVisit`）衍生，所以地圖上
  看到的陣容就是開戰的陣容。駐守不動（朝向照種子）；巡邏沿 ``patrol`` 的直線路線來回，你走一格它走
  一格，起點照種子。
- **這一趟**：進入一個有敵人的地點時，從角色的 ``field`` 串流
  （:data:`~trpg.world.rng.STREAM_FIELD`）抽一次種子；換地點才重來（進出室內不算）。
- **清空與重生**（21.10 第 9 條，6C-1b）：規則 ``battle.clear_kinds`` 的種類（營地、精英巢穴、遺跡、
  祭壇）打贏一隊只有那一隊消失（世界的
  ``defeated_spawns``，所有人看得到）；這張圖現在會出現的隊伍都打完才寫地點「已清空」
  （:meth:`WorldState.is_cleared`），重生時間照 ``battle.respawn_seconds``，每隊對齊地點的。
  ``personal`` 的隊伍只對自己消失（角色這一趟的 ``defeated``）、不算進共享清空、下一趟回來再
  出現；其他種類的地點照 6C-1，打贏的那一隊到離開這個地點前不再出現。
- **日夜**（21.10 第 11 條）：``day_phase`` 有寫的隊伍只在那個時段出現。
- **進圖寬限**（21.10 第 8 條）：走出口或門抵達的那一格不檢查，從走的第一步才檢查。
- **視野**（21.10 第 3 條）：前方扇形——往前 ≥ 1 格、橫向偏移 ≤ 往前格數（90°）、曼哈頓距離
  ≤ :data:`SIGHT_RANGE`；被擋視線的地形（牆）、物件、表面與高低差遮住（同戰鬥的視線規則：兩個方向
  都畫 Bresenham 線，中間的格子高度 ≥ 兩端最高 ＋ 1 也擋）。只算站得上去的格子。不追擊。
- **開打**：走進視野或和敵人四方向相鄰就開打（產生 ``pending_encounter``，同移動遇敵用
  :func:`~trpg.world.solutions.make_encounter`）。順序：你走一格 → 檢查 → 敵人走一格 → 再檢查；踩上
  出口或門的那一格只檢查一次（人已經離開）。先手（21.10 第 4 條）：被看到＝敵方先手；在視野外、站在
  敵人背後（往前 < 0）＝我方先手；其他（站在側面）照現行先攻。
- **戰後**（21.10 第 7 條）：打贏就站在接觸點（走路停在那一格）；撤退回到進這張地圖時站的格子；
  全滅照現行回小鎮。

確定性：只用角色的 ``field`` 串流衍生的種子與 :func:`~trpg.shared.rng.fnv1a64`；敵人依 ``spawns`` 的
順序檢查，視野格依 (y, x) 排序（守則 2）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from trpg.content.fields import FieldMapDef, FieldSpawn
from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef
from trpg.engine.rules.geometry import bresenham
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Surface
from trpg.world.actions import (
    BattleEndedEvent,
    EncounterEvent,
    FightAction,
    LocationClearedEvent,
    WorldEvent,
)
from trpg.world.battle import with_cleared
from trpg.world.clock import day_phase
from trpg.world.common import rules_of, world_map_of
from trpg.world.encounters import EncounterLineup, roll_lineup
from trpg.world.field import FieldGrid, field_grid, field_map, outdoor_map, placed
from trpg.world.field_actions import WalkedEvent
from trpg.world.rng import STREAM_FIELD, derive_seed, draw
from trpg.world.solutions import make_encounter
from trpg.world.state import (
    CharacterState,
    DefeatedSpawn,
    Facing,
    FieldContact,
    FieldPos,
    FieldVisit,
    WorldState,
)

__all__ = [
    "SIGHT_RANGE",
    "FieldEnemy",
    "after_fight",
    "appears",
    "arrive_watch",
    "contact_of",
    "enemy_lineup",
    "field_enemies",
    "lineup_seed",
    "shared_clear",
    "sight_cells",
    "spawn_place",
    "spawn_route",
    "visit_for",
    "walk_watch",
    "with_defeated_spawn",
    "with_visit",
]

type XY = tuple[int, int]
type First = Literal["ally", "enemy"] | None

SIGHT_RANGE: Final = 4
"""敵人的視野距離（前方扇形 4 格，21.10 第 3 條；潛行減半是 6C-5）。"""

_VECTORS: Final[dict[Facing, XY]] = {"n": (0, -1), "e": (1, 0), "s": (0, 1), "w": (-1, 0)}
_FACINGS: Final[tuple[Facing, ...]] = ("n", "e", "s", "w")


@dataclass(frozen=True)
class FieldEnemy:
    """地圖上的一隊敵人（目前位置、朝向、看得到的格子）。"""

    index: int
    """``spawns`` 的索引。"""
    spawn: FieldSpawn
    x: int
    y: int
    facing: Facing
    sight: tuple[XY, ...]
    """看得到的格子（依 (y, x) 排序）。"""

    @property
    def xy(self) -> XY:
        return (self.x, self.y)

    @property
    def patrols(self) -> bool:
        return len(spawn_route(self.spawn)) > 1


# ---------------------------------------------------------------------------
# 這一趟
# ---------------------------------------------------------------------------


def _spawn_map(library: ContentLibrary, char: CharacterState) -> FieldMapDef | None:
    """所在地點有敵人的室外圖；沒有＝``None``。"""
    found = outdoor_map(library, char.region, char.location)
    return found if found is not None and found.spawns else None


def visit_for(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> FieldVisit | None:
    """角色這一趟（只算、不改計數）：所在地點沒有有敵人的實地地圖＝``None``；已有同一地點的就照舊；
    否則用 ``field`` 串流的下一個種子開新的一趟（:func:`with_visit` 實際抽的就是這一個）。"""
    found = _spawn_map(library, char)
    if found is None:
        return None
    visit = char.field_visit
    if visit is not None and (visit.region, visit.location) == (char.region, char.location):
        return visit
    counter = char.rng_counters.get(STREAM_FIELD, 0)
    seed = Rng(derive_seed(world.season_seed, char.character_id, STREAM_FIELD, counter)).next_u32()
    pos = placed(library, char).field
    arrived = pos if pos is not None and pos.map == found.id else None
    if arrived is None:
        arrived = FieldPos(map=found.id, x=found.entry[0], y=found.entry[1])
    return FieldVisit(region=char.region, location=char.location, seed=seed, arrived=arrived)


def with_visit(library: ContentLibrary, world: WorldState, char: CharacterState) -> CharacterState:
    """把這一趟寫進角色（新的一趟會用掉 ``field`` 串流的一次）；沒有變化時回傳同一個物件。"""
    visit = visit_for(library, world, char)
    if visit == char.field_visit:
        return char
    if visit is not None:
        _rng, char = draw(world.season_seed, char, STREAM_FIELD)  # 種子已由 visit_for 算好
    return char.model_copy(update={"field_visit": visit})


def shared_clear(library: ContentLibrary, region: str, location: str) -> bool:
    """這個地點的隊伍是不是「打贏一隊、所有人看到它消失，全打完才寫已清空」（21.10 第 9 條）：
    規則 ``battle.clear_kinds`` 列的種類（正式內容：營地、精英巢穴、遺跡、祭壇；6C-2 從程式常數
    搬到 ``content/world/rules.yaml``）。其他種類照 6C-1：打贏的那一隊只在這一趟消失。"""
    place = world_map_of(library, region).location_by_id().get(location)
    if place is None:
        return False
    return place.kind in rules_of(library).battle.clear_kinds


def appears(spawn: FieldSpawn, now: int) -> bool:
    """這一隊現在的時段會不會出現（``day_phase`` 省略＝全天，21.10 第 11 條）。"""
    return spawn.day_phase is None or spawn.day_phase == day_phase(now)


def _won_contact(
    before: CharacterState, char: CharacterState, action: object, events: tuple[WorldEvent, ...]
) -> FieldContact | None:
    """這個動作是不是打贏了地圖上的一隊（回傳那次接觸）。"""
    encounter = before.pending_encounter
    visit = char.field_visit
    if (
        not isinstance(action, FightAction)
        or encounter is None
        or encounter.contact is None
        or visit is None
        or (visit.region, visit.location) != (encounter.region, encounter.location)
        or not any(isinstance(e, BattleEndedEvent) and e.won for e in events)
    ):
        return None
    return encounter.contact


def with_defeated_spawn(
    world: WorldState, region: str, location: str, spawn: int, respawn_at: int
) -> WorldState:
    """把第 ``spawn`` 隊寫成被打贏、到 ``respawn_at`` 重生（已有就更新；依地點、索引排序）。"""
    key = (region, location, spawn)
    kept = [s for s in world.defeated_spawns if s.key() != key]
    kept.append(DefeatedSpawn(region=region, location=location, spawn=spawn, respawn_at=respawn_at))
    kept.sort(key=DefeatedSpawn.key)
    return world.model_copy(update={"defeated_spawns": tuple(kept)})


def _clear_if_done(
    library: ContentLibrary, world: WorldState, found: FieldMapDef, visit: FieldVisit, now: int
) -> tuple[WorldState, tuple[WorldEvent, ...]]:
    """這張圖現在會出現的共享隊伍都打完了：地點寫「已清空」，每隊的重生時間對齊地點的。"""
    region, location = visit.region, visit.location
    shared = [i for i, s in enumerate(found.spawns) if not s.personal and appears(s, now)]
    if any(not world.spawn_defeated(region, location, i, now) for i in shared):
        return world, ()
    respawn_at = now + rules_of(library).battle.respawn_seconds
    world = with_cleared(world, region, location, respawn_at)
    for s in world.defeated_spawns:
        if (s.region, s.location) == (region, location):
            world = with_defeated_spawn(world, region, location, s.spawn, respawn_at)
    return world, (LocationClearedEvent(location=location, respawn_at=respawn_at),)


def after_fight(
    library: ContentLibrary,
    world: WorldState,
    before: CharacterState,
    char: CharacterState,
    *,
    action: object,
    events: tuple[WorldEvent, ...],
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """打贏地圖上的一隊（21.10 第 9 條）。

    - 共享的地點（:func:`shared_clear`）、不是 ``personal`` 的隊伍：寫進世界的 ``defeated_spawns``
      （所有人看到它消失，重生時間照 ``battle.respawn_seconds``）；這張圖現在會出現的共享隊伍都打完
      才寫地點「已清空」（:class:`LocationClearedEvent`）。
    - ``personal`` 的隊伍、或不共享的地點：記進角色這一趟的 ``defeated``，下一趟回來再出現。"""
    contact = _won_contact(before, char, action, events)
    visit = char.field_visit
    found = None if contact is None else field_map(library, contact.map)
    if contact is None or visit is None or found is None or contact.spawn >= len(found.spawns):
        return world, char, ()
    spawn = found.spawns[contact.spawn]
    if spawn.personal or not shared_clear(library, visit.region, visit.location):
        defeated = tuple(sorted({*visit.defeated, contact.spawn}))
        update = {"field_visit": visit.model_copy(update={"defeated": defeated})}
        return world, char.model_copy(update=update), ()
    respawn_at = now + rules_of(library).battle.respawn_seconds
    world = with_defeated_spawn(world, visit.region, visit.location, contact.spawn, respawn_at)
    world, cleared = _clear_if_done(library, world, found, visit, now)
    return world, char, cleared


# ---------------------------------------------------------------------------
# 巡邏與視野
# ---------------------------------------------------------------------------


def spawn_route(spawn: FieldSpawn) -> tuple[XY, ...]:
    """巡邏走的格子（``at`` 起，沿 ``patrol`` 各點之間的直線，先走 x 再走 y）；駐守＝只有
    ``at``。"""
    points = list(spawn.patrol) or [spawn.at]
    if points[0] != spawn.at:
        points.insert(0, spawn.at)
    cells = [points[0]]
    for goal in points[1:]:
        x, y = cells[-1]
        while (x, y) != goal:
            if x != goal[0]:
                x += 1 if goal[0] > x else -1
            else:
                y += 1 if goal[1] > y else -1
            cells.append((x, y))
    return tuple(cells)


def _spawn_rng(seed: int, index: int, what: str) -> Rng:
    return Rng(fnv1a64(f"{seed}:{index}:{what}".encode()))


def lineup_seed(visit: FieldVisit, index: int) -> int:
    """第 ``index`` 隊的陣容種子（32 位元）。"""
    return _spawn_rng(visit.seed, index, "lineup").next_u32()


def _toward(a: XY, b: XY) -> Facing:
    delta = (b[0] - a[0], b[1] - a[1])
    return next((f for f, v in _VECTORS.items() if v == delta), "s")


def _bounce(step: int, length: int) -> int:
    period = 2 * (length - 1)
    k = step % period
    return k if k < length else period - k


def spawn_place(visit: FieldVisit, index: int, spawn: FieldSpawn, ticks: int) -> tuple[XY, Facing]:
    """第 ``ticks`` 步時這一隊站哪一格、面向哪裡（巡邏面向下一格；駐守照種子）。"""
    route = spawn_route(spawn)
    rng = _spawn_rng(visit.seed, index, "patrol")
    if len(route) == 1:
        return route[0], _FACINGS[rng.randint(0, len(_FACINGS) - 1)]
    start = rng.randint(0, 2 * (len(route) - 1) - 1)
    here = route[_bounce(start + ticks, len(route))]
    after = route[_bounce(start + ticks + 1, len(route))]
    return here, _toward(here, after)


@dataclass(frozen=True)
class _Sight:
    """一張地圖的視線資料：站得上去的格子、高度、擋視線的格子。"""

    grid: FieldGrid
    opaque: tuple[tuple[bool, ...], ...]

    def height(self, cell: XY) -> int:
        return self.grid.heights[cell[1]][cell[0]]

    def clear(self, a: XY, b: XY) -> bool:
        limit = max(self.height(a), self.height(b)) + 1
        for line in (bresenham(a, b), bresenham(b, a)):
            for x, y in line[1:-1]:
                if self.opaque[y][x] or self.grid.heights[y][x] >= limit:
                    return False
        return True

    def cells(self, at: XY, facing: Facing, radius: int = SIGHT_RANGE) -> tuple[XY, ...]:
        fx, fy = _VECTORS[facing]
        out: list[XY] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                forward = dx * fx + dy * fy
                if forward < 1 or abs(dx * fy - dy * fx) > forward or abs(dx) + abs(dy) > radius:
                    continue
                cell = (at[0] + dx, at[1] + dy)
                if self.grid.standable(cell) and self.clear(at, cell):
                    out.append(cell)
        return tuple(sorted(out, key=lambda c: (c[1], c[0])))


def _sight(library: ContentLibrary, char: CharacterState, found: FieldMapDef) -> _Sight:
    rules = library.ruleset
    terrain = rules.terrain.by_id()
    objects = rules.objects.by_id()
    surfaces = {s.id: s for s in rules.surfaces.surfaces}
    opaque = [[terrain[tid].blocks_sight for _h, tid in row] for row in found.grid()]
    for placed_obj in found.objects:
        obj = objects.get(placed_obj.kind)
        if obj is not None and obj.has_tag("blocks_sight"):
            opaque[placed_obj.at[1]][placed_obj.at[0]] = True
    for surface in found.surfaces:
        found_def = None if surface.surface is Surface.NONE else surfaces.get(surface.surface)
        if found_def is not None and found_def.blocks_sight:
            opaque[surface.at[1]][surface.at[0]] = True
    return _Sight(grid=field_grid(library, char, found), opaque=tuple(tuple(r) for r in opaque))


def sight_cells(
    library: ContentLibrary,
    char: CharacterState,
    found: FieldMapDef,
    at: XY,
    facing: Facing,
    *,
    radius: int = SIGHT_RANGE,
) -> tuple[XY, ...]:
    """站在 ``at``、面向 ``facing`` 的敵人看得到的格子（依 (y, x) 排序）。"""
    return _sight(library, char, found).cells(at, facing, radius)


# ---------------------------------------------------------------------------
# 地圖上的敵人
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Watch:
    """一張室外圖上會出現的敵人（不含位置；位置照步數算）。"""

    map: FieldMapDef
    visit: FieldVisit
    sight: _Sight
    spawns: tuple[tuple[int, FieldSpawn], ...]

    def enemies(self, ticks: int) -> tuple[FieldEnemy, ...]:
        out: list[FieldEnemy] = []
        for index, spawn in self.spawns:
            (x, y), facing = spawn_place(self.visit, index, spawn, ticks)
            out.append(
                FieldEnemy(
                    index=index,
                    spawn=spawn,
                    x=x,
                    y=y,
                    facing=facing,
                    sight=self.sight.cells((x, y), facing),
                )
            )
        return tuple(out)

    def contact(self, cell: XY, ticks: int) -> tuple[FieldEnemy, First] | None:
        """站在 ``cell`` 時碰到的第一隊（依 ``spawns`` 順序）與先手；沒碰到＝``None``。"""
        for enemy in self.enemies(ticks):
            touched, first = contact_of(enemy, cell)
            if touched:
                return enemy, first
        return None


def contact_of(enemy: FieldEnemy, cell: XY) -> tuple[bool, First]:
    """站在 ``cell`` 會不會和 ``enemy`` 開打、誰先手：被看到＝敵方；相鄰且在背後＝我方；相鄰在側面
    ＝照現行先攻（``None``）。"""
    if cell in enemy.sight:
        return True, "enemy"
    dx, dy = cell[0] - enemy.x, cell[1] - enemy.y
    if abs(dx) + abs(dy) > 1:
        return False, None
    fx, fy = _VECTORS[enemy.facing]
    forward = dx * fx + dy * fy
    if forward < 0:
        return True, "ally"
    if forward > 0 or (dx, dy) == (0, 0):  # 正前方、同一格
        return True, "enemy"
    return True, None


def _target(library: ContentLibrary, char: CharacterState) -> LocationDef | None:
    place = world_map_of(library, char.region).location_by_id().get(char.location)
    return None if place is None or place.level_max is None else place


def _watch(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> _Watch | None:
    """角色所在室外圖會出現的敵人；在室內、沒有敵人、地點已清空＝``None``。"""
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    visit = visit_for(library, world, char)
    if found is None or found.is_interior or visit is None or found.place != visit.location:
        return None
    if _target(library, char) is None:
        return None
    spawns = _shown(library, world, found, visit, now)
    if not spawns:
        return None
    return _Watch(map=found, visit=visit, sight=_sight(library, char, found), spawns=spawns)


def _shown(
    library: ContentLibrary, world: WorldState, found: FieldMapDef, visit: FieldVisit, now: int
) -> tuple[tuple[int, FieldSpawn], ...]:
    """現在會出現的隊伍（21.10 第 9、11 條）：

    - 不在這個時段的（``day_phase``）不出現。
    - ``personal``：這一趟打贏了就不出現（地點「已清空」也照樣在）。
    - 其他：地點「已清空」就不出現；共享的地點看世界的 ``defeated_spawns``，不共享的看這一趟。"""
    region, location = visit.region, visit.location
    cleared = world.is_cleared(region, location, now)
    shared = shared_clear(library, region, location)
    out: list[tuple[int, FieldSpawn]] = []
    for i, spawn in enumerate(found.spawns):
        if not appears(spawn, now):
            continue
        if spawn.personal or not shared:
            gone = i in visit.defeated or (cleared and not spawn.personal)
        else:
            gone = cleared or world.spawn_defeated(region, location, i, now)
        if not gone:
            out.append((i, spawn))
    return tuple(out)


def field_enemies(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[FieldEnemy, ...]:
    """目前地圖上看得見的敵人（畫面用；只算、不改狀態）。"""
    char = placed(library, char)
    watch = _watch(library, world, char, now)
    if watch is None:
        return ()
    return watch.enemies(watch.visit.ticks)


def enemy_lineup(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    enemy: FieldEnemy,
    now: int,
) -> EncounterLineup | None:
    """這一隊現在碰到時的陣容（同開戰時 :func:`roll_lineup` 的結果；增援不算）。"""
    visit = visit_for(library, world, char)
    target = _target(library, char)
    if visit is None or target is None or char.field is None:
        return None
    result, _ = make_encounter(library, world, char, target, now)
    contact = _contact_model(char.field.map, visit, enemy, (char.field.x, char.field.y), None)
    return roll_lineup(library, result.model_copy(update={"contact": contact}), char.story_flags)


def _contact_model(
    map_id: str, visit: FieldVisit, enemy: FieldEnemy, at: XY, first: First
) -> FieldContact:
    return FieldContact(
        map=map_id,
        spawn=enemy.index,
        group=enemy.spawn.group,
        lineup_seed=lineup_seed(visit, enemy.index),
        x=at[0],
        y=at[1],
        first=first,
        retreat_to=visit.arrived,
        enemy_at=enemy.xy,
    )


def _start(  # noqa: PLR0917 - 開打要接觸的全部資料
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    watch: _Watch,
    hit: tuple[FieldEnemy, First],
    at: XY,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    enemy, first = hit
    target = _target(library, char)
    assert target is not None
    result, char = make_encounter(library, world, char, target, now)
    contact = _contact_model(watch.map.id, watch.visit, enemy, at, first)
    result = result.model_copy(update={"from_location": char.location, "contact": contact})
    char = char.model_copy(update={"pending_encounter": result})
    return char, (EncounterEvent(result=result),)


# ---------------------------------------------------------------------------
# 走路的鉤子（:func:`trpg.world.field.walk` 呼叫）
# ---------------------------------------------------------------------------


def walk_watch(  # noqa: PLR0917 - 同 field.WatchFn 的簽名
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    found: FieldMapDef,
    walked: WalkedEvent,
    now: int,
) -> tuple[WalkedEvent, CharacterState, tuple[WorldEvent, ...]]:
    """逐格檢查敵人：碰到就在那一格停下（``stopped="enemy"``）並開打；推進巡邏的步數。"""
    if found.is_interior:
        return walked, char, ()
    char = with_visit(library, world, char)
    visit = char.field_visit
    if visit is None:
        return walked, char, ()
    watch = _watch(library, world, char, now)
    ticks = visit.ticks
    hit: tuple[FieldEnemy, First] | None = None
    steps = walked.steps
    for k, cell in enumerate(steps):
        leaving = k == len(steps) - 1 and walked.stopped in ("exit", "door")
        hit = None if watch is None else watch.contact(cell, ticks)
        if hit is None and not leaving:
            ticks += 1  # 你走一格、它走一格
            hit = None if watch is None else watch.contact(cell, ticks)
        if hit is not None:
            walked = _cut(walked, char, k)
            break
    char = char.model_copy(update={"field_visit": visit.model_copy(update={"ticks": ticks})})
    if hit is None or watch is None:
        return walked, char, ()
    char, events = _start(library, world, char, watch, hit, (walked.x, walked.y), now)
    return walked, char, events


def _cut(walked: WalkedEvent, char: CharacterState, k: int) -> WalkedEvent:
    """走路停在第 ``k`` 格（碰到敵人）。"""
    steps = walked.steps[: k + 1]
    cell = steps[-1]
    if k > 0:
        before = steps[-2]
    else:
        assert char.field is not None
        before = (char.field.x, char.field.y)
    return walked.model_copy(
        update={
            "steps": steps,
            "x": cell[0],
            "y": cell[1],
            "facing": _toward(before, cell),
            "stopped": "enemy",
        }
    )


def arrive_watch(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """走出口或門到了另一張圖：開始這一趟。進圖寬限（21.10 第 8 條，6C-1b）：抵達的那一格不檢查
    視野與相鄰，從玩家走的第一步才開始檢查。"""
    del now
    return with_visit(library, world, char), ()
