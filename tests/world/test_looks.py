"""外觀選項（Phase 6R-2，#137；:mod:`trpg.world.looks`）。

- 主城隨時免費改（不限次數、不花錢）；不在主城、有遭遇時擋；選項要在種族清單內。
- 換種族時新種族也有的選項保留，沒有的改回預設；引擎不讀外觀。
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.battle import LookChoice
from trpg.content.library import ContentLibrary
from trpg.world.actions import ChangeLookAction, ChangeRaceAction, LookChangedEvent
from trpg.world.errors import WorldActionError
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _in_capital(make_char: MakeChar, race: str = "human") -> CharacterState:
    char = make_char(region="capital", location="capital")
    return char.model_copy(update={"hero": char.hero.model_copy(update={"race": race})})


def _custom(char: CharacterState) -> LookChoice | None:
    return None if char.hero.doll is None else char.hero.doll.custom


def test_change_look_free_and_repeatable(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _in_capital(make_char)
    look = LookChoice(hair="ponytail", beard="none", lashes=True, frame="slim")
    first = world_step(library, make_world(), char, ChangeLookAction(look=look), NOON)
    assert _custom(first.char) == look
    hero_back = first.char.hero.model_copy(update={"doll": char.hero.doll})
    assert first.char.model_copy(update={"hero": hero_back}) == char  # 只改外觀，不花錢
    assert any(isinstance(e, LookChangedEvent) for e in first.events)
    again = world_step(library, make_world(), first.char, ChangeLookAction(), NOON)
    assert _custom(again.char) is None  # 回到種族預設
    restored = loads_char(dumps_char(first.char))
    assert _custom(restored) == look


def test_change_look_rejects(library: ContentLibrary, make_char: MakeChar) -> None:
    outside = make_char()
    assert outside.region != "capital"
    with pytest.raises(WorldActionError, match="主城"):
        world_step(library, make_world(), outside, ChangeLookAction(), NOON)
    elf = _in_capital(make_char, "elf")
    with pytest.raises(WorldActionError, match="鬍子"):
        world_step(
            library, make_world(), elf, ChangeLookAction(look=LookChoice(beard="full")), NOON
        )


def test_race_change_keeps_shared_options(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _in_capital(make_char)
    look = LookChoice(face="heart", hair="twin", beard="goatee")
    char = world_step(library, make_world(), char, ChangeLookAction(look=look), NOON).char
    after = world_step(library, make_world(), char, ChangeRaceAction(race="elf"), NOON).char
    assert _custom(after) == LookChoice(face="heart", hair="twin")  # 精靈沒有鬍子


def test_old_char_format_loads_with_race_default(make_char: MakeChar) -> None:
    data = json.loads(dumps_char(make_char()))
    assert data["format"] == "trpg-char/14"
    data["format"] = "trpg-char/10"
    old = loads_char(json.dumps(data))
    assert old.format == "trpg-char/14" and _custom(old) is None
