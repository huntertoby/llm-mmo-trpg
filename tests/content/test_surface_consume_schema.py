"""Phase 3C-3b：``on_enter_surface`` 的參數、``consume_status`` 的預算與示範技能。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.battle import Dice
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.shared.types import Surface
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill


def test_surface_param_only_belongs_to_on_enter_surface() -> None:
    assert TriggerSpec(event="on_enter_surface").surface is None
    assert TriggerSpec(event="on_enter_surface", surface=Surface.OIL).surface is Surface.OIL
    with pytest.raises(ValidationError, match="只有 on_enter_surface 使用 surface"):
        TriggerSpec(event="on_hit", surface=Surface.OIL)
    with pytest.raises(ValidationError, match="不可為 none"):
        TriggerSpec(event="on_enter_surface", surface=Surface.NONE)


def test_the_trigger_definition_is_epic_and_never_composed_randomly() -> None:
    lib = library()
    definition = lib.ruleset.trigger_def("on_enter_surface")
    assert (definition.min_rarity, definition.random_composer, definition.has_other) == (
        "epic",
        False,
        True,
    )
    seen = {
        s.trigger.event
        for seed in range(60)
        if (s := compose_random_skill(seed, tier=1, rarity="epic", skeleton="passive")).trigger
    }
    assert "on_enter_surface" not in seen


def test_the_consume_status_skeleton_is_never_picked_by_the_random_composer() -> None:
    for seed in range(40):
        skill = compose_random_skill(seed, tier=2, rarity="rare")
        assert all(e.type != "consume_status" for e in skill.effects)


def test_demo_skills_pass_validation_and_budget() -> None:
    lib = library()
    for skill_id in ("skill_detonate_burning", "skill_tide_snare"):
        skill = lib.skills[skill_id]
        assert validate_skill(skill, lib) == [], skill_id
        assert 0.7 <= float(skill_budget(skill, lib).ratio) <= 1.0
    tide = lib.skills["skill_tide_snare"]
    assert tide.trigger is not None
    assert (tide.trigger.event, tide.trigger.surface) == ("on_enter_surface", Surface.WATER)
    assert tide.rarity == "epic"


def test_demo_skills_are_equipped_by_builds() -> None:
    builds = {b.id: b.hero.skills for b in library().builds.builds}
    assert "skill_detonate_burning" in builds["build_fire"]
    assert "skill_tide_snare" in builds["build_storm"]


def test_consume_status_budget_scales_with_the_then_dice() -> None:
    lib = library()
    skill = lib.skills["skill_detonate_burning"]
    spec = skill.effects[0]
    assert spec.then is not None
    bigger_then = tuple(t.model_copy(update={"dice": Dice(count=4, sides=6)}) for t in spec.then)
    bigger = skill.model_copy(update={"effects": (spec.model_copy(update={"then": bigger_then}),)})
    assert skill_budget(bigger, lib).total > skill_budget(skill, lib).total


def test_consume_status_is_only_for_the_consume_status_skeleton_rule() -> None:
    skill = library().skills["skill_detonate_burning"]
    assert isinstance(skill, SkillDef) and skill.skeleton == "consume_status"
    other = skill.model_copy(update={"skeleton": "strike"})
    assert any(v.rule.startswith("skeleton.") for v in validate_skill(other, library()))
