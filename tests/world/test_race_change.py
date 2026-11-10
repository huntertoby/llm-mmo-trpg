"""這一季的免費換種族（Phase 6R-1，#138；:mod:`trpg.world.race_change`）。

- 第一季（``s1``）開放；其他季沒開。
- 在主城才能換；遭遇處理完才能換；每季一次；換成同一族、不存在的種族不行。
- 只改種族：等級、技能、屬性、裝備不變；舊存檔（``trpg-char/9``）照讀，還沒用過。
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import ChangeRaceAction, RaceChangedEvent
from trpg.world.errors import WorldActionError
from trpg.world.race_change import free_race_change_open, race_change_problem
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CHAR_FORMAT, CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _fox_in_capital(make_char: MakeChar) -> CharacterState:
    char = make_char(region="capital", location="capital")
    return char.model_copy(update={"hero": char.hero.model_copy(update={"race": "fox"})})


def test_first_season_opens_the_free_change(library: ContentLibrary) -> None:
    assert free_race_change_open(library, make_world())
    assert not free_race_change_open(library, make_world(season_id="s2"))


def test_change_race_in_capital_once(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _fox_in_capital(make_char)
    result = world_step(library, make_world(), char, ChangeRaceAction(race="elf"), NOON)
    after = result.char
    assert after.hero.race == "elf" and after.free_race_change_used
    assert (after.level, after.hero.skills, after.hero.attributes) == (
        char.level,
        char.hero.skills,
        char.hero.attributes,
    )
    (event,) = [e for e in result.events if isinstance(e, RaceChangedEvent)]
    assert (event.from_race, event.to_race, event.free) == ("fox", "elf", True)
    with pytest.raises(WorldActionError, match="已經用過"):
        world_step(library, make_world(), after, ChangeRaceAction(race="fox"), NOON)


@pytest.mark.parametrize(("race", "reason"), [("fox", "已經是這個種族"), ("nobody", "未知的種族")])
def test_change_race_rejects_bad_targets(
    library: ContentLibrary, make_char: MakeChar, race: str, reason: str
) -> None:
    with pytest.raises(WorldActionError, match=reason):
        world_step(
            library, make_world(), _fox_in_capital(make_char), ChangeRaceAction(race=race), NOON
        )


def test_change_race_only_in_capital_and_this_season(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    field = make_char()  # 雲嶺
    assert race_change_problem(library, make_world(), field, None) == "只有在主城能換種族"
    with pytest.raises(WorldActionError, match="主城"):
        world_step(library, make_world(), field, ChangeRaceAction(race="elf"), NOON)
    capital = _fox_in_capital(make_char)
    assert race_change_problem(library, make_world(), capital, None) is None
    later = make_world(season_id="s2")
    assert race_change_problem(library, later, capital, "elf") == "這一季沒有開放免費換種族"


def test_old_character_files_load_as_not_used(make_char: MakeChar) -> None:
    char = make_char()
    data = json.loads(dumps_char(char))
    assert data["format"] == CHAR_FORMAT == "trpg-char/13"
    data["format"] = "trpg-char/9"
    data.pop("free_race_change_used", None)
    old = loads_char(json.dumps(data))
    assert old.format == CHAR_FORMAT and not old.free_race_change_used
    assert old.gear_origin == char.gear_origin  # /9 已有來歷，不重算成綁定
