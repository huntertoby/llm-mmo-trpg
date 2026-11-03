"""主城的抵達與安全區、荒原首次走過才亮起、大世界圖的三種狀態（Phase 6D-5；21.1、21.9）。"""

from __future__ import annotations

import dataclasses
from collections import deque
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.api.world_presenter import world_view
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    CampAction,
    LoadoutAction,
    RestAction,
    TavernAction,
    TeleportAction,
    TravelAction,
    WorldAction,
)
from trpg.world.atlas import atlas_regions, capital_stone, region_lit, unlocked_stones
from trpg.world.battle import _lost
from trpg.world.errors import WorldActionError
from trpg.world.field import field_grid, field_map
from trpg.world.field_actions import SneakAction, UseTeleportStoneAction, WalkAction
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, loads_char, read_log
from trpg.world.state import CharacterState, FieldPos, LocationRef, WorldState
from trpg.world.step import new_character, world_step

OPEN = ("ashen_waste_open",)
FERRY_START = FieldPos(map="ashen_ferry", x=16, y=2)
"""雲嶺「往灰燼荒原的渡口」的 ``entry``。"""


@pytest.fixture(scope="module")
def calm(field_library: ContentLibrary) -> ContentLibrary:
    """不會遇敵、地圖上沒有駐守的完整內容庫（走路測試不被敵人打斷）。"""
    lib = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    maps = {k: m.model_copy(update={"spawns": ()}) for k, m in lib.field_maps.items()}
    return dataclasses.replace(lib, field_maps=maps)


def _char(library: ContentLibrary, **updates: Any) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    return char.model_copy(update=updates) if updates else char


def _step(
    library: ContentLibrary,
    char: CharacterState,
    action: WorldAction,
    world: WorldState | None = None,
) -> tuple[WorldState, CharacterState, list[Any]]:
    result = world_step(library, world or make_world(), char, action, NOON)
    return result.world, result.char, list(result.events)


def _in_capital(library: ContentLibrary) -> CharacterState:
    _, char, _ = _step(library, _char(library), UseTeleportStoneAction(to="stone_capital"))
    return char


def _path(
    library: ContentLibrary, char: CharacterState, goal: tuple[int, int]
) -> tuple[tuple[int, int], ...]:
    """BFS 找一條到 ``goal`` 的路（不經過其他出口、門、傳送石）。"""
    assert char.field is not None
    found = field_map(library, char.field.map)
    assert found is not None
    grid = field_grid(library, char, found)
    portals = {c for e in found.exits for c in e.at} | {d.at for d in found.doors}
    portals |= {s.at for s in found.teleport_stones}
    climb = library.ruleset.core.max_climb_height
    start = (char.field.x, char.field.y)
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        if cell in portals and cell != start:
            continue
        for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
            nxt = (cell[0] + dx, cell[1] + dy)
            if nxt not in prev and grid.can_step(cell, nxt, climb):
                prev[nxt] = cell
                queue.append(nxt)
    assert goal in prev, f"走不到 {goal}"
    out: list[tuple[int, int]] = []
    at: tuple[int, int] | None = goal
    while at is not None and at != start:
        out.append(at)
        at = prev[at]
    return tuple(reversed(out))


def _at_ferry(library: ContentLibrary) -> CharacterState:
    return _char(library, location="ashen_ferry", field=FERRY_START)


# ---------------------------------------------------------------------------
# 主城的抵達
# ---------------------------------------------------------------------------


def test_capital_stone_is_unlocked_from_the_start(calm: ContentLibrary) -> None:
    char = _char(calm)
    assert capital_stone(calm) == "stone_capital"
    assert "stone_capital" not in char.teleport_stones  # 存檔不寫，規則上一開始就解鎖
    assert "stone_capital" in unlocked_stones(calm, char)


@pytest.mark.parametrize(
    ("name", "updates", "action"),
    [
        ("城鎮→主城傳送石", {}, UseTeleportStoneAction(to="stone_capital")),
        ("城鎮→主城（城鎮傳送）", {}, TeleportAction(region="capital")),
        (
            "野外傳送石→主城",
            {
                "location": "rain_terraces",
                "field": FieldPos(map="rain_terraces", x=17, y=6),
                "teleport_stones": ("stone_rain_terraces",),
            },
            UseTeleportStoneAction(to="stone_capital"),
        ),
        (
            "野外傳送石→主城（城鎮傳送）",
            {
                "location": "rain_terraces",
                "field": FieldPos(map="rain_terraces", x=17, y=6),
                "teleport_stones": ("stone_rain_terraces",),
            },
            TeleportAction(region="capital"),
        ),
    ],
)
def test_teleport_to_capital(
    calm: ContentLibrary, name: str, updates: dict[str, Any], action: WorldAction
) -> None:
    char = _char(calm, **updates)
    _, moved, _ = _step(calm, char, action)
    assert (moved.region, moved.location) == ("capital", "capital"), name
    assert "capital" not in moved.visited_towns
    assert LocationRef(region="capital", location="capital") in moved.visited_locations


