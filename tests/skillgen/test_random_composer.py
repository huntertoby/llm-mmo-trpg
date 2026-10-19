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
ENABLED = (
    "strike",
    "area",
    "control",
    "displace",
    "combo",
    "aura",
    "passive",
    "reaction",
    "stance",
    "builder_finisher",
    "trap",
)
RARITIES = ("common", "rare", "epic")
"""組合器產生的稀有度：傳說只能手寫（Phase 3C-4a，抽到傳說時降為史詩）。"""


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
        expected = {"passive": "passive", "reaction": "reaction", "stance": "stance"}
        assert skill.kind == expected.get(skill.skeleton, "active")
        assert skill.narrative.concept
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
        skill = compose_random_skill(seed, skeleton=skeleton, rarity="epic")
        assert skill.skeleton == skeleton and skill.rarity == "epic"


@pytest.mark.parametrize("rarity", RARITIES)
def test_every_rarity_can_be_composed(rarity: SkillRarity) -> None:
    for seed in range(8):
        assert compose_random_skill(seed, rarity=rarity).rarity == rarity


def test_legendary_is_hand_written_only() -> None:
    """Phase 3C-4a：組合器不產生傳說（需要源力代價與改寫規則型原語）。"""
    with pytest.raises(ComposeError, match="傳說"):
        compose_random_skill(0, rarity="legendary")


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
        compose_random_skill(1, skeleton="passive", rarity="rare")
    with pytest.raises(ComposeError, match="被動"):
        compose_random_skill(1, skeleton="passive", rarity="epic", category="weapon")


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


# ---------------------------------------------------------------------------
# 被動（Phase 2E-1）
# ---------------------------------------------------------------------------


def test_explicit_passive_composes_valid_passives_for_every_trigger() -> None:
    library = lib()
    events: set[str] = set()
    for seed in range(60):
        skill = compose_random_skill(seed, skeleton="passive", rarity="epic")
        assert validate_skill(skill, library) == []
        assert skill.kind == "passive" and skill.ap_cost is None and skill.trigger is not None
        assert skill.category == "spell" and skill.shape.type == "self"
        events.add(skill.trigger.event)
        low, high = tuning_bounds(library)
        assert low <= skill_budget(skill, library).ratio <= high, seed
    assert len(events) >= 6


def test_passives_only_appear_from_epic_and_do_not_change_other_seeds() -> None:
    skills = [compose_random_skill(seed) for seed in FAST_SEEDS]
    passives = [s for s in skills if s.kind == "passive"]
    assert passives and all(s.rarity in ("epic", "legendary") for s in passives)
    for seed in range(40):
        assert compose_random_skill(seed, rarity="common").kind == "active"
        assert compose_random_skill(seed, rarity="rare").kind != "passive"


def test_explicit_non_passive_skeleton_never_becomes_a_passive() -> None:
    for seed in range(30):
        assert compose_random_skill(seed, skeleton="strike", rarity="epic").kind == "active"


# ---------------------------------------------------------------------------
# 反應技與姿態（Phase 2E-2）
# ---------------------------------------------------------------------------


def test_explicit_reactions_are_valid_in_every_tier_and_cover_every_event() -> None:
    library = lib()
    events: set[str] = set()
    low, high = tuning_bounds(library)
    for tier in range(1, 6):
        for seed in range(30):
            skill = compose_random_skill(seed, skeleton="reaction", rarity="rare", tier=tier)
            assert validate_skill(skill, library) == [], (tier, seed)
            assert skill.kind == "reaction" and skill.ap_cost is None and skill.reaction
            assert skill.shape.type in ("self", "single")
            events.add(skill.reaction.event)
            assert low <= skill_budget(skill, library).ratio <= high, (tier, seed)
    assert events == {"hit_by_melee", "hit_by_attack", "enemy_leaves_adjacent", "ally_hit_adjacent"}


