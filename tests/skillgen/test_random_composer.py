"""隨機組合器（Phase 2B-3 5.1、5.3；驗收 2–4）。"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction

import pytest

from tests.skillgen.helpers import lib
from trpg.content.skills import SkillDef, SkillRarity
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.composer_parts import dice_ladder
from trpg.skillgen.composer_tuning import tuning_bounds
from trpg.skillgen.random_composer import (
    MAX_ATTEMPTS,
    ComposeError,
    compose_random_skill,
    compose_with_stats,
)
from trpg.skillgen.skill_yaml import skill_from_yaml, skill_to_yaml
from trpg.skillgen.validate import validate_skill

FAST_SEEDS = range(100)
ENABLED = ("strike", "area", "control", "displace", "combo", "aura")
RARITIES = ("common", "rare", "epic", "legendary")


def test_same_seed_gives_the_same_skill_field_by_field() -> None:
    for seed in (0, 1, 7, 99, 12345):
        first, again = compose_random_skill(seed), compose_random_skill(seed)
        assert first == again
        assert first.model_dump() == again.model_dump()


def test_different_seeds_give_different_skills() -> None:
    skills = {skill_to_yaml(compose_random_skill(seed)) for seed in range(30)}
    assert len(skills) == 30


def test_every_fast_seed_composes_a_valid_skill_in_the_budget_window() -> None:
    library = lib()
    low, high = tuning_bounds(library)
    for seed in FAST_SEEDS:
        skill = compose_random_skill(seed)
        assert validate_skill(skill, library) == []
        assert skill.id == f"skill_rand_{seed}" and skill.name_zh.endswith(f"#{seed}")
        assert skill.provenance.origin == "level_up"
        assert skill.kind == "active" and skill.narrative.concept
        ratio = skill_budget(skill, library).ratio
        assert low <= ratio <= high, (seed, float(ratio))


def test_category_matches_weapon_req_and_tags_start_with_the_theme() -> None:
    for seed in FAST_SEEDS:
        skill = compose_random_skill(seed)
        allowed = ("melee", "ranged") if skill.category == "weapon" else ("focus", "any")
        assert skill.weapon_req in allowed
        assert skill.tags[1] == skill.skeleton and len(set(skill.tags)) == len(skill.tags)


def test_dice_use_the_allowed_sides_and_counts() -> None:
    sides = {int(d.split("d")[1]) for d in dice_ladder(lib().composer.dice)}
    assert sides == {4, 6, 8, 10, 12}
    for seed in FAST_SEEDS:
        for effect in compose_random_skill(seed, category="spell").effects:
            if effect.dice is not None:
                assert effect.dice.sides in sides


@pytest.mark.parametrize("skeleton", ENABLED)
def test_every_enabled_skeleton_can_be_composed(skeleton: str) -> None:
    for seed in range(5):
        skill = compose_random_skill(seed, skeleton=skeleton, rarity="legendary")
        assert skill.skeleton == skeleton and skill.rarity == "legendary"


@pytest.mark.parametrize("rarity", RARITIES)
def test_every_rarity_can_be_composed(rarity: SkillRarity) -> None:
    for seed in range(8):
        assert compose_random_skill(seed, rarity=rarity).rarity == rarity


@pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
def test_every_tier_can_be_composed(tier: int) -> None:
    for seed in range(8):
        assert compose_random_skill(seed, tier=tier).tier == tier


def test_fixed_parameters_are_respected() -> None:
    skill = compose_random_skill(
        3, tier=4, rarity="epic", skeleton="area", category="weapon", ap_cost=2
    )
    assert (skill.tier, skill.rarity, skill.skeleton, skill.category, skill.ap_cost) == (
        4,
        "epic",
        "area",
        "weapon",
        2,
    )


def test_impossible_parameters_raise_a_compose_error() -> None:
    with pytest.raises(ComposeError, match="displace"):
        compose_random_skill(1, skeleton="displace", rarity="common")
    with pytest.raises(ComposeError, match="combo"):
        compose_random_skill(1, skeleton="combo", rarity="common")
    with pytest.raises(ComposeError, match="未知的骨架"):
        compose_random_skill(1, skeleton="nope")
    with pytest.raises(ComposeError, match="passive"):
        compose_random_skill(1, skeleton="passive")


def test_skeleton_without_rarity_picks_a_feasible_rarity() -> None:
    for seed in range(20):
        assert compose_random_skill(seed, skeleton="displace").rarity != "common"


def test_combo_always_has_a_condition_and_conditions_need_rare() -> None:
    for seed in FAST_SEEDS:
        skill = compose_random_skill(seed)
        has_condition = skill.condition is not None or any(e.condition for e in skill.effects)
        if skill.skeleton == "combo":
            assert has_condition
        if skill.rarity == "common":
            assert not has_condition


def test_no_harmful_status_or_surface_is_aimed_at_allies() -> None:
    rules = lib().ruleset
    statuses, surfaces = rules.statuses.by_id(), rules.surfaces
    for seed in range(300):
        for effect in compose_random_skill(seed).effects:
            if effect.affects not in ("allies", "self"):
                continue
            if effect.type == "apply_status":
                assert effect.status is not None and statuses[effect.status].beneficial
            if effect.type == "create_surface":
                assert effect.surface is not None and surfaces.get(effect.surface).beneficial


def test_average_retries_are_small_and_bounded() -> None:
    attempts = [compose_with_stats(seed).attempts for seed in FAST_SEEDS]
    assert max(attempts) <= MAX_ATTEMPTS
    assert sum(attempts) / len(attempts) < 3


def test_skills_survive_a_yaml_round_trip() -> None:
    for seed in FAST_SEEDS:
        skill = compose_random_skill(seed)
        again = skill_from_yaml(skill_to_yaml(skill))
        assert isinstance(again, SkillDef) and again == skill


def test_distribution_over_the_fast_seeds_has_every_group() -> None:
    skills = [compose_random_skill(seed) for seed in FAST_SEEDS]
    assert {s.tier for s in skills} == {1, 2, 3, 4, 5}
    assert {s.rarity for s in skills} == set(RARITIES)
    assert {s.skeleton for s in skills} == set(ENABLED)
    assert max(Counter(s.skeleton for s in skills).values()) <= 40


@pytest.mark.slow
def test_one_thousand_seeds_are_all_valid_and_spread_out() -> None:
    library = lib()
    skills = [compose_random_skill(seed) for seed in range(1000)]
    assert all(validate_skill(s, library) == [] for s in skills)
    assert {s.tier for s in skills} == {1, 2, 3, 4, 5}
    assert {s.rarity for s in skills} == set(RARITIES)
    counts = Counter(s.skeleton for s in skills)
    assert set(counts) == set(ENABLED) and max(counts.values()) <= 400
    ratios = [skill_budget(s, library).ratio for s in skills]
    assert min(ratios) >= Fraction(75, 100) and max(ratios) <= Fraction(95, 100)


def test_effects_are_not_repeated_except_distinct_statuses_and_combo_damage() -> None:
    for seed in range(300):
        skill = compose_random_skill(seed)
        kinds = Counter(e.type for e in skill.effects)
        for kind, count in kinds.items():
            if count > 1:
                assert kind in ("apply_status", "damage")
                assert kind == "apply_status" or skill.skeleton == "combo"
        statuses = [e.status for e in skill.effects if e.type == "apply_status"]
        assert len(statuses) == len(set(statuses))
