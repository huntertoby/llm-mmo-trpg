"""地圖上的東西（Phase 6C-5；21.6、21.9 第 8～12 條、21.10 第 6、9 條）。

隱藏入口的感知、事件「！」、營火、情境物件、潛行、新手固定戰在任務完成後不再出現，與三個重播測試。
用正式的實地地圖；除了潛行的測試，所有 ``spawns`` 都拿掉（不讓巡邏擋路）。
"""

from __future__ import annotations

import dataclasses
from collections import deque
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.api.world_field_view import field_view
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    CampAction,
    EncounterEvent,
    EventTriggeredEvent,
    LocationRevealedEvent,
    PerceptionCheckEvent,
    WorldAction,
)
from trpg.world.battle import prepare_battle, with_cleared
from trpg.world.errors import WorldActionError
from trpg.world.field import FieldCtx, arrival, field_grid, field_map, placed
from trpg.world.field_actions import (
    EventMarkedEvent,
    FieldObjectUsedEvent,
    SneakAction,
    SneakStartedEvent,
    UseFieldObjectAction,
    WalkAction,
    WalkedEvent,
)
from trpg.world.field_enemies import field_enemies, sight_range
from trpg.world.field_things import object_status
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, loads_char, read_log
from trpg.world.state import CharacterState, FieldPos, QuestState, WorldState
from trpg.world.step import camp_problem, new_character, world_step

type XY = tuple[int, int]

DAY = 86_400


def _calm(library: ContentLibrary, *, keep_spawns: bool = False, **rules: Any) -> ContentLibrary:
    calm = with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0}, **rules)
    if keep_spawns:
        return calm
    fields = {k: m.model_copy(update={"spawns": ()}) for k, m in calm.field_maps.items()}
    return dataclasses.replace(calm, field_maps=fields)


def _eventful(library: ContentLibrary) -> ContentLibrary:
    """每次進入地圖都觸發事件。"""
    content = library.world_event_content
    assert content.rules is not None
    frequency = content.rules.frequency.model_copy(
        update={"per_step_permille": 1000, "max_permille": 1000}
    )
    rules = content.rules.model_copy(update={"frequency": frequency})
    return dataclasses.replace(
        library, world_event_content=dataclasses.replace(content, rules=rules)
    )


@pytest.fixture(scope="module")
def calm(field_library: ContentLibrary) -> ContentLibrary:
    return _calm(field_library)


@pytest.fixture(scope="module")
def sharp(field_library: ContentLibrary) -> ContentLibrary:
    """感知必定成功（DC 很低）。"""
    return _calm(field_library, perception={"dc_base": -40})


@pytest.fixture(scope="module")
def blind(field_library: ContentLibrary) -> ContentLibrary:
    """感知必定失敗（DC 很高）。"""
    return _calm(field_library, perception={"dc_base": 100})


@pytest.fixture(scope="module")
def eventful(field_library: ContentLibrary) -> ContentLibrary:
    return _eventful(_calm(field_library))


def _char(
    library: ContentLibrary, location: str, at: XY | None = None, **updates: Any
) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    region = updates.pop("region", "cloud_ridge")
    char = char.model_copy(update={"region": region, "location": location, "field": None})
    char = placed(library, char)
    if at is not None:
        assert char.field is not None
        char = char.model_copy(
            update={"field": char.field.model_copy(update={"x": at[0], "y": at[1]})}
        )
    return char.model_copy(update=updates) if updates else char


def _map(library: ContentLibrary, char: CharacterState) -> FieldMapDef:
    assert char.field is not None
    found = field_map(library, char.field.map)
    assert found is not None
    return found


def _path(library: ContentLibrary, char: CharacterState, goal: XY) -> tuple[XY, ...]:
    """四方向 BFS（不經過出口、門、傳送石；鄰格順序固定）。"""
    found = _map(library, char)
    grid = field_grid(library, char, found)
    climb = library.ruleset.core.max_climb_height
    portals = {c for e in found.exits for c in e.at} | {d.at for d in found.doors}
    portals |= {s.at for s in found.teleport_stones}
    assert char.field is not None
    start = (char.field.x, char.field.y)
    prev: dict[XY, XY | None] = {start: None}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here == goal:
            break
        if here != start and here in portals:
            continue
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nxt = (here[0] + dx, here[1] + dy)
            if nxt not in prev and grid.can_step(here, nxt, climb):
                prev[nxt] = here
                queue.append(nxt)
    assert goal in prev, f"走不到 {goal}"
    out: list[XY] = []
    cur: XY | None = goal
    while cur is not None and cur != start:
        out.append(cur)
        cur = prev[cur]
    return tuple(reversed(out))