def test_explicit_stances_are_valid_in_every_tier_and_have_a_stance_status() -> None:
    library = lib()
    stances = {s.id for s in library.ruleset.statuses.statuses if s.stance}
    seen: set[str] = set()
    for tier in range(1, 6):
        for seed in range(30):
            skill = compose_random_skill(seed, skeleton="stance", rarity="rare", tier=tier)
            assert validate_skill(skill, library) == [], (tier, seed)
            assert skill.kind == "stance" and skill.ap_cost is None and skill.shape.type == "self"
            used = {getattr(e, "status", "") for e in skill.effects}
            seen |= used & stances
    assert seen == stances


def test_reactions_and_stances_need_rare_and_ignore_ap_arguments() -> None:
    with pytest.raises(ComposeError):
        compose_random_skill(1, skeleton="reaction", rarity="common")
    with pytest.raises(ComposeError):
        compose_random_skill(1, skeleton="stance", rarity="common")
    with pytest.raises(ComposeError, match="AP"):
        compose_random_skill(1, skeleton="reaction", rarity="rare", ap_cost=2)


def test_reactions_and_stances_never_use_stance_statuses_elsewhere() -> None:
    stances = {s.id for s in lib().ruleset.statuses.statuses if s.stance}
    for seed in range(120):
        skill = compose_random_skill(seed, rarity="epic")
        if skill.kind != "stance":
            assert not stances & {getattr(e, "status", None) for e in skill.effects}, seed


def test_random_reactions_and_stances_appear_without_changing_common_seeds() -> None:
    skills = [compose_random_skill(seed, rarity="rare") for seed in range(200)]
    kinds = {s.kind for s in skills}
    assert {"reaction", "stance"} <= kinds
    assert all(compose_random_skill(seed, rarity="common").kind == "active" for seed in range(60))

    """Phase 2H-1：400 個種子中有自身狀態代價的技能都是主動技能，狀態在允許清單內、2–3 回合。"""
    """Phase 2H-1：400 個種子中有自身狀態代價的技能都是主動技能，狀態在允許內、2–3 回合。"""
    library = lib()
    allowed = set(library.budget.allowance.self_status.allowed)
    found = [
        skill
        for seed in range(400)
        if (skill := compose_random_skill(seed, library=library)).cost.self_status is not None
    ]
    assert found
    for skill in found:
        assert skill.kind == "active"
        assert skill.cost.self_status is not None
        assert skill.cost.self_status.status in allowed
        assert skill.cost.self_status.duration in (2, 3)


def test_the_composer_sometimes_adds_a_valid_dual_attribute_or_mastery() -> None:
    """Phase 2H-2：400 個種子中有雙屬性（史詩以上）與專精的技能，且組合都合法、兩者不並存。"""
    library = lib()
    rules = library.ruleset
    found = [compose_random_skill(seed, library=library) for seed in range(400)]
    dual = [s for s in found if s.secondary_scaling_attr is not None]
    mastered = [s for s in found if s.mastery is not None]
    assert dual and {m.mastery for m in mastered} == {"range", "duration"}
    for skill in dual:
        assert skill.rarity in ("epic", "legendary")
        assert skill.secondary_scaling_attr != skill.scaling_attr
        assert skill.mastery is None
    for skill in mastered:
        assert skill.secondary_scaling_attr is None
        if skill.mastery == "range":
            assert skill.shape.range is not None
        else:
            assert any(e.type == "apply_status" for e in skill.effects)
    assert rules.core.dual_scaling_min_rarity == "epic"


def test_rule_rewrite_primitives_are_hand_written_only() -> None:
    """Phase 3C-4a：改寫規則型原語（光環骨架的核心之一）不會被組合器選到。"""
    library = lib()
    rewrites = {p.id for p in library.ruleset.primitives.primitives if p.category == "rule_rewrite"}
    assert rewrites == {"grant_ap", "reset_cooldown", "cheat_death"}
    for seed in range(60):
        skill = compose_random_skill(seed, rarity="epic", skeleton="aura")
        assert not {e.type for e in skill.effects} & rewrites, seed
