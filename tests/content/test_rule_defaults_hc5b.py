"""HC-5b：組合器、候選、挑選、預算與進化的常數（原本寫死在 ``skillgen/``）搬進 content 之後的
規則對照。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.composer_rules import ComposerRules, ProposalSearch, composer_rule_problems
from trpg.content.roguelite import RunRules
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_pick import SkillPickRules
from trpg.content.skill_rules import BudgetRules


def _read(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


_COMPOSER = [
    ("structure", "delayed_damage_rounds"),
    ("structure", "delayed_damage_radius"),
    ("structure", "gamble_win_permille"),
    ("structure", "gamble_backlash_permille"),
    ("structure", "gamble_backlash_chance_permille"),
    ("structure", "second_element_multiplier_permille"),
    ("condition", "point_blank_min_reach"),
    ("sacrifice", "radius"),
    ("special", "ladders"),
    ("special", "condition_permille"),
    ("special", "source_points"),
    ("special", "grant_ap_amounts"),
    ("special", "rewrite_ranges"),
    ("special", "cheat_death_durations"),
    ("special", "redirect_permille"),
    ("special", "redirect_durations"),
    ("special", "lasting_mana"),
    ("special", "lasting_cooldowns"),
    ("variant", "range_delta"),
    ("llm_topic", "max_keywords"),
    ("llm_topic", "witness_min_keywords"),
    ("llm_topic", "max_nested_effects"),
    ("llm_topic", "max_tags"),
    ("llm_cost", "default_ap"),
    ("recipes", "param_permille"),
    ("recipes", "high_ground_permille"),
    ("recipes", "exploit_surface_permille"),
    ("search",),
    *(("search", name) for name in ("composer_attempts", "keyword_tries", "probe_cooldown")),
    *(("search", "proposal", name) for name in ProposalSearch.model_fields),
]
_OTHERS: list[tuple[str, type[BaseModel], tuple[str, ...]]] = [
    ("skill_budget.yaml", BudgetRules, ("shield_duration_start",)),
    ("skill_budget.yaml", BudgetRules, ("modifier", "shape_to_reference_size")),
    *(
        ("skill_budget.yaml", BudgetRules, ("retier_growth", name))
        for name in (
            "weak_floor_exempt_min_tier",
            "summon_hp_steps",
            "cost_scales_permille",
            "rock_multiplier_permille",
        )
    ),
    *(
        ("skill_evolution.yaml", EvolutionTable, (name,))
        for name in (
            "low_multiplier_floor",
            "low_multiplier_step",
            "first_knob_weight",
            "extra_cooldown_steps",
            "min_cooldown",
            "max_cooldown",
        )
    ),
    *(
        ("skill_pick.yaml", SkillPickRules, ("pool", name))
        for name in (
            "max_off_route",
            "slot_keyword_tries",
            "wish_cards",
            "wish_seed_permille",
            "wish_tag_extra",
        )
    ),
    ("roguelite.yaml", RunRules, ("candidates", "bridge_variant_cap")),
]


def _drop(data: dict[str, Any], path: tuple[str, ...]) -> None:
    node = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]


@pytest.mark.parametrize("path", _COMPOSER, ids="/".join)
def test_composer_numbers_have_no_program_default(path: tuple[str, ...]) -> None:
    """程式不再有模組常數：``skill_composer.yaml`` 少寫一格就驗證失敗。"""
    data = _read("skill_composer.yaml")
    _drop(data, path)
    with pytest.raises(ValidationError, match=path[-1]):
        ComposerRules.model_validate(data)


@pytest.mark.parametrize(
    ("name", "model", "path"), _OTHERS, ids=[f"{n}:{'/'.join(p)}" for n, _, p in _OTHERS]
)
def test_other_numbers_have_no_program_default(
    name: str, model: type[BaseModel], path: tuple[str, ...]
) -> None:
    data = _read(name)
    _drop(data, path)
    with pytest.raises(ValidationError, match=path[-1]):
        model.model_validate(data)


def test_values_are_the_old_constants() -> None:
    """搬家照現值：內容檔的值等於原本寫死的常數（HC-5b 不改數值）。"""
    lib = library()
    c = lib.composer
    assert c.structure.gamble_win_permille == (1500, 2000, 2500, 3000)
    assert c.structure.gamble_backlash_permille == (250, 500, 750)
    assert c.structure.gamble_backlash_chance_permille == 700
    assert (c.structure.delayed_damage_rounds.min, c.structure.delayed_damage_rounds.max) == (1, 3)
    assert (c.sacrifice.radius.min, c.sacrifice.radius.max) == (0, 2)
    assert c.condition.point_blank_min_reach == 2
    ladders = c.special.ladders
    assert ladders.damage_permille == tuple(range(100, 701, 50))
    assert ladders.hit_bonus == (1, 2, 3) and ladders.cooldown_delta == (-1, -2)
    assert c.special.lasting_mana == (1, 4, 8, 12)
    assert c.special.lasting_cooldowns == (2, 3, 4, 5, 6)
    assert (c.variant.range_delta.min, c.variant.range_delta.max) == (-3, 3)
    assert c.search.composer_attempts == 100 and c.search.keyword_tries == 300
    assert c.search.proposal.witness_max == 24
    growth = lib.budget.retier_growth
    assert growth.summon_hp_steps == (0, 100, 200, 300, 450, 600, 800, 1000)
    assert growth.cost_scales_permille == (1000, 500, 0)
    assert lib.skill_pick.pool.wish_cards == 3
    assert lib.roguelite.candidates.bridge_variant_cap == 400


def test_default_ap_cannot_exceed_the_ap_cap() -> None:
    """補值器補的 AP 不能超過 ``skill_limits.max_ap_cost``（載入檢查，同白板 AP）。"""
    lib = library()
    top = lib.ruleset.core.skill_limits.max_ap_cost
    cost = lib.composer.llm_cost.model_copy(update={"default_ap": top + 1})
    composer = lib.composer.model_copy(update={"llm_cost": cost})
    basic = lib.budget.min_character_tier.basic_summon_units
    problems = composer_rule_problems(composer, lib.ruleset.core, basic)
    assert any("llm_cost.default_ap" in p for p in problems)


def test_wish_candidates_cannot_be_fewer_than_the_cards() -> None:
    data = _read("skill_pick.yaml")
    data["pool"]["wish_candidates"] = data["pool"]["wish_cards"] - 1
    with pytest.raises(ValidationError, match="wish_cards"):
        SkillPickRules.model_validate(data)
