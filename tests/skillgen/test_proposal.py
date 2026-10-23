"""LLM 技能提議模型（Phase 3E-2g 原型，4-L3 正式化）：由 YAML 產生的 discriminated union、提議不含
數值、提議 → SkillDef 的結構往返、結構化錯誤。全部用固定的提議 JSON，不需要網路與模型。"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.known_budget_exceptions import RANGE_BUDGET_EXCEPTIONS
from tests.skillgen.helpers import general_effect_tags, standard_form, union_tags
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.proposal import (
    LLM_ID_PREFIX,
    ProposalContext,
    ProposalModels,
    ProposalResult,
    build_proposal_models,
    evaluate_proposal,
    feedback_payload,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import (
    NumberFiller,
    apply_numbers,
    fixed_filler,
    minimal_filler,
    numeric_param_names,
    split_numbers,
)


@cache
def _lib() -> ContentLibrary:
    return library()


@cache
def _models() -> ProposalModels:
    return build_proposal_models(_lib())


def _evaluate(data: str | dict[str, Any], ctx: ProposalContext | None = None) -> ProposalResult:
    ctx = ctx or ProposalContext(tier=1, rarity="rare")
    return evaluate_proposal(data, _models(), _lib(), ctx)


def _same(a: SkillDef, b: SkillDef) -> bool:
    """除了 ID 與來源（呼叫端決定）以外完全相同；武器技的縮放屬性由引擎設為武器大類主屬性
    （看手上武器，3H-6），不比對。``skill_scaling.yaml`` 例外清單裡的內建技能（3H-7）：提議出來的
    技能沒有那個 ID，縮放屬性依效果推導的主題收進允許範圍，也不比對。"""
    skip = {"id", "provenance"}
    excepted = {o.skill for o in _lib().skill_scaling.overrides}
    if b.category == "weapon" or b.id in excepted:
        skip |= {"scaling_attr", "secondary_scaling_attr"}
    return a.model_dump(exclude=skip) == b.model_dump(exclude=skip)


def _special_ids() -> set[str]:
    return {
        p.id
        for p in _lib().ruleset.primitives.primitives
        if p.allowed_shapes is not None or p.position or p.sole_effect or p.others_affect
    }


# ---------------------------------------------------------------------------
# 模型產生
# ---------------------------------------------------------------------------


def test_one_branch_per_primitive_from_yaml() -> None:
    lib = _lib()
    schema = _models().json_schema()
    primitives = lib.ruleset.primitives.by_id()
    # 一般型態只有沒有組合規則的原語；有組合規則的原語在自己的型態（Phase 4-L5b）
    assert general_effect_tags(schema) == set(primitives) - _special_ids()
    assert {f"Effect_{i}" for i in primitives} <= set(schema["$defs"])
    for primitive in primitives.values():
        model = schema["$defs"][f"Effect_{primitive.id}"]
        # 每一支只有該原語自己的非數值參數（加上 type、affects、condition）
        params = {n for n, spec in primitive.params.items() if spec.type not in ("int", "dice")}
        assert set(model["properties"]) == {"type", "affects", "condition"} | params, primitive.id
        expected = ["type", *sorted(n for n in params if _must(primitive.params[n]))]
        assert model.get("required", ["type"]) == expected, primitive.id
        assert model["additionalProperties"] is False
        assert model["description"] == primitive.llm_hint


def _must(spec: Any) -> bool:
    return bool(spec.required and spec.required_when is None)


def test_proposal_has_no_numeric_fields() -> None:
    """骰子、範圍數值、持續回合等一律不在提議裡（決定 #3）；縮放只留依什麼縮放。"""
    lib = _lib()
    schema = _models().json_schema()
    items = {
        f"{prefix}_{item.id}": item
        for prefix, table in (
            ("Effect", lib.ruleset.primitives.primitives),
            ("Condition", lib.ruleset.conditions.conditions),
        )
        for item in table
    }
    all_numeric: set[str] = set()
    for key, item in items.items():
        numeric = numeric_param_names(item.params)
        all_numeric |= numeric
        assert numeric.isdisjoint(schema["$defs"][key]["properties"]), key
    assert {"dice", "duration", "distance", "permille", "multiplier_permille"} <= all_numeric
    assert set(schema["$defs"]["Scaling"]["properties"]) == {"by"}
    assert set(standard_form(schema)["properties"]).isdisjoint({"ap_cost", "cost"})
    assert "range_delta" not in schema["$defs"]["Variant"]["properties"]
    for key, definition in schema["$defs"].items():
        if key.startswith("Trigger_"):
            assert set(definition["properties"]).isdisjoint({"max_per_round", "max_distance"})