def _step(
    library: ContentLibrary,
    char: CharacterState,
    action: WorldAction,
    now: int = NOON,
    world: WorldState | None = None,
) -> tuple[CharacterState, list[object]]:
    result = world_step(library, world or make_world(), char, action, now)
    return result.char, list(result.events)


def _of[T](kind: type[T], events: list[object]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


def _dist(a: XY, b: XY) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------------------
# 1. 隱藏入口：3 格內自動感知
# ---------------------------------------------------------------------------

PERCEIVE = 3
"""規則 ``field.perceive_range``（6C-R2 從程式常數搬到規則；21.10 第 17 條「3 格內」）。"""

CRACK: XY = (6, 1)
"""北坡獵場上往鶴歸崖的裂縫（``crane_cliff_crack``）。"""


def _near_crack(library: ContentLibrary, char: CharacterState) -> tuple[XY, ...]:
    """從目前位置走到裂縫 3 格內的最短路徑。"""
    found = _map(library, char)
    grid = field_grid(library, char, found)
    cells = ((x, y) for y in range(found.height) for x in range(found.width))
    goals = sorted(
        c for c in cells if grid.standable(c) and _dist(c, CRACK) <= PERCEIVE and c != CRACK
    )
    paths = [_path(library, char, g) for g in goals if _reachable(library, char, g)]
    return min(paths, key=len)


def _reachable(library: ContentLibrary, char: CharacterState, goal: XY) -> bool:
    try:
        _path(library, char, goal)
    except AssertionError:
        return False
    return True


def test_walking_near_hidden_door_reveals_it(sharp: ContentLibrary) -> None:
    char = _char(sharp, "north_slope")
    path = _near_crack(sharp, char)
    assert all(_dist(c, CRACK) > PERCEIVE for c in path[:-1])  # 最後一格才進入 3 格
    before = field_view(sharp, char)
    assert before is not None and all(d.id != "crane_cliff_crack" for d in before.doors)
    moved, events = _step(sharp, char, WalkAction(path=path))
    checks = _of(PerceptionCheckEvent, events)
    assert [c.location for c in checks] == ["crane_cliff"] and checks[0].success
    assert [e.location for e in _of(LocationRevealedEvent, events)] == ["crane_cliff"]
    assert moved.has_revealed("cloud_ridge", "crane_cliff")
    after = field_view(sharp, moved)
    assert after is not None and any(d.id == "crane_cliff_crack" for d in after.doors)
    tile = next(t for t in after.tiles if (t.x, t.y) == CRACK)
    assert tile.walkable  # 門可站
    assert _of(WalkedEvent, events)[0].stopped == "end"


def test_failed_perception_waits_until_tomorrow(blind: ContentLibrary) -> None:
    char = _char(blind, "north_slope")
    path = _near_crack(blind, char)
    moved, events = _step(blind, char, WalkAction(path=path))
    check = _of(PerceptionCheckEvent, events)
    assert len(check) == 1 and not check[0].success
    assert not moved.has_revealed("cloud_ridge", "crane_cliff")
    # 同一天在 3 格內來回走：不再判定
    assert moved.field is not None
    here = (moved.field.x, moved.field.y)
    back = path[-2] if len(path) > 1 else (char.field.x, char.field.y)  # type: ignore[union-attr]
    again, events = _step(blind, moved, WalkAction(path=(back, here)), NOON + 60)
    assert _of(PerceptionCheckEvent, events) == []
    # 隔天（6 點刷新）再判定一次
    _tomorrow, events = _step(blind, again, WalkAction(path=(back, here)), NOON + DAY)
    assert len(_of(PerceptionCheckEvent, events)) == 1


def test_far_from_door_never_checks(sharp: ContentLibrary) -> None:
    char = _char(sharp, "north_slope")
    assert char.field is not None
    start = (char.field.x, char.field.y)
    found = _map(sharp, char)
    grid = field_grid(sharp, char, found)
    step = next(
        (start[0] + dx, start[1] + dy)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        if grid.can_step(start, (start[0] + dx, start[1] + dy), 1)
    )
    assert _dist(step, CRACK) > PERCEIVE
    _moved, events = _step(sharp, char, WalkAction(path=(step,)))
    assert _of(PerceptionCheckEvent, events) == []


def test_arrival_by_exit_no_longer_checks_neighbours(sharp: ContentLibrary) -> None:
    """有實地地圖的地點：抵達時不再對相鄰的隱藏地點判定（21.9 第 10 條），要走到入口 3 格內。"""
    char = _char(sharp, "winter_lake")
    found = _map(sharp, char)
    exit_ = next(e for e in found.exits if e.to == "north_slope")
    inside = arrival(sharp, char, found, exit_.id, 0)
    char = char.model_copy(update={"field": inside})
    moved, events = _step(sharp, char, WalkAction(path=(exit_.at[0],)))
    assert moved.location == "north_slope"
    assert moved.field is not None
    assert _dist((moved.field.x, moved.field.y), CRACK) > PERCEIVE
    assert _of(PerceptionCheckEvent, events) == []
    assert not moved.has_revealed("cloud_ridge", "crane_cliff")


# ---------------------------------------------------------------------------
# 2. 事件「！」
# ---------------------------------------------------------------------------


def _enter_ferry_steps(
    library: ContentLibrary,
) -> tuple[CharacterState, CharacterState, list[object]]:
    """站在霧渡鎮往渡口石階的出口旁，踩上出口。"""
    char = _char(library, "mist_ferry")
    town = _map(library, char)
    exit_ = next(e for e in town.exits if e.to == "ferry_steps")
    char = char.model_copy(update={"field": arrival(library, char, town, exit_.id, 0)})
    moved, events = _step(library, char, WalkAction(path=(exit_.at[0],)))
    assert moved.location == "ferry_steps"
    return char, moved, events


def test_event_is_placed_on_a_spot(eventful: ContentLibrary) -> None:
    _start, moved, events = _enter_ferry_steps(eventful)
    assert moved.pending_event is None  # 不直接開卡
    mark = moved.field_event
    assert mark is not None and mark.map == "ferry_steps"
    spots = {s.id: s.at for s in _map(eventful, moved).event_spots}
    assert (mark.x, mark.y) == spots[mark.spot]
    if mark.trigger.skeleton in spots:  # 優先放在同名的事件點
        assert mark.spot == mark.trigger.skeleton
    assert _of(EventTriggeredEvent, events) == []
    marked = _of(EventMarkedEvent, events)
    assert len(marked) == 1 and (marked[0].x, marked[0].y) == (mark.x, mark.y)
    view = field_view(eventful, moved)
    assert view is not None and view.event_mark is not None
    assert (view.event_mark.x, view.event_mark.y) == (mark.x, mark.y)


def test_touching_the_mark_opens_the_card_once(eventful: ContentLibrary) -> None:
    _start, moved, _ = _enter_ferry_steps(eventful)
    mark = moved.field_event
    assert mark is not None
    path = _path(eventful, moved, (mark.x, mark.y))
    opened, events = _step(eventful, moved, WalkAction(path=path), NOON + 30)
    walked = _of(WalkedEvent, events)[0]
    assert walked.stopped == "event"
    assert _dist((walked.x, walked.y), (mark.x, mark.y)) <= 1  # 相鄰就停
    assert opened.field_event is None
    assert opened.pending_event is not None
    assert opened.pending_event.skeleton == mark.trigger.skeleton
    assert opened.pending_event.at == NOON + 30
    assert len(_of(EventTriggeredEvent, events)) == 1
    # 同一趟不會再開：再走回來也不停
    view = field_view(eventful, opened)
    assert view is not None and view.event_mark is None


def test_no_spots_opens_the_card_right_away(eventful: ContentLibrary) -> None:
    lib = dataclasses.replace(
        eventful,
        field_maps={
            k: m.model_copy(update={"event_spots": ()}) for k, m in eventful.field_maps.items()
        },
    )
    _start, moved, events = _enter_ferry_steps(lib)
    assert moved.field_event is None and moved.pending_event is not None
    assert len(_of(EventTriggeredEvent, events)) == 1


def test_leaving_drops_the_mark(calm: ContentLibrary, eventful: ContentLibrary) -> None:
    _start, moved, _ = _enter_ferry_steps(eventful)
    assert moved.field_event is not None
    found = _map(calm, moved)
    back = next(e for e in found.exits if e.to == "mist_ferry")
    gone, _ = _step(calm, moved, WalkAction(path=_path(calm, moved, back.at[0])))
    assert gone.location == "mist_ferry" and gone.field_event is None
    # 回去時又擲到事件：新的「！」屬於新地點
    again, _ = _step(eventful, moved, WalkAction(path=_path(eventful, moved, back.at[0])))
    assert again.field_event is not None and again.field_event.trigger.location == "mist_ferry"


def test_town_events_are_placed_too(eventful: ContentLibrary) -> None:
    """城鎮照現行擲事件（非戰鬥），一樣放在事件點上（含室內圖的事件點）。"""
    char = _char(eventful, "ferry_steps")
    found = _map(eventful, char)
    exit_ = next(e for e in found.exits if e.to == "mist_ferry")
    char = char.model_copy(update={"field": arrival(eventful, char, found, exit_.id, 0)})
    moved, _ = _step(eventful, char, WalkAction(path=(exit_.at[0],)))
    assert moved.location == "mist_ferry"
    assert moved.field_event is not None
    assert moved.field_event.map == "mist_ferry_tavern"  # 骨架同名的事件點在酒館裡
    assert moved.field_event.spot == moved.field_event.trigger.skeleton


# ---------------------------------------------------------------------------
# 3. 營火
# ---------------------------------------------------------------------------

LAKE_FIRE: XY = (3, 9)


def test_camp_campfire_needs_the_clear(calm: ContentLibrary) -> None:
    """6C-5b（21.10 第 13 條）：冬湖是營地，要先清空才能用帳篷旁的營火。"""
    world = make_world()
    off = _char(calm, "winter_lake", (11, 15))
    assert camp_problem(calm, world, off, NOON) is not None  # 營地敵人還在
    on = _char(calm, "winter_lake", LAKE_FIRE)
    assert camp_problem(calm, world, on, NOON) == "冬湖的敵人還在，要先清空才能紮營"
    world = with_cleared(world, "cloud_ridge", "winter_lake", NOON + 600)
    assert camp_problem(calm, world, on, NOON) is None
    camped, _ = _step(calm, on, CampAction(), world=world)
    assert camped.supplies == on.supplies - 1
    assert camped.camped_at is not None and camped.camped_at.location == "winter_lake"


def test_campfire_does_not_open_towns_or_boss(calm: ContentLibrary) -> None:
    town = _char(calm, "mist_ferry")
    assert camp_problem(calm, make_world(), town, NOON) == "城鎮裡直接休息，不用紮營"


# ---------------------------------------------------------------------------
# 4. 情境物件
# ---------------------------------------------------------------------------


def _beside(library: ContentLibrary, char: CharacterState, at: XY) -> CharacterState:
    found = _map(library, char)
    grid = field_grid(library, char, found)
    cell = next(
        (at[0] + dx, at[1] + dy)
        for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0))
        if grid.standable((at[0] + dx, at[1] + dy))
    )
    assert char.field is not None
    return char.model_copy(
        update={"field": char.field.model_copy(update={"x": cell[0], "y": cell[1]})}
    )


