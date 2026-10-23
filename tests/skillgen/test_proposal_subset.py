"""Phase 4-L4：提議的 schema 子集——模型篩選、題目篩選（稀有度、骨架範圍、關鍵字、大小）、
確定性、往返、`available` 格式。全部不需要網路與模型。"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tests.content.test_llm_hint import IDENTIFIER
from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import rarity_rank
from trpg.shared.tokens import PROMPT_TOKEN_BUDGET
from trpg.skillgen.proposal import (
    CLOSED_SKELETONS,
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers
from trpg.skillgen.proposal_subset import (
    DEFAULT_SUBSET_TOKEN_BUDGET,
    ProposalRequest,
    ProposalSubset,
    SubsetError,
    available_payload,
    build_subset_models,
    select_subset,
)

RARITIES = ("common", "rare", "epic", "legendary")


@cache
def _lib() -> ContentLibrary:
    return library()


def _evaluate(models: ProposalModels, data: dict[str, Any]) -> Any:
    return evaluate_proposal(data, models, _lib(), ProposalContext(tier=1, rarity="legendary"))


BASE: dict[str, Any] = {
    "name_zh": "測試技",
    "kind": "active",
    "skeleton": "area",
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "shape": {"type": "cone", "size": 2},
    "effects": [{"type": "damage"}],
}


def _errors(models: ProposalModels, data: dict[str, Any]) -> dict[str, Any]:
    result = _evaluate(models, data)
    return {e.path: e for e in result.errors if e.stage == "proposal"}


# ---------------------------------------------------------------------------
# 模型：篩掉的值得到可定位的錯誤，allowed 只列子集
# ---------------------------------------------------------------------------


def test_unfiltered_models_are_unchanged_by_new_parameters() -> None:
    lib = _lib()
    rules = lib.ruleset
    default = build_proposal_models(lib).json_schema()
    explicit = build_proposal_models(
        lib,
        primitives=[p.id for p in rules.primitives.primitives],
        shapes=[s.id for s in rules.shapes.shapes],
        conditions=[c.id for c in rules.conditions.conditions],
        triggers=[t.id for t in rules.skill_triggers.triggers],
        skeletons=sorted(set(lib.skeletons) - CLOSED_SKELETONS),
    ).json_schema()
    assert json.dumps(default, sort_keys=True) == json.dumps(explicit, sort_keys=True)


def test_filtered_shape_is_union_tag_invalid_with_subset_allowed() -> None:
    models = build_proposal_models(_lib(), shapes=["single", "line", "ring"])
    errors = _errors(models, BASE)  # cone 被篩掉
    error = errors["shape"]
    assert error.code == "union_tag_invalid"
    assert set(error.allowed) == {"single", "line", "ring"}
    assert "cone" not in error.allowed


def test_filtered_skeleton_is_literal_error_with_subset_allowed() -> None:
    models = build_proposal_models(_lib(), skeletons=["strike", "control"])
    error = _errors(models, BASE)["skeleton"]  # area 被篩掉
    assert error.code == "literal_error"
    assert set(error.allowed) == {"strike", "control"}


def test_kind_follows_selected_skeletons() -> None:
    models = build_proposal_models(_lib(), skeletons=["strike"])
    error = _errors(models, {**BASE, "kind": "passive"})["kind"]
    assert set(error.allowed) == {"active"}


def _plain_conditions() -> list[str]:
    """沒有必填非數值參數的條件（提議只需要 ``type``）。"""
    out = []
    for cond in _lib().ruleset.conditions.conditions:
        needs = [n for n, p in cond.params.items() if p.required and p.type not in ("int", "dice")]
        if not needs:
            out.append(cond.id)
    return out


def test_filtered_condition_is_union_tag_invalid_with_subset_allowed() -> None:
    plain = _plain_conditions()
    assert len(plain) >= 3
    kept, other = plain[:2], plain[2]
    models = build_proposal_models(_lib(), conditions=kept)
    data = {**BASE, "condition": {"type": other}}
    error = _errors(models, data)["condition"]
    assert error.code == "union_tag_invalid"
    assert set(error.allowed) == set(kept)
    # 效果上的條件也一樣
    effect_data = {**BASE, "effects": [{"type": "damage", "condition": {"type": other}}]}
    assert _errors(models, effect_data)["effects[0].condition"].code == "union_tag_invalid"


def test_filtered_trigger_is_union_tag_invalid_with_subset_allowed() -> None:
    plain = [
        t.id
        for t in _lib().ruleset.skill_triggers.triggers
        if not any(p.required for p in t.params.values())
    ]
    assert len(plain) >= 3
    models = build_proposal_models(_lib(), triggers=plain[:2])
    passive = {
        **BASE,
        "kind": "passive",
        "skeleton": "passive",
        "category": "spell",
        "weapon_req": "any",
        "shape": {"type": "self"},
        "trigger": {"event": plain[2]},
    }
    error = _errors(models, passive)["trigger"]
    assert error.code == "union_tag_invalid"
    assert set(error.allowed) == set(plain[:2])


def test_empty_conditions_or_triggers_remove_the_fields() -> None:
    models = build_proposal_models(_lib(), conditions=[], triggers=[])
    schema = models.json_schema()
    assert "condition" not in schema["properties"]
    assert "trigger" not in schema["properties"]
    errors = _errors(models, {**BASE, "condition": {"type": "x"}})
    assert errors["condition"].code == "extra_forbidden"
    full = build_proposal_models(_lib()).json_schema()
    assert "condition" in full["properties"]
    assert "trigger" in full["properties"]


def test_empty_shapes_or_skeletons_are_rejected() -> None:
    with pytest.raises(ValueError):
        build_proposal_models(_lib(), shapes=[])
    with pytest.raises(ValueError):
        build_proposal_models(_lib(), skeletons=["reaction"])


# ---------------------------------------------------------------------------
# 題目驗證
# ---------------------------------------------------------------------------


def test_request_validation_messages_are_chinese() -> None:
    with pytest.raises(ValueError, match="階級"):
        ProposalRequest(tier=0, rarity="rare")
    with pytest.raises(ValueError, match="技能種類"):
        ProposalRequest(tier=1, rarity="rare", kind="reaction")
    with pytest.raises(ValueError, match="關鍵字"):
        ProposalRequest(tier=1, rarity="rare", keywords=("ignite", "wet", "charged"))
    with pytest.raises(ValueError, match="關鍵字"):
        ProposalRequest(tier=1, rarity="rare", keywords=("ignite", "ignite"))


def test_unknown_ids_raise_value_error() -> None:
    with pytest.raises(ValueError, match="未知的骨架"):
        select_subset(_lib(), ProposalRequest(tier=1, rarity="rare", skeleton="no_such"))
    with pytest.raises(ValueError, match="未知的關鍵字"):
        select_subset(_lib(), ProposalRequest(tier=1, rarity="rare", keywords=("no_such",)))


def test_no_valid_skeleton_raises_subset_error() -> None:
    cases = [
        ProposalRequest(tier=1, rarity="common", skeleton="passive"),  # 稀有度不足
        ProposalRequest(tier=1, rarity="common", skeleton="stance"),
        ProposalRequest(tier=1, rarity="common", skeleton="combo"),  # 需要條件，普通沒有條件
        ProposalRequest(tier=1, rarity="legendary", skeleton="reaction"),  # 提議不開放
        ProposalRequest(tier=1, rarity="legendary", skeleton="strike", kind="stance"),
        ProposalRequest(tier=1, rarity="common", kind="passive"),
    ]
    for request in cases:
        with pytest.raises(SubsetError):
            select_subset(_lib(), request)


def test_subset_error_when_core_does_not_fit() -> None:
    request = ProposalRequest(tier=1, rarity="rare", skeleton="strike")
    with pytest.raises(SubsetError, match="token"):
        select_subset(_lib(), request, token_budget=500)


# ---------------------------------------------------------------------------
# 篩選規則
# ---------------------------------------------------------------------------


def _subset(rarity: str, skeleton: str | None = None, *kws: str, kind: str | None = None) -> Any:
    request = ProposalRequest(
        tier=2,
        rarity=rarity,  # type: ignore[arg-type]
        skeleton=skeleton,
        kind=kind,
        keywords=tuple(kws),
    )
    return select_subset(_lib(), request)


def test_rarity_filters_primitives_shapes_conditions_and_triggers() -> None:
    rules = _lib().ruleset
    for rarity in RARITIES:
        rank = rarity_rank(rarity)
        subset = _subset(rarity, "strike" if rarity == "common" else None)
        for p in subset.primitives:
            assert rarity_rank(rules.primitives.by_id()[p].min_rarity) <= rank, (rarity, p)
        for s in subset.shapes:
            assert rarity_rank(rules.shapes.by_id()[s].min_rarity) <= rank, (rarity, s)
        for c in subset.conditions:
            assert rarity_rank(rules.conditions.by_id()[c].min_rarity) <= rank, (rarity, c)
        for sk in subset.skeletons:
            assert rarity_rank(_lib().skeletons[sk].min_rarity) <= rank, (rarity, sk)
    assert _subset("common", "strike").conditions == ()  # 條件從稀有起
    assert _subset("rare", "strike").conditions != ()


def test_rarity_blocked_primitive_is_dropped_and_proposal_rejected() -> None:
    subset = _subset("common", "strike", "ignite")
    dropped = dict(subset.dropped)
    blocked = [
        p.id
        for p in _lib().ruleset.primitives.primitives
        if rarity_rank(p.min_rarity) > 0 and p.id in {"damage", "apply_status", "push"}
    ]
    assert blocked == [] or all(b not in subset.primitives for b in blocked)
    # 普通的 strike 子集不含稀有以上的原語；提議它們得到 union_tag_invalid
    rare_only = next(
        p.id
        for p in _lib().ruleset.primitives.primitives
        if rarity_rank(p.min_rarity) > 0 and p.id not in subset.primitives
    )
    models = build_subset_models(_lib(), subset)
    errors = _errors(models, {**BASE, "skeleton": "strike", "effects": [{"type": rare_only}]})
    assert errors["effects[0]"].code == "union_tag_invalid"
    assert rare_only not in errors["effects[0]"].allowed
    assert isinstance(dropped, dict)


def test_skeleton_scope_limits_primitives_and_shapes() -> None:
    lib = _lib()
    for skeleton_id in sorted(set(lib.skeletons) - CLOSED_SKELETONS):
        skeleton = lib.skeletons[skeleton_id]
        kind = skeleton.kinds[0]
        try:
            subset = _subset("legendary", skeleton_id, kind=kind)
        except SubsetError:
            continue
        assert subset.skeletons == (skeleton_id,)
        assert set(subset.shapes) <= set(skeleton.shapes)
        allowed = set(skeleton.core.primitives) | set(skeleton.require_any_primitives)
        if skeleton.secondary.max_count > 0:
            allowed |= (
                set(skeleton.secondary.primitives)
                if skeleton.secondary.primitives is not None
                else {p.id for p in lib.ruleset.primitives.primitives}
            )
        # 核心必填的巢狀參數需要的原語（then、effects）是例外
        support = {"damage", "heal", "shield", "apply_status"}
        extra = set(subset.primitives) - allowed
        assert extra <= support, (skeleton_id, extra)
        assert set(skeleton.core.primitives) & set(subset.primitives)


def test_without_skeleton_uses_all_enabled_skeletons_of_the_kind() -> None:
    lib = _lib()
    subset = _subset("legendary")
    expected = sorted(
        s.id
        for s in lib.skeletons.values()
        if s.enabled and "active" in s.kinds and s.id not in CLOSED_SKELETONS
    )
    assert list(subset.skeletons) == expected
    assert _subset("legendary", kind="stance").skeletons == ("stance",)
    assert _subset("epic", kind="passive").skeletons == ("passive",)
    assert _subset("epic", "passive").kind == "passive"  # kind 省略 → 依骨架
    assert _subset("epic", "stance").kind == "stance"
    assert _subset("epic", "passive").triggers != ()
    assert _subset("epic", "strike").triggers == ()  # 觸發只給被動


def test_requires_condition_skeleton_always_has_a_condition() -> None:
    subset = _subset("rare", "combo")
    assert subset.conditions != ()


# ---------------------------------------------------------------------------
# 關鍵字
# ---------------------------------------------------------------------------


def _exclusive_effects(keyword_id: str) -> list[str]:
    keyword = _lib().ruleset.keywords.by_id()[keyword_id]
    found = {
        r.source_id
        for r in (*keyword.makes, *keyword.uses)
        if r.grade == "exclusive" and r.source == "effect"
    }
    return sorted(found)


@pytest.mark.parametrize("keyword_id", _lib().ruleset.keywords.ids())
def test_keyword_primitives_appear_under_some_skeleton(keyword_id: str) -> None:
    lib = _lib()
    wanted = _exclusive_effects(keyword_id)
    assert wanted, keyword_id
    skeleton_ids = sorted(
        s.id for s in lib.skeletons.values() if s.enabled and s.id not in CLOSED_SKELETONS
    )
    seen: set[str] = set()
    for skeleton_id in skeleton_ids:
        skeleton = lib.skeletons[skeleton_id]
        try:
            subset = _subset("legendary", skeleton_id, keyword_id, kind=skeleton.kinds[0])
        except SubsetError:
            continue
        present = set(wanted) & set(subset.primitives)
        seen |= present
        dropped = dict(subset.dropped)
        for primitive in set(wanted) - present:
            assert primitive in dropped, (keyword_id, skeleton_id, primitive)  # 沒收的都有原因
    assert seen, f"{keyword_id} 的專屬原語沒有在任何骨架的子集中出現"


def test_keyword_primitives_survive_a_tight_budget() -> None:
    """預算很緊時，題目關鍵字的專屬原語比其他附帶原語先收。"""
    request = ProposalRequest(tier=1, rarity="legendary", skeleton="control", keywords=("wet",))
    tight = select_subset(_lib(), request, token_budget=11_000)
    plain = select_subset(
        _lib(), ProposalRequest(tier=1, rarity="legendary", skeleton="control"), token_budget=11_000
    )
    wanted = {
        p for p in _exclusive_effects("wet") if p in _subset("legendary", "control").primitives
    }
    assert wanted
    assert wanted <= set(tight.primitives)
    assert tight.tokens <= 11_000
    assert plain.tokens <= 11_000


def test_keyword_condition_and_trigger_are_collected_or_dropped() -> None:
    subset = _subset("epic", "passive", "ignite")
    assert "on_status_applied" in subset.triggers or "on_status_applied" in dict(subset.dropped)
    common = _subset("common", "strike", "high_ground")
    assert "high_ground" in common.keywords
    # 稀有度擋下的條件進 dropped，不進子集
    conds = {
        r.source_id
        for r in (*_lib().ruleset.keywords.by_id()["high_ground"].makes,)
        if r.grade == "exclusive" and r.source == "condition"
    }
    for c in conds:
        assert c not in common.conditions
        assert c in dict(common.dropped)


def test_active_skill_drops_trigger_keywords() -> None:
    subset = _subset("legendary", "strike", "ignite")
    assert "on_status_applied" not in subset.triggers
    assert "on_status_applied" in dict(subset.dropped)


# ---------------------------------------------------------------------------
# 確定性與大小
# ---------------------------------------------------------------------------


def _bytes(subset: ProposalSubset) -> tuple[bytes, bytes]:
    schema = build_subset_models(_lib(), subset).json_schema()
    return (
        json.dumps(schema, ensure_ascii=False).encode(),
        json.dumps(available_payload(_lib(), subset), ensure_ascii=False).encode(),
    )


def test_same_request_gives_identical_schema_and_available_bytes() -> None:
    request = ProposalRequest(tier=3, rarity="epic", skeleton="control", keywords=("wet", "ignite"))
    first = select_subset(_lib(), request)
    second = select_subset(_lib(), request)
    assert first == second
    assert _bytes(first) == _bytes(second)
    for field in ("skeletons", "primitives", "shapes", "conditions", "triggers", "keywords"):
        assert list(getattr(first, field)) == sorted(getattr(first, field))
    assert all(isinstance(v, tuple) for v in (first.primitives, first.dropped))


def test_subset_fits_within_the_token_budget() -> None:
    subset = _subset("legendary", "control", "wet")
    assert subset.tokens <= DEFAULT_SUBSET_TOKEN_BUDGET
    assert DEFAULT_SUBSET_TOKEN_BUDGET < PROMPT_TOKEN_BUDGET
    small = select_subset(
        _lib(), ProposalRequest(tier=1, rarity="legendary", skeleton="control"), token_budget=9000
    )
    assert small.tokens <= 9000
    assert len(small.conditions) < len(subset.conditions)


# ---------------------------------------------------------------------------
# 往返：子集涵蓋手寫技能的結構時，提議仍通過提議格式與轉換
# ---------------------------------------------------------------------------


def _structure(node: Any, found: dict[str, set[str]]) -> None:
    if isinstance(node, dict):
        for key, bucket in (("type", "types"), ("event", "events")):
            value = node.get(key)
            if isinstance(value, str):
                found[bucket].add(value)
        for value in node.values():
            _structure(value, found)
    elif isinstance(node, list):
        for item in node:
            _structure(item, found)


def _covered(proposal: dict[str, Any], subset: ProposalSubset) -> bool:
    found: dict[str, set[str]] = {"types": set(), "events": set()}
    _structure(proposal, found)
    allowed = {*subset.primitives, *subset.shapes, *subset.conditions}
    return found["types"] <= allowed and found["events"] <= set(subset.triggers)


def test_handwritten_skills_round_trip_through_subset_models() -> None:
    lib = _lib()
    checked: list[str] = []
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        try:
            proposal = proposal_from_skill(skill, lib)
        except ValueError:
            continue
        if skill.skeleton in CLOSED_SKELETONS:
            continue
        request = ProposalRequest(
            tier=skill.tier, rarity=skill.rarity, kind=skill.kind, skeleton=skill.skeleton
        )
        try:
            subset = select_subset(lib, request)
        except SubsetError:
            continue
        if not _covered(proposal, subset):
            continue
        _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), lib)
        ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
        fill = fixed_filler(removed)
        full = evaluate_proposal(proposal, build_proposal_models(lib), lib, ctx, fill=fill)
        if any(e.stage == "proposal" for e in full.errors):
            continue  # 原型刻意不開放的部分（例如 cost 的 on_miss）
        result = evaluate_proposal(proposal, build_subset_models(lib, subset), lib, ctx, fill=fill)
        assert [e for e in result.errors if e.stage in ("proposal", "skill")] == [], skill.id
        checked.append(skill.id)
        if len(checked) >= 10:
            break
    assert len(checked) >= 10, checked


# ---------------------------------------------------------------------------
# available 格式
# ---------------------------------------------------------------------------


def _handmade_subset() -> ProposalSubset:
    return ProposalSubset(
        kind="passive",
        skeletons=("passive",),
        primitives=("apply_status", "damage"),
        shapes=("self",),
        conditions=("target_has_status",),
        triggers=("on_kill",),
        keywords=("ignite",),
    )


def test_available_payload_format_snapshot() -> None:
    payload = available_payload(_lib(), _handmade_subset())
    assert list(payload) == [
        "skeletons",
        "primitives",
        "shapes",
        "conditions",
        "triggers",
        "keywords",
    ]
    assert [e["id"] for e in payload["primitives"]] == ["apply_status", "damage"]  # 依 ID 排序
    assert all(set(e) == {"id", "hint"} for e in payload["skeletons"])
    assert all(set(e) == {"id", "hint"} for e in payload["shapes"])
    assert all(set(e) == {"id", "hint"} for e in payload["conditions"])
    assert all(set(e) == {"id", "hint"} for e in payload["triggers"])
    assert all(set(e) == {"id", "name_zh", "hint"} for e in payload["keywords"])
    assert payload["keywords"][0]["name_zh"] == "點燃"
    damage = next(e for e in payload["primitives"] if e["id"] == "damage")
    assert set(damage) == {"id", "hint", "params"}
    assert "element" in damage["params"]
    # 數值參數與數值範圍不列
    assert "dice" not in damage["params"]
    assert "multiplier_permille" not in damage["params"]
    flat = json.dumps(payload, ensure_ascii=False)
    for forbidden in ('"min"', '"max"', "permille", "dice"):
        assert forbidden not in flat, forbidden
    assert payload == available_payload(_lib(), _handmade_subset())


def test_available_lists_only_subset_items() -> None:
    subset = _subset("rare", "strike", "ignite")
    payload = available_payload(_lib(), subset)
    assert [e["id"] for e in payload["skeletons"]] == ["strike"]
    assert [e["id"] for e in payload["primitives"]] == sorted(subset.primitives)
    assert [e["id"] for e in payload["shapes"]] == sorted(subset.shapes)
    assert [e["id"] for e in payload["keywords"]] == ["ignite"]


def test_every_hint_is_clean_chinese_without_identifiers() -> None:
    lib = _lib()
    rules = lib.ruleset
    subset = ProposalSubset(
        kind="active",
        skeletons=tuple(sorted(set(lib.skeletons) - CLOSED_SKELETONS)),
        primitives=tuple(sorted(p.id for p in rules.primitives.primitives)),
        shapes=tuple(sorted(s.id for s in rules.shapes.shapes)),
        conditions=tuple(sorted(c.id for c in rules.conditions.conditions)),
        triggers=tuple(sorted(t.id for t in rules.skill_triggers.triggers)),
        keywords=(),
    )
    payload = available_payload(lib, subset)
    texts: list[tuple[str, str]] = []
    for group in ("skeletons", "shapes", "conditions", "triggers"):
        texts += [(f"{group}.{e['id']}", e["hint"]) for e in payload[group]]
    for entry in payload["primitives"]:
        texts.append((f"primitives.{entry['id']}", entry["hint"]))
        texts += [(f"primitives.{entry['id']}.{n}", h) for n, h in entry["params"].items()]
    for keyword in rules.keywords.keywords:
        texts.append((f"keywords.{keyword.id}", keyword.description_zh))
    assert [where for where, hint in texts if not hint.strip()] == []
    assert [where for where, hint in texts if IDENTIFIER.search(hint)] == []