def test_required_when_params_are_optional_in_proposal() -> None:
    inscribe = _models().json_schema()["$defs"]["Effect_inscribe"]
    assert "element" in inscribe["properties"]
    assert "element" not in inscribe.get("required", [])  # required_when: unless_filled tag


def test_trigger_models_follow_yaml_params() -> None:
    schema = _models().json_schema()
    for trig in _lib().ruleset.skill_triggers.triggers:
        model = schema["$defs"][f"Trigger_{trig.id}"]
        expected = {"event", *trig.params} | ({"target"} if trig.has_other else set())
        assert set(model["properties"]) == expected, trig.id
        required = {"event", *(n for n, p in trig.params.items() if p.required)}
        assert set(model["required"]) == required, trig.id
        assert model["description"] == trig.llm_hint
    assert schema["$defs"]["Trigger_every_n_hits"]["properties"]["n"]["enum"] == [2, 3]


def test_hints_become_schema_descriptions() -> None:
    lib = _lib()
    schema = _models().json_schema()
    for cond in lib.ruleset.conditions.conditions:
        assert schema["$defs"][f"Condition_{cond.id}"]["description"] == cond.llm_hint
    for shape in lib.ruleset.shapes.shapes:
        model = schema["$defs"][f"Shape_{shape.id}"]
        assert model["description"] == shape.llm_hint
        for name, spec in shape.params.items():
            assert model["properties"][name]["description"] == spec.llm_hint
    status = schema["$defs"]["Effect_apply_status"]["properties"]["status"]
    assert (
        status["description"] == lib.ruleset.primitive_def("apply_status").params["status"].llm_hint
    )


def test_enumerations_come_from_content() -> None:
    schema = _models().json_schema()
    status = schema["$defs"]["Effect_apply_status"]["properties"]["status"]
    # 4-L5c：只列技能能施加的狀態（有預算點數）
    statuses = {s.id for s in _lib().ruleset.statuses.statuses if s.budget_points is not None}
    assert set(status["enum"]) == statuses
    cleanse = schema["$defs"]["Effect_cleanse"]["properties"]["affects"]["anyOf"][0]
    assert "enemies" not in cleanse["enum"]  # forbid_affects


def test_variant_effects_exclude_lookup_by_skill_id() -> None:
    models = _models()
    flagged = {p.id for p in _lib().ruleset.primitives.primitives if p.lookup_by_skill_id}
    assert flagged == {"copy_skill", "delayed_damage", "zone"}
    assert flagged.isdisjoint(models.variant_primitive_ids)
    assert flagged <= set(models.primitive_ids)
    schema = models.json_schema()
    variant = schema["$defs"]["Variant"]["properties"]["add_effect"]["anyOf"][0]
    name = str(variant["$ref"]).rsplit("/", 1)[-1]
    assert flagged.isdisjoint(union_tags(schema["$defs"][name]))


def test_primitive_subset_shrinks_schema() -> None:
    full = len(json.dumps(_models().json_schema()))
    sub = build_proposal_models(_lib(), primitives=["damage", "apply_status", "zone"])
    assert sub.primitive_ids == ("damage", "apply_status", "zone")
    assert len(json.dumps(sub.json_schema())) < full / 2
    alone = build_proposal_models(_lib(), primitives=["zone", "push"])
    assert alone.primitive_ids == ("push",)
    assert alone.excluded_primitives[0][0] == "zone"


# ---------------------------------------------------------------------------
# 提議 → SkillDef
# ---------------------------------------------------------------------------

CLEAVE = {
    "form": "standard",
    "name_zh": "橫掃劈砍",
    "concept": "巨劍掃出一道弧，把前方的人一起削倒",
    "cast_flavor": "盜賊頭目雙手揮動巨劍，朝面前橫掃",
    "kind": "active",
    "skeleton": "area",
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "shape": {"type": "cone", "size": 2},
    "effects": [{"type": "damage"}],
    "tags": ["physical", "melee", "area"],
}


def _numbers_of(skill: SkillDef) -> NumberFiller:
    """把手寫技能的數值放回去的補值器（測試用的固定預算器）。"""
    _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), _lib())
    return fixed_filler(removed)


