"""LB-2b 待決 6：變奏的射程加值 ``range_delta`` 開放給提議模型（只開 +1～+2，照組合器）。

驗證器與預算照舊。全部離線。
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter

from trpg.content.library import ContentLibrary
from trpg.llm.prompts.proposal import VARIANTS_NOTE_ZH, build_proposal_prompt, field_notes
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalError,
    evaluate_proposal,
    proposal_from_skill,
    to_skill_def,
)
from trpg.skillgen.proposal.evaluate import RANGE_DELTA_ADVICE, advise
from trpg.skillgen.proposal.schema_shape import VARIANT_SWAP_FIELDS
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers
from trpg.skillgen.proposal_subset import ProposalRequest

EPIC_COMBO = ProposalRequest(1, "epic", skeleton="combo", wants_variants=True)
"""LB-2c 起變奏欄位只在題目要求變奏時給；這裡測的是要求時的 schema 與說明。"""
_BASE = frozenset({"id", "name_zh", "when"})


def test_variant_branches_include_range_delta(library: ContentLibrary) -> None:
    assert "range_delta" in VARIANT_SWAP_FIELDS
    schema = build_proposal_prompt(library, EPIC_COMBO).json_schema
    branches = schema["$defs"]["Variant"]["anyOf"]
    assert len(branches) == 15
    only = [b for b in branches if set(b["required"]) - _BASE == {"range_delta"}]
    assert len(only) == 1
    assert only[0]["properties"]["range_delta"]["enum"] == [1, 2]


def test_variants_note_mentions_range_bonus(library: ContentLibrary) -> None:
    request = EPIC_COMBO
    notes = field_notes(library, request, build_proposal_prompt(library, request).subset)
    assert "range_delta" in VARIANTS_NOTE_ZH and "range_delta" in notes["variants"]


def _tidal(library: ContentLibrary, delta: Any) -> tuple[dict[str, Any], Any]:
    """潮汐之矛（居高＝射程 +2，``skill_tidal_spear``）的提議，把居高變奏的射程加值換成 ``delta``。
    數值照原技能放回（射程加值除外：那是 LLM 選的）。"""
    skill = library.skills["skill_tidal_spear"]
    data = proposal_from_skill(skill, library)
    data["variants"][1]["range_delta"] = delta
    _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), library)
    kept = [(path, value) for path, value in removed if path[-1] != "range_delta"]
    return data, fixed_filler(kept)


def test_llm_range_delta_reaches_the_skill(library: ContentLibrary) -> None:
    """LLM 選的 +1 原樣進技能（補值器不動它），變奏型態的射程 3 → 4；規則層（預算等）照常判定。"""
    skill = library.skills["skill_tidal_spear"]
    prompt = build_proposal_prompt(library, ProposalRequest(1, "epic", skeleton="combo"))
    ctx = ProposalContext(skill.tier, skill.rarity)
    data, fill = _tidal(library, 1)
    result = evaluate_proposal(json.dumps(data), prompt.models, library, ctx, fill=fill)
    assert not [e for e in result.errors if e.stage in ("proposal", "skill")]
    proposal = TypeAdapter(prompt.models.skill).validate_python(data)
    converted = to_skill_def(proposal, ctx, fill, library)
    assert converted.variant("high_tide").range_delta == 1
    assert converted.variant_form("high_tide").shape.range == 4


def test_range_delta_only_plus_one_or_two(library: ContentLibrary) -> None:
    """射程變短或 +3 的變奏提議模型直接擋下（驗證器的 −1～+2 不變，只是 LLM 只開加值）。"""
    prompt = build_proposal_prompt(library, ProposalRequest(1, "epic", skeleton="combo"))
    ctx = ProposalContext(1, "epic")
    for delta in (-1, 0, 3):
        data, fill = _tidal(library, delta)
        result = evaluate_proposal(json.dumps(data), prompt.models, library, ctx, fill=fill)
        codes = {(e.path, e.code) for e in result.errors if e.stage == "proposal"}
        assert ("variants[1].range_delta", "literal_error") in codes, (delta, result.errors)


def test_variants_note_lists_shapes_with_numeric_range(library: ContentLibrary) -> None:
    """初版重測 Gemma 在 line、cone 上填 range_delta：說明要列出這題哪些形狀有射程。"""
    request = ProposalRequest(1, "epic", wants_variants=True)
    subset = build_proposal_prompt(library, request).subset
    note = field_notes(library, request, subset)["variants"]
    shapes = library.ruleset.shapes.by_id()
    ranged = [s for s in subset.shapes if "range" in shapes[s].params]
    plain = [s for s in subset.shapes if s not in ranged]
    assert ranged and plain
    head, tail = note.split("這題有射程的形狀：")[1].split("沒有射程")[0].split("；")
    assert all(s in head for s in ranged)
    assert all(s in tail for s in plain)


def test_range_delta_error_gets_fix_advice(library: ContentLibrary) -> None:
    """range_delta 配上沒有射程的形狀：判定不變，回饋附修法。"""
    error = ProposalError(
        "skill",
        "variants[0].range_delta",
        "value_error",
        "變奏「甲」：range_delta 只能用在射程是數字的形狀，收到 line 的射程 None",
    )
    advised = advise(error, library)
    assert advised.message == error.message + RANGE_DELTA_ADVICE
    assert advised.code == error.code and advised.path == error.path
