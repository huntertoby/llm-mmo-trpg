"""RC-1：組合器補配方（``docs/玩法PM交接.md`` 4.1.19，``docs/phases/PhaseRC-1報告.md``）。"""

from __future__ import annotations

import dataclasses
from functools import cache

import pytest

from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordRule
from trpg.content.skills import CASTER_CONDITIONS, SkillDef
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.composer_recipes import (
    beside_keywords,
    passive_recipes,
    pick_recipe,
    reaction_recipes,
    summon_choices,
    unit_keywords,
)
from trpg.skillgen.random_composer import (
    ComposeError,
    compose_random_skill,
    compose_with_stats,
    default_library,
)
from trpg.skillgen.validate import validate_skill

SEEDS = range(12)


@cache
def _without_recipes() -> ContentLibrary:
    """RC-1 前的組合器：三個新配方的機率都是 0。"""
    lib = default_library()
    recipes = lib.composer.recipes.model_copy(
        update={"passive_permille": 0, "reaction_permille": 0, "summon_permille": 0}
    )
    composer = lib.composer.model_copy(update={"recipes": recipes})
    return dataclasses.replace(lib, composer=composer)


@cache
def _with_beside_rule() -> ContentLibrary:
    """推導表多一條「召喚到身邊＝製造召喚物」（RC-1 時還沒有；伴生、護主在有這條時才生效）。"""
    lib = default_library()
    keywords = tuple(
        k.model_copy(update={"makes": (*k.makes, KeywordRule(effect="summon_beside"))})
        if k.id == "summon"
        else k
        for k in lib.keywords.keywords
    )
    return dataclasses.replace(lib, keywords=lib.keywords.model_copy(update={"keywords": keywords}))


def _same(a: SkillDef, b: SkillDef) -> bool:
    return a.model_dump(mode="json") == b.model_dump(mode="json")


@pytest.mark.parametrize("skeleton", ["passive", "reaction"])
def test_seeds_without_a_recipe_are_unchanged(skeleton: str) -> None:
    """沒抽到新配方的種子，結果與 RC-1 前（機率 0）逐字相同。"""
    lib = default_library()
    recipes = passive_recipes(lib, 2) if skeleton == "passive" else reaction_recipes(lib, 2)
    permille = (
        lib.composer.recipes.passive_permille
        if skeleton == "passive"
        else lib.composer.recipes.reaction_permille
    )
    checked = 0
    for seed in range(40):
        if pick_recipe(seed, skeleton, recipes, permille, None) is not None:
            continue
        new = compose_random_skill(seed, tier=2, rarity="epic", skeleton=skeleton, library=lib)
        old = compose_random_skill(
            seed, tier=2, rarity="epic", skeleton=skeleton, library=_without_recipes()
        )
        assert _same(new, old), seed
        checked += 1
    assert checked > 20


def test_plain_active_seeds_without_summon_are_unchanged() -> None:
    lib = default_library()
    for seed in range(30):
        new = compose_random_skill(seed, tier=2, rarity="rare", library=lib)
        if new.skeleton == "summon":
            continue
        old = compose_random_skill(seed, tier=2, rarity="rare", library=_without_recipes())
        assert _same(new, old), seed


def test_tier_one_summons_only_basic_units() -> None:
    lib = default_library()
    basic = set(lib.budget.min_character_tier.basic_summon_units)
    assert {u.unit for u in summon_choices(lib, 1, None)} == basic
    for seed in SEEDS:
        skill = compose_random_skill(seed, tier=1, rarity="rare", skeleton="summon", library=lib)
        assert skill.kind == "active"
        assert next(e.unit for e in skill.effects if e.type == "summon") in basic
        assert not validate_skill(skill, lib)


def test_summon_list_excludes_afterimage_and_prefers_matching_units() -> None:
    lib = default_library()
    units = {u.unit for u in summon_choices(lib, 2, None)}
    assert "summon_afterimage" not in units
    fire = summon_choices(lib, 2, "ignite")
    assert fire and all("ignite" in unit_keywords(lib, u.unit) for u in fire)
    for seed in SEEDS:
        skill = compose_random_skill(
            seed, tier=2, rarity="epic", skeleton="summon", keyword="high_ground", library=lib
        )
        unit = next(e.unit for e in skill.effects if e.type == "summon")
        assert "high_ground" in unit_keywords(lib, unit)
        assert 1 <= next(e.duration for e in skill.effects if e.type == "summon") <= 4


def test_common_still_has_no_summon() -> None:
    """Q4：規則照現行，common 沒有召喚。"""
    with pytest.raises(ComposeError):
        compose_random_skill(0, tier=2, rarity="common", skeleton="summon")