def _structure_round_trip(skill: SkillDef) -> ProposalResult:
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
    return evaluate_proposal(
        proposal_from_skill(skill, _lib()), _models(), _lib(), ctx, fill=_numbers_of(skill)
    )


@pytest.mark.parametrize("skill_id", ["skill_cleave", "skill_execute", "skill_bloodlust"])
def test_structure_round_trips_with_fixed_numbers(skill_id: str) -> None:
    original = _lib().skills[skill_id]
    proposal = proposal_from_skill(original, _lib())
    flat = json.dumps(proposal, ensure_ascii=False)
    assert not any(k in flat for k in ('"dice"', '"cooldown"', '"mana"', '"ap_cost"', "permille"))
    result = _structure_round_trip(original)
    assert result.errors == ()
    assert result.skill is not None
    assert _same(result.skill, original)
    assert result.skill.id.startswith(LLM_ID_PREFIX)
    assert result.skill.provenance.created_by == "llm"
    assert _structure_round_trip(original).skill == result.skill  # ID 由內容（含數值）決定


def test_same_structure_different_numbers_get_different_ids() -> None:
    original = _lib().skills["skill_cleave"]
    full = original.model_dump(mode="json", exclude_defaults=True)
    structure, removed = split_numbers(full, _lib())
    bumped = [(path, v + 1 if path[-1] == "multiplier_permille" else v) for path, v in removed]
    ctx = ProposalContext(tier=original.tier, rarity=original.rarity, rank=original.rank)
    proposal = proposal_from_skill(original, _lib())
    a = evaluate_proposal(proposal, _models(), _lib(), ctx, fill=fixed_filler(removed))
    b = evaluate_proposal(proposal, _models(), _lib(), ctx, fill=fixed_filler(bumped))
    assert a.skill is not None
    assert b.skill is not None
    assert a.skill.id != b.skill.id
    assert "multiplier_permille" not in structure["effects"][0]


def test_split_and_apply_numbers_are_inverse_for_every_skill() -> None:
    for skill in sorted(_lib().skills.values(), key=lambda s: s.id):
        full = skill.model_dump(mode="json", exclude_defaults=True)
        structure, removed = split_numbers(full, _lib())
        assert apply_numbers(structure, removed) == full, skill.id


def test_default_filler_fills_required_numbers_only() -> None:
    """預設補值器不保證通過預算，但補出的技能一定通過 schema 檢查（錯誤只會在 rules 階段）。"""
    proposal = {
        **CLEAVE,
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": "int",
        "effects": [
            {"type": "damage", "element": "fire", "condition": {"type": "target_hp_below"}},
            {"type": "heal"},
            {"type": "apply_status", "status": "burning"},
        ],
    }
    result = _evaluate(proposal)
    assert {e.stage for e in result.errors} <= {"rules"}
    data = _minimal_data(proposal)
    assert data["ap_cost"] == 2
    damage, heal, status = data["effects"]
    assert damage["dice"] == "1d4"
    assert damage["condition"]["permille"] == 1
    assert heal["dice"] == "1d4"
    assert "duration" not in status  # 選填的持續回合保持省略
    assert "multiplier_permille" not in damage


def _minimal_data(proposal: dict[str, Any]) -> dict[str, Any]:
    return minimal_filler(_lib())(dict(proposal))


_EXCLUDED_CODES = {"union_tag_invalid", "extra_forbidden"}
"""原型刻意不開放的部分（非原語的巢狀效果、cost 的 source／on_miss 等）造成的錯誤代碼。"""


def test_every_expressible_builtin_skill_round_trips() -> None:
    """提議格式能表達的手寫技能全部往返等價；失敗的只能是原型刻意不開放的部分。"""
    passed = 0
    for skill in sorted(_lib().skills.values(), key=lambda s: s.id):
        try:
            proposal_from_skill(skill, _lib())
        except ValueError:
            continue  # 反應、修正型、複合技能等頂層欄位不開放
        result = _structure_round_trip(skill)
        if result.skill is None:
            allowed = {("proposal", c) for c in _EXCLUDED_CODES}
            if _lib().budget.min_cost_problem(skill.kind, skill.category, skill.cost):
                allowed.add(("rules", "cap.min_cost"))  # 內建技能不達最低花費（3-48c，列在報告）
            if skill.id in RANGE_BUDGET_EXCEPTIONS:  # 射程係數後超出預算範圍（3-49，列在報告）
                allowed |= {("rules", "budget.over"), ("rules", "budget.weak")}
            assert {(e.stage, e.code) for e in result.errors} <= allowed, (skill.id, result.errors)
            continue
        assert _same(result.skill, skill), skill.id
        passed += 1
    assert passed >= 150, passed


