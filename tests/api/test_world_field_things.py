"""實地地圖上的東西（6C-5）的畫面：營火、事件「！」、情境物件、潛行、朋友的腳印、留言石碑與區域圖的
足跡；伺服器從其他角色的存檔組足跡（不掃日誌）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.world.helpers import NOON, hero, make_world
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.api.world_field_things import (
    FOOTPRINT_FRIENDS_MAX,
    PRINTS_MAX,
    FieldSocial,
    Visitor,
    footprint_cells,
    things_line,
)
from trpg.api.world_field_view import field_view
from trpg.api.world_presenter import world_view
from trpg.content.library import ContentLibrary
from trpg.world.field import field_grid, field_map, placed
from trpg.world.field_actions import EventMarkedEvent, SneakStartedEvent
from trpg.world.layout import char_path
from trpg.world.save import dumps_char, write_atomic
from trpg.world.state import CharacterState, LocationRef
from trpg.world.step import new_character


def _char(
    library: ContentLibrary, location: str, cid: str = "alice", **updates: Any
) -> CharacterState:
    char = new_character(library, cid, hero(library), region="cloud_ridge")
    char = placed(library, char.model_copy(update={"location": location, "field": None}))
    return char.model_copy(update=updates) if updates else char


def _social(*names: str, notes: int = 0) -> FieldSocial:
    visitors = tuple(Visitor(f"c{i}", n) for i, n in enumerate(names))
    place = ("cloud_ridge", "ferry_steps")
    return FieldSocial(visitors={place: visitors}, notes={place: notes} if notes else {})


def test_campfires_objects_and_sneak_fields(field_library: ContentLibrary) -> None:
    lake = field_view(
        field_library, _char(field_library, "winter_lake"), world=make_world(), now=NOON
    )
    assert lake is not None
    assert [(c.id, c.x, c.y) for c in lake.campfires] == [("campfire_winter_lake", 3, 9)]
    assert lake.sneak_problem_zh is None and lake.sneak_cost == 1 and not lake.sneaking
    town = field_view(
        field_library, _char(field_library, "mist_ferry"), world=make_world(), now=NOON
    )
    assert town is not None and town.sneak_problem_zh is not None  # 城鎮不用潛行
    summit = field_view(
        field_library, _char(field_library, "cloud_summit"), world=make_world(), now=NOON
    )
    assert summit is not None
    gate = next(o for o in summit.situation_objects if o.id == "summit_gate")
    assert (gate.name_zh, gate.use, gate.usable) == ("觀門", "encounter", True)
    rift = field_view(
        field_library, _char(field_library, "crystal_rift"), world=make_world(), now=NOON
    )
    assert rift is not None
    wall = next(o for o in rift.situation_objects if o.id == "rift_mist_wall")
    assert wall.use == "note" and not wall.usable and wall.note_zh


def test_footprints_are_deterministic_and_walkable(field_library: ContentLibrary) -> None:
    char = _char(field_library, "ferry_steps")
    social = _social("阿岳", "小白", "老鐵", "多一位")
    first = field_view(field_library, char, social=social)
    second = field_view(field_library, char, social=social)
    assert first is not None and second is not None
    assert first.footprints == second.footprints and first.footprints
    owners = {p.owner for p in first.footprints}
    assert (
        owners <= {"c0", "c1", "c2"} and len(owners) <= FOOTPRINT_FRIENDS_MAX
    )  # 依角色 ID 最多 3 位
    walkable = {(t.x, t.y) for t in first.tiles if t.walkable}
    assert all((p.x, p.y) in walkable for p in first.footprints)
    found = field_map(field_library, "ferry_steps")
    assert found is not None
    grid = field_grid(field_library, char, found)
    assert len(footprint_cells(field_library, char, found, grid, "c0")) <= PRINTS_MAX
    assert field_view(field_library, char) is not None
    plain = field_view(field_library, char)
    assert plain is not None and plain.footprints == () and plain.note_stone is None


def test_note_stone_only_when_there_are_notes(field_library: ContentLibrary) -> None:
    char = _char(field_library, "ferry_steps")
    none = field_view(field_library, char, social=_social())
    some = field_view(field_library, char, social=_social(notes=2))
    assert none is not None and none.note_stone is None
    assert some is not None and some.note_stone is not None and some.note_stone.count == 2
    walkable = {(t.x, t.y) for t in some.tiles if t.walkable}
    assert (some.note_stone.x, some.note_stone.y) in walkable


def test_region_map_shows_footprints(field_library: ContentLibrary) -> None:
    char = _char(field_library, "mist_ferry")
    view = world_view(field_library, make_world(), char, NOON, social=_social("阿岳"))
    steps = next(loc for loc in view.map.locations if loc.id == "ferry_steps")
    assert steps.fog == "silhouette" and steps.footprints == ("阿岳",)
    far = [loc for loc in view.map.locations if loc.fog == "fog"]
    assert all(loc.footprints == () for loc in far)


def test_store_builds_social_from_other_saves(
    field_library: ContentLibrary, tmp_path: Path
) -> None:
    store = WorldStore(
        field_library, SessionStore(field_library), tmp_path, prefetch=False, clock=lambda: NOON
    )
    me = _char(field_library, "mist_ferry", "alice")
    bob = _char(
        field_library,
        "rain_terraces",
        "bob",
        visited_locations=(LocationRef(region="cloud_ridge", location="ferry_steps"),),
    )
    for c in (me, bob):
        write_atomic(char_path(tmp_path, c.character_id), dumps_char(c))
    store.notes.add(bob, "小心石階上的盜賊", NOON)
    social = store.field_social("alice")
    assert [v.character_id for v in social.visitors_at("cloud_ridge", "ferry_steps")] == ["bob"]
    assert [v.character_id for v in social.visitors_at("cloud_ridge", "rain_terraces")] == ["bob"]
    assert social.visitors_at("cloud_ridge", "mist_ferry") == ()  # 自己不算
    assert social.notes == {("cloud_ridge", "rain_terraces"): 1}


def test_lines() -> None:
    marked = EventMarkedEvent(location="ferry_steps", map="ferry_steps", x=1, y=1, spot="s")
    assert things_line(None, "cloud_ridge", marked) is not None  # type: ignore[arg-type]
    sneak = SneakStartedEvent(supplies_spent=1, supplies_left=2)
    line = things_line(None, "cloud_ridge", sneak)  # type: ignore[arg-type]
    assert line is not None and "1 補給" in line
