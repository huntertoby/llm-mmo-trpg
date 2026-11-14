"""LB-2：送給約束解碼的 schema 收緊（類別分支、變奏分支與數量）、欄位說明、重試回饋的修法。

全部離線；不呼叫真模型。
"""

from __future__ import annotations

import json
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.llm.prompts.proposal import (
    CATEGORY_NOTE_ZH,
    PROMPT_TOKEN_BUDGET,
    build_proposal_prompt,
    field_notes,
)
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalError,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal.build import WEAPON_REQ_BY_CATEGORY
from trpg.skillgen.proposal.evaluate import MAIN_DAMAGE_ADVICE, SECONDARY_ADVICE, advise
from trpg.skillgen.proposal.schema_shape import (
    VARIANT_SWAP_FIELDS,
    drop_descriptions,
    limit_variants,
    prune_defs,
    split_variants,
)
from trpg.skillgen.proposal_subset import SCHEMA_CHAR_LIMIT, ProposalRequest, json_chars

VARIANT = {
    "type": "object",
    "additionalProperties": False,
    "description": "變奏",
    "properties": {
        "id": {"type": "string"},
        "name_zh": {"type": "string"},
        "when": {"type": "object"},
        "shape": {"anyOf": [{"$ref": "#/$defs/Shape"}, {"type": "null"}]},
        "element": {"anyOf": [{"$ref": "#/$defs/Element"}, {"type": "null"}]},
        "add_effect": {"anyOf": [{"$ref": "#/$defs/Effect"}, {"type": "null"}]},
        "replace_effect": {"anyOf": [{"$ref": "#/$defs/Swap"}, {"type": "null"}]},
    },
    "required": ["id", "name_zh", "when"],
}
SKILL: dict[str, Any] = {
    "$defs": {
        "Variant": VARIANT,
        "Layout": {
            "type": "object",
            "properties": {
                "effects": {"type": "array"},
                "variants": {"type": "array", "items": {"$ref": "#/$defs/Variant"}, "maxItems": 2},
            },
        },
        "Unused": {"type": "string"},
    },
    "anyOf": [{"$ref": "#/$defs/Layout"}],
}


def _defs(schema: dict[str, Any]) -> dict[str, Any]:
    defs: dict[str, Any] = schema["$defs"]
    return defs


def test_split_variants_one_or_two_swaps_exactly() -> None:
    branches = _defs(split_variants(SKILL))["Variant"]["anyOf"]
    chosen = [sorted(set(b["required"]) - {"id", "name_zh", "when"}) for b in branches]
    assert len(branches) == 4 + 6  # 1 項 4 種 ＋ 2 項 6 種
    assert all(1 <= len(c) <= 2 for c in chosen)
    assert len({tuple(c) for c in chosen}) == len(chosen)
    for branch, fields in zip(branches, chosen, strict=True):
        assert branch["additionalProperties"] is False
        swaps = [f for f in VARIANT_SWAP_FIELDS if f in branch["properties"]]
        assert sorted(swaps) == fields  # 沒選到的替換欄位不在這一支
        for field in fields:  # 選到的必填、不能是 null
            assert {"type": "null"} not in branch["properties"][field].get("anyOf", [])
    assert SKILL["$defs"]["Variant"] is VARIANT  # 原 schema 不動


def test_limit_variants_by_rarity() -> None:
    one = _defs(limit_variants(SKILL, 1))["Layout"]["properties"]["variants"]
    assert one["maxItems"] == 1
    none = _defs(limit_variants(SKILL, 0))["Layout"]["properties"]
    assert "variants" not in none
    assert _defs(limit_variants(SKILL, 5))["Layout"]["properties"]["variants"]["maxItems"] == 2


def test_prune_and_drop_descriptions() -> None:
    pruned = prune_defs(limit_variants(SKILL, 0))
    assert set(_defs(pruned)) == {"Layout"}  # 不能帶變奏時變奏模型也拿掉
    assert "Unused" not in _defs(prune_defs(SKILL))
    assert "description" not in json.dumps(drop_descriptions(SKILL))
    # properties 的鍵是欄位名，叫 description 的欄位不能被當成說明去掉
    kept = drop_descriptions({"properties": {"description": {"type": "string"}}})
    assert kept == {"properties": {"description": {"type": "string"}}}


def _schema_text(library: ContentLibrary, request: ProposalRequest) -> dict[str, Any]:
    return build_proposal_prompt(library, request).json_schema