def _ashen(library: ContentLibrary, location: str, **updates: Any) -> CharacterState:
    return _char(
        library,
        location,
        region="ashen_waste",
        visited_towns=("ashen_waste", "cloud_ridge"),
        **updates,
    )


def test_altar_opens_its_event_once_a_day(calm: ContentLibrary) -> None:
    char = _beside(calm, _ashen(calm, "horned_altar"), (14, 8))
    used, events = _step(calm, char, UseFieldObjectAction(object="horned_fire_altar"))
    assert _of(FieldObjectUsedEvent, events)[0].use == "event"
    assert used.pending_event is not None and used.pending_event.skeleton == "noon_altar"
    with pytest.raises(WorldActionError, match="先處理眼前的事件"):
        _step(calm, used, UseFieldObjectAction(object="horned_fire_altar"))
    cleared = used.model_copy(update={"pending_event": None})
    with pytest.raises(WorldActionError, match="今天已經看過"):
        _step(calm, cleared, UseFieldObjectAction(object="horned_fire_altar"), NOON + 60)
    again, _ = _step(calm, cleared, UseFieldObjectAction(object="horned_fire_altar"), NOON + DAY)
    assert again.pending_event is not None


@pytest.mark.parametrize(
    ("location", "object_id", "message"),
    [
        ("ash_well_village", "ash_well", "只能看"),  # 守點目標：只有說明卡
        ("ruined_fortress", "pit_lava_seal", "只能看"),  # 旗標沒開：鎖住
        ("ruined_fortress", "no_such_thing", "沒有物件"),
    ],
)
def test_objects_that_only_show_a_card(
    calm: ContentLibrary, location: str, object_id: str, message: str
) -> None:
    char = _ashen(calm, location)
    found = _map(calm, char)
    spot = next((s for s in found.situation_objects if s.id == object_id), None)
    if spot is not None:
        char = _beside(calm, char, spot.at)
    with pytest.raises(WorldActionError, match=message):
        _step(calm, char, UseFieldObjectAction(object=object_id))


