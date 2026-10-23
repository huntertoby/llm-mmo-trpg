"""Phase 3-25b：戰場變奏的隨機組合器、進化模板、工坊步驟。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.evolution import EvolutionRequest, _build
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.variant_gen import add_variant, variant_eligible


def test_the_composer_makes_valid_variants_for_seeds_0_to_49() -> None:
    lib = library()
    made = 0
    for seed in range(50):
        skill = compose_random_skill(seed, library=lib)
        assert validate_skill(skill, lib) == [], seed
        if skill.variants:
            made += 1
            assert skill.rarity != "common" and skill.kind == "active"
            assert len(skill.variants) <= lib.ruleset.core.variant_max_by_rarity[skill.rarity]
    assert made >= 1


def test_the_composer_is_deterministic_with_variants() -> None:
    lib = library()
    seeds = [s for s in range(50) if compose_random_skill(s, library=lib).variants]
    assert seeds
    for seed in seeds:
        assert compose_random_skill(seed, library=lib) == compose_random_skill(seed, library=lib)


def test_common_skills_never_get_variants_from_the_composer() -> None:
    lib = library()
    for seed in range(40):
        assert compose_random_skill(seed, rarity="common", library=lib).variants == ()


def test_add_variant_respects_the_rarity_cap() -> None:
    lib = library()
    rare = lib.skills["skill_oil_spark_throw"]  # 稀有已經帶 1 個，滿了
    assert not variant_eligible(rare, lib)
    assert add_variant(rare, lib, Rng(1)) is None
    assert not variant_eligible(lib.skills["skill_fire_bolt"], lib)  # 普通


def test_the_evolution_variant_op_builds_a_legal_skill() -> None:
    lib = library()
    template = next(t for t in lib.evolution.templates if t.op == "variant")
    assert template.id == "battle_variant" and template.branch == "deepen"
    built = 0
    for skill in lib.skills.values():
        if skill.kind != "active" or skill.followup is not None or skill.trap is not None:
            continue
        request = EvolutionRequest(skill, SkillUsage(uses=4, targets=4, distance=8), {}, 5)
        evolved = _build(request, template, None, lib)
        if evolved is None:
            continue
        built += 1
        assert evolved.variants and validate_skill(evolved, lib) == []
        assert evolved.rarity != "common"
        if built >= 6:
            break
    assert built >= 1


def _epic_draft() -> dict[str, Any]:
    skill = compose_random_skill(3, rarity="epic", library=library())
    return skill.model_dump(mode="json", exclude_none=True)


def test_the_workshop_offers_a_variants_step_for_rare_and_above() -> None:
    lib = library()
    options = draft_options(_epic_draft(), lib)
    assert options.next_step is None
    step = options.steps[-1]
    assert step.id == "variants"
    field = step.fields[0]
    assert field.type == "variants" and field.max_count == 2
    assert {f.field for f in field.fields} >= {"id", "name_zh", "when", "shape", "range_delta"}
    common = compose_random_skill(3, rarity="common", library=lib).model_dump(
        mode="json", exclude_none=True
    )
    assert "variants" not in [s.id for s in draft_options(common, lib).steps]


def test_the_workshop_shows_a_budget_per_form() -> None:
    lib = library()
    draft = _epic_draft()
    draft["variants"] = [
        {
            "id": "high_reach",
            "name_zh": "居高遠投",
            "when": {"caster_high_ground": True},
            "range_delta": 1,
        }
    ]
    check = check_draft(draft, lib)
    assert check.budget is not None and len(check.budget.variants) == 1
    form = check.budget.variants[0]
    assert form.id == "high_reach" and form.range_text.startswith("射程 ")
    assert check.budget.variant_surcharge_permille == lib.budget.variant_surcharge_permille
    assert check.skill is not None
    SkillDef.model_validate(check.skill)


def test_the_workshop_reports_bad_variants_as_problems() -> None:
    draft = _epic_draft()
    draft["variants"] = [{"id": "bad", "name_zh": "壞", "when": {}, "range_delta": 1}]
    check = check_draft(draft, library())
    assert not check.legal and check.problems
