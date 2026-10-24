"""工坊、驗證器、隨機組合器、LLM 提議的武器親和與限定武器（Phase 3I-5，06 6.10 #50）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import WIELDING_EFFECT_ONLY, SkillDef
from trpg.skillgen.affinity import grant_affinity
from trpg.skillgen.draft import build_skill
from trpg.skillgen.option_gear import gear_choices, gear_pool
from trpg.skillgen.option_models import Choice, FieldSpec
from trpg.skillgen.options import draft_options
from trpg.skillgen.proposal import ProposalContext, _Refs, _unheld_errors
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

LIB: ContentLibrary = load_library()


def _step_fields(draft: Mapping[str, Any], step: str) -> tuple[FieldSpec, ...]:
    options = draft_options(draft, LIB)
    return next(s.fields for s in options.steps if s.id == step)


def _field(fields: tuple[FieldSpec, ...], name: str) -> FieldSpec:
    return next(f for f in fields if f.field == name)


def _reason(choice: Choice) -> object:
    return choice.info.get("unavailable_zh")


BASE: dict[str, Any] = {
    "skeleton": "combo",
    "name_zh": "測試技能",
    "ap_cost": 2,
    "kind": "active",
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "tier": 1,
    "shape": {"type": "single", "range": "weapon"},
    "effects": [{"type": "damage", "multiplier_permille": 800, "affects": "enemies"}],
}


# ---------------------------------------------------------------------------
# 工坊：限定武器（多選）與事前停用
# ---------------------------------------------------------------------------


def test_the_gear_pool_lists_playable_weapons_and_offhands_only() -> None:
    ids = [g for g, _, _ in gear_pool(LIB)]
    assert {"whip", "fist", "dual_dagger", "round_shield", "tome"} <= set(ids)
    assert "spark_staff" not in ids  # 召喚物專用的武器不列
    assert len(ids) == len(set(ids))


def test_weapon_only_field_marks_classes_that_do_not_fit_the_weapon_req() -> None:
    field = _field(_step_fields(BASE, "basics"), "weapon_only")
    assert field.type == "multi_choice"
    by_id = {str(c.value): c for c in field.choices}
    assert _reason(by_id["whip"]) is None
    assert _reason(by_id["round_shield"]) is None  # 副手不分大類
    assert "遠程武器" in str(_reason(by_id["bow"])) or "弓" in str(_reason(by_id["bow"]))
    ranged = _field(_step_fields({**BASE, "weapon_req": "ranged"}, "basics"), "weapon_only")
    marked = {str(c.value) for c in ranged.choices if _reason(c) is not None}
    assert "whip" in marked and "pistol" not in marked


def test_the_disabled_options_are_exactly_what_the_validator_rejects() -> None:
    """工坊停用的選項與驗證器同源：停用的選了會違規，沒停用的不會。"""
    field = _field(_step_fields(BASE, "basics"), "weapon_only")
    full = {
        **BASE,
        "name_zh": "測試",
        "rarity": "rare",
        "ap_cost": 2,
        "cost": {"stamina": 8, "cooldown": 2},
        "effects": [
            {"type": "damage", "multiplier_permille": 1100, "affects": "enemies"},
            {"type": "damage", "multiplier_permille": 800, "affects": "enemies"},
        ],
        "condition": None,
        "provenance": {"origin": "workshop"},
    }
    for choice in field.choices:
        skill = build_skill({**full, "weapon_only": [choice.value]})
        rejected = any(v.rule == "reference" for v in validate_skill(skill, LIB))
        assert rejected is (_reason(choice) is not None), choice.value


# ---------------------------------------------------------------------------
# 工坊：武器親和（效果條件）
# ---------------------------------------------------------------------------


def _damage_choice(draft: Mapping[str, Any]) -> Choice:
    effects = _field(_step_fields(draft, "effects"), "effects")
    return next(c for c in effects.choices if c.value == "damage")


def test_damage_effects_get_an_effect_condition_with_the_wielding_weapon() -> None:
    cond = _field(_damage_choice(BASE).params, "condition")
    wield = next(c for c in cond.choices if c.value == "wielding_weapon")
    assert wield.info.get("unavailable_zh") is None  # 效果層級可以選
    weapon = _field(wield.params, "weapon")
    by_id = {str(c.value): c for c in weapon.choices}
    assert _reason(by_id["whip"]) is None and _reason(by_id["bow"]) is not None
    assert [str(c.value) for c in weapon.choices] == [
        str(c.value) for c in gear_choices(LIB, "melee")
    ]


def test_the_skill_level_condition_menu_blocks_the_wielding_condition() -> None:
    field = _field(_step_fields(BASE, "condition"), "condition")
    wield = next(c for c in field.choices if c.value == "wielding_weapon")
    assert _reason(wield) == WIELDING_EFFECT_ONLY


def test_an_affinity_draft_fits_the_options_and_validates() -> None:
    draft = {
        **BASE,
        "name_zh": "鞭擊",
        "rarity": "rare",
        "ap_cost": 2,
        "cost": {"stamina": 8, "cooldown": 2},
        "effects": [
            {"type": "damage", "multiplier_permille": 1100, "affects": "enemies"},
            {
                "type": "damage",
                "multiplier_permille": 1000,
                "affects": "enemies",
                "condition": {"type": "wielding_weapon", "weapon": "whip"},
            },
        ],
        "provenance": {"origin": "workshop"},
    }
    options = draft_options(draft, LIB)
    assert options.problems == ()
    assert validate_skill(build_skill(draft), LIB) == []


# ---------------------------------------------------------------------------
# 隨機組合器：依主角手上的裝備加親和條件
# ---------------------------------------------------------------------------


def _has_affinity(skill: SkillDef) -> bool:
    return any(
        e.condition is not None and e.condition.type == "wielding_weapon" for e in skill.effects
    )


def test_the_composer_adds_affinity_only_for_held_gear_and_stays_valid() -> None:
    held = {"one_handed_sword": "單手劍", "round_shield": "圓盾"}
    granted = 0
    for seed in range(60):
        plain = compose_random_skill(seed, tier=1, rarity="rare", skeleton="combo", library=LIB)
        assert not _has_affinity(plain)
        with_gear = compose_random_skill(
            seed, tier=1, rarity="rare", skeleton="combo", library=LIB, held=held
        )
        assert validate_skill(with_gear, LIB) == []
        if _has_affinity(with_gear):
            granted += 1
            assert with_gear.id == plain.id
            cond = next(
                e.condition
                for e in with_gear.effects
                if e.condition is not None and e.condition.type == "wielding_weapon"
            )
            assert cond.weapon in held  # 只指定主角手上的裝備
            assert [e.type for e in with_gear.effects] == [e.type for e in plain.effects]
    assert granted > 0


def test_affinity_is_deterministic_and_off_without_gear() -> None:
    skill = compose_random_skill(7, tier=1, rarity="rare", skeleton="combo", library=LIB)
    held = {"one_handed_sword": "單手劍"}
    assert grant_affinity(skill, held, LIB) == grant_affinity(skill, held, LIB)
    assert grant_affinity(skill, None, LIB) is skill
    assert grant_affinity(skill, {}, LIB) is skill


def test_affinity_never_picks_a_weapon_of_the_wrong_class() -> None:
    held = {"bow": "弓", "one_handed_sword": "單手劍"}
    for seed in range(80):
        skill = compose_random_skill(
            seed, tier=1, rarity="rare", skeleton="combo", category="weapon", library=LIB, held=held
        )
        for effect in skill.effects:
            if effect.condition is not None and effect.condition.type == "wielding_weapon":
                weapon = LIB.weapons[str(effect.condition.weapon)]
                assert skill.weapon_req in ("any", weapon.weapon_class)


# ---------------------------------------------------------------------------
# LLM 提議：親和條件只能指定主角手上的裝備
# ---------------------------------------------------------------------------


def test_a_proposal_may_only_name_gear_the_hero_holds() -> None:
    skill = LIB.skills["skill_chain_lash"]  # 親和：鞭
    ctx_ok = ProposalContext(1, "rare", held={"whip": "鞭"})
    assert _unheld_errors(skill, ctx_ok) == []
    ctx_bad = ProposalContext(1, "rare", held={"one_handed_sword": "單手劍"})
    errors = _unheld_errors(skill, ctx_bad)
    assert len(errors) == 1 and errors[0].code == "gear.not_held"
    assert errors[0].allowed == ("one_handed_sword",)
    assert _unheld_errors(skill, ProposalContext(1, "rare")) == []  # 沒給手上裝備：不檢查


@pytest.mark.parametrize("weapon", ["whip", "round_shield", "tome"])
def test_the_llm_condition_model_offers_the_playable_gear(weapon: str) -> None:
    assert weapon in _Refs.of(LIB).weapons