def test_object_needs_to_be_beside(calm: ContentLibrary) -> None:
    char = _ashen(calm, "horned_altar")
    with pytest.raises(WorldActionError, match="旁邊"):
        _step(calm, char, UseFieldObjectAction(object="horned_fire_altar"))


def test_lava_seal_card_follows_the_world_flag(calm: ContentLibrary) -> None:
    char = _ashen(calm, "ruined_fortress")
    found = _map(calm, char)
    spot = next(s for s in found.situation_objects if s.id == "pit_lava_seal")
    ctx = FieldCtx(library=calm, world=make_world(), map=found, now=NOON)
    closed = object_status(ctx, char, spot)
    opened = object_status(
        FieldCtx(library=calm, world=make_world(flags=("heart_pit_open",)), map=found, now=NOON),
        char,
        spot,
    )
    assert closed.use == "note" and "還過不去" in closed.note_zh
    assert "冷卻" in opened.note_zh


def test_secret_door_needs_the_thread(calm: ContentLibrary) -> None:
    char = _char(calm, "cliff_gang_fort")
    found = _map(calm, char)
    spot = next(s for s in found.situation_objects if s.id == "gang_fort_secret_door")
    ctx = FieldCtx(library=calm, world=make_world(), map=found, now=NOON)
    assert not object_status(ctx, char, spot).shown
    view = field_view(calm, char, world=make_world(), now=NOON)
    assert view is not None and all(o.id != "gang_fort_secret_door" for o in view.situation_objects)


