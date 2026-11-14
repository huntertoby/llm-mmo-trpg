"""LB-2c（玩法 PM 交接 4.1.18 第 1、2、3、5 點）：只改送給約束解碼的 schema、prompt 與回饋。

1. 題目沒要求變奏時 schema 沒有 ``variants``、prompt 沒有變奏說明
   （提議模型與驗證不變）。
2. ``self_on_high_ground`` 開放給 LLM、工坊、白板、閃現（拿掉 ``handwritten_only``）。
3. 被動題目的 schema 固定 ``category: spell``、``weapon_req: any``；
   被動 ``budget.over`` 回饋附修法。
4. ``RANGE_DELTA_ADVICE`` 不再舉「single 並填數字 range」的例子。

全部離線。
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from pydantic import TypeAdapter

from trpg.content.library import ContentLibrary
from trpg.llm.prompts.proposal import (
    FIXED_CATEGORY_NOTE_ZH,
    build_proposal_prompt,
    field_notes,
    fixed_category,
    variant_limit,
)
from trpg.skillgen.option_params import condition_choice
from trpg.skillgen.proposal import ProposalError, proposal_from_skill
from trpg.skillgen.proposal.evaluate import (
    PASSIVE_BUDGET_ADVICE,
    RANGE_DELTA_ADVICE,
    advise,
)
from trpg.skillgen.proposal.schema_shape import fix_category
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.validate import validate_skill

EPIC_COMBO = ProposalRequest(1, "epic", skeleton="combo")
Q12 = ProposalRequest(1, "epic", skeleton="passive", keywords=("high_ground",))
HIGH = "self_on_high_ground"


def _top_branches(schema: dict[str, Any]) -> list[dict[str, Any]]:
    defs = schema["$defs"]
    out = []
    for item in schema["oneOf"]:
        out.append(defs[item["$ref"].removeprefix("#/$defs/")])
    return out


# -- 1：變奏欄位只在題目要求時給 ---------------------------------------------------------


def test_no_variants_in_schema_or_notes_unless_the_topic_asks(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, EPIC_COMBO)
    assert not EPIC_COMBO.wants_variants
    assert variant_limit(library, EPIC_COMBO, prompt.subset) == 0
    assert '"variants"' not in json.dumps(prompt.json_schema)
    assert "variants" not in field_notes(library, EPIC_COMBO, prompt.subset)
    assert "variants" not in prompt.messages[1]["content"].split("<available>")[0]


def test_topic_asking_for_variants_gets_the_field_and_note(library: ContentLibrary) -> None:
    request = replace(EPIC_COMBO, wants_variants=True)
    prompt = build_proposal_prompt(library, request)
    limit = library.ruleset.core.variant_max_by_rarity["epic"]
    assert variant_limit(library, request, prompt.subset) == limit > 0
    branches = prompt.json_schema["$defs"]["Variant"]["anyOf"]
    assert len(branches) == 15
    assert "range_delta" in field_notes(library, request, prompt.subset)["variants"]


def test_passives_never_get_variants(library: ContentLibrary) -> None:
    request = replace(Q12, wants_variants=True)
    prompt = build_proposal_prompt(library, request)
    assert variant_limit(library, request, prompt.subset) == 0
    assert '"variants"' not in json.dumps(prompt.json_schema)


def test_models_still_accept_variants_validation_unchanged(library: ContentLibrary) -> None:
    """只收窄 schema：驗證用的提議模型照舊收變奏（Mock 與手寫技能的轉換不變）。"""
    prompt = build_proposal_prompt(library, EPIC_COMBO)
    assert "variants" in json.dumps(prompt.models.json_schema())


# -- 2：self_on_high_ground 開放 -------------------------------------------------------


def test_self_on_high_ground_is_open_to_generated_skills(library: ContentLibrary) -> None:
    cond = library.ruleset.conditions.by_id()[HIGH]
    assert not cond.handwritten_only
    assert "unavailable_zh" not in condition_choice(cond, library, effect_level=True).info
    base = library.skills["skill_eagle_eye"]
    made = base.model_copy(
        update={"provenance": base.provenance.model_copy(update={"origin": "workshop"})}
    )
    rules = {v.rule for v in validate_skill(made, library)}
    assert "condition.handwritten_only" not in rules


def test_q12_offers_self_on_high_ground(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, Q12)
    assert HIGH in prompt.subset.conditions
    user = prompt.messages[1]["content"]
    available = json.loads(user.split("<available>\n")[1].split("\n</available>")[0])
    assert f"條件 {HIGH}" in available["keywords"][0]["ways"]
    assert HIGH in json.dumps(prompt.json_schema)


def test_eagle_eye_passes_the_q12_models(library: ContentLibrary) -> None:
    """鷹眼（被動、站在高處）在 Q12 的提議模型下轉得過去（條件不再被篩掉）。"""
    prompt = build_proposal_prompt(library, Q12)
    data = proposal_from_skill(library.skills["skill_eagle_eye"], library)
    TypeAdapter(prompt.models.skill).validate_python(data)


# -- 3：被動題目固定 spell／any、budget.over 回饋 --------------------------------------------


def test_passive_schema_fixes_category_and_weapon_req(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, Q12)
    assert fixed_category(library, prompt.subset) == ("spell", "any")
    branches = _top_branches(prompt.json_schema)
    assert branches
    for node in branches:
        assert node["properties"]["category"] == {"const": "spell", "type": "string"}
        assert node["properties"]["weapon_req"] == {"const": "any", "type": "string"}
    note = field_notes(library, Q12, prompt.subset)["category"]
    assert note == FIXED_CATEGORY_NOTE_ZH.format(category="spell", weapon_req="any")


def test_active_schema_keeps_both_categories(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, EPIC_COMBO)
    assert fixed_category(library, prompt.subset) is None
    consts = {n["properties"]["category"].get("const") for n in _top_branches(prompt.json_schema)}
    assert consts == {"weapon", "spell"}


def test_fix_category_drops_other_branches_and_never_empties() -> None:
    schema = {
        "oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
        "$defs": {
            "A": {
                "properties": {"category": {"const": "weapon"}, "weapon_req": {"enum": ["melee"]}}
            },
            "B": {"properties": {"category": {"const": "spell"}, "weapon_req": {"enum": ["any"]}}},
        },
    }
    fixed = fix_category(schema, "spell", "any")
    assert fixed["oneOf"] == [{"$ref": "#/$defs/B"}]
    assert fixed["$defs"]["B"]["properties"]["weapon_req"] == {"const": "any", "type": "string"}
    assert fix_category(schema, "other", "any") == schema


def test_passive_budget_over_gets_trigger_advice(library: ContentLibrary) -> None:
    error = ProposalError(
        "rules", "", "budget.over", "超出預算：total 5.50 ÷ 可用預算 4.20 ＝ 131.0%"
    )
    passive = library.skills["skill_eagle_eye"]
    advised = advise(error, library, passive)
    assert advised.message == error.message + PASSIVE_BUDGET_ADVICE.format(
        trigger="every_n_hits（n: 3）"
    )
    assert advised.code == error.code
    active = library.skills["skill_tidal_spear"]
    assert advise(error, library, active) == error
    assert advise(error, library) == error


# -- 4：RANGE_DELTA_ADVICE 不舉 single 的例子 ---------------------------------------------


def test_range_delta_advice_has_no_single_range_example() -> None:
    assert "single" not in RANGE_DELTA_ADVICE
    assert "例" not in RANGE_DELTA_ADVICE
