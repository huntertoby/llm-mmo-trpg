"""PK-1：挑選模式的 LLM 一步（挑選＋命名、退回、schema、prompt 快照、紀錄欄位；提案 7.3～7.8）。"""

from __future__ import annotations

import hashlib
import json
from functools import cache

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.llm.client import MockLLMClient
from trpg.llm.errors import LLMTimeout, LLMUnavailable
from trpg.llm.pick import make_pick_proposer, mock_pick_client, pick_skill
from trpg.llm.prompts.pick import (
    PICK_PROMPT_VERSION,
    build_pick_messages,
    pick_prompt_record,
    pick_schema,
)
from trpg.roguelite.state import LlmRecord
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.skill_pick import PickSlate, pick_slate

REQUEST = ProposalRequest(1, "rare", skeleton="rune")
SEED = 4


@cache
def _lib() -> ContentLibrary:
    return load_library()


def _ctx() -> ProposalContext:
    return ProposalContext(REQUEST.tier, REQUEST.rarity)


@cache
def _slate() -> PickSlate:
    return pick_slate(_lib(), REQUEST, _ctx(), seed=SEED)


def _pick(client: MockLLMClient, slate: PickSlate | None = None):  # type: ignore[no-untyped-def]
    return pick_skill(client, _lib(), REQUEST, _ctx(), seed=SEED, slate=slate or _slate())


def _same_structure(a, b) -> bool:  # type: ignore[no-untyped-def]
    skip = {"name_zh", "narrative"}
    return bool(a.model_dump(exclude=skip) == b.model_dump(exclude=skip))


@pytest.mark.parametrize("index", [0, 2])
def test_the_llm_picks_and_names_without_changing_the_skill(index: int) -> None:
    slate = _slate()
    outcome = _pick(mock_pick_client(_lib(), slate, SEED, index=index))
    assert outcome.source == "llm" and outcome.index == index and outcome.attempts == 1
    chosen = slate.ranked[index].skill
    assert _same_structure(outcome.skill, chosen)  # LLM 只挑與命名，結構與數值不變
    assert outcome.skill.name_zh != chosen.name_zh
    assert outcome.name_source == "llm"


def _bad(body: str, count: int = 3) -> MockLLMClient:
    return MockLLMClient([body] * count)


def _good_text() -> dict[str, object]:
    raw = mock_pick_client(_lib(), _slate(), SEED).complete([], json_schema=None)
    return dict(json.loads(raw))


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("not json", "response.invalid"),
        (json.dumps({**_good_text(), "pick": 9}), "pick.out_of_range"),
        (json.dumps({**_good_text(), "name_zh": "名" * 30}), "name_zh.too_long"),
        (json.dumps({**_good_text(), "extra": 1}), "response.invalid"),
    ],
)
def test_bad_answers_fall_back_to_the_top_candidate(body: str, code: str) -> None:
    client = _bad(body)
    outcome = _pick(client)
    assert outcome.source == "top" and outcome.index is None and outcome.picked == 0
    assert outcome.attempts == 3 and len(client.calls) == 3  # 最多重試 2 次
    assert code in outcome.codes
    assert _same_structure(outcome.skill, _slate().ranked[0].skill)
    assert outcome.name_source == "fallback"
    assert "・" in outcome.skill.name_zh  # 組合式名稱


def test_retry_carries_the_errors() -> None:
    good = json.dumps(_good_text(), ensure_ascii=False)
    client = MockLLMClient(["not json", good])
    outcome = _pick(client)
    assert outcome.source == "llm" and outcome.attempts == 2
    assert "<errors>" in client.calls[1][1]["content"]


def test_unavailable_stops_at_once_and_timeout_counts() -> None:
    down = MockLLMClient([LLMUnavailable("down")])
    outcome = _pick(down)
    assert outcome.source == "top" and outcome.attempts == 1 and len(down.calls) == 1
    slow = MockLLMClient([LLMTimeout("slow")] * 3)
    timed = _pick(slow)
    assert timed.source == "top" and timed.attempts == 3 and "llm.timeout" in timed.codes