def test_boss_gate_starts_the_boss_fight(calm: ContentLibrary) -> None:
    char = _beside(calm, _char(calm, "cloud_summit"), (6, 1))
    fought, events = _step(calm, char, UseFieldObjectAction(object="summit_gate"))
    assert fought.pending_encounter is not None
    assert fought.pending_encounter.location == "cloud_summit"
    assert fought.pending_encounter.from_location == "cloud_summit"
    assert len(_of(EncounterEvent, events)) == 1
    prepared = prepare_battle(calm, fought)  # Boss 戰照舊用 Boss 地圖（沒有接觸點，不切 12×12）
    assert prepared.field_cut is None


# ---------------------------------------------------------------------------
# 5. 潛行
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def guarded(field_library: ContentLibrary) -> ContentLibrary:
    return _calm(field_library, keep_spawns=True)


def test_sneak_costs_supply_and_halves_sight(guarded: ContentLibrary) -> None:
    world = make_world()
    char = _char(guarded, "cliff_gang_fort")
    normal = field_enemies(guarded, world, char, NOON)
    assert normal
    sneaky, events = _step(guarded, char, SneakAction(), world=world)
    assert sneaky.sneaking and sneaky.supplies == char.supplies - 1
    assert _of(SneakStartedEvent, events)[0].supplies_left == sneaky.supplies
    assert sight_range(guarded, sneaky) == sight_range(guarded, char) // 2 == 2
    halved = field_enemies(guarded, world, sneaky, NOON)
    for a, b in zip(normal, halved, strict=True):
        assert set(b.sight) <= set(a.sight)
        assert all(_dist(c, b.xy) <= 2 for c in b.sight)
    with pytest.raises(WorldActionError, match="已經在潛行"):
        _step(guarded, sneaky, SneakAction(), world=world)


@pytest.mark.parametrize(
    ("location", "updates", "message"),
    [
        ("mist_ferry", {}, "城鎮"),
        ("cliff_gang_fort", {"supplies": 0}, "補給不足"),
    ],
)
def test_sneak_problems(
    guarded: ContentLibrary, location: str, updates: dict[str, Any], message: str
) -> None:
    char = _char(guarded, location, **updates)
    with pytest.raises(WorldActionError, match=message):
        _step(guarded, char, SneakAction())


def test_sneak_ends_on_the_next_map(calm: ContentLibrary) -> None:
    char = _char(calm, "mist_ferry")
    town = _map(calm, char)
    exit_ = next(e for e in town.exits if e.to == "ferry_steps")
    char = char.model_copy(update={"field": arrival(calm, char, town, exit_.id, 0)})
    moved, _ = _step(calm, char, WalkAction(path=(exit_.at[0],)))
    sneaky, _ = _step(calm, moved, SneakAction())
    found = _map(calm, sneaky)
    back = next(e for e in found.exits if e.to == "mist_ferry")
    sneaky = sneaky.model_copy(update={"field": arrival(calm, sneaky, found, back.id, 0)})
    home, _ = _step(calm, sneaky, WalkAction(path=(back.at[0],)))
    assert home.location == "mist_ferry" and not home.sneaking


