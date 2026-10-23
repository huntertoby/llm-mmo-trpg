"""4-L5c：只能填 true 的開關、只列技能能施加的狀態、專屬錯誤代碼（全部不需要網路與模型）。"""

from __future__ import annotations

import copy
import json
from functools import cache
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    EffectSpec,
    SkillDef,
    SkillRuleError,
    _check_composition,
    composition_rules,
    true_only_params,
)
from trpg.skillgen.proposal import (
    ProposalContext,
    _pydantic_errors,
    budget_statuses,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
    rarity_statuses,
)


@cache
def _lib() -> ContentLibrary:
    return library()


# ---------------------------------------------------------------------------
# 1. 只能填 true 的開關
# ---------------------------------------------------------------------------


def _yaml_true_only() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for primitive in _lib().ruleset.primitives.primitives:
        names = {n for n, spec in primitive.params.items() if spec.true_only}
        if names:
            out[primitive.id] = names
    return out


def test_true_only_list_comes_from_yaml_and_covers_all_flags() -> None:
    assert {k: set(v) for k, v in true_only_params().items()} == _yaml_true_only()
    assert _yaml_true_only() == {"damage": {"explode", "split_heal"}}
    for primitive in _lib().ruleset.primitives.primitives:
        for name, spec in primitive.params.items():
            if spec.true_only:
                assert spec.type == "bool", (primitive.id, name)


def _skill_with(flag: str) -> SkillDef:
    for skill_id in sorted(_lib().skills):
        skill = _lib().skills[skill_id]
        if any(getattr(e, flag, None) for e in skill.effects):
            return skill
    raise AssertionError(f"沒有帶 {flag} 的手寫技能")


@pytest.mark.parametrize("flag", ["explode", "split_heal"])
def test_flag_schema_only_accepts_true(flag: str) -> None:
    models = build_proposal_models(_lib())
    schema = json.dumps(models.json_schema(), ensure_ascii=False)
    assert f'"{flag}":{{' in schema.replace(" ", "")
    skill = _lib().skills["skill_fire_arrow"]
    proposal = proposal_from_skill(skill, _lib())
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity)

    def with_flag(value: bool) -> dict[str, Any]:
        data = copy.deepcopy(proposal)
        for effect in data["effects"]:
            if effect["type"] == "damage":
                effect[flag] = value
        return data

    ok = evaluate_proposal(with_flag(True), models, _lib(), ctx)
    assert not [e for e in ok.errors if e.stage == "proposal"]
    bad = evaluate_proposal(with_flag(False), models, _lib(), ctx)
    errors = [e for e in bad.errors if e.stage == "proposal"]
    assert errors and all(e.code == "literal_error" for e in errors)
    assert any(e.path.endswith(flag) for e in errors)


def test_skill_validator_reports_flag_true_only_with_path() -> None:
    skill = _skill_with("explode")
    data = skill.model_dump(mode="json", exclude_none=True)
    for effect in data["effects"]:
        if effect.get("explode"):
            effect["explode"] = False
    with pytest.raises(ValidationError) as caught:
        SkillDef.model_validate(data)
    errors = _pydantic_errors(caught.value, "skill", data)
    assert [e.code for e in errors] == ["flag.true_only"]
    assert errors[0].path.endswith(".explode") and errors[0].path.startswith("effects[")


# ---------------------------------------------------------------------------
# 2. 列舉只放技能能用的 ID
# ---------------------------------------------------------------------------


def _status_enums(schema: dict[str, Any]) -> dict[str, list[str]]:
    """每個 apply_status 型號（頂層與巢狀位置）的 status 可用值。"""
    out: dict[str, list[str]] = {}
    for name, model in schema["$defs"].items():
        if name.endswith("_apply_status") and model.get("properties", {}).get("status"):
            status = model["properties"]["status"]
            out[name] = status.get("enum") or [status["const"]]
    return out


def test_apply_status_lists_only_statuses_with_budget_points() -> None:
    lib = _lib()
    without = {s.id for s in lib.ruleset.statuses.statuses if s.budget_points is None}
    assert "charging" in without  # 蓄力：沒有預算點數
    expected = set(budget_statuses(lib))
    assert expected.isdisjoint(without) and expected
    enums = _status_enums(build_proposal_models(lib).json_schema())
    assert enums and all(set(v) == expected for v in enums.values())


