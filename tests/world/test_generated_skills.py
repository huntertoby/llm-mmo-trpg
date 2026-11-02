"""角色的生成技能（Phase 5A-5；``docs/phases/Phase5計畫.md`` 10.4）。"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.world.actions import LoadoutAction
from trpg.world.battle import prepare_battle
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _generated(library: ContentLibrary, char: CharacterState) -> SkillDef:
    """把主角第一招複製成一個不在內容庫的技能。"""
    base = library.skills[char.hero.skills[0]]
    return base.model_copy(update={"id": "skill_gen_test_bolt", "name_zh": "測試生成技"})


def _with_generated(library: ContentLibrary, char: CharacterState) -> CharacterState:
    skill = _generated(library, char)
    skills = (skill.id, *char.hero.skills[1:])
    hero = char.hero.model_copy(update={"skills": skills})
    return char.model_copy(
        update={
            "hero": hero,
            "generated_skills": (skill,),
            "bench": tuple(sorted({*char.bench, char.hero.skills[0]})),
        }
    )


def test_battle_ruleset_includes_generated(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_generated(library, make_char())
    char = char.model_copy(
        update={
            "location": "bamboo_path",
            "pending_encounter": make_encounter("bamboo_path", battle_map="dark_forest"),
        }
    )
    prepared = prepare_battle(library, char)
    assert "skill_gen_test_bolt" in prepared.setup.ruleset.skills.by_id()


def test_loadout_knows_generated(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_generated(library, make_char())
    original = char.bench[0]
    action = LoadoutAction(skills=(original, *char.hero.skills[1:]))
    result = world_step(library, make_world(), char, action, NOON)
    assert "skill_gen_test_bolt" in result.char.bench
    back = world_step(
        library, make_world(), result.char, LoadoutAction(skills=("skill_gen_test_bolt",)), NOON
    )
    assert back.char.hero.skills == ("skill_gen_test_bolt",)


def test_old_char_without_field_loads(library: ContentLibrary, make_char: MakeChar) -> None:
    raw = json.loads(dumps_char(make_char()))
    raw.pop("generated_skills")
    loaded = loads_char(json.dumps(raw))
    assert loaded.generated_skills == ()


def test_generated_must_be_sorted(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    a = _generated(library, char)
    b = a.model_copy(update={"id": "skill_gen_a"})
    with pytest.raises(ValueError, match="generated_skills"):
        CharacterState.model_validate({**char.model_dump(), "generated_skills": (a, b)})
    round_trip = loads_char(dumps_char(_with_generated(library, char)))
    assert round_trip.generated_skills[0].id == "skill_gen_test_bolt"