def test_capital_needs_a_town_or_stone(calm: ContentLibrary) -> None:
    char = _char(calm, location="rain_terraces", field=FieldPos(map="rain_terraces", x=3, y=3))
    for action in (UseTeleportStoneAction(to="stone_capital"), TeleportAction(region="capital")):
        with pytest.raises(WorldActionError, match=r"傳送石|城鎮"):
            _step(calm, char, action)


def test_leave_capital(calm: ContentLibrary) -> None:
    char = _in_capital(calm)
    assert char.field == FieldPos(map="capital", x=15, y=11)
    _, home, _ = _step(calm, char, TeleportAction(region="cloud_ridge"))
    assert (home.region, home.location) == ("cloud_ridge", "mist_ferry")
    stoned = char.model_copy(update={"teleport_stones": ("stone_rain_terraces",)})
    _, there, _ = _step(calm, stoned, UseTeleportStoneAction(to="stone_rain_terraces"))
    assert (there.region, there.location) == ("cloud_ridge", "rain_terraces")
    with pytest.raises(WorldActionError, match="還沒去過"):
        _step(calm, char, TeleportAction(region="ashen_waste"))


# ---------------------------------------------------------------------------
# 安全區
# ---------------------------------------------------------------------------


def _ok(library: ContentLibrary, char: CharacterState, action: WorldAction) -> list[str]:
    return [e.kind for e in _step(library, char, action)[2]]


@pytest.mark.parametrize(
    ("action", "allowed", "message"),
    [
        (RestAction(), True, None),  # 整備亭與酒館直接休息（照現行城鎮：城裡都能休息）
        (TavernAction(), True, None),
        (CampAction(), False, "不用紮營"),
        (SneakAction(), False, "不用潛行"),
        (TravelAction(to="mist_ferry"), False, "實地地圖"),
        (TeleportAction(region="capital"), False, "已經在"),
    ],
)
def test_safe_zone_rules(
    calm: ContentLibrary, action: WorldAction, allowed: bool, message: str | None
) -> None:
    char = _in_capital(calm).model_copy(update={"hp": 1})
    if allowed:
        assert _ok(calm, char, action)
    else:
        with pytest.raises(WorldActionError, match=message):
            _step(calm, char, action)


def test_capital_loadout(calm: ContentLibrary) -> None:
    char = _in_capital(calm)
    assert "loadout_changed" in _ok(calm, char, LoadoutAction(skills=tuple(char.hero.skills)))


def test_walking_in_capital_costs_nothing(calm: ContentLibrary) -> None:
    """走城裡、進出室內：不擲骰、不推進事件步數、不花補給、沒有遭遇（21.10 第 2、5 條）。"""
    char = _in_capital(calm)
    walked = char
    for goal in ((15, 5), (15, 4)):  # 走到導師殿的門
        _, walked, _ = _step(calm, walked, WalkAction(path=_path(calm, walked, goal)))
    assert walked.field is not None and walked.field.map == "capital_mentor_hall"
    assert walked.pending_encounter is None and walked.pending_event is None
    assert walked.field_event is None
    assert walked.rng_counters == char.rng_counters
    assert walked.event_steps == char.event_steps
    assert walked.supplies == char.supplies


def test_wipe_never_returns_to_capital(calm: ContentLibrary) -> None:
    """野外全滅回本區的小鎮（9.6.9），去過主城也一樣。"""
    char = _char(
        calm,
        location="rain_terraces",
        visited_locations=(
            LocationRef(region="capital", location="capital"),
            LocationRef(region="cloud_ridge", location="mist_ferry"),
        ),
    )
    lost, _ = _lost(calm, char, char.mana)
    assert (lost.region, lost.location) == ("cloud_ridge", "mist_ferry")


# ---------------------------------------------------------------------------
# 荒原：第一次要親自走過渡口
# ---------------------------------------------------------------------------


