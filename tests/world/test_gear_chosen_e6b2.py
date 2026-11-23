"""E6-b2 第 1 項：大世界角色的招牌勾選（``CharacterState.gear_chosen``）存讀與開戰。"""

from __future__ import annotations

import json
from collections.abc import Callable

from tests.roguelite.signature_helpers import GRAPPLE, gear_item, sig_library
from trpg.content.library import ContentLibrary
from trpg.world.gear import hero_loadout
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CHAR_FORMAT, CharacterState

MakeChar = Callable[..., CharacterState]
PICK = f"hands:{GRAPPLE}"


def test_gear_chosen_is_not_written_when_empty(make_char: MakeChar) -> None:
    raw = json.loads(dumps_char(make_char()))
    assert "gear_chosen" not in raw and raw["format"] == CHAR_FORMAT


def test_gear_chosen_round_trips(make_char: MakeChar) -> None:
    char = make_char(gear_chosen=(PICK,))
    raw = json.loads(dumps_char(char))
    assert raw["gear_chosen"] == [PICK]
    assert loads_char(dumps_char(char)) == char


def test_old_character_without_gear_chosen_still_loads(make_char: MakeChar) -> None:
    char = make_char()
    raw = json.loads(dumps_char(char))
    raw.pop("gear_chosen", None)
    assert loads_char(json.dumps(raw)).gear_chosen == ()


def test_hero_loadout_carries_gear_chosen(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = sig_library(library)
    char = make_char(equipment={"hands": gear_item("g", "hands", GRAPPLE)}, gear_chosen=(PICK,))
    assert hero_loadout(lib, char).chosen == (PICK,)
    assert hero_loadout(lib, make_char()).chosen == ()
