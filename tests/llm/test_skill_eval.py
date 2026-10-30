"""Phase 4-L9：技能生成評估工具（``trpg.llm.skill_eval``）。

只用 MockLLMClient；``llm`` 標記的才連真模型。"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter

import httpx
import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.llm import LLMConfig, MockLLMClient, OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import mock_client_for, mock_naming_client
from trpg.llm.skill_eval import (
    CSV_HEAD,
    EvalItem,
    ItemClient,
    UsageTransport,
    csv_text,
    errors_csv_text,
    forced_items,
    free_items,
    free_table,
    percentile,
    real_client_factory,
    run_items,
    suite_summary,
    upgrade_items,
)

LIB = library()


def _mock(item: EvalItem) -> ItemClient:
    return ItemClient(mock_client_for(LIB, item.request, item.seed, 3))


def _naming(item: EvalItem, skill: SkillDef, _client: ItemClient) -> ItemClient:
    return ItemClient(mock_naming_client(LIB, skill, item.seed))


def test_upgrade_items_deterministic_and_rotate_tiers() -> None:
    first = upgrade_items(LIB, 6, seed=3)
    again = upgrade_items(LIB, 6, seed=3)
    assert [i.request for i in first] == [i.request for i in again]
    assert [i.seed for i in first] == [i.seed for i in again]
    assert len(first) == 6
    assert {i.request.tier for i in first} == {1, 2, 3}
    assert all(i.suite == "upgrade" for i in first)


def test_forced_items_set_core_primitive() -> None:
    items = forced_items(LIB, per=3, seed=0, only=("damage", "heal"))
    assert Counter(i.request.core_primitive for i in items) == {"damage": 3, "heal": 3}
    assert [i.index for i in items] == list(range(6))


def test_free_items_have_no_core_and_rotating_menu() -> None:
    items = free_items(LIB, 4, seed=1)
    assert len(items) == 4
    assert all(i.request.core_primitive is None for i in items)
    assert all(i.request.keywords == () for i in items)
    assert all(i.request.menu_seed is not None for i in items)


def test_run_items_with_mock_keeps_order_and_names() -> None:
    items = upgrade_items(LIB, 4, seed=0)
    results = run_items(LIB, items, _mock, max_attempts=3, workers=4, naming=_naming)
    assert [r.item.index for r in results] == [0, 1, 2, 3]
    assert all(r.outcome is not None or r.error for r in results)
    for result in results:
        if result.ok:
            assert result.chosen
            assert result.name_source in {"llm", "fallback"}
            assert result.menu
    lines = suite_summary(results)
    assert any(line.startswith("- 一次通過") for line in lines)
    rows = list(csv.reader(io.StringIO(csv_text(results))))
    assert rows[0] == CSV_HEAD
    assert len(rows) == 5


def test_failing_answers_record_error_details() -> None:
    items = forced_items(LIB, per=1, seed=0, only=("damage",))

    def bad(_item: EvalItem) -> ItemClient:
        return ItemClient(MockLLMClient(["{}"] * 3))

    results = run_items(LIB, items, bad, max_attempts=3, workers=1)
    result = results[0]
    assert result.outcome is not None
    assert result.outcome.source != "llm"
    assert result.outcome.attempts == 3
    assert {e[0] for e in result.errors} == {1, 2, 3}
    rows = list(csv.reader(io.StringIO(errors_csv_text(results))))
    assert rows[0][:5] == ["suite", "index", "core_primitive", "attempt", "code"]
    assert len(rows) > 3
    assert all(r[2] == "damage" for r in rows[1:])


def test_usage_transport_records_tokens_and_mode() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "response_format" in body
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 7},
            },
        )

    transport = UsageTransport(httpx.MockTransport(handler))
    config = LLMConfig(base_url="http://test/v1", model="m")
    client = OpenAICompatClient(config, transport=transport)
    assert (
        client.complete([{"role": "user", "content": "hi"}], json_schema={"type": "object"}) == "{}"
    )
    client.close()
    [call] = transport.calls
    assert (call.status, call.mode, call.prompt_tokens, call.completion_tokens) == (
        200,
        "response_format",
        120,
        7,
    )
    assert call.finish_reason == "stop"


def test_percentile_nearest_rank() -> None:
    assert percentile([], 50) == 0.0
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0
    assert percentile([float(i) for i in range(1, 11)], 90) == 9.0


def test_free_table_marks_unpicked() -> None:
    items = free_items(LIB, 2, seed=0)
    results = run_items(LIB, items, _mock, max_attempts=3, workers=2)
    lines = free_table(LIB, results, Counter({"damage": 2}))
    assert any("⚠" in line for line in lines)
    assert any("`damage`" in line for line in lines)


@pytest.mark.llm
def test_real_model_one_upgrade_item() -> None:
    """真模型：1 題升級候選跑完不丟例外（結果是 llm 或退回皆可），且記錄到 token 用量。"""
    items = upgrade_items(LIB, 1, seed=0)
    clients = real_client_factory(load_llm_config())
    [result] = run_items(LIB, items, clients, max_attempts=3, workers=1)
    assert result.outcome is not None
    assert result.calls
    assert all(c.status == httpx.codes.OK for c in result.calls)