def _cross(library: ContentLibrary, world: WorldState) -> tuple[CharacterState, list[Any]]:
    char = _at_ferry(library)
    _, moved, events = _step(library, char, WalkAction(path=_path(library, char, (0, 5))), world)
    return moved, events


def test_walk_across_the_ferry_lights_ashen_waste(calm: ContentLibrary) -> None:
    world = make_world(flags=OPEN)
    char = _at_ferry(calm)
    assert not region_lit(char, "ashen_waste")
    moved, events = _cross(calm, world)
    assert (moved.region, moved.location) == ("ashen_waste", "ash_ferry")
    assert moved.field is not None and moved.field.map == "ash_ferry"
    assert region_lit(moved, "ashen_waste")
    assert "ashen_waste" not in moved.visited_towns  # 還沒到過餘燼集，但已經能傳送
    assert any(e.kind == "field_entered" for e in events)
    assert moved.rng_counters == char.rng_counters  # 和原本渡口的傳送一樣不擲骰
    # 渡口兩端都不能直接傳送（要走）；回到雲嶺的城鎮之後，可以直接傳送到餘燼集
    with pytest.raises(WorldActionError, match="要走到盡頭的出口過去"):
        _step(calm, moved, TeleportAction(region="cloud_ridge"), world)
    home = moved.model_copy(
        update={"region": "cloud_ridge", "location": "mist_ferry", "field": None}
    )
    _, ember, _ = _step(calm, home, TeleportAction(region="ashen_waste"), world)
    assert (ember.region, ember.location) == ("ashen_waste", "ember_market")


def test_ferry_gate_cannot_teleport_across(calm: ContentLibrary) -> None:
    """畫了跨區出口的渡口不能直接傳送過去（不然就不用走過渡口）。"""
    with pytest.raises(WorldActionError, match="要走到盡頭的出口過去"):
        _step(calm, _at_ferry(calm), TeleportAction(region="ashen_waste"), make_world(flags=OPEN))


def test_town_teleport_to_ashen_needs_the_walk(calm: ContentLibrary) -> None:
    with pytest.raises(WorldActionError, match="還沒去過"):
        _step(calm, _char(calm), TeleportAction(region="ashen_waste"), make_world(flags=OPEN))


def test_ferry_crossing_needs_the_world_event(calm: ContentLibrary) -> None:
    with pytest.raises(WorldActionError, match="還沒開放"):
        _cross(calm, make_world())


# ---------------------------------------------------------------------------
# 大世界圖的三種狀態（石碑也用這份）
# ---------------------------------------------------------------------------