def test_rarity_and_budget_filters_combine() -> None:
    lib = _lib()
    models = build_proposal_models(lib, rarity="common")
    expected = set(budget_statuses(lib)) & set(rarity_statuses(lib, "common"))
    enums = _status_enums(models.json_schema())
    assert enums and all(set(v) == expected for v in enums.values())
    assert expected < set(budget_statuses(lib))


def test_a_status_without_budget_points_is_rejected_by_the_proposal_model() -> None:
    lib = _lib()
    models = build_proposal_models(lib)
    skill = _lib().skills["skill_fire_arrow"]
    proposal = proposal_from_skill(skill, lib)
    proposal["effects"] = [*proposal["effects"], {"type": "apply_status", "status": "burning"}]
    for effect in proposal["effects"]:
        if effect["type"] == "apply_status":
            effect["status"] = "charging"
    result = evaluate_proposal(
        proposal, models, lib, ProposalContext(tier=skill.tier, rarity=skill.rarity)
    )
    assert any(e.stage == "proposal" and e.code == "literal_error" for e in result.errors)
    assert not any(e.code == "budget.unavailable" for e in result.errors)


# ---------------------------------------------------------------------------
# 4. 專屬錯誤代碼
# ---------------------------------------------------------------------------


def _effects(*specs: tuple[str, str]) -> tuple[EffectSpec, ...]:
    return tuple(EffectSpec.model_construct(type=t, affects=a) for t, a in specs)  # type: ignore[arg-type]


def _raises(kind: str, effects: tuple[EffectSpec, ...]) -> SkillRuleError:
    with pytest.raises(SkillRuleError) as caught:
        _check_composition(kind, effects)
    return caught.value


def _rules(attr: str) -> list[str]:
    return sorted(
        r.primitive for r in composition_rules().values() if getattr(r, attr) not in (None, False)
    )


@pytest.mark.parametrize("name", _rules("max_per_skill"))
def test_code_max_per_skill(name: str) -> None:
    rule = composition_rules()[name]
    assert rule.max_per_skill is not None
    error = _raises("active", _effects(*[(name, "self")] * (rule.max_per_skill + 1)))
    assert error.code == "combo.max_per_skill"
    assert error.path.startswith("effects[")


@pytest.mark.parametrize("name", _rules("sole_effect"))
def test_code_sole_effect(name: str) -> None:
    error = _raises("active", _effects((name, "self"), ("damage", "self")))
    assert (error.code, error.path) == ("combo.sole_effect", "effects")


@pytest.mark.parametrize("name", _rules("position"))
def test_code_position(name: str) -> None:
    rule = composition_rules()[name]
    effects = (
        _effects(("damage", "self"), (name, "self"))
        if rule.position == "first"
        else _effects((name, "self"), ("damage", "self"))
    )
    error = _raises("active", effects)
    assert error.code == "combo.position"


@pytest.mark.parametrize("name", _rules("others_affect"))
def test_code_others_affect(name: str) -> None:
    error = _raises("active", _effects((name, "self"), ("damage", "enemies")))
    assert error.code == "combo.others_affect"
    assert error.path == "effects[1].affects"


@pytest.mark.parametrize("name", _rules("active_only"))
def test_code_active_only(name: str) -> None:
    error = _raises("passive", _effects((name, "self")))
    assert (error.code, error.path) == ("combo.active_only", "kind")


def test_combo_code_reaches_the_proposal_error() -> None:
    """手寫技能複製一個「每技能最多 N 個」的效果 → ``stage: skill`` 的錯誤代碼是 ``combo.*``。"""
    limited = {
        r.primitive: r.max_per_skill for r in composition_rules().values() if r.max_per_skill
    }
    for skill_id in sorted(_lib().skills):
        skill = _lib().skills[skill_id]
        hit = next((e for e in skill.effects if e.type in limited and limited[e.type] == 1), None)
        if hit is None:
            continue
        data = skill.model_dump(mode="json", exclude_none=True)
        data["effects"] = [
            *data["effects"],
            copy.deepcopy(data["effects"][skill.effects.index(hit)]),
        ]
        with pytest.raises(ValidationError) as caught:
            SkillDef.model_validate(data)
        errors = _pydantic_errors(caught.value, "skill", data)
        assert "combo.max_per_skill" in [e.code for e in errors]
        return
    raise AssertionError("沒有使用限制每技能一個的原語的手寫技能")
