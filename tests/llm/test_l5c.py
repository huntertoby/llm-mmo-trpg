"""4-L5c：false 視為省略的清理、schema 字元上限、token 估算不含 schema（全部用 Mock）。"""

from __future__ import annotations

import json

import pytest

from trpg.content.library import ContentLibrary
from trpg.llm import MockLLMClient
from trpg.llm.prompts import proposal as prompt_module
from trpg.llm.prompts.proposal import build_proposal_prompt, estimate_messages_tokens
from trpg.llm.propose import propose_skill
from trpg.llm.response import drop_false_flags
from trpg.skillgen.proposal import ProposalContext, proposal_from_skill
from trpg.skillgen.proposal_subset import (
    SCHEMA_CHAR_LIMIT,
    ProposalRequest,
    SubsetError,
    available_payload,
    json_chars,
    json_tokens,
    select_subset,
)
from trpg.skillgen.random_composer import default_library


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


def test_false_flags_are_treated_as_omitted() -> None:
    text = json.dumps(
        {
            "name_zh": "x",
            "effects": [
                {"type": "damage", "explode": False, "split_heal": True, "element": "fire"},
                {"type": "heal", "explode": False},  # 不是只能填 true 的原語：原樣保留
            ],
        },
        ensure_ascii=False,
    )
    out = json.loads(drop_false_flags(text))
    assert out["effects"][0] == {"type": "damage", "split_heal": True, "element": "fire"}
    assert out["effects"][1] == {"type": "heal", "explode": False}
    assert drop_false_flags("不是 JSON") == "不是 JSON"
    same = json.dumps({"type": "damage", "explode": True})
    assert drop_false_flags(same) == same


def test_loop_accepts_a_proposal_with_false_flags(library: ContentLibrary) -> None:
    proposal = proposal_from_skill(library.skills["skill_fire_arrow"], library)
    for effect in proposal["effects"]:
        if effect["type"] == "damage":
            effect["explode"] = False
    client = MockLLMClient([json.dumps(proposal, ensure_ascii=False)])
    outcome = propose_skill(
        client,
        library,
        ProposalRequest(1, "common", skeleton="strike"),
        ProposalContext(1, "common"),
        seed=1,
    )
    assert (outcome.source, outcome.attempts) == ("llm", 1)
    assert len(client.calls) == 1


def test_prompt_tokens_count_messages_only_and_schema_has_a_char_limit(
    library: ContentLibrary,
) -> None:
    request = ProposalRequest(1, "legendary", skeleton="control", keywords=("wet",))
    prompt = build_proposal_prompt(library, request)
    assert prompt.tokens == estimate_messages_tokens(prompt.messages)
    assert prompt.subset.tokens == json_tokens(available_payload(library, prompt.subset))
    assert prompt.schema_chars == json_chars(prompt.json_schema) <= SCHEMA_CHAR_LIMIT
    # 子集由訊息估算決定，與 schema 長度無關
    assert select_subset(library, request).tokens == prompt.subset.tokens


def test_schema_over_the_char_limit_is_rejected(
    library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompt_module, "SCHEMA_CHAR_LIMIT", 1_000)
    with pytest.raises(SubsetError, match="schema"):
        build_proposal_prompt(library, ProposalRequest(1, "rare"))