# ---------------------------------------------------------------------------
# 6. 新手固定戰：任務完成後不再出現
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "group"),
    [
        ("ferry_steps", "bandit_raiders"),
        ("bamboo_path", "mist_wolf_pack"),
        ("rain_terraces", "terrace_clash"),
    ],
)
@pytest.mark.parametrize("done", [False, True])
def test_starter_fights_vanish_after_the_quest(
    guarded: ContentLibrary, location: str, group: str, done: bool
) -> None:
    quest = QuestState(
        quest="starter_ferry", steps_done=3 if done else 1, done=done, started_at=NOON
    )
    char = _char(guarded, location, quests=(quest,))
    groups = {e.spawn.group for e in field_enemies(guarded, make_world(), char, NOON)}
    assert (group in groups) is not done


# ---------------------------------------------------------------------------
# 存檔與重播
# ---------------------------------------------------------------------------


def _play(
    library: ContentLibrary, start: CharacterState, actions: list[WorldAction]
) -> tuple[CharacterState, list[WorldLogEntry]]:
    world, char = make_world(), start
    entries: list[WorldLogEntry] = []
    for seq, action in enumerate(actions, start=1):
        result = world_step(library, world, char, action, NOON + seq)
        world, char = result.world, result.char
        entries.append(WorldLogEntry(seq=seq, now=NOON + seq, character_id="alice", action=action))
    return char, entries


def _replays(
    library: ContentLibrary,
    start: CharacterState,
    entries: list[WorldLogEntry],
    live: CharacterState,
) -> None:
    log = read_log(dumps_log(entries))
    first = replay(library, make_world(), {"alice": start}, log.entries)
    second = replay(library, make_world(), {"alice": start}, log.entries)
    assert dumps_char(first.characters["alice"]) == dumps_char(live)
    assert dumps_char(second.characters["alice"]) == dumps_char(live)
    assert first.events == second.events


def test_replay_perceive_and_enter_hidden_door(sharp: ContentLibrary) -> None:
    start = _char(sharp, "north_slope")
    near = _near_crack(sharp, start)
    revealed, _ = _step(sharp, start, WalkAction(path=near), NOON + 1)
    to_door = _path(sharp, revealed, CRACK)
    live, entries = _play(sharp, start, [WalkAction(path=near), WalkAction(path=to_door)])
    assert live.location == "crane_cliff"
    _replays(sharp, start, entries, live)


def test_replay_event_mark_opens_card(eventful: ContentLibrary) -> None:
    start, moved, _ = _enter_ferry_steps(eventful)
    town = _map(eventful, start)
    exit_ = next(e for e in town.exits if e.to == "ferry_steps")
    mark = moved.field_event
    assert mark is not None
    actions: list[WorldAction] = [WalkAction(path=(exit_.at[0],))]
    entered, _ = _play(eventful, start, actions)
    assert entered.field_event is not None
    actions.append(
        WalkAction(path=_path(eventful, entered, (entered.field_event.x, entered.field_event.y)))
    )
    live, entries = _play(eventful, start, actions)
    assert live.pending_event is not None and live.field_event is None
    _replays(eventful, start, entries, live)


def test_replay_sneak_shrinks_sight(guarded: ContentLibrary) -> None:
    start = _char(guarded, "cliff_gang_fort")
    live, entries = _play(guarded, start, [SneakAction()])
    assert live.sneaking
    enemies = field_enemies(guarded, make_world(), live, NOON + 1)
    assert all(_dist(c, e.xy) <= 2 for e in enemies for c in e.sight)
    _replays(guarded, start, entries, live)


def test_char_save_round_trip_and_old_format(eventful: ContentLibrary) -> None:
    _start, moved, _ = _enter_ferry_steps(eventful)
    sneaky = moved.model_copy(update={"sneaking": True})
    assert loads_char(dumps_char(sneaky)) == sneaky
    data = dumps_char(_char(eventful, "mist_ferry")).replace("trpg-char/14", "trpg-char/4")
    old = loads_char(data)
    assert old.format == "trpg-char/14" and old.field_event is None and not old.sneaking
    _ = FieldPos  # 匯入給型別用
