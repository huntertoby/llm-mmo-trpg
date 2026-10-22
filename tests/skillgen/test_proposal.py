"""LLM 技能提議模型原型（Phase 3E-2g）：由 YAML 產生的 discriminated union、提議 → SkillDef 往返、
結構化錯誤。全部用固定的提議 JSON，不需要網路與模型。"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
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
    """除了 ID 與來源（呼叫端決定）以外完全相同。"""
    skip = {"id", "provenance"}
    return a.model_dump(exclude=skip) == b.model_dump(exclude=skip)


def _effect_branches(schema: dict[str, Any], key: str = "effects") -> dict[str, str]:
    items = schema["properties"][key]["items"]
    mapping: dict[str, str] = items["discriminator"]["mapping"]
    return mapping


# ---------------------------------------------------------------------------
# 模型產生
# ---------------------------------------------------------------------------


def test_one_branch_per_primitive_from_yaml() -> None:
    lib = _lib()
    schema = _models().json_schema()
    yaml_ids = {p.id for p in lib.ruleset.primitives.primitives}
    assert set(_effect_branches(schema)) == yaml_ids
    damage = schema["$defs"]["Effect_damage"]["properties"]
    spec = lib.ruleset.primitive_def("damage").params["multiplier_permille"]
    ranged = damage["multiplier_permille"]["anyOf"][0]
    assert (ranged["minimum"], ranged["maximum"]) == (spec.min, spec.max)
    assert "pattern" in damage["dice"]["anyOf"][0]
    # 每一支只有該原語自己的參數（加上 type、affects、condition）
    heal = schema["$defs"]["Effect_heal"]
    assert set(heal["properties"]) == {"type", "affects", "condition", "dice"}
    assert heal["required"] == ["type", "dice"]
    assert heal["additionalProperties"] is False


def test_enumerations_come_from_content() -> None:
    schema = _models().json_schema()
    status = schema["$defs"]["Effect_apply_status"]["properties"]["status"]
    statuses = {s.id for s in _lib().ruleset.statuses.statuses}
    assert set(status["enum"]) == statuses
    cleanse = schema["$defs"]["Effect_cleanse"]["properties"]["affects"]["anyOf"][0]
    assert "enemies" not in cleanse["enum"]  # forbid_affects


def test_variant_effects_exclude_lookup_by_skill_id() -> None:
    models = _models()
    flagged = {p.id for p in _lib().ruleset.primitives.primitives if p.lookup_by_skill_id}
    assert flagged == {"copy_skill", "delayed_damage", "zone"}
    assert flagged.isdisjoint(models.variant_primitive_ids)
    assert flagged <= set(models.primitive_ids)
    variant = models.json_schema()["$defs"]["Variant"]["properties"]["add_effect"]["anyOf"][0]
    assert flagged.isdisjoint(variant["discriminator"]["mapping"])


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
    "name_zh": "橫掃劈砍",
    "concept": "巨劍掃出一道弧，把前方的人一起削倒",
    "cast_flavor": "盜賊頭目雙手揮動巨劍，朝面前橫掃",
    "kind": "active",
    "skeleton": "area",
    "category": "weapon",
    "weapon_req": "melee",
    "ap_cost": 2,
    "scaling_attr": "str",
    "shape": {"type": "cone", "size": 2},
    "effects": [{"type": "damage", "multiplier_permille": 1400}],
    "cost": {"mana": 4, "cooldown": 2},
    "tags": ["physical", "melee", "area"],
}
EXECUTE = {
    "name_zh": "處決",
    "concept": "對已經站不穩的敵人補上決定性的一擊",
    "cast_flavor": "你看準破綻，毫不留情地一劍落下",
    "kind": "active",
    "skeleton": "strike",
    "category": "weapon",
    "weapon_req": "melee",
    "ap_cost": 2,
    "scaling_attr": "str",
    "shape": {"type": "single", "range": "weapon"},
    "effects": [{"type": "damage", "multiplier_permille": 2000}],
    "condition": {"type": "target_hp_below", "permille": 400},
    "cost": {"mana": 5, "cooldown": 2},
    "tags": ["physical", "melee", "finisher"],
}
BLOODLUST = {
    "name_zh": "嗜血",
    "concept": "每一次擊倒敵人，都讓血液重新沸騰、傷口癒合",
    "cast_flavor": "倒下的敵人還沒落地，你的傷口已經止住了血",
    "kind": "passive",
    "skeleton": "passive",
    "category": "spell",
    "weapon_req": "any",
    "scaling_attr": "str",
    "shape": {"type": "self"},
    "effects": [{"type": "heal", "dice": "1d6", "affects": "self"}],
    "trigger": {"event": "on_kill", "target": "self", "max_per_round": 1},
    "cost": {"mana": 2},
    "tags": ["physical", "spell", "passive", "heal", "kill"],
}


@pytest.mark.parametrize(
    ("skill_id", "proposal"),
    [("skill_cleave", CLEAVE), ("skill_execute", EXECUTE), ("skill_bloodlust", BLOODLUST)],
)
def test_handwritten_json_round_trips(skill_id: str, proposal: dict[str, Any]) -> None:
    original = _lib().skills[skill_id]
    ctx = ProposalContext(tier=original.tier, rarity=original.rarity, rank=original.rank)
    result = _evaluate(json.dumps(proposal, ensure_ascii=False), ctx)
    assert result.errors == ()
    assert result.skill is not None
    assert _same(result.skill, original)
    assert result.skill.id.startswith(LLM_ID_PREFIX)
    assert result.skill.provenance.created_by == "llm"
    assert _evaluate(proposal, ctx).skill == result.skill  # ID 由內容決定


@pytest.mark.parametrize(
    "skill_id",
    ["skill_frost_ledge_cleave", "skill_detonate_burning", "skill_fire_wall", "skill_fire_bolt"],
)
def test_variants_nested_and_zone_round_trip(skill_id: str) -> None:
    original = _lib().skills[skill_id]
    ctx = ProposalContext(tier=original.tier, rarity=original.rarity, rank=original.rank)
    result = _evaluate(proposal_from_skill(original), ctx)
    assert result.skill is not None, result.errors
    assert _same(result.skill, original)


_EXCLUDED_CODES = {"union_tag_invalid", "extra_forbidden"}
"""原型刻意不開放的部分（非原語的巢狀效果、cost 的 source／on_miss 等）造成的錯誤代碼。"""


def test_every_expressible_builtin_skill_round_trips() -> None:
    """提議格式能表達的手寫技能全部往返等價；失敗的只能是原型刻意不開放的部分。"""
    passed = 0
    for skill in sorted(_lib().skills.values(), key=lambda s: s.id):
        try:
            data = proposal_from_skill(skill)
        except ValueError:
            continue  # 反應、修正型、複合技能等頂層欄位不開放
        ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
        result = _evaluate(data, ctx)
        if result.skill is None:
            assert {(e.stage, e.code) for e in result.errors} <= {
                ("proposal", c) for c in _EXCLUDED_CODES
            }, (skill.id, result.errors)
            continue
        assert _same(result.skill, skill), skill.id
        passed += 1
    assert passed >= 150


# ---------------------------------------------------------------------------
# 結構化錯誤
# ---------------------------------------------------------------------------


def test_invalid_proposal_errors_are_locatable() -> None:
    bad = {
        **CLEAVE,
        "effects": [
            {"type": "damage", "multiplier_permille": 1400, "dice": "2x6"},
            {"type": "heal", "dice": "1d4", "radius": 2},
            {"type": "apply_status", "status": "no_such_status", "duration": 2},
            {"type": "fireball"},
        ],
    }
    result = _evaluate(bad)
    assert result.skill is None
    by_path = {e.path: e for e in result.errors}
    assert by_path["effects[0].dice"].code == "string_pattern_mismatch"
    assert by_path["effects[1].radius"].code == "extra_forbidden"
    status = by_path["effects[2].status"]
    assert status.code == "literal_error"
    assert "burning" in status.allowed
    unknown = by_path["effects[3]"]
    assert unknown.code == "union_tag_invalid"
    assert "damage" in unknown.allowed
    assert all(e.stage == "proposal" for e in result.errors)
    assert all(e.message for e in result.errors)


def test_caller_fields_and_variant_lookup_rejected() -> None:
    bad = {
        **CLEAVE,
        "rarity": "legendary",
        "variants": [
            {
                "id": "flame",
                "name_zh": "火海",
                "when": {"caster_high_ground": True},
                "add_effect": {"type": "zone", "anchor": "tile", "when": "enter", "duration": 2},
            }
        ],
    }
    result = _evaluate(bad)
    paths = {e.path: e for e in result.errors}
    assert paths["rarity"].code == "extra_forbidden"
    zone = paths["variants[0].add_effect"]
    assert zone.code == "union_tag_invalid"
    assert "zone" not in zone.allowed


def test_rules_stage_reports_budget() -> None:
    greedy = {**CLEAVE, "effects": [{"type": "damage", "multiplier_permille": 9000}]}
    result = _evaluate(greedy, ProposalContext(tier=1, rarity="common"))
    assert result.skill is None
    assert result.errors
    assert all(e.stage == "rules" for e in result.errors)
    assert any(e.code.startswith("budget") for e in result.errors)


def test_skill_stage_reports_schema_rules() -> None:
    """提議格式合法、但 SkillDef 自己的檢查不過（這裡：武器技的傷害效果不可填骰子）。"""
    bad = {**CLEAVE, "effects": [{"type": "damage", "dice": "2d6", "multiplier_permille": 1400}]}
    result = _evaluate(bad)
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
