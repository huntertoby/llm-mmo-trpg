"""實地地圖上的位置與走路（Phase 6B-2；``docs/phases/Phase6計畫.md`` 第 3 節、21.2、21.10）。

- **位置**：:attr:`CharacterState.field`（地圖、x、y、朝向）一定屬於角色所在地點的實地地圖或它的
  室內圖。舊存檔或位置失效（換了地點）時 :func:`placed` 放到地點實地地圖的 ``entry``；這一步不進
  日誌，重播時算出來的結果一樣。所在地點沒有實地地圖時 ``field`` 是 ``None``，照舊用 ``travel``。
- **走路**（:func:`walk`）：每一步四方向相鄰、可站（地形、物件、高低差，和戰鬥同一套規則）、不是
  NPC 站的格子、不是還沒發現的隱藏門；碰到出口、門、傳送石就停下並觸發。走格子不抽亂數、不花時間
  與補給（21.10 第 2 條）。
- **出口**：一次 ``travel``（呼叫者傳入，沿用全部既有檢查與擲骰順序；這段不趕路），抵達時站在對面
  ``arrive`` 出口往地圖內側一格的可站格（6B-1 待決第 7 點）。室內圖的出口回到門外一格，不算一步。
- **門**：室內圖不算進入一張地圖（Q6：不擲骰、不扣時間）；通往隱藏地點的門算 ``travel``。
- **傳送石**：踩上就解鎖；:func:`use_teleport_stone` 傳到另一顆已解鎖的。

確定性：只看內容與角色狀態；候選格依固定順序挑，不依賴 ``set`` 的迭代順序（守則 2）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from trpg.content.fields import FieldDoor, FieldExit, FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.maps import passable_grid
from trpg.world.actions import TravelAction, WorldEvent
from trpg.world.common import world_map_of
from trpg.world.errors import WorldActionError
from trpg.world.field_actions import (
    FieldEnteredEvent,
    StopReason,
    TeleportStoneUnlockedEvent,
    TeleportStoneUsedEvent,
    UseTeleportStoneAction,
    WalkAction,
    WalkedEvent,
)
from trpg.world.state import CharacterState, Facing, FieldPos, WorldState
from trpg.world.town import with_visited_town

__all__ = [
    "ArriveFn",
    "FieldGrid",
    "FieldHooks",
    "TravelFn",
    "WatchFn",
    "field_grid",
    "field_map",
    "hidden_door",
    "outdoor_map",
    "placed",
    "stale_field",
    "use_teleport_stone",
    "walk",
]

type XY = tuple[int, int]
type WorldResult = tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]
type TravelFn = Callable[
    [ContentLibrary, WorldState, CharacterState, TravelAction, int], WorldResult
]
"""一次 ``travel``（:func:`trpg.world.step` 的移動；這裡不直接匯入，避免循環）。"""
type WatchFn = Callable[
    [ContentLibrary, WorldState, CharacterState, FieldMapDef, WalkedEvent, int],
    tuple[WalkedEvent, CharacterState, tuple[WorldEvent, ...]],
]
"""走完路徑檢查之後、觸發出口等之前（6C-1 看得見的敵人：碰到就截短路徑並開打）。"""
type ArriveFn = Callable[
    [ContentLibrary, WorldState, CharacterState, int], tuple[CharacterState, tuple[WorldEvent, ...]]
]
"""走出口或門換到另一張圖之後（6C-1：一到就被看到時開打）。"""


@dataclass(frozen=True)
class FieldHooks:
    """``walk`` 需要、但住在別的模組的函式（避免循環匯入）。"""

    travel: TravelFn
    watch: WatchFn | None = None
    arrive: ArriveFn | None = None


_DIRS: tuple[tuple[XY, Facing], ...] = (
    ((0, 1), "s"),
    ((0, -1), "n"),
    ((-1, 0), "w"),
    ((1, 0), "e"),
)
"""四個方向與朝向；門外找可站格照這個順序（南、北、西、東）。"""


# ---------------------------------------------------------------------------
# 查詢
# ---------------------------------------------------------------------------


def field_map(library: ContentLibrary, map_id: str) -> FieldMapDef | None:
    return library.field_maps.get(map_id)


def outdoor_map(library: ContentLibrary, region: str, location: str) -> FieldMapDef | None:
    """地點的實地地圖（室外圖）；還沒畫＝``None``。"""
    for map_id in sorted(library.field_maps):
        found = library.field_maps[map_id]
        if found.region == region and found.location == location:
            return found
    return None


def _belongs(found: FieldMapDef | None, char: CharacterState) -> bool:
    return found is not None and found.region == char.region and found.place == char.location


def placed(library: ContentLibrary, char: CharacterState) -> CharacterState:
    """位置有效的角色：``field`` 屬於所在地點就照舊；否則放到地點實地地圖的 ``entry``（沒有地圖＝
    ``None``）。不進日誌（重播時一樣算得出來）。"""
    if char.field is not None and _belongs(field_map(library, char.field.map), char):
        return char
    found = outdoor_map(library, char.region, char.location)
    pos = None if found is None else FieldPos(map=found.id, x=found.entry[0], y=found.entry[1])
    if pos == char.field:
        return char
    return char.model_copy(update={"field": pos})


def stale_field(before: CharacterState, after: CharacterState) -> CharacterState:
    """其他動作（撤退、全滅、``travel``、傳送）換了地點時，舊位置作廢（之後 :func:`placed` 放到
    ``entry``）。"""
    if after.field is None or (before.region, before.location) == (after.region, after.location):
        return after
    return after.model_copy(update={"field": None})


@dataclass(frozen=True)
class FieldGrid:
    """一張地圖給角色走的格子：可站與高度（不含角色本身的狀態以外的東西）。"""

    map: FieldMapDef
    heights: tuple[tuple[int, ...], ...]
    open: tuple[tuple[bool, ...], ...]
    """可以站上去的格子（地形、物件；NPC 站的格子、未發現的隱藏門不行）。"""

    def standable(self, cell: XY) -> bool:
        x, y = cell
        return self.map.in_bounds(x, y) and self.open[y][x]

    def can_step(self, start: XY, cell: XY, max_climb: int) -> bool:
        if not self.standable(cell):
            return False
        return self.heights[cell[1]][cell[0]] - self.heights[start[1]][start[0]] <= max_climb


def hidden_door(char: CharacterState, found: FieldMapDef, door: FieldDoor) -> bool:
    """還沒發現的隱藏門（不可站、不顯示）。"""
    return door.hidden_until == "reveal" and not char.has_revealed(found.region, door.to)


def field_grid(library: ContentLibrary, char: CharacterState, found: FieldMapDef) -> FieldGrid:
    rules = library.ruleset
    passable = passable_grid(found, rules.terrain.by_id(), rules.objects.by_id())
    blocked = {npc.at for npc in found.npcs}
    blocked |= {d.at for d in found.doors if hidden_door(char, found, d)}
    grid = found.grid()
    return FieldGrid(
        map=found,
        heights=tuple(tuple(h for h, _ in row) for row in grid),
        open=tuple(
            tuple(ok and (x, y) not in blocked for x, ok in enumerate(row))
            for y, row in enumerate(passable)
        ),
    )


def _portal_cells(found: FieldMapDef) -> set[XY]:
    cells = {c for e in found.exits for c in e.at}
    cells |= {d.at for d in found.doors}
    cells |= {s.at for s in found.teleport_stones}
    return cells


def _inward(found: FieldMapDef, cell: XY) -> tuple[XY, Facing]:
    """邊緣格往地圖內側一格（角落照 x 邊、再 y 邊）。"""
    x, y = cell
    if x == 0:
        return (1, y), "e"
    if x == found.width - 1:
        return (x - 1, y), "w"
    if y == 0:
        return (x, 1), "s"
    return (x, y - 1), "n"


def _entry_pos(found: FieldMapDef) -> FieldPos:
    return FieldPos(map=found.id, x=found.entry[0], y=found.entry[1])


def arrival(
    library: ContentLibrary, char: CharacterState, found: FieldMapDef, portal_id: str, index: int
) -> FieldPos:
    """從 ``portal_id``（這張地圖上的出口或門）進來時站的格子。

    - 出口：第 ``index`` 格（超出時取最後一格；之後依和它的距離挑其他格）往內側一格的可站格。
    - 門：門外一格（南、北、西、東的順序找第一個可站格）。
    都不行時站 ``entry``。可站格不能是出口、門、傳送石（不會一到就觸發）。"""
    grid = field_grid(library, char, found)
    portals = _portal_cells(found)
    portal = found.portal(portal_id)
    candidates: list[tuple[XY, Facing]] = []
    if isinstance(portal, FieldExit):
        j = min(index, len(portal.at) - 1)
        order = sorted(range(len(portal.at)), key=lambda k: (abs(k - j), k))
        candidates = [_inward(found, portal.at[k]) for k in order]
    elif isinstance(portal, FieldDoor):
        dx, dy = portal.at
        candidates = [((dx + ox, dy + oy), facing) for (ox, oy), facing in _DIRS]
    for cell, facing in candidates:
        if grid.standable(cell) and cell not in portals:
            return FieldPos(map=found.id, x=cell[0], y=cell[1], facing=facing)
    return _entry_pos(found)


# ---------------------------------------------------------------------------
# 走路
# ---------------------------------------------------------------------------


def _facing(start: XY, cell: XY) -> Facing | None:
    delta = (cell[0] - start[0], cell[1] - start[1])
    return next((facing for d, facing in _DIRS if d == delta), None)


def _stop_at(char: CharacterState, found: FieldMapDef, cell: XY) -> StopReason | None:
    if any(cell in e.at for e in found.exits):
        return "exit"
    if any(d.at == cell and not hidden_door(char, found, d) for d in found.doors):
        return "door"
    if any(s.at == cell for s in found.teleport_stones):
        return "stone"
    return None


def _walk_path(
    library: ContentLibrary, char: CharacterState, found: FieldMapDef, action: WalkAction
) -> tuple[WalkedEvent, int]:
    """逐格檢查路徑；回傳走路事件與停下那一格在出口的第幾格（不是出口＝0）。"""
    assert char.field is not None
    grid = field_grid(library, char, found)
    climb = library.ruleset.core.max_climb_height
    here: XY = (char.field.x, char.field.y)
    facing: Facing = char.field.facing
    steps: list[XY] = []
    stopped: StopReason = "end"
    for number, cell in enumerate(action.path, start=1):
        step_facing = _facing(here, cell)
        if step_facing is None:
            raise WorldActionError(f"第 {number} 格 {list(cell)} 和前一格不相鄰")
        if not grid.can_step(here, cell, climb):
            raise WorldActionError(f"第 {number} 格 {list(cell)} 走不過去")
        here, facing = cell, step_facing
        steps.append(cell)
        reason = _stop_at(char, found, cell)
        if reason is not None:
            stopped = reason
            break
    event = WalkedEvent(
        map=found.id, steps=tuple(steps), x=here[0], y=here[1], facing=facing, stopped=stopped
    )
    index = next((e.at.index(here) for e in found.exits if here in e.at), 0)
    return event, index


def walk(  # noqa: PLR0917 - 和世界動作處理同簽名，外加鉤子
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WalkAction,
    now: int,
    hooks: FieldHooks,
) -> WorldResult:
    """沿 ``action.path`` 走；不合法拋 :class:`WorldActionError`（狀態不變）。"""
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能移動")
    char = placed(library, char)
    if char.field is None:
        raise WorldActionError("這裡還沒有實地地圖，請用 travel 移動")
    found = field_map(library, char.field.map)
    assert found is not None
    walked, index = _walk_path(library, char, found, action)
    seen: tuple[WorldEvent, ...] = ()
    if hooks.watch is not None:  # 6C-1：碰到敵人就停在那一格開打
        walked, char, seen = hooks.watch(library, world, char, found, walked, now)
    pos = FieldPos(map=found.id, x=walked.x, y=walked.y, facing=walked.facing)
    char = char.model_copy(update={"field": pos})  # 同一個地點裡走動不算離開營火
    events: list[WorldEvent] = [walked, *seen]
    cell = (walked.x, walked.y)
    if walked.stopped == "stone":
        char, unlocked = _unlock_stone(char, found, cell)
        events += unlocked
    elif walked.stopped in ("exit", "door"):
        if walked.stopped == "exit":
            world, char, more = _take_exit(
                library, world, char, found, (cell, index), now, hooks.travel
            )
        else:
            world, char, more = _take_door(library, world, char, found, cell, now, hooks.travel)
        events += more
        if hooks.arrive is not None:
            char, more = hooks.arrive(library, world, char, now)
            events += more
    return world, char, tuple(events)


def _unlock_stone(
    char: CharacterState, found: FieldMapDef, cell: XY
) -> tuple[CharacterState, list[WorldEvent]]:
    stone = next(s for s in found.teleport_stones if s.at == cell)
    if stone.id in char.teleport_stones:
        return char, []
    stones = tuple(sorted({*char.teleport_stones, stone.id}))
    return char.model_copy(update={"teleport_stones": stones}), [
        TeleportStoneUnlockedEvent(stone=stone.id)
    ]


def _enter(
    library: ContentLibrary,
    char: CharacterState,
    target: FieldMapDef | None,
    portal_id: str,
    index: int,
) -> CharacterState:
    pos = None if target is None else arrival(library, char, target, portal_id, index)
    return char.model_copy(update={"field": pos})


def _entered(char: CharacterState, via: str) -> FieldEnteredEvent:
    pos = char.field
    return FieldEnteredEvent.model_validate(
        {
            "map": None if pos is None else pos.map,
            "location": char.location,
            "x": None if pos is None else pos.x,
            "y": None if pos is None else pos.y,
            "via": via,
        }
    )


def _take_exit(  # noqa: PLR0917 - 出口需要整套移動參數
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    found: FieldMapDef,
    at: tuple[XY, int],
    now: int,
    travel: TravelFn,
) -> WorldResult:
    cell, index = at
    exit_ = next(e for e in found.exits if cell in e.at)
    if found.is_interior:  # 室內圖的出口：回到門外一格，不算一步（Q6）
        outside = outdoor_map(library, char.region, char.location)
        char = _enter(library, char, outside, exit_.arrive, 0)
        return world, char, (_entered(char, "exit"),)
    if exit_.region is not None and exit_.region != found.region:
        raise WorldActionError("跨區的出口還沒開放，請用傳送")
    world, char, events = travel(library, world, char, TravelAction(to=exit_.to), now)
    target = outdoor_map(library, char.region, exit_.to)
    char = _enter(library, char, target, exit_.arrive, index)
    return world, char, (*events, _entered(char, "exit"))


def _take_door(  # noqa: PLR0917 - 門需要整套移動參數
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    found: FieldMapDef,
    cell: XY,
    now: int,
    travel: TravelFn,
) -> WorldResult:
    door = next(d for d in found.doors if d.at == cell)
    interior = field_map(library, door.to)
    if interior is not None and interior.interior_of == found.place:  # 室內：不擲骰（Q6）
        back = next((e.id for e in interior.exits if e.arrive == door.id), interior.exits[0].id)
        char = _enter(library, char, interior, back, 0)
        return world, char, (_entered(char, "door"),)
    world, char, events = travel(library, world, char, TravelAction(to=door.to), now)
    target = outdoor_map(library, char.region, door.to)
    back_id = door.id
    if target is not None:
        back_id = next((e.id for e in target.exits if e.arrive == door.id), back_id)
    char = _enter(library, char, target, back_id, 0)
    return world, char, (*events, _entered(char, "door"))


# ---------------------------------------------------------------------------
# 傳送石
# ---------------------------------------------------------------------------


def _stone_map(library: ContentLibrary, stone_id: str) -> tuple[FieldMapDef, XY] | None:
    for map_id in sorted(library.field_maps):
        found = library.field_maps[map_id]
        for stone in found.teleport_stones:
            if stone.id == stone_id:
                return found, stone.at
    return None


def use_teleport_stone(
    library: ContentLibrary, char: CharacterState, action: UseTeleportStoneAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """站在傳送石上傳到另一顆已解鎖的；跨區要去過那一區的小鎮（同 ``teleport``）。不擲骰。"""
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能傳送")
    char = placed(library, char)
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    here = None
    if pos is not None and found is not None:
        here = next((s for s in found.teleport_stones if s.at == (pos.x, pos.y)), None)
    if here is None:
        raise WorldActionError("要站在傳送石上才能傳送")
    if action.to == here.id:
        raise WorldActionError("已經在這顆傳送石上")
    if action.to not in char.teleport_stones:
        raise WorldActionError(f"還沒走到過傳送石 {action.to}")
    target = _stone_map(library, action.to)
    if target is None or target[0].location is None:
        raise WorldActionError(f"沒有傳送石 {action.to}")
    dest, (x, y) = target
    location = dest.location
    assert location is not None
    if dest.region != char.region and dest.region not in char.visited_towns:
        raise WorldActionError(f"還沒去過 {dest.region} 的小鎮，不能傳送")

    char = char.model_copy(
        update={
            "region": dest.region,
            "location": location,
            "camped_at": None,
            "field": FieldPos(map=dest.id, x=x, y=y),
        }
    )
    if world_map_of(library, dest.region).location_by_id()[location].kind == "town":
        char = with_visited_town(char, dest.region)
    event = TeleportStoneUsedEvent(
        from_stone=here.id, to_stone=action.to, region=dest.region, location=location
    )
    return char, (event,)