def _states(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> dict[str, tuple[str, str | None]]:
    return {s.region: (s.status, s.condition_zh) for s in atlas_regions(library, world, char)}


LATER = ("later", "之後的賽季")


@pytest.mark.parametrize(
    ("case", "flags", "visited", "ashen"),
    [
        ("世界事件還沒結束", (), (), ("locked", "世界事件：霧潮入侵")),
        ("開放了、還沒走過", OPEN, (), ("locked", "先走過雲嶺的「往灰燼荒原的渡口」")),
        ("走過渡口", OPEN, (("ashen_waste", "ash_ferry"),), ("open", None)),
    ],
)
def test_atlas_states(
    calm: ContentLibrary,
    case: str,
    flags: tuple[str, ...],
    visited: tuple[tuple[str, str], ...],
    ashen: tuple[str, str | None],
) -> None:
    refs = [LocationRef(region=r, location=loc) for r, loc in visited]
    char = _char(calm)
    refs = sorted({*char.visited_locations, *refs}, key=LocationRef.key)
    char = char.model_copy(update={"visited_locations": tuple(refs)})
    states = _states(calm, make_world(flags=flags), char)
    assert list(states) == [
        "cloud_ridge",
        "crystal_crown",
        "arcane_hub",
        "ashen_waste",
        "frost_tide",
    ]
    assert states["cloud_ridge"] == ("open", None), case
    assert states["ashen_waste"] == ashen, case
    for later in ("crystal_crown", "arcane_hub", "frost_tide"):
        assert states[later] == LATER, case


# ---------------------------------------------------------------------------
# 重播與存檔
# ---------------------------------------------------------------------------


def _play(
    library: ContentLibrary, world: WorldState, char: CharacterState, actions: list[WorldAction]
) -> tuple[WorldState, CharacterState, list[WorldLogEntry]]:
    entries: list[WorldLogEntry] = []
    for seq, action in enumerate(actions, start=1):
        now = NOON + seq * 60
        result = world_step(library, world, char, action, now)
        world, char = result.world, result.char
        entries.append(WorldLogEntry(seq=seq, now=now, character_id="alice", action=action))
    return world, char, entries


def _replays(
    library: ContentLibrary, world: WorldState, start: CharacterState, actions: list[WorldAction]
) -> CharacterState:
    end_world, live, entries = _play(library, world, start, actions)
    log = read_log(dumps_log(entries))
    first = replay(library, world, {"alice": start}, log.entries)
    second = replay(library, world, {"alice": start}, log.entries)
    assert first.characters["alice"] == live == second.characters["alice"]
    assert first.world == end_world == second.world
    assert loads_char(dumps_char(live)) == live
    return live


def test_capital_trip_replays(calm: ContentLibrary) -> None:
    start = _char(calm)
    actions: list[WorldAction] = [
        UseTeleportStoneAction(to="stone_capital"),
        WalkAction(path=((15, 10), (14, 10))),
        RestAction(),
        TeleportAction(region="cloud_ridge"),
        TeleportAction(region="capital"),
        UseTeleportStoneAction(to="stone_mist_ferry"),
    ]
    start = start.model_copy(update={"teleport_stones": ("stone_mist_ferry",)})
    live = _replays(calm, make_world(), start, actions)
    assert (live.region, live.location) == ("cloud_ridge", "mist_ferry")


def test_ferry_crossing_replays(calm: ContentLibrary) -> None:
    """走過渡口 → 回雲嶺的城鎮（傳送）→ 主城 → 從主城傳到餘燼集；重播兩次結果一樣。"""
    world = make_world(flags=OPEN)
    start = _at_ferry(calm)
    cross = WalkAction(path=_path(calm, start, (0, 5)))
    _, across, _ = _play(calm, world, start, [cross])
    back = WalkAction(path=_path(calm, across, (0, 8)))  # 灰渡口的出口回雲嶺的渡口
    _, returned, _ = _play(calm, world, across, [back])
    home = WalkAction(path=_path(calm, returned, (16, 0)))  # 渡口回霧渡鎮
    actions: list[WorldAction] = [
        cross,
        back,
        home,
        TeleportAction(region="capital"),
        TeleportAction(region="ashen_waste"),
    ]
    live = _replays(calm, world, start, actions)
    assert (live.region, live.location) == ("ashen_waste", "ember_market")
    assert region_lit(live, "ashen_waste")


# ---------------------------------------------------------------------------
# 畫面（大世界圖、這裡的傳送選項）
# ---------------------------------------------------------------------------


def test_atlas_view_in_capital(calm: ContentLibrary) -> None:
    view = world_view(calm, make_world(), _in_capital(calm), NOON)
    atlas = view.atlas
    assert atlas is not None and atlas.can_teleport and atlas.art_url is None
    assert atlas.capital.current and not atlas.capital.can_teleport
    assert [m.region for m in atlas.maps] == ["cloud_ridge"]  # 點進去看的區域圖
    assert not any(loc.current for m in atlas.maps for loc in m.locations)
    by = {r.region: r for r in atlas.regions}
    assert by["cloud_ridge"].can_teleport and by["cloud_ridge"].town_name_zh == "霧渡鎮"
    assert not by["ashen_waste"].can_teleport and by["ashen_waste"].status == "locked"
    assert by["frost_tide"].condition_zh == "之後的賽季"
    assert [t.region for t in view.here.teleports] == ["cloud_ridge"]
    assert view.field is not None and view.field.map_id == "capital"


def test_atlas_view_away_from_town(calm: ContentLibrary) -> None:
    char = _char(calm, location="rain_terraces", field=FieldPos(map="rain_terraces", x=3, y=3))
    atlas = world_view(calm, make_world(), char, NOON).atlas
    assert atlas is not None and not atlas.can_teleport
    assert atlas.teleport_problem_zh is not None and "傳送石" in atlas.teleport_problem_zh
    assert not atlas.capital.can_teleport


def test_here_teleports(calm: ContentLibrary) -> None:
    town = world_view(calm, make_world(), _char(calm), NOON)
    assert [t.region for t in town.here.teleports] == ["capital"]
    assert town.here.teleports[0].name_zh == "主城"
    ferry = world_view(calm, make_world(flags=OPEN), _at_ferry(calm), NOON)
    assert ferry.here.teleports == ()  # 要走過去
