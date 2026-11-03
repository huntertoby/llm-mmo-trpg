"""移動與遇敵（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.5）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world, with_rules, without_season
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    EncounterCheckEvent,
    EncounterEvent,
    TravelAction,
    TraveledEvent,
)
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, LocationRef
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def test_new_character_starts_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert char.location == "mist_ferry"
    assert char.level == 1
    assert char.supplies == 5
    assert char.hp > 0
    assert char.rng_counters == {}


def test_travel_to_neighbor(calm: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char()
    result = world_step(calm, world, char, TravelAction(to="hunter_hut"), NOON)
    assert result.char.location == "hunter_hut"
    assert without_season(result.world) == world
    assert isinstance(result.events[0], TraveledEvent)
    check = result.events[1]
    assert isinstance(check, EncounterCheckEvent)
    assert check.chance_permille == 0
    assert not check.encountered
    assert result.char.rng_counters == {"event": 1, "travel": 1}
    assert result.char.pending_encounter is None


@pytest.mark.parametrize(
    ("updates", "to", "message"),
    [
        ({}, "bamboo_path", "不和目前所在"),
        ({}, "nowhere", "沒有地點"),
        ({"location": "north_slope"}, "crane_cliff", "還沒發現"),
        ({}, "ashen_ferry", "還沒開放"),
    ],
)
def test_illegal_travel(
    library: ContentLibrary,
    make_char: MakeChar,
    updates: dict[str, object],
    to: str,
    message: str,
) -> None:
    char = make_char(**updates)
    before = char.model_dump()
    with pytest.raises(WorldActionError, match=message):
        world_step(library, make_world(), char, TravelAction(to=to), NOON)
    assert char.model_dump() == before


def test_unlock_flag_opens_gate(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world(flags=("mist_tide_success",))
    result = world_step(library, world, make_char(), TravelAction(to="ashen_ferry"), NOON)
    assert result.char.location == "ashen_ferry"


def test_revealed_hidden_location_is_reachable(calm: ContentLibrary, make_char: MakeChar) -> None:
    ref = LocationRef(region="cloud_ridge", location="crane_cliff")
    char = make_char(location="north_slope", revealed=(ref,))
    result = world_step(calm, make_world(), char, TravelAction(to="crane_cliff"), NOON)
    assert result.char.location == "crane_cliff"


def test_hasten_halves_chance(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="ferry_steps")
    normal = world_step(library, make_world(), char, TravelAction(to="bamboo_path"), NOON)
    fast = world_step(
        library, make_world(), char, TravelAction(to="bamboo_path", hasten=True), NOON
    )
    assert normal.char.supplies == char.supplies
    assert fast.char.supplies == char.supplies - 1
    n_check = normal.events[1]
    f_check = fast.events[1]
    assert isinstance(n_check, EncounterCheckEvent)
    assert isinstance(f_check, EncounterCheckEvent)
    assert f_check.chance_permille == n_check.chance_permille * 500 // 1000
    assert f_check.chance_permille > 0


def test_hasten_without_supplies(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(supplies=0)
    with pytest.raises(WorldActionError, match="補給不足"):
        world_step(library, make_world(), char, TravelAction(to="ferry_steps", hasten=True), NOON)


def test_chance_grows_with_level(library: ContentLibrary, make_char: MakeChar) -> None:
    low = world_step(
        library, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON
    ).events[1]
    high = world_step(
        library,
        make_world(),
        make_char(location="sword_tomb"),
        TravelAction(to="crystal_rift"),
        NOON,
    ).events[1]
    assert isinstance(low, EncounterCheckEvent)
    assert isinstance(high, EncounterCheckEvent)
    assert 0 < low.chance_permille < high.chance_permille


def test_encounter_result(ambush: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    result = world_step(ambush, make_world(), char, TravelAction(to="ferry_steps"), NOON)
    encounter = result.char.pending_encounter
    assert encounter is not None
    assert encounter.location == "ferry_steps"
    assert encounter.region == "cloud_ridge"
    assert encounter.level == 1
    assert encounter.battle_map == "cliff_outpost"
    assert encounter.weather in ambush.weather
    assert encounter.day_phase == "day"
    assert encounter.at == NOON
    assert any(isinstance(e, EncounterEvent) and e.result == encounter for e in result.events)
    assert result.char.rng_counters == {"battle": 1, "event": 1, "travel": 1}


def test_encounter_without_battle_map(ambush: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="mist_ferry")
    result = world_step(ambush, make_world(), char, TravelAction(to="hunter_hut"), NOON)
    encounter = result.char.pending_encounter
    assert encounter is not None
    assert encounter.battle_map is None  # 村落沒有戰鬥地圖，5A-4 從區域地圖池挑


def test_no_encounter_into_town(ambush: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="hunter_hut")
    result = world_step(ambush, make_world(), char, TravelAction(to="mist_ferry"), NOON)
    assert result.char.pending_encounter is None


def test_pending_encounter_blocks_travel(ambush: ContentLibrary, make_char: MakeChar) -> None:
    first = world_step(ambush, make_world(), make_char(), TravelAction(to="ferry_steps"), NOON)
    with pytest.raises(WorldActionError, match="遭遇"):
        world_step(ambush, make_world(), first.char, TravelAction(to="mist_ferry"), NOON)


def test_same_inputs_same_result(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="cloud_sea_bridge")
    a = world_step(library, make_world(), char, TravelAction(to="sword_tomb"), NOON)
    b = world_step(library, make_world(), char, TravelAction(to="sword_tomb"), NOON)
    assert a.char == b.char
    assert a.events == b.events


def test_counter_changes_the_roll(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = with_rules(library, encounter={"base_permille": 500, "max_permille": 500})
    rolls = set()
    char = make_char(location="cloud_sea_bridge")
    for counter in range(8):
        c = char.model_copy(update={"rng_counters": {"travel": counter}})
        event = world_step(lib, make_world(), c, TravelAction(to="sword_tomb"), NOON).events[1]
        assert isinstance(event, EncounterCheckEvent)
        rolls.add(event.roll)
    assert len(rolls) > 1
