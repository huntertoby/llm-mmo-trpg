"""Phase 3-25a：戰場變奏的 schema 與驗證、預算逐型態＋加價、關鍵字聯集、示範技能。"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.library import skill_reference_problems
from trpg.content.skills import SkillDef
from trpg.narrative.skill_icon import icon_of
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.validate import validate_skill

DEMOS = (
    "skill_tidal_spear",
    "skill_wall_brace_bash",
    "skill_oil_spark_throw",
    "skill_frost_ledge_cleave",
)
_WATER = {"id": "wet", "name_zh": "濕", "when": {"caster_surface": ["water"]}, "range_delta": 1}


def _data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "skill_t_variant",
        "name_zh": "測試變奏",
        "tier": 1,
        "rarity": "rare",
        "skeleton": "combo",
        "category": "spell",
        "weapon_req": "focus",
        "ap_cost": 2,
        "scaling_attr": "int",
        "shape": {"type": "single", "range": 3},
        "effects": [
            {"type": "damage", "dice": "2d6", "element": "ice"},
            {"type": "apply_status", "status": "slow", "duration": 1},
        ],
        "condition": {"type": "target_has_status", "status": "slow"},
        "cost": {"mana": 4, "cooldown": 2},
        "variants": [_WATER],
    }
    data.update(overrides)
    return data


def _problems(skill: SkillDef) -> list[str]:
    lib = library()
    return skill_reference_problems(skill, lib.ruleset, lib.skills)


def test_a_valid_variant_builds_its_form() -> None:
    skill = SkillDef.model_validate(_data())
    form = skill.variant_form("wet")
    assert form.shape.range == 4 and form.variants == () and form.id == skill.id
    assert form.cost == skill.cost and form.skeleton == skill.skeleton
    assert _problems(skill) == []


# ---------------------------------------------------------------------------
# schema 拒絕
# ---------------------------------------------------------------------------


def test_common_skills_cannot_carry_variants() -> None:
    skill = SkillDef.model_validate(_data(rarity="common"))
    assert any("稀有度 common 最多帶 0 個變奏" in p for p in _problems(skill))


def test_rare_skills_carry_one_and_epic_two() -> None:
    second = {**_WATER, "id": "wet2"}
    rare = SkillDef.model_validate(_data(variants=[_WATER, second]))
    assert any("稀有度 rare 最多帶 1 個變奏" in p for p in _problems(rare))
    epic = SkillDef.model_validate(_data(rarity="epic", variants=[_WATER, second]))
    assert _problems(epic) == []


def test_three_variants_are_rejected() -> None:
    three = [{**_WATER, "id": f"v{i}"} for i in range(3)]
    with pytest.raises(ValidationError, match="最多 2 個變奏"):
        SkillDef.model_validate(_data(rarity="epic", variants=three))


def test_composite_skills_cannot_carry_variants() -> None:
    lib = library()
    composite = next(s for s in lib.skills.values() if s.followup is not None)
    data = composite.model_dump(mode="json", exclude_defaults=True)
    data["variants"] = [{**_WATER, "range_delta": None, "element": "fire"}]
    with pytest.raises(ValidationError, match="複合技能"):
        SkillDef.model_validate(data)


def test_the_main_damage_and_the_only_effect_cannot_be_replaced() -> None:
    swap = {"index": 0, "effect": {"type": "damage", "dice": "1d4", "element": "fire"}}
    bad = {**_WATER, "range_delta": None, "replace_effect": swap}
    with pytest.raises(ValidationError, match="主傷害"):
        SkillDef.model_validate(_data(variants=[bad]))
    lone = _data(effects=[{"type": "damage", "dice": "2d6", "element": "ice"}], variants=[bad])
    with pytest.raises(ValidationError, match="唯一的效果"):
        SkillDef.model_validate(lone)
    side = {"index": 1, "effect": {"type": "apply_status", "status": "weaken", "duration": 1}}
    ok = SkillDef.model_validate(
        _data(variants=[{**_WATER, "range_delta": None, "replace_effect": side}])
    )
    assert ok.variant_form("wet").effects[1].status == "weaken"


def test_only_active_skills_may_carry_variants() -> None:
    lib = library()
    reaction = lib.skills["skill_ambush_stab"].model_dump(mode="json", exclude_defaults=True)
    reaction["variants"] = [{**_WATER, "range_delta": None, "element": "fire"}]
    with pytest.raises(ValidationError, match="只有主動技能可以帶變奏"):
        SkillDef.model_validate(reaction)


@pytest.mark.parametrize(
    ("variant", "message"),
    [
        ({**_WATER, "when": {}}, "恰好填一種"),
        ({**_WATER, "when": {"caster_surface": ["water"], "caster_high_ground": True}}, "恰好"),
        ({**_WATER, "range_delta": None}, "1～2 項"),
        ({**_WATER, "element": "fire", "shape": {"type": "line", "size": 3}}, "1～2 項"),
        ({**_WATER, "range_delta": 0}, "不可為 0"),
        ({**_WATER, "cooldown": 1}, "Extra inputs"),  # 不能改代價
        ({**_WATER, "range_delta": None, "skeleton": "strike"}, "Extra inputs"),  # 不能改骨架
    ],
)
def test_bad_variant_shapes_are_rejected(variant: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(_data(variants=[variant]))


def test_unknown_surfaces_are_cross_checked() -> None:
    skill = SkillDef.model_validate(
        _data(variants=[{**_WATER, "when": {"caster_surface": ["grass"]}}])
    )
    assert any("未知的表面 grass" in p for p in _problems(skill))


def test_range_delta_needs_a_numeric_range() -> None:
    with pytest.raises(ValidationError, match="射程是數字"):
        SkillDef.model_validate(_data(shape={"type": "single", "range": "weapon"}))


# ---------------------------------------------------------------------------
# 預算：逐型態 ＋ 加價
# ---------------------------------------------------------------------------


def test_budget_adds_the_surcharge_per_variant_and_reports_each_form() -> None:
    lib = library()
    surcharge = lib.budget.variant_surcharge_permille
    assert surcharge == 100
    spear = lib.skills["skill_tidal_spear"]
    report = skill_budget(spear, lib)
    plain = skill_budget(spear.model_copy(update={"variants": ()}), lib)
    assert report.variant_surcharge_permille == 2 * surcharge
    assert report.total == plain.total * Fraction(1000 + 2 * surcharge, 1000)
    assert [v.id for v in report.variants] == ["tide_pierce", "high_tide"]
    for form in report.variants:
        expected = skill_budget(spear.variant_form(form.id), lib)
        assert form.report.total == expected.total and form.report.ok


def test_a_form_outside_the_window_is_a_violation() -> None:
    lib = library()
    strong = {"type": "damage", "dice": "6d6", "element": "fire"}
    data = _data(variants=[{**_WATER, "range_delta": None, "add_effect": strong}])
    rules = {v.rule for v in validate_skill(SkillDef.model_validate(data), lib)}
    assert "variant.wet.budget.over" in rules


# ---------------------------------------------------------------------------
# 關鍵字聯集
# ---------------------------------------------------------------------------


def test_keywords_are_the_union_of_all_forms() -> None:
    lib = library()
    spear = derive_keywords(lib.skills["skill_tidal_spear"], lib.keywords)
    assert "charged" in spear.makes and "charged" in spear.variant  # 水中型態的雷
    assert "frozen" in spear.makes and "frozen" not in spear.variant  # 基礎型態就有
    bash = derive_keywords(lib.skills["skill_wall_brace_bash"], lib.keywords)
    assert "collision" in bash.makes and bash.variant == ("collision",)
    exclusive = derive_keywords(
        lib.skills["skill_oil_spark_throw"], lib.keywords, exclusive_only=True
    )
    assert "ignite" in exclusive.makes and exclusive.variant == ("ignite",)
    plain = derive_keywords(lib.skills["skill_fire_bolt"], lib.keywords)
    assert plain.variant == ()


# ---------------------------------------------------------------------------
# 示範技能
# ---------------------------------------------------------------------------


def test_the_demo_skills_cover_every_condition_and_pass_validation() -> None:
    lib = library()
    skills = [lib.skills[s] for s in DEMOS]
    assert sorted(s.rarity for s in skills) == ["epic", "epic", "rare", "rare"]
    kinds = {v.when.kind for s in skills for v in s.variants}
    assert kinds == {
        "caster_surface",
        "caster_high_ground",
        "caster_adjacent_blocker",
        "target_surface",
    }
    assert {s.weapon_req for s in skills} >= {"melee", "focus"}  # 近戰與法術都有
    for skill in skills:
        assert validate_skill(skill, lib) == [], skill.id
        assert skill_budget(skill, lib).ok
        icon = icon_of(skill.model_dump(mode="json"))
        assert not icon.partial and icon.segments[0].shape_id is not None
