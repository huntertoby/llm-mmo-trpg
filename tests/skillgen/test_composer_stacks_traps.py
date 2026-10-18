"""Phase 2E-3：隨機組合器能組出蓄力／終結與陷阱技能，且不影響 common 的種子。"""

from __future__ import annotations

import pytest

from tests.skillgen.helpers import lib
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.skill_yaml import skill_from_yaml, skill_to_yaml
from trpg.skillgen.validate import validate_skill

SEEDS = range(60)


def test_builder_finisher_skills_have_exactly_one_stack_effect() -> None:
    kinds = set()
    for seed in SEEDS:
        skill = compose_random_skill(seed, skeleton="builder_finisher")
        assert validate_skill(skill, lib()) == []
        stack_effects = [e for e in skill.effects if e.type in ("add_stack", "consume_stack")]
        assert len(stack_effects) == 1 and any(e.type == "damage" for e in skill.effects)
        kinds.add(stack_effects[0].type)
        if skill.cost.stacks is not None:
            assert stack_effects[0].type == "consume_stack"
            assert lib().ruleset.stack_def(stack_effects[0].stack or "").owner == "self"
        assert skill_from_yaml(skill_to_yaml(skill)) == skill
    assert kinds == {"add_stack", "consume_stack"}


def test_trap_skills_start_with_place_trap_and_have_a_trap_field() -> None:
    triggers, shapes = set(), set()
    for seed in SEEDS:
        skill = compose_random_skill(seed, skeleton="trap")
        assert validate_skill(skill, lib()) == []
        assert skill.effects[0].type == "place_trap" and skill.shape.type == "ground_tile"
        assert skill.trap is not None and skill.kind == "active"
        triggers.add(skill.trap.trigger)
        shapes.add(skill.trap.shape)
        assert skill_from_yaml(skill_to_yaml(skill)) == skill
    assert triggers == {"enter", "delay"} and shapes == {"single", "cross", "square3"}


def test_the_new_skeletons_need_rare_or_better() -> None:
    for name in ("builder_finisher", "trap"):
        with pytest.raises(ComposeError):
            compose_random_skill(1, skeleton=name, rarity="common")


def test_unspecified_skeletons_never_pick_them_for_common_skills() -> None:
    for seed in range(150):
        skill = compose_random_skill(seed, rarity="common")
        assert skill.skeleton not in ("builder_finisher", "trap")


def test_the_new_skeletons_appear_when_no_skeleton_is_given() -> None:
    seen = {compose_random_skill(seed, rarity="epic").skeleton for seed in range(400)}
    assert {"builder_finisher", "trap"} <= seen


def test_the_same_seed_gives_the_same_new_skill() -> None:
    for name in ("builder_finisher", "trap"):
        assert compose_random_skill(5, skeleton=name) == compose_random_skill(5, skeleton=name)
