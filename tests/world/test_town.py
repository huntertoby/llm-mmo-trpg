"""撤退與城鎮服務（Phase 5A-4；``docs/phases/Phase5計畫.md`` 9.2）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    LoadoutAction,
    RestAction,
    RetreatAction,
    TeleportAction,
    TravelAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, LocationRef
from trpg.world.step import max_hp, max_mana, world_step

MakeChar = Callable[..., CharacterState]


# ---------------------------------------------------------------------------
# 撤退
# ---------------------------------------------------------------------------


def test_retreat_goes_back_without_cost(ambush: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(location="ferry_steps")
    met = world_step(ambush, world, char, TravelAction(to="bamboo_path"), NOON).char
    assert met.pending_encounter is not None
    assert met.pending_encounter.from_location == "ferry_steps"
    result = world_step(ambush, world, met, RetreatAction(), NOON + 1)
    back = result.char
    assert back.location == "ferry_steps"
    assert back.pending_encounter is None
    assert back.supplies == met.supplies
    assert back.rng_counters == met.rng_counters
    assert (back.hp, back.mana) == (met.hp, met.mana)
    assert [e.kind for e in result.events] == ["retreated"]


def test_retreat_without_origin_goes_to_town(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="bamboo_path", pending_encounter=make_encounter("bamboo_path"))
    result = world_step(library, make_world(), char, RetreatAction(), NOON)
    assert result.char.location == "mist_ferry"


def test_retreat_needs_encounter(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="沒有遭遇"):
        world_step(library, make_world(), make_char(), RetreatAction(), NOON)


# ---------------------------------------------------------------------------
# 休息
# ---------------------------------------------------------------------------


def test_rest_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(hp=3, mana=0, stamina=1, supplies=0, fatigued=True)
    result = world_step(library, make_world(), char, RestAction(), NOON)
    rested = result.char
    assert rested.hp == max_hp(library, rested)
    assert rested.mana == max_mana(library, rested)
    assert rested.stamina is None
    assert library.world_rules is not None
    assert rested.supplies == library.world_rules.supplies.start
    assert rested.fatigued  # 疲憊要打完一場才消失
    rich = world_step(
        library, make_world(), char.model_copy(update={"supplies": 9}), RestAction(), NOON
    )
    assert rich.char.supplies == 9


def test_rest_only_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="只有城鎮"):
        world_step(library, make_world(), make_char(location="hunter_hut"), RestAction(), NOON)
    pending = make_char(pending_encounter=make_encounter("ferry_steps"))
    with pytest.raises(WorldActionError, match="遭遇"):
        world_step(library, make_world(), pending, RestAction(), NOON)


# ---------------------------------------------------------------------------
# 換技能
# ---------------------------------------------------------------------------


def test_loadout_in_town_moves_to_bench(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    skills = char.hero.skills
    assert len(skills) >= 2
    kept = skills[1:]
    result = world_step(library, make_world(), char, LoadoutAction(skills=kept), NOON)
    assert result.char.hero.skills == kept
    assert result.char.bench == (skills[0],)
    back = world_step(library, make_world(), result.char, LoadoutAction(skills=skills), NOON)
    assert back.char.hero.skills == skills
    assert back.char.bench == ()


def test_loadout_at_campfire_only(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="hunter_hut")
    action = LoadoutAction(skills=char.hero.skills[1:])
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        world_step(library, make_world(), char, action, NOON)
    camped = char.model_copy(
        update={"camped_at": LocationRef(region="cloud_ridge", location="hunter_hut")}
    )
    assert world_step(library, make_world(), camped, action, NOON).char.hero.skills == (
        action.skills
    )


def test_loadout_rejects_bad_lists(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    world = make_world()
    with pytest.raises(WorldActionError, match="沒有的技能"):
        world_step(library, world, char, LoadoutAction(skills=("skill_hush",)), NOON)
    first = char.hero.skills[0]
    with pytest.raises(WorldActionError, match="重複"):
        world_step(library, world, char, LoadoutAction(skills=(first, first)), NOON)
    actives = sorted(s.id for s in library.skills.values() if s.kind == "active" and s.tier == 1)
    many = tuple(actives[:7])
    rich = char.model_copy(update={"bench": tuple(sorted(set(many) - set(char.hero.skills)))})
    with pytest.raises(WorldActionError):
        world_step(library, world, rich, LoadoutAction(skills=many), NOON)


# ---------------------------------------------------------------------------
# 傳送
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def two_regions(library: ContentLibrary) -> ContentLibrary:
    """多一張「灰燼荒原」地點圖（照抄雲嶺，只換區域；測試傳送用）。"""
    cloud = library.world_maps["cloud_ridge"]
    ashen = cloud.model_copy(update={"region": "ashen_waste", "name_zh": "灰燼荒原"})
    return dataclasses.replace(library, world_maps={**library.world_maps, "ashen_waste": ashen})


def test_new_character_knows_its_town(make_char: MakeChar) -> None:
    assert make_char().visited_towns == ("cloud_ridge",)


def test_gate_then_town_teleport(two_regions: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char()
    with pytest.raises(WorldActionError, match="還沒去過"):
        world_step(two_regions, world, char, TeleportAction(region="ashen_waste"), NOON)
    at_gate = char.model_copy(update={"location": "ashen_ferry"})
    with pytest.raises(WorldActionError, match="不通往"):
        world_step(two_regions, world, at_gate, TeleportAction(region="frost_tide"), NOON)
    result = world_step(two_regions, world, at_gate, TeleportAction(region="ashen_waste"), NOON)
    moved = result.char
    assert (moved.region, moved.location) == ("ashen_waste", "mist_ferry")
    assert moved.visited_towns == ("ashen_waste", "cloud_ridge")
    assert [e.kind for e in result.events] == ["teleported"]
    home = world_step(two_regions, world, moved, TeleportAction(region="cloud_ridge"), NOON)
    assert (home.char.region, home.char.location) == ("cloud_ridge", "mist_ferry")


def test_teleport_errors(two_regions: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(visited_towns=("cloud_ridge", "frost_tide"))
    with pytest.raises(WorldActionError, match="已經在"):
        world_step(two_regions, world, char, TeleportAction(region="cloud_ridge"), NOON)
    with pytest.raises(WorldActionError, match="地點圖"):
        world_step(two_regions, world, char, TeleportAction(region="frost_tide"), NOON)
    field = char.model_copy(update={"location": "hunter_hut"})
    with pytest.raises(WorldActionError, match="城鎮與傳送點"):
        world_step(two_regions, world, field, TeleportAction(region="ashen_waste"), NOON)


def test_travel_into_town_marks_visit(calm: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="ferry_steps", visited_towns=())
    result = world_step(calm, make_world(), char, TravelAction(to="mist_ferry"), NOON)
    assert result.char.visited_towns == ("cloud_ridge",)