def test_prompt_schema_splits_category_and_variants(library: ContentLibrary) -> None:
    schema = _schema_text(library, ProposalRequest(1, "rare", skeleton="strike"))
    defs = _defs(schema)
    for category, reqs in WEAPON_REQ_BY_CATEGORY.items():
        branch = defs[f"SkillProposal_{category}"]["properties"]
        assert branch["category"]["const"] == category
        allowed = branch["weapon_req"]
        values = allowed.get("enum") or [allowed.get("const")]
        if "$ref" in allowed:
            values = defs[allowed["$ref"].rsplit("/", 1)[1]]["enum"]
        assert sorted(values) == sorted(reqs)
        assert branch["variants"]["maxItems"] == 1  # rare 最多 1 個
    assert "anyOf" in defs["Variant"]
    common = _defs(_schema_text(library, ProposalRequest(1, "common", skeleton="strike")))
    assert "variants" not in common["SkillProposal_weapon"]["properties"]
    assert "Variant" not in common


def test_wide_question_falls_back_to_unsplit_when_too_big(library: ContentLibrary) -> None:
    """類別分支後超過 SCHEMA_CHAR_LIMIT 的寬題目改用不分支的模型（不丟 SubsetError）。"""
    prompt = build_proposal_prompt(library, ProposalRequest(3, "epic", keywords=("ignite", "wet")))
    assert json_chars(prompt.json_schema) <= SCHEMA_CHAR_LIMIT
    assert prompt.tokens <= PROMPT_TOKEN_BUDGET


def test_handwritten_variants_fit_the_variant_branches(library: ContentLibrary) -> None:
    """手寫技能的變奏都是 1～2 項替換內容（分支沒有擋掉合法的提議）。"""
    seen = 0
    for skill in library.skills.values():
        if not skill.variants:
            continue
        try:
            proposal = proposal_from_skill(skill, library)
        except ValueError:
            continue
        for spec, variant in zip(skill.variants, proposal.get("variants", []), strict=True):
            if spec.range_delta is not None:
                continue  # range_delta 不開放給 LLM（提議模型沒有這個欄位）
            swaps = [f for f in VARIANT_SWAP_FIELDS if variant.get(f) is not None]
            assert 1 <= len(swaps) <= 2, (skill.id, swaps)
            seen += 1
    assert seen


def test_field_notes_cover_hidden_rules(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, ProposalRequest(1, "rare", keywords=("high_ground",)))
    notes = field_notes(
        library, ProposalRequest(1, "rare", keywords=("high_ground",)), prompt.subset
    )
    assert notes["category"] == CATEGORY_NOTE_ZH and "melee" in notes["category"]
    assert "頂層" in notes["element"]
    assert "最多 1 個" in notes["variants"] and "主傷害" in notes["variants"]
    user = prompt.messages[1]["content"]
    request_block = json.loads(user.split("<request>\n")[1].split("\n</request>")[0])
    assert request_block["fields_note_zh"] == notes
    if "raise_terrain" in prompt.subset.primitives:
        assert "earth" in notes["element"] and "raise_terrain" in notes["element"]
    common = build_proposal_prompt(library, ProposalRequest(1, "common", skeleton="strike"))
    common_notes = field_notes(
        library, ProposalRequest(1, "common", skeleton="strike"), common.subset
    )
    assert "不要填 variants" in common_notes["variants"]


def test_terrain_feedback_names_the_top_level_field(library: ContentLibrary) -> None:
    """``exclusion.terrain_needs_earth`` 的回饋要說出頂層 element 填什麼（判定不變）。"""
    skill = next(
        s
        for s in library.skills.values()
        if any(e.type == "raise_terrain" for e in s.effects) and s.kind == "active"
    )
    request = ProposalRequest(skill.tier, skill.rarity, skeleton=skill.skeleton)
    prompt = build_proposal_prompt(library, request)
    data = proposal_from_skill(skill, library)
    data.pop("element", None)  # 技能元素只靠標籤：拿掉 earth 標籤就不是大地技能
    data["tags"] = [t for t in data.get("tags", []) if t != "earth"]
    result = evaluate_proposal(
        json.dumps(data, ensure_ascii=False),
        prompt.models,
        library,
        ProposalContext(skill.tier, skill.rarity),
    )
    errors = [e for e in result.errors if e.code == "exclusion.terrain_needs_earth"]
    assert errors and not result.ok
    assert 'element: "earth"' in errors[0].message and "頂層" in errors[0].message


def test_advice_for_main_damage_and_secondary_count(library: ContentLibrary) -> None:
    main = ProposalError(
        "skill",
        "variants[0].replace_effect.index",
        "value_error",
        "變奏「甲」：主傷害（第 0 個效果）不能被換掉",
    )
    assert advise(main, library).message.endswith(MAIN_DAMAGE_ADVICE)
    extra = ProposalError("rules", "", "skeleton.secondary_count", "骨架 strike：附帶效果最多 1 個")
    assert advise(extra, library).message.endswith(SECONDARY_ADVICE)
    other = ProposalError("rules", "", "budget.over", "超出預算")
    assert advise(other, library) is other  # 其他錯誤不動
