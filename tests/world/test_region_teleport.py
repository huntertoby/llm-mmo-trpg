"""區域圖（只能看）＋傳送石（Phase 6C-6；21.1、21.2）：去過的地點、迷霧三段、從圖上傳送的條件。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.api.world_presenter import world_view
from trpg.api.world_region_view import fog_levels
from trpg.api.world_schemas import WorldMapView
from trpg.content.library import ContentLibrary
from trpg.world.actions import TeleportAction, WorldAction
from trpg.world.errors import WorldActionError
from trpg.world.field_actions import TeleportStoneUsedEvent, UseTeleportStoneAction
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState, FieldPos, LocationRef
from trpg.world.step import new_character, reveal_location, world_step

TOWN_STONE = "stone_mist_ferry"
TERRACE_STONE = "stone_rain_terraces"


@pytest.fixture(scope="module")
def calm_maps(field_library: ContentLibrary) -> ContentLibrary:
    return with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})


def _char(library: ContentLibrary, **updates: Any) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    return char.model_copy(update=updates) if updates else char


def _step(
    library: ContentLibrary, char: CharacterState, action: WorldAction
) -> tuple[CharacterState, list[object]]:
    result = world_step(library, make_world(), char, action, NOON)
    return result.char, list(result.events)


def _map(library: ContentLibrary, char: CharacterState) -> WorldMapView:
    return world_view(library, make_world(), char, NOON).map


def _fog(view: WorldMapView) -> dict[str, str]:
    return {loc.id: loc.fog for loc in view.locations}


# ---------------------------------------------------------------------------
# 去過的地點（visited_locations）
# ---------------------------------------------------------------------------


def test_step_records_departure_and_arrival(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, teleport_stones=(TOWN_STONE, TERRACE_STONE))
    assert char.location == "mist_ferry"
    assert [r.key() for r in char.visited_locations] == [("cloud_ridge", "mist_ferry")]  # 建角就記
    char = char.model_copy(update={"visited_locations": ()})  # 舊存檔：出發的地點也會補記
    moved, _ = _step(calm_maps, char, UseTeleportStoneAction(to=TERRACE_STONE))
    assert moved.location == "rain_terraces"
    assert [r.key() for r in moved.visited_locations] == [
        ("cloud_ridge", "mist_ferry"),
        ("cloud_ridge", "rain_terraces"),
    ]


def test_visited_is_deterministic_and_sorted(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, teleport_stones=(TOWN_STONE, TERRACE_STONE))
    runs = []
    for _ in range(2):
        moved, _ = _step(calm_maps, char, UseTeleportStoneAction(to=TERRACE_STONE))
        back, _ = _step(calm_maps, moved, UseTeleportStoneAction(to=TOWN_STONE))
        runs.append(dumps_char(back))
    assert runs[0] == runs[1]
    again, _ = _step(calm_maps, loads_char(runs[0]), UseTeleportStoneAction(to=TERRACE_STONE))
    assert len(again.visited_locations) == 2  # 重複走進不會再記


def test_visited_must_be_sorted(calm_maps: ContentLibrary) -> None:
    refs = (
        LocationRef(region="cloud_ridge", location="rain_terraces"),
        LocationRef(region="cloud_ridge", location="mist_ferry"),
    )
    with pytest.raises(ValueError, match="visited_locations"):
        CharacterState.model_validate({**_char(calm_maps).model_dump(), "visited_locations": refs})


def test_old_char_format_loads_without_visited(calm_maps: ContentLibrary) -> None:
    data = json.loads(dumps_char(_char(calm_maps)))
    data["format"] = "trpg-char/3"
    data.pop("visited_locations", None)
    old = loads_char(json.dumps(data))
    assert old.format == "trpg-char/15"
    assert old.visited_locations == ()
    assert _fog(_map(calm_maps, old))["mist_ferry"] == "visited"  # 目前位置一定算去過


# ---------------------------------------------------------------------------
# 從圖上傳送：站在傳送石上或在城鎮裡
# ---------------------------------------------------------------------------


def test_town_teleport_without_standing_on_stone(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, teleport_stones=(TERRACE_STONE,))
    view = _map(calm_maps, char)
    assert view.can_teleport is True
    assert view.teleport_problem_zh is None
    moved, events = _step(calm_maps, char, UseTeleportStoneAction(to=TERRACE_STONE))
    assert moved.location == "rain_terraces"
    used = [e for e in events if isinstance(e, TeleportStoneUsedEvent)]
    assert [(u.from_stone, u.to_stone) for u in used] == [(TOWN_STONE, TERRACE_STONE)]


def test_field_not_on_stone_cannot_teleport(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, teleport_stones=(TOWN_STONE, TERRACE_STONE))
    there, _ = _step(calm_maps, char, UseTeleportStoneAction(to=TERRACE_STONE))
    entry = calm_maps.field_maps["rain_terraces"].entry
    off = there.model_copy(update={"field": FieldPos(map="rain_terraces", x=entry[0], y=entry[1])})
    view = _map(calm_maps, off)
    assert view.can_teleport is False
    assert view.teleport_problem_zh is not None and "傳送石" in view.teleport_problem_zh
    with pytest.raises(WorldActionError, match="站在傳送石上或在城鎮裡"):
        _step(calm_maps, off, UseTeleportStoneAction(to=TOWN_STONE))
    on_stone = _map(calm_maps, there)  # 傳過去站在傳送石上
    assert on_stone.can_teleport is True
    assert [s.id for s in on_stone.stones if s.here] == [TERRACE_STONE]


def test_encounter_blocks_map_teleport(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, teleport_stones=(TERRACE_STONE,))
    view = world_view(calm_maps, make_world(), char, NOON, battle_id="b1").map
    assert view.can_teleport is False
    assert view.teleport_problem_zh == "戰鬥進行中"


def test_old_teleport_action_still_records_visit(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, visited_towns=("ashen_waste", "cloud_ridge"))
    moved, _ = _step(calm_maps, char, TeleportAction(region="ashen_waste"))
    assert moved.has_visited("cloud_ridge", "mist_ferry")
    assert moved.has_visited(moved.region, moved.location)


# ---------------------------------------------------------------------------
# 迷霧三段與隱藏地點
# ---------------------------------------------------------------------------


def test_fog_levels_three_bands() -> None:
    edges = [("a", "b"), ("b", "c"), ("c", "d")]
    assert fog_levels("abcd", edges, {"a"}) == {
        "a": "visited",
        "b": "silhouette",
        "c": "fog",
        "d": "fog",
    }


def test_region_fog_from_town(calm_maps: ContentLibrary) -> None:
    fog = _fog(_map(calm_maps, _char(calm_maps)))
    assert fog["mist_ferry"] == "visited"
    assert fog["ferry_steps"] == fog["hunter_hut"] == fog["ashen_ferry"] == "silhouette"
    assert fog["bamboo_path"] == "fog"
    assert fog["cloud_summit"] == "fog"
    assert "elixir_cave" not in fog  # 隱藏地點發現前完全不給
    assert "crane_cliff" not in fog


def test_revealed_hidden_location_joins_fog(calm_maps: ContentLibrary) -> None:
    char = _char(
        calm_maps,
        visited_locations=(LocationRef(region="cloud_ridge", location="herb_valley"),),
    )
    assert "elixir_cave" not in _fog(_map(calm_maps, char))
    found = reveal_location(char, "cloud_ridge", "elixir_cave")
    assert _fog(_map(calm_maps, found))["elixir_cave"] == "silhouette"


def test_stones_hidden_in_fog_and_locked_shown(calm_maps: ContentLibrary) -> None:
    char = _char(calm_maps, teleport_stones=(TOWN_STONE,))
    stones = {s.id: s for s in _map(calm_maps, char).stones}
    assert stones[TOWN_STONE].unlocked is True
    assert stones[TOWN_STONE].here is True
    assert TERRACE_STONE not in stones  # 梯田在霧裡
    near = char.model_copy(
        update={"visited_locations": (LocationRef(region="cloud_ridge", location="bamboo_path"),)}
    )
    stones = {s.id: s for s in _map(calm_maps, near).stones}
    assert stones[TERRACE_STONE].unlocked is False  # 剪影地點的傳送石：看得到、鎖著
