"""Phase 4-L5b：讓隱藏的組合規則看得見——提議的版型（form）、稀有度篩狀態、錯誤路徑。

全部用固定的提議 JSON，不需要網路與模型。"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    SHAPE_REQUIRED_PRIMITIVES,
    EffectSpec,
    SkillRuleError,
    _check_composition,
    composition_rules,
    rarity_rank,
)
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    ProposalResult,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_layouts import STANDARD_LAYOUT, is_special, layout_id, plan_layouts
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    available_payload,
    build_subset_models,
    select_subset,
)


@cache
def _lib() -> ContentLibrary:
    return library()


@cache
def _models() -> ProposalModels:
    return build_proposal_models(_lib())


def _evaluate(data: dict[str, Any], models: ProposalModels | None = None) -> ProposalResult:
    ctx = ProposalContext(tier=2, rarity="epic")
    return evaluate_proposal(data, models or _models(), _lib(), ctx)


RUSH: dict[str, Any] = {"type": "charge_through", "on_hit": "knock_prone"}
CHARGE: dict[str, Any] = {
    "layout": "charge_through",
    "kind": "active",
    "skeleton": "displace",
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "shape": {"type": "ground_tile", "range": 3},
    "effects": [{"type": "charge_through", "on_hit": "knock_prone"}],
}


def _by_path(result: ProposalResult) -> dict[str, Any]:
    return {e.path: e for e in result.errors}


# ---------------------------------------------------------------------------
# 版型：組合規則進 schema
# ---------------------------------------------------------------------------


def test_charge_through_form_only_offers_ground_tile() -> None:
    result = _evaluate({**CHARGE, "shape": {"type": "single", "range": 1}})
    error = _by_path(result)["shape.type"]  # 只有一種形狀：直接是那個形狀的模型
    assert (error.stage, error.code) == ("proposal", "literal_error")
    assert error.allowed == ("ground_tile",)


def test_charge_through_is_not_in_the_standard_form() -> None:
    result = _evaluate({**CHARGE, "layout": STANDARD_LAYOUT})
    error = _by_path(result)["effects[0]"]
    assert error.code == "union_tag_invalid"
    assert "charge_through" not in error.allowed
    assert "damage" in error.allowed


def test_charge_through_other_effects_only_affect_self() -> None:
    enemies = {"type": "apply_status", "status": "hasted", "affects": "enemies"}
    result = _evaluate({**CHARGE, "effects": [RUSH, enemies]})
    error = _by_path(result)["effects[1].affects"]
    assert (error.stage, error.code) == ("proposal", "literal_error")
    assert error.allowed == ("self",)
    # 省略 affects 時就是 self：提議格式與 SkillDef 的檢查都過
    plain = {"type": "apply_status", "status": "hasted"}
    ok = _evaluate({**CHARGE, "effects": [RUSH, plain]})
    assert {e.stage for e in ok.errors} <= {"rules"}
    # 對自己造成傷害沒有意義：其他效果不開放有害的原語（施加狀態除外）
    damage = _evaluate({**CHARGE, "effects": [RUSH, {"type": "damage"}]})
    assert _by_path(damage)["effects[1]"].code == "union_tag_invalid"


def test_position_rule_is_reported_with_a_path() -> None:
    """位置（第一個效果）仍由驗證器檢查，錯誤帶路徑（4-L5b 第 3 點）。"""
    effects = [{"type": "apply_status", "status": "hasted"}, RUSH]
    result = _evaluate({**CHARGE, "effects": effects})
    error = _by_path(result)["effects[1]"]
    assert error.stage == "skill"
    assert "第一個效果" in error.message


def test_sole_effect_layouts_allow_one_effect() -> None:
    form = next(f for f in plan_layouts(_lib(), **_full())[0] if f.id == "teleport_target")
    assert form.max_effects == 1
    assert form.effects == ("teleport_target",)
    assert form.shapes == ("unit_then_tile",)


def _full() -> dict[str, Any]:
    rules = _lib().ruleset
    return {
        "primitives": [p.id for p in rules.primitives.primitives],
        "shapes": [s.id for s in rules.shapes.shapes],
        "kinds": ("active", "passive", "stance"),
    }


def test_every_special_primitive_has_a_form_and_standard_has_none() -> None:
    plans, excluded = plan_layouts(_lib(), **_full())
    rules = composition_rules()
    by_id = {p.id: p for p in plans}
    standard = by_id[STANDARD_LAYOUT]
    for primitive in _lib().ruleset.primitives.primitives:
        rule = rules[primitive.id]
        if is_special(rule):
            assert primitive.id not in standard.effects
            assert primitive.id in by_id[layout_id(rule)].leads, primitive.id
            form = by_id[layout_id(rule)]
            if rule.allowed_shapes is not None:
                assert set(form.shapes) <= set(rule.allowed_shapes), primitive.id
        else:
            assert primitive.id in standard.effects
    assert excluded == ()
    # 要求特定原語的形狀不在一般版型
    assert set(standard.shapes).isdisjoint(SHAPE_REQUIRED_PRIMITIVES)


def test_shape_required_primitives_agree_with_yaml() -> None:
    rules = composition_rules()
    for shape, primitives in SHAPE_REQUIRED_PRIMITIVES.items():
        for primitive in primitives:
            assert shape in (rules[primitive].allowed_shapes or ()), (shape, primitive)


def test_handwritten_skills_map_to_existing_layouts() -> None:
    layouts = {f for f, _ in _models().layouts}
    for skill in sorted(_lib().skills.values(), key=lambda s: s.id):
        try:
            proposal = proposal_from_skill(skill, _lib())
        except ValueError:
            continue
        assert proposal["layout"] in layouts, (skill.id, proposal["layout"])
        assert next(iter(proposal)) == "layout"


def test_missing_form_lists_the_layouts() -> None:
    data = {k: v for k, v in CHARGE.items() if k != "layout"}
    error = _by_path(_evaluate(data))["layout"]
    assert error.code == "union_tag_not_found"
    assert set(error.allowed) == {f for f, _ in _models().layouts}


def test_schema_drops_annotation_keywords() -> None:
    schema = _models().json_schema()
    keys: set[str] = set()

    def walk(node: Any, *, names: bool = False) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if not names:
                    keys.add(key)
                walk(value, names=key in ("properties", "$defs") and not names)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    assert keys.isdisjoint({"title", "discriminator", "default"})
    assert "oneOf" in json.dumps(schema)


# ---------------------------------------------------------------------------
# 組合規則：YAML 是唯一來源，驗證器照它檢查
# ---------------------------------------------------------------------------


def _effect(primitive: str, **fields: Any) -> EffectSpec:
    return EffectSpec.model_validate({"type": primitive, **fields})


def _composition_cases() -> list[tuple[str, str, str, tuple[EffectSpec, ...]]]:
    cases: list[tuple[str, str, str, tuple[EffectSpec, ...]]] = []
    for primitive, rule in sorted(composition_rules().items()):
        me = _effect(primitive)
        other = _effect("heal", affects="allies")
        if rule.active_only:
            cases.append((primitive, "active_only", "passive", (me,)))
        if rule.sole_effect:
            cases.append((primitive, "sole_effect", "active", (me, _effect("heal"))))
        if rule.position == "first":
            cases.append((primitive, "first", "active", (_effect("heal", affects="self"), me)))
        if rule.position == "last":
            cases.append((primitive, "last", "active", (me, _effect("heal", affects="self"))))
        if rule.max_per_skill == 1:
            cases.append((primitive, "max", "active", (me, me)))
        if rule.others_affect == "self":
            cases.append((primitive, "others_affect", "active", (me, other)))
    return cases


@pytest.mark.parametrize(("primitive", "rule", "kind", "effects"), _composition_cases())
def test_every_yaml_composition_rule_is_enforced(
    primitive: str, rule: str, kind: str, effects: tuple[EffectSpec, ...]
) -> None:
    with pytest.raises(SkillRuleError) as info:
        _check_composition(kind, effects)
    assert primitive in str(info.value), rule
    assert info.value.path


def test_composition_rules_cover_the_known_primitives() -> None:
    rules = composition_rules()
    assert rules["charge_through"].position == "first"
    assert rules["charge_through"].others_affect == "self"
    assert rules["charge_through"].allowed_shapes == ("ground_tile",)
    assert rules["gamble"].position == "last"
    assert {p for p, r in rules.items() if r.sole_effect} == {
        "copy_skill",
        "enter_form",
        "rule_change",
        "swap_any",
        "teleport_target",
        "zone",
    }
    assert {p for p, r in rules.items() if r.others_affect} == {
        "charge_through",
        "revive",
        "summon",
    }


# ---------------------------------------------------------------------------
# 稀有度篩狀態
# ---------------------------------------------------------------------------


def _status_enum(models: ProposalModels) -> set[str]:
    schema = models.json_schema()
    return set(schema["$defs"]["Effect_apply_status"]["properties"]["status"]["enum"])


def test_status_enum_follows_request_rarity() -> None:
    statuses = _lib().ruleset.statuses.statuses
    rare_only = sorted(s.id for s in statuses if rarity_rank(s.min_rarity) > 0)
    assert rare_only, "需要至少一個稀有以上的狀態"
    common = select_subset(_lib(), ProposalRequest(tier=1, rarity="common", skeleton="strike"))
    assert common.rarity == "common"
    allowed = _status_enum(build_subset_models(_lib(), common))
    assert allowed.isdisjoint(rare_only)
    legendary = build_proposal_models(_lib(), rarity="legendary")
    assert set(rare_only) <= _status_enum(legendary)


def test_rarity_blocked_status_is_rejected_at_proposal_stage() -> None:
    blocked = next(s.id for s in _lib().ruleset.statuses.statuses if rarity_rank(s.min_rarity) > 0)
    subset = select_subset(_lib(), ProposalRequest(tier=1, rarity="common", skeleton="strike"))
    models = build_subset_models(_lib(), subset)
    proposal = {
        "layout": "standard",
        "kind": "active",
        "skeleton": "strike",
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": "int",
        "shape": {"type": "single", "range": 3},
        "effects": [
            {"type": "damage", "element": "fire"},
            {"type": "apply_status", "status": blocked},
        ],
    }
    ctx = ProposalContext(tier=1, rarity="common")
    result = evaluate_proposal(proposal, models, _lib(), ctx)
    error = _by_path(result)["effects[1].status"]
    assert (error.stage, error.code) == ("proposal", "literal_error")
    assert blocked not in error.allowed


def test_non_active_requests_drop_active_only_primitives() -> None:
    subset = select_subset(_lib(), ProposalRequest(tier=1, rarity="epic", kind="passive"))
    rules = composition_rules()
    assert not any(rules[p].active_only for p in subset.primitives)


# ---------------------------------------------------------------------------
# available：版型與骨架結構
# ---------------------------------------------------------------------------


def test_available_lists_layouts_and_skeleton_structure() -> None:
    subset = select_subset(_lib(), ProposalRequest(tier=2, rarity="rare", skeleton="displace"))
    payload = available_payload(_lib(), subset)
    layouts = {f["id"]: f["hint"] for f in payload["layouts"]}
    assert layouts == dict(build_subset_models(_lib(), subset).layouts)
    skeleton = payload["skeletons"][0]
    core = _lib().skeletons["displace"].core
    assert skeleton["core"]["primitives"] == [p for p in core.primitives if p in subset.primitives]
    if core.min_share_permille:
        assert f"{core.min_share_permille / 10:g}%" in skeleton["core"]["note"]
    strike = available_payload(
        _lib(), select_subset(_lib(), ProposalRequest(1, "rare", "active", "strike"))
    )
    share = _lib().skeletons["strike"].core.min_share_permille
    assert share and f"{share / 10:g}%" in strike["skeletons"][0]["core"]["note"]
    assert skeleton["shapes"] == [
        s for s in _lib().skeletons["displace"].shapes if s in subset.shapes
    ]
    assert "最多" in skeleton["secondary"]["note"] or "不能" in skeleton["secondary"]["note"]