# ---------------------------------------------------------------------------
# 結構化錯誤
# ---------------------------------------------------------------------------


def test_invalid_proposal_errors_are_locatable() -> None:
    bad = {
        **CLEAVE,
        "effects": [
            {"type": "damage", "multiplier_permille": 1400, "element": "no_element"},
            {"type": "heal", "dice": "1d4", "radius": 2},
            {"type": "apply_status", "status": "no_such_status"},
            {"type": "fireball"},
        ],
    }
    result = _evaluate(bad)
    assert result.skill is None
    by_path = {e.path: e for e in result.errors}
    assert by_path["effects[0].multiplier_permille"].code == "extra_forbidden"  # 數值不是 LLM 的事
    assert by_path["effects[0].element"].code == "enum"
    assert by_path["effects[1].dice"].code == "extra_forbidden"
    assert by_path["effects[1].radius"].code == "extra_forbidden"
    status = by_path["effects[2].status"]
    assert status.code == "literal_error"
    assert "burning" in status.allowed
    unknown = by_path["effects[3]"]
    assert unknown.code == "union_tag_invalid"
    assert "damage" in unknown.allowed
    assert all(e.stage == "proposal" for e in result.errors)
    assert all(e.message for e in result.errors)


def test_numeric_top_level_fields_are_rejected() -> None:
    result = _evaluate({**CLEAVE, "ap_cost": 2, "cost": {"mana": 4}})
    codes = {e.path: e.code for e in result.errors}
    assert codes == {"ap_cost": "extra_forbidden", "cost": "extra_forbidden"}


def test_caller_fields_and_variant_lookup_rejected() -> None:
    bad = {
        **CLEAVE,
        "rarity": "legendary",
        "variants": [
            {
                "id": "flame",
                "name_zh": "火海",
                "when": {"caster_high_ground": True},
                "add_effect": {"type": "zone", "anchor": "tile", "when": "enter"},
            }
        ],
    }
    result = _evaluate(bad)
    paths = {e.path: e for e in result.errors}
    assert paths["rarity"].code == "extra_forbidden"
    zone = paths["variants[0].add_effect"]
    assert zone.code == "union_tag_invalid"
    assert "zone" not in zone.allowed


def _overlay(*items: tuple[tuple[str | int, ...], Any]) -> NumberFiller:
    return lambda data: apply_numbers(data, items)


def test_rules_stage_reports_budget() -> None:
    greedy = _overlay((("ap_cost",), 2), (("effects", 0, "multiplier_permille"), 9000))
    ctx = ProposalContext(tier=1, rarity="common")
    result = evaluate_proposal(CLEAVE, _models(), _lib(), ctx, fill=greedy)
    assert result.skill is None
    assert result.errors
    assert all(e.stage == "rules" for e in result.errors)
    assert any(e.code.startswith("budget") for e in result.errors)


def test_skill_stage_reports_schema_rules() -> None:
    """提議格式合法、但 SkillDef 自己的檢查不過（這裡：預算器誤給武器技的傷害填了骰子）。"""
    wrong = _overlay((("ap_cost",), 2), (("effects", 0, "dice"), "2d6"))
    result = evaluate_proposal(CLEAVE, _models(), _lib(), ProposalContext(1, "rare"), fill=wrong)
    assert result.skill is None
    assert {e.stage for e in result.errors} <= {"skill", "rules"}
    assert result.errors


def test_json_errors_and_feedback_payload() -> None:
    broken = _evaluate("{not json")
    assert [(e.stage, e.code) for e in broken.errors] == [("proposal", "json_invalid")]
    errors = _evaluate({**CLEAVE, "shape": {"type": "cone", "size": 9}}).errors
    assert [(e.path, e.code) for e in errors] == [("shape.size", "less_than_equal")]
    payload = json.loads(feedback_payload(errors, attempt=1, max_attempts=3))
    assert payload["attempt"] == 1
    assert payload["errors"][0] == {
        "stage": "proposal",
        "path": "shape.size",
        "code": "less_than_equal",
        "message": "必須 ≤ 4",
    }
