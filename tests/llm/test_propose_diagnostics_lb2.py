"""LB-2：提議失敗的完整診斷（原始輸出、錯誤全文、pydantic 位置、回饋文字）與日誌。

全部用 MockLLMClient，不需網路。
"""

from __future__ import annotations

import json
import logging

import pytest

from trpg.content.library import ContentLibrary
from trpg.llm import LLMTimeout, MockLLMClient
from trpg.llm.propose import AttemptDetail, AttemptRecord, propose_skill
from trpg.skillgen.proposal import ProposalContext, ProposalError, proposal_from_skill
from trpg.skillgen.proposal_subset import ProposalRequest

STRIKE = ProposalRequest(1, "common", skeleton="strike")
CTX = ProposalContext(1, "common")
BAD_SHAPE = json.dumps({"kind": "active", "skeleton": "strike"})


def _good(library: ContentLibrary) -> str:
    skill = library.skills["skill_fire_arrow"]
    return json.dumps(proposal_from_skill(skill, library), ensure_ascii=False)


def _nested_bad(library: ContentLibrary) -> str:
    data = json.loads(_good(library))
    data["effects"][0]["bogus_field"] = 1
    return json.dumps(data, ensure_ascii=False)


def test_failed_attempt_keeps_raw_errors_and_feedback(library: ContentLibrary) -> None:
    raw = "```json\n" + _nested_bad(library) + "\n```"
    client = MockLLMClient([raw, _good(library)])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert outcome.source == "llm" and outcome.attempts == 2
    first = outcome.records[0].detail
    assert first is not None
    assert first.raw == raw  # 清理前的原始輸出
    assert first.errors and {e["code"] for e in first.errors} == set(outcome.codes[0])
    assert all(e["message"] for e in first.errors)
    assert any("bogus_field" in e.get("loc", "") for e in first.errors)  # pydantic 原始位置
    assert any(e.get("input") == "1" for e in first.errors)
    # 回饋文字就是下一次 prompt 的 <errors> 內容
    assert first.feedback is not None
    second_user = client.calls[1][1]["content"]
    assert json.loads(first.feedback)["attempt"] == 1
    for error in json.loads(first.feedback)["errors"]:
        assert error["code"] in second_user
    passed = outcome.records[1].detail
    assert passed is not None and passed.errors == () and passed.feedback is None


def test_last_attempt_has_no_feedback(library: ContentLibrary) -> None:
    client = MockLLMClient([BAD_SHAPE, BAD_SHAPE])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3, max_attempts=2)
    assert outcome.source != "llm"
    details = [r.detail for r in outcome.records]
    assert details[0] is not None and details[0].feedback is not None
    assert details[1] is not None and details[1].feedback is None and details[1].errors


def test_call_error_is_recorded(library: ContentLibrary) -> None:
    client = MockLLMClient([LLMTimeout("慢"), _good(library)])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    detail = outcome.records[0].detail
    assert detail is not None and detail.call_error == "慢" and detail.raw == ""
    assert detail.to_json()["call_error"] == "慢"


def test_value_error_diagnostic_has_validator_location_and_input() -> None:
    error = ProposalError(
        "proposal", "effects[0]", "value_error", "原因", loc="effects.0.damage", input='{"a": 1}'
    )
    data = error.diagnostic()
    assert data["loc"] == "effects.0.damage" and data["input"] == '{"a": 1}'
    # 送給 LLM 的版本不帶診斷欄位，也不影響比較
    assert "loc" not in error.to_json() and "input" not in error.to_json()
    assert error == ProposalError("proposal", "effects[0]", "value_error", "原因")


def test_detail_does_not_change_record_equality() -> None:
    plain = AttemptRecord(("x",), 1.0)
    detailed = AttemptRecord(("x",), 1.0, detail=AttemptDetail(raw="r"))
    assert plain == detailed


def test_failures_are_logged_without_raw_output(
    library: ContentLibrary, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "玩家秘密字串"
    raw = json.dumps({"kind": "active", "skeleton": "strike", "note": secret}, ensure_ascii=False)
    client = MockLLMClient([raw, _good(library)])
    with caplog.at_level(logging.INFO, logger="trpg.llm"):
        propose_skill(client, library, STRIKE, CTX, seed=3)
    lines = [r.getMessage() for r in caplog.records if r.name == "trpg.llm"]
    assert any("第 1 次嘗試不合格" in line for line in lines)
    assert all(secret not in line for line in lines)
