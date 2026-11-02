"""紮營＝營火（Phase 5A-2；09 9.6.11 #114）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import CampAction, CampedEvent, TravelAction
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, ClearedLocation, LocationRef
from trpg.world.step import camp_problem, max_hp, max_mana, world_step

MakeChar = Callable[..., CharacterState]


def test_camp_restores_and_spends_supply(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="hunter_hut", hp=3, mana=0, stamina=0)
    result = world_step(library, make_world(), char, CampAction(), NOON)
    camped = result.char
    assert camped.supplies == char.supplies - 1
    assert camped.hp == max_hp(library, char)
    assert camped.mana == max_mana(library, char)
    assert camped.stamina is None
    assert camped.camped_at == LocationRef(region="cloud_ridge", location="hunter_hut")
    assert result.events == (
        CampedEvent(
            location="hunter_hut", supplies_left=camped.supplies, hp=camped.hp, mana=camped.mana
        ),
    )


@pytest.mark.parametrize("location", ["old_pine_altar", "herb_valley", "crystal_rift"])
def test_camp_allowed_kinds(library: ContentLibrary, make_char: MakeChar, location: str) -> None:
    result = world_step(library, make_world(), make_char(location=location), CampAction(), NOON)
    assert result.char.camped_at is not None


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"location": "mist_ferry"}, "城鎮"),
        ({"location": "north_slope"}, "不能紮營"),
        ({"location": "cloud_summit"}, "不能紮營"),
        ({"location": "ferry_steps"}, "敵人還在"),
        ({"location": "hunter_hut", "supplies": 0}, "補給不足"),
    ],
)
def test_camp_forbidden(
    library: ContentLibrary, make_char: MakeChar, updates: dict[str, object], message: str
) -> None:
    char = make_char(**updates)
    assert camp_problem(library, make_world(), char, NOON) is not None
    with pytest.raises(WorldActionError, match=message):
        world_step(library, make_world(), char, CampAction(), NOON)


def test_cleared_camp_until_respawn(library: ContentLibrary, make_char: MakeChar) -> None:
    cleared = ClearedLocation(region="cloud_ridge", location="ferry_steps", respawn_at=NOON + 600)
    world = make_world(cleared=(cleared,))
    char = make_char(location="ferry_steps")
    assert world_step(library, world, char, CampAction(), NOON).char.camped_at is not None
    with pytest.raises(WorldActionError, match="敵人還在"):
        world_step(library, world, char, CampAction(), NOON + 600)


def test_pending_encounter_blocks_camp(ambush: ContentLibrary, make_char: MakeChar) -> None:
    moved = world_step(ambush, make_world(), make_char(), TravelAction(to="hunter_hut"), NOON)
    assert moved.char.pending_encounter is not None
    with pytest.raises(WorldActionError, match="遭遇"):
        world_step(ambush, make_world(), moved.char, CampAction(), NOON)


def test_leaving_clears_camp(calm: ContentLibrary, make_char: MakeChar) -> None:
    camped = world_step(calm, make_world(), make_char(location="hunter_hut"), CampAction(), NOON)
    moved = world_step(calm, make_world(), camped.char, TravelAction(to="mist_ferry"), NOON)
    assert moved.char.camped_at is None