@pytest.mark.parametrize("tier", [1, 3])
def test_epic_passive_high_ground_q12(tier: int) -> None:
    """Q12：epic 被動＋高處組得出來，而且 ``height_advantage`` 只配有另一方的觸發、作用在另一方。"""
    lib = default_library()
    triggers = {t.id: t for t in lib.ruleset.skill_triggers.triggers}
    for seed in SEEDS:
        skill = compose_with_stats(
            seed, tier=tier, rarity="epic", skeleton="passive", keyword="high_ground", library=lib
        ).skill
        assert skill_has_keywords(skill, ["high_ground"], lib)
        assert skill.trigger is not None and skill.condition is not None
        if skill.condition.type == "height_advantage":
            assert triggers[skill.trigger.event].has_other
            assert skill.trigger.target == "other"


@pytest.mark.parametrize("stack", ["combo_point", "fury", "focus", "ki"])
def test_passive_stack_recipes(stack: str) -> None:
    lib = default_library()
    events = {e.event for e in lib.composer.recipes.stack_events[stack]}
    for seed in SEEDS:
        skill = compose_with_stats(
            seed, tier=2, rarity="epic", skeleton="passive", keyword=stack, library=lib
        ).skill
        assert skill.trigger is not None and skill.trigger.max_per_round == 1
        adds = [e for e in skill.effects if e.type == "add_stack"]
        assert not any(e.type == "consume_stack" for e in skill.effects)
        if adds:  # 累積：+1、時機照層數的個性
            assert adds[0].amount == 1 and adds[0].stack == stack
            assert skill.trigger.event in events
        else:  # 利用：自身層數達 N，層數不扣
            assert skill.condition is not None
            assert skill.condition.type == "self_stack_at_least"
            assert skill.condition.count == lib.composer.recipes.stack_counts[stack]


@pytest.mark.parametrize("keyword", ["prone", "marked", "wet"])
def test_passive_exploit_conditions_target_the_other_party(keyword: str) -> None:
    lib = default_library()
    triggers = {t.id: t for t in lib.ruleset.skill_triggers.triggers}
    for seed in SEEDS:
        skill = compose_with_stats(
            seed, tier=2, rarity="epic", skeleton="passive", keyword=keyword, library=lib
        ).skill
        assert skill_has_keywords(skill, [keyword], lib)
        condition = skill.condition
        if condition is not None and condition.type not in CASTER_CONDITIONS:
            assert skill.trigger is not None
            assert triggers[skill.trigger.event].has_other
            assert skill.trigger.target == "other"


@pytest.mark.parametrize("keyword", ["fury", "high_ground", "wet", "ki"])
def test_reaction_recipes(keyword: str) -> None:
    lib = default_library()
    for seed in SEEDS:
        skill = compose_with_stats(
            seed, tier=2, rarity="rare", skeleton="reaction", keyword=keyword, library=lib
        ).skill
        assert skill.kind == "reaction"
        assert skill_has_keywords(skill, [keyword], lib)
        assert not any(e.type == "consume_stack" for e in skill.effects)
        if skill.condition is not None and skill.condition.type == "height_advantage":
            assert skill.shape.type == "single"  # 比的是觸發者（攻擊者）


def test_keyword_composer_only_counts_exclusive_rules() -> None:
    """RC-0 第 4 節第 6 項：指定關鍵字時只認專屬規則。"""
    lib = default_library()
    for seed in SEEDS:
        skill = compose_with_stats(seed, tier=2, keyword="summon", library=lib).skill
        assert skill_has_keywords(skill, ["summon"], lib)


def test_companion_and_guardian_wait_for_a_keyword_rule() -> None:
    """``summon_beside`` 沒有推導規則時伴生、護主不列入；補上規則後組得出來。"""
    lib = default_library()
    assert beside_keywords(lib, 2) == ()
    patched = _with_beside_rule()
    assert "summon" in beside_keywords(patched, 2)
    passive = compose_with_stats(
        0, tier=2, rarity="epic", skeleton="passive", keyword="summon", library=patched
    ).skill
    assert passive.trigger is not None and passive.trigger.event == "on_battle_start"
    assert [e.type for e in passive.effects] == ["summon_beside"]
    reaction = compose_with_stats(
        0, tier=2, rarity="rare", skeleton="reaction", keyword="summon", library=patched
    ).skill
    assert reaction.reaction is not None and reaction.reaction.event == "hit_by_melee"
    assert reaction.effects[0].strike_other
