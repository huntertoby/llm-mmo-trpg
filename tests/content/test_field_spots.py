"""實地地圖上的東西（6C-5）的內容檢查：情境物件的用途接得上、``until_quest`` 的任務存在、
營火站得上。"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import passable_grid


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_object_events_belong_to_their_location(library: ContentLibrary) -> None:
    for found in library.field_maps.values():
        for spot in found.situation_objects:
            if spot.use != "event":
                continue
            table = library.world_event_content.events[found.region]
            skeleton = table.skeleton_by_id().get(spot.event or spot.id)
            assert skeleton is not None, (found.id, spot.id)
            assert found.place in skeleton.locations, (found.id, spot.id)


def test_boss_gates_sit_on_fightable_locations(library: ContentLibrary) -> None:
    gates = []
    for found in library.field_maps.values():
        for spot in found.situation_objects:
            if spot.use == "encounter":
                place = library.world_maps[found.region].location_by_id()[found.place]
                assert place.level_max is not None and place.kind == "boss", (found.id, spot.id)
                gates.append(spot.id)
    assert sorted(gates) == ["pit_gate", "summit_gate"]


def test_until_quest_names_a_real_quest(library: ContentLibrary) -> None:
    quests = {q.id for table in library.world_quests.quests.values() for q in table.quests}
    used = [
        (found.id, spawn.until_quest)
        for found in library.field_maps.values()
        for spawn in found.spawns
        if spawn.until_quest is not None
    ]
    assert sorted(m for m, _ in used) == ["bamboo_path", "ferry_steps", "rain_terraces"]
    assert all(q in quests for _, q in used)


def test_until_step_names_a_step_of_the_quest(library: ContentLibrary) -> None:
    """6C-5b：新手固定戰寫了是哪一步（那一步完成就不再出現），步驟要存在於 ``until_quest``。"""
    steps = {
        q.id: {s.id for s in q.steps}
        for table in library.world_quests.quests.values()
        for q in table.quests
    }
    used = [
        (spawn.until_quest, spawn.until_step)
        for found in library.field_maps.values()
        for spawn in found.spawns
        if spawn.until_quest is not None
    ]
    assert used and all(step is not None for _, step in used)  # 三場固定戰都照步驟
    assert all(step in steps[q] for q, step in used if q is not None)


def test_campfires_are_standable(library: ContentLibrary) -> None:
    rules = library.ruleset
    for found in library.field_maps.values():
        grid = passable_grid(found, rules.terrain.by_id(), rules.objects.by_id())
        for fire in found.campfires:
            x, y = fire.at
            assert grid[y][x], (found.id, fire.id)
