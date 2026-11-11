"""地圖上的東西（Phase 6C-5；``docs/phases/Phase6計畫.md`` 第 1 節 6C-5 列、21.4、21.6、21.9
第 8～12 條、21.10 第 6 條）。

- **隱藏入口**（#112、21.9 第 10 條）：走到 ``hidden_until: reveal`` 的門規則
  ``field.perceive_range`` 格（曼哈頓距離）內，對門通往的隱藏地點自動感知判定（DC、每天一次、
  影子不能代判照 #112，:mod:`trpg.world.perception`）。逐格照走過的順序判定；走出口或門抵達
  新地圖時，抵達格也算一次。
- **事件「！」**（21.6、21.9 第 9 條）：進入一張有實地地圖的地點時，``roll_event`` 照舊擲機率與
  骨架；觸發的事件不直接開卡，而是放在這個地點的事件點上（:class:`~trpg.world.state.FieldEventMark`）：
  優先放在和骨架同名的事件點，沒有就從全部事件點挑；候選超過一個時用 ``spot`` 串流挑。走路碰到
  （站上或四方向相鄰）就停下、開事件卡；同一趟只開一次，換地點就消失。地點沒有任何事件點時照舊
  直接開卡。
- **營火**（#114）：站在 ``campfires`` 的格子上可以紮營（照 #114 的花費）；「敵人還在的營地不能
  紮營」在營火點上不算（:func:`on_campfire`）。其他規則照舊。
- **情境物件**（21.6「走到旁邊點了就開」）：站在旁邊（四方向相鄰或同一格）送 ``use_field_object``。
  ``use`` 照內容：``event``＝開這個地點的事件骨架（照骨架的情境模板；每個物件每天一次，骨架要在
  現在合格）、``encounter``＝這個地點的遭遇（Boss 門）、``note``＝只看說明卡（不送動作）。
- **潛行**（Q7）：花 ``hasten.cost`` 補給，到進入下一張地圖為止敵人視野減半（捨去小數，
  :func:`trpg.world.field_enemies.sight_range`）。

確定性：只看內容與角色狀態；事件點、門依內容的順序處理（守則 2），亂數只在挑事件點時用 ``spot``
串流（候選只有一個時不抽）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.fields import FieldMapDef, FieldSpot, SpotUse
from trpg.content.library import ContentLibrary
from trpg.world.actions import EncounterEvent, EventTriggeredEvent, WorldEvent
from trpg.world.calendar import day_of
from trpg.world.clock import day_phase
from trpg.world.common import rules_of, world_map_of
from trpg.world.errors import WorldActionError
from trpg.world.events import event_candidates
from trpg.world.field import FieldCtx, exit_open, field_map, hidden_door, outdoor_map, placed
from trpg.world.field_actions import (
    EventMarkedEvent,
    FieldObjectUsedEvent,
    SneakAction,
    SneakStartedEvent,
    UseFieldObjectAction,
    WalkedEvent,
)
from trpg.world.opening_limits import spot_problem
from trpg.world.perception import can_perceive, perceive
from trpg.world.rng import STREAM_SPOT, draw
from trpg.world.situations import held_threads
from trpg.world.solutions import make_encounter
from trpg.world.state import (
    CharacterState,
    EventTrigger,
    FieldEventMark,
    ObjectUse,
    WorldState,
)
from trpg.world.threads import active_threads
from trpg.world.weather import weather_at

__all__ = [
    "ObjectStatus",
    "arrive_sense",
    "drop_stale_marks",
    "location_spots",
    "object_status",
    "on_campfire",
    "place_event",
    "sense_walk",
    "sneak",
    "sneak_problem",
    "use_field_object",
]

type XY = tuple[int, int]


def _near(a: XY, b: XY, reach: int) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) <= reach


def drop_stale_marks(before: CharacterState, after: CharacterState) -> CharacterState:
    """換了地點：潛行結束（Q7「到進入下一張地圖為止」），不屬於新地點的「！」消失。"""
    if (before.region, before.location) == (after.region, after.location):
        return after
    mark = after.field_event
    stale = mark is not None and (mark.trigger.region, mark.trigger.location) != (
        after.region,
        after.location,
    )
    if not stale and not after.sneaking:
        return after
    return after.model_copy(update={"field_event": None if stale else mark, "sneaking": False})


# ---------------------------------------------------------------------------
# 隱藏入口
# ---------------------------------------------------------------------------


def _sense_doors(
    ctx: FieldCtx, char: CharacterState, cells: Sequence[XY]
) -> tuple[CharacterState, list[WorldEvent]]:
    """依序站過 ``cells``：每一格對 3 格內還沒發現的隱藏入口判定（每個地點每天一次）。"""
    library, found = ctx.library, ctx.map
    doors = [d for d in found.doors if hidden_door(char, found, d)]
    if found.is_interior or not doors or not cells:
        return char, []
    locations = world_map_of(library, found.region).location_by_id()
    today = day_of(library, ctx.now)
    reach = rules_of(library).field.perceive_range  # 21.6「3 格內」（6C-R2 搬到規則）
    events: list[WorldEvent] = []
    for cell in cells:
        for door in doors:
            hidden = locations.get(door.to)
            if hidden is None or not _near(cell, door.at, reach):
                continue
            if not can_perceive(char, found.region, hidden, today):
                continue
            char, more = perceive(
                library, ctx.world, char, hidden, region=found.region, today=today
            )
            events += more
    return char, events


def sense_walk(
    ctx: FieldCtx, char: CharacterState, walked: WalkedEvent
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """走完一段（觸發出口等之前）：走過的格子做隱藏入口的感知；碰到「！」就開事件卡
    （:data:`trpg.world.field.SenseFn`）。"""
    char, events = _sense_doors(ctx, char, walked.steps)
    if walked.stopped == "event":
        char, opened = _open_event(char, ctx.now)
        events += opened
    return char, tuple(events)


def arrive_sense(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """走出口或門抵達另一張圖：抵達格也做一次隱藏入口的感知。"""
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    if pos is None or found is None:
        return char, ()
    ctx = FieldCtx(library=library, world=world, map=found, now=now)
    char, events = _sense_doors(ctx, char, [(pos.x, pos.y)])
    return char, tuple(events)


# ---------------------------------------------------------------------------
# 事件「！」
# ---------------------------------------------------------------------------


def location_spots(
    library: ContentLibrary, region: str, location: str
) -> tuple[tuple[FieldMapDef, FieldSpot], ...]:
    """地點的所有事件點（室外圖與室內圖，依地圖 ID、內容順序）。"""
    out: list[tuple[FieldMapDef, FieldSpot]] = []
    for map_id in sorted(library.field_maps):
        found = library.field_maps[map_id]
        if found.region == region and found.place == location:
            out += [(found, s) for s in found.event_spots]
    return tuple(out)


def place_event(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Sequence[WorldEvent],
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """``roll_event`` 剛觸發的事件改放到地圖的事件點上（見模組說明）；沒有實地地圖或事件點＝
    不變。"""
    trigger = char.pending_event
    if trigger is None or outdoor_map(library, char.region, char.location) is None:
        return char, tuple(events)
    index = next(
        (
            i
            for i, e in enumerate(events)
            if isinstance(e, EventTriggeredEvent) and e.trigger == trigger
        ),
        None,
    )
    spots = location_spots(library, char.region, char.location)
    if index is None or not spots:
        return char, tuple(events)
    pool = [p for p in spots if p[1].id == trigger.skeleton] or list(spots)
    picked = pool[0]
    if len(pool) > 1:
        rng, char = draw(world.season_seed, char, STREAM_SPOT)
        picked = rng.choice(pool)
    found, spot = picked
    mark = FieldEventMark(trigger=trigger, map=found.id, x=spot.at[0], y=spot.at[1], spot=spot.id)
    char = char.model_copy(update={"pending_event": None, "field_event": mark})
    marked = EventMarkedEvent(
        location=char.location, map=found.id, x=spot.at[0], y=spot.at[1], spot=spot.id
    )
    out = list(events)
    out[index] = marked
    return char, tuple(out)


def _open_event(char: CharacterState, now: int) -> tuple[CharacterState, list[WorldEvent]]:
    mark = char.field_event
    if mark is None or char.pending_event is not None:
        return char, []
    trigger = mark.trigger.model_copy(update={"at": now})
    char = char.model_copy(update={"pending_event": trigger, "field_event": None})
    return char, [EventTriggeredEvent(trigger=trigger)]


# ---------------------------------------------------------------------------
# 營火與潛行
# ---------------------------------------------------------------------------


def on_campfire(library: ContentLibrary, char: CharacterState) -> bool:
    """站在營火點的格子上。"""
    char = placed(library, char)
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    return (
        pos is not None
        and found is not None
        and any(c.at == (pos.x, pos.y) for c in found.campfires)
    )


def sneak_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """不能潛行的原因；可以時回傳 ``None``。"""
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能潛行"
    if char.sneaking:
        return "已經在潛行了（到下一張地圖為止）"
    char = placed(library, char)
    found = None if char.field is None else field_map(library, char.field.map)
    if found is None:
        return "這裡沒有實地地圖，移動時用趕路"
    place = world_map_of(library, char.region).location_by_id().get(char.location)
    if found.is_interior or (place is not None and place.kind == "town"):
        return "城鎮與室內不用潛行"
    cost = rules_of(library).hasten.cost
    if char.supplies < cost:
        return f"補給不足，潛行要 {cost} 補給"
    return None


def sneak(
    library: ContentLibrary,
    _world: WorldState,
    char: CharacterState,
    _action: SneakAction,
    _now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    problem = sneak_problem(library, char)
    if problem is not None:
        raise WorldActionError(problem)
    cost = rules_of(library).hasten.cost
    char = char.model_copy(update={"sneaking": True, "supplies": char.supplies - cost})
    return char, (SneakStartedEvent(supplies_spent=cost, supplies_left=char.supplies),)


# ---------------------------------------------------------------------------
# 情境物件
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObjectStatus:
    """一個情境物件現在的樣子（畫面與動作共用）。"""

    spot: FieldSpot
    shown: bool
    """``requires_thread`` 沒持有＝不顯示。"""
    use: SpotUse
    """實際的用途：鎖住（``requires_flag`` 沒開）時是 ``note``。"""
    note_zh: str
    problem_zh: str | None
    """``use`` 是 ``event``／``encounter`` 但現在不能用的原因；可以用＝``None``。"""

    @property
    def usable(self) -> bool:
        return self.shown and self.use != "note" and self.problem_zh is None


def _skeleton_id(spot: FieldSpot) -> str:
    return spot.event or spot.id


def _used_today(
    library: ContentLibrary, char: CharacterState, map_id: str, spot: str, now: int
) -> bool:
    today = day_of(library, now)
    return any(u.map == map_id and u.object == spot and u.day == today for u in char.object_uses)


def _event_problem(ctx: FieldCtx, char: CharacterState, spot: FieldSpot) -> str | None:
    library, world, found, now = ctx.library, ctx.world, ctx.map, ctx.now
    if char.pending_event is not None:
        return "先處理眼前的事件"
    if _used_today(library, char, found.id, spot.id, now):
        return "今天已經看過了，明天再來"
    ids = {
        s.id
        for s in event_candidates(
            library,
            world,
            char.region,
            char.location,
            now,
            unlocked=char.unlocked_skeletons,
            finished=char.finished_skeletons,
            failed=char.failed_skeletons,
        )
    }
    if _skeleton_id(spot) not in ids:
        return "現在沒有什麼動靜"
    return None


def object_status(ctx: FieldCtx, char: CharacterState, spot: FieldSpot) -> ObjectStatus:
    """``ctx.map`` 上的情境物件 ``spot`` 現在的樣子。"""
    world, now = ctx.world, ctx.now
    shown = spot.requires_thread is None or spot.requires_thread in held_threads(world, char, now)
    if spot.requires_flag is not None and not world.has_flag(spot.requires_flag):
        note = spot.locked_zh or spot.note_zh
        return ObjectStatus(spot=spot, shown=shown, use="note", note_zh=note, problem_zh=None)
    problem: str | None = None
    if spot.use == "event":
        problem = _event_problem(ctx, char, spot)
    elif spot.use == "encounter" and char.pending_encounter is not None:
        problem = "還有沒處理的遭遇"
    else:
        problem = spot_problem(char, spot.use)  # OB-4（#150）：入門期不能直接開戰
    note = _gate_note(ctx, char, spot)
    return ObjectStatus(spot=spot, shown=shown, use=spot.use, note_zh=note, problem_zh=problem)


def _gate_note(ctx: FieldCtx, char: CharacterState, spot: FieldSpot) -> str:
    """說明卡的文字：擋路的情境物件（出口的 ``gate.spot``，#122 霧牆）依角色自己的主線進度換文字
    （關著＝原文＋「霧太濃，還過不去」與任務提示；開著＝``open_zh``）；其他照 ``note_zh``。"""
    found = ctx.map
    exit_ = next((e for e in found.exits if e.gate is not None and e.gate.spot == spot.id), None)
    if exit_ is None or exit_.gate is None:
        return spot.note_zh
    if exit_open(ctx.library, char, found, exit_):
        return exit_.gate.open_zh or spot.note_zh
    notice = exit_.gate.notice_zh() + "。"
    return f"{spot.note_zh}{notice}" if spot.note_zh else notice


def _object_trigger(
    library: ContentLibrary, world: WorldState, char: CharacterState, skeleton_id: str, now: int
) -> EventTrigger:
    table = library.world_event_content.events[char.region]
    skeleton = table.skeleton_by_id()[skeleton_id]
    live = {t.thread for t in active_threads((*char.threads, *world.threads), now)}
    hits = sorted(live.intersection(skeleton.follows))
    return EventTrigger(
        region=char.region,
        location=char.location,
        skeleton=skeleton_id,
        candidates=(skeleton_id,),
        follows_thread=hits[0] if hits else None,
        weather=weather_at(library, world, char.region, now),
        day_phase=day_phase(now),
        at=now,
    )


def _with_use(char: CharacterState, use: ObjectUse) -> CharacterState:
    uses = [u for u in char.object_uses if (u.map, u.object) != (use.map, use.object)]
    uses.append(use)
    uses.sort(key=lambda u: (u.map, u.object))
    return char.model_copy(update={"object_uses": tuple(uses)})


def use_field_object(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: UseFieldObjectAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """點了站在旁邊的情境物件；不合法拋 :class:`WorldActionError`。"""
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇")
    char = placed(library, char)
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    spot = (
        None
        if found is None
        else next((s for s in found.situation_objects if s.id == action.object), None)
    )
    if pos is None or found is None or spot is None:
        raise WorldActionError(f"這裡沒有物件 {action.object}")
    status = object_status(FieldCtx(library=library, world=world, map=found, now=now), char, spot)
    if not status.shown:
        raise WorldActionError(f"這裡沒有物件 {action.object}")
    if not _near((pos.x, pos.y), spot.at, 1):
        raise WorldActionError("要走到物件旁邊才能用")
    if status.use == "note":
        raise WorldActionError("這個物件只能看")
    if status.problem_zh is not None:
        raise WorldActionError(status.problem_zh)
    used = FieldObjectUsedEvent(map=found.id, object=spot.id, use=status.use)
    if status.use == "event":
        trigger = _object_trigger(library, world, char, _skeleton_id(spot), now)
        char = _with_use(char, ObjectUse(map=found.id, object=spot.id, day=day_of(library, now)))
        char = char.model_copy(update={"pending_event": trigger})
        return char, (used, EventTriggeredEvent(trigger=trigger))
    target = world_map_of(library, char.region).location_by_id()[char.location]
    if target.level_max is None:
        raise WorldActionError("這裡沒有可以挑戰的對手")
    result, char = make_encounter(library, world, char, target, now)
    result = result.model_copy(update={"from_location": char.location})
    char = char.model_copy(update={"pending_encounter": result})
    return char, (used, EncounterEvent(result=result))
