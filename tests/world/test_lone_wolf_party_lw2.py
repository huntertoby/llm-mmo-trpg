"""LW-2 出城前提示（06 6.37「提示與標灰」，#156）：隊伍面板的 ``PartyView.lone_wolf``。

角色沒帶獨狼條件的技能或詞條時沒有提示；帶了時列出名字，並照隊伍人數判斷成不成立。
"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import make_world
from trpg.api.world_party_view import lone_wolf_view, party_view
from trpg.content.equipment import AffixRoll
from trpg.content.library import ContentLibrary
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]
STRIDER = "skill_lone_strider"


def _with_strider(char: CharacterState) -> CharacterState:
    hero = char.hero.model_copy(update={"skills": (*char.hero.skills[:-1], STRIDER)})
    return char.model_copy(update={"hero": hero})


def _alone(char: CharacterState) -> CharacterState:
    return char.model_copy(update={"mercenaries": (), "shadows": (), "companions": ()})


def test_no_hint_without_lone_wolf_things(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _alone(make_char("bob"))
    assert party_view(library, make_world(), char, in_battle=False).lone_wolf is None


def test_going_alone_with_a_lone_wolf_skill(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _alone(_with_strider(make_char("bob")))
    view = party_view(library, make_world(), char, in_battle=False)
    assert view.lone_wolf is not None
    assert view.lone_wolf.ok
    assert view.lone_wolf.skills_zh == ("獨行者",)
    assert view.lone_wolf.affixes_zh == ()


def test_a_mercenary_breaks_lone_wolf(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_strider(make_char("bob")).model_copy(
        update={"mercenaries": ("merc_tiebi",), "shadows": (), "companions": ()}
    )
    view = party_view(library, make_world(), char, in_battle=False)
    assert len(view.members) == 2
    assert view.lone_wolf is not None and not view.lone_wolf.ok


def test_lone_wolf_affix_is_listed(library: ContentLibrary, make_char: MakeChar) -> None:
    armor = library.items["item_test_armor"].model_copy(
        update={"affixes": (AffixRoll(affix="affix_cond_lone_defense", value=150),)}
    )
    char = _alone(make_char("bob")).model_copy(update={"equipment": {"body": armor}})
    hint = lone_wolf_view(library, char, 1)
    assert hint is not None and hint.ok and hint.skills_zh == ()
    assert hint.affixes_zh == (f"{armor.name_zh}的「獨行的」",)