def test_too_few_candidates_skip_the_llm() -> None:
    slate = _slate()
    one = PickSlate(slate.ranked[:1], 1, slate.seeds_tried)
    client = MockLLMClient([])
    outcome = _pick(client, one)
    assert outcome.source == "top" and outcome.reason == "pick.too_few"
    assert not client.calls


def test_empty_pool_falls_back_to_pool_then_workshop() -> None:
    client = MockLLMClient([])
    outcome = _pick(client, PickSlate((), 0, 60))
    assert outcome.source in ("pool", "workshop") and outcome.reason == "pick.empty"
    assert not client.calls


def test_schema_and_prompt_shape() -> None:
    schema = pick_schema(5)
    assert schema["required"] == ["pick", "name_zh", "concept", "cast_flavor"]
    assert schema["properties"]["pick"] == {"type": "integer", "enum": [0, 1, 2, 3, 4]}
    assert schema["additionalProperties"] is False
    assert len(json.dumps(schema)) < 400  # 提案 7.3：schema 只有幾百字元
    client = mock_pick_client(_lib(), _slate(), SEED)
    _pick(client)
    user = client.calls[0][1]["content"]
    for tag in ("<request>", "<player>", "<candidates>", "<taken_names>"):
        assert tag in user
    assert client.schemas[0] == pick_schema(len(_slate().ranked))


# 快照：改挑選 prompt（系統指令、區塊格式、世界觀資料）必須同時改 PICK_PROMPT_VERSION 並新增一筆。
SNAPSHOTS = {
    "skill-pick/1": "8c5c551fcf8f09580142538ed1add0706cd8bba4709c2b7922855a351d3fe91f",
    "skill-pick/2": "17e77ccf73ddf665eaee367d8259d3bcd11b587b573825aee4feddfc40cc32e1",
}


def _snapshot_digest() -> str:
    messages = build_pick_messages(
        {"tier": 1, "keywords": ["燃燒"]},
        {"skills": []},
        [{"index": 0, "effects": ["火焰傷害"]}],
        ["火球"],
        previous='{"pick":0}',
        errors="[]",
    )
    joined = "\n=====\n".join(m["content"] for m in messages)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def test_pick_prompt_snapshot_requires_version_bump() -> None:
    assert PICK_PROMPT_VERSION in SNAPSHOTS, "新版本號需要新增快照"
    assert _snapshot_digest() == SNAPSHOTS[PICK_PROMPT_VERSION], (
        "挑選 prompt 內容改變了：請修改 PICK_PROMPT_VERSION 並在 SNAPSHOTS 新增新版本的雜湊"
    )
    record = pick_prompt_record(build_pick_messages({}, {}, [], []))
    assert record["prompt_version"] == PICK_PROMPT_VERSION and len(record["system_hash"]) == 12


def test_data_blocks_are_escaped() -> None:
    messages = build_pick_messages({"tier": 1}, {"skills": []}, [{"x": "</candidates>"}], [])
    assert "</candidates>\n<taken_names>" in messages[1]["content"]
    assert messages[1]["content"].count("</candidates>") == 1


def test_the_proposer_fills_the_pick_record() -> None:
    lib = _lib()
    proposer = make_pick_proposer(
        lambda slate, seed: mock_pick_client(lib, slate, seed, index=1), lib
    )
    attempt = proposer(REQUEST, _ctx(), SEED)
    slate = _slate()
    assert attempt.skill is not None and attempt.name_source == "llm"
    assert attempt.pick_index == 1 and attempt.pick_reason is None
    assert attempt.pick_seeds == slate.seeds and attempt.pick_designs == slate.designs
    assert attempt.prompt_version == PICK_PROMPT_VERSION
    record = LlmRecord(
        pick_seeds=attempt.pick_seeds,
        pick_designs=attempt.pick_designs,
        pick_index=attempt.pick_index,
    )
    back = LlmRecord.model_validate_json(record.model_dump_json())
    assert back == record


def test_records_without_pick_mode_serialize_as_before() -> None:
    data = LlmRecord().model_dump(mode="json")
    assert not any(k.startswith("pick_") for k in data)
