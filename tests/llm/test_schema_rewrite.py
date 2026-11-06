"""MAC-2：``oneOf`` → ``anyOf`` 改寫、退回 ``guided_json`` 的警告、``llm ping`` 的 schema 寫法。

全部用 ``httpx.MockTransport``，不需網路。
"""

from __future__ import annotations

import copy
import io
import json
import logging
from typing import Any

import httpx
import pytest

from trpg.cli.llm import PING_SCHEMA, cmd_llm_ping
from trpg.llm import ChatMessage, LLMBadResponse, LLMConfig, OpenAICompatClient
from trpg.llm.client import rewrite_oneof_as_anyof

MSGS = [ChatMessage(role="user", content="哈囉")]
NESTED: dict[str, Any] = {
    "type": "object",
    "title": "T",
    "properties": {
        "kind": {"oneOf": [{"const": "a"}, {"const": "b"}]},
        "items": {"type": "array", "items": {"oneOf": [{"$ref": "#/$defs/X"}, {"type": "null"}]}},
        "mix": {"allOf": [{"oneOf": [{"type": "integer"}]}], "anyOf": [{"oneOf": [{}]}]},
    },
    "required": ["kind"],
    "$defs": {"X": {"oneOf": [{"type": "string"}, {"type": "integer"}], "minLength": 1}},
}


def ok_body(text: str = "{}") -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def client_with(handler: Any, **cfg: Any) -> OpenAICompatClient:
    return OpenAICompatClient(LLMConfig(**cfg), transport=httpx.MockTransport(handler))


def _has_key(node: Any, key: str) -> bool:
    if isinstance(node, dict):
        return key in node or any(_has_key(v, key) for v in node.values())
    if isinstance(node, list):
        return any(_has_key(v, key) for v in node)
    return False


# ---- 改寫函式 ----


def test_rewrite_renames_nested_oneof_and_keeps_rest() -> None:
    original = copy.deepcopy(NESTED)
    out = rewrite_oneof_as_anyof(NESTED)
    assert original == NESTED  # 原 dict 未被改
    assert out is not NESTED
    assert not _has_key(out, "oneOf")
    assert out["properties"]["kind"] == {"anyOf": [{"const": "a"}, {"const": "b"}]}
    assert out["properties"]["items"]["items"] == {
        "anyOf": [{"$ref": "#/$defs/X"}, {"type": "null"}]
    }
    assert out["properties"]["mix"]["allOf"] == [{"anyOf": [{"type": "integer"}]}]
    assert out["properties"]["mix"]["anyOf"] == [{"anyOf": [{}]}]
    assert out["$defs"]["X"] == {"anyOf": [{"type": "string"}, {"type": "integer"}], "minLength": 1}
    # 其他鍵原樣
    assert (out["type"], out["title"], out["required"]) == ("object", "T", ["kind"])


def test_rewrite_leaves_oneof_when_anyof_already_present() -> None:
    both = {"oneOf": [{"type": "string"}], "anyOf": [{"type": "integer"}]}
    assert rewrite_oneof_as_anyof(both) == both


# ---- request body ----


def test_request_body_has_no_oneof_in_both_modes() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=ok_body())

    client_with(handler).complete(MSGS, json_schema=NESTED)
    client_with(handler, json_schema_mode="guided_json").complete(MSGS, json_schema=NESTED)
    sent_rf = bodies[0]["response_format"]["json_schema"]["schema"]
    sent_gj = bodies[1]["guided_json"]
    assert not _has_key(sent_rf, "oneOf") and _has_key(sent_rf, "anyOf")
    assert not _has_key(sent_gj, "oneOf") and _has_key(sent_gj, "anyOf")
    assert sent_rf == sent_gj == rewrite_oneof_as_anyof(NESTED)


def test_rewrite_disabled_sends_oneof_untouched() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=ok_body())

    client_with(handler, oneof_as_anyof=False).complete(MSGS, json_schema=NESTED)
    assert bodies[0]["response_format"]["json_schema"]["schema"] == NESTED
    assert LLMConfig().oneof_as_anyof is True


# ---- 退回 guided_json 的警告 ----


def test_fallback_to_guided_json_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "response_format" in json.loads(request.content):
            return httpx.Response(400, json={"error": "oneOf constraints are not supported"})
        return httpx.Response(200, json=ok_body())

    client = client_with(handler)
    assert client.accepted_schema_mode is None
    with caplog.at_level(logging.WARNING, logger="trpg.llm"):
        client.complete(MSGS, json_schema=NESTED)
        client.complete(MSGS, json_schema=NESTED)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "拒絕 response_format（HTTP 400）" in warnings[0].getMessage()
    assert "guided_json" in warnings[0].getMessage()
    assert client.accepted_schema_mode == "guided_json"


def test_no_warning_when_response_format_accepted(caplog: pytest.LogCaptureFixture) -> None:
    client = client_with(lambda r: httpx.Response(200, json=ok_body()))
    with caplog.at_level(logging.WARNING, logger="trpg.llm"):
        client.complete(MSGS, json_schema=NESTED)
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]
    assert client.accepted_schema_mode == "response_format"


def test_all_modes_rejected_warns_only_for_first_fallback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = client_with(lambda r: httpx.Response(422, json={}))
    with caplog.at_level(logging.WARNING, logger="trpg.llm"), pytest.raises(LLMBadResponse):
        client.complete(MSGS, json_schema=NESTED)
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1
    assert client.accepted_schema_mode is None


# ---- trpg llm ping ----


def _ping(handler: Any) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cmd_llm_ping(out, err, transport=httpx.MockTransport(handler))
    return code, out.getvalue(), err.getvalue()


def test_ping_probe_schema_has_oneof_and_reports_response_format() -> None:
    assert "oneOf" in PING_SCHEMA  # 頂層（LM Studio MLX 只拒絕頂層的 oneOf）
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=ok_body("好"))

    code, out, err = _ping(handler)
    assert code == 0 and err == ""
    assert "schema 寫法：response_format" in out
    assert len(bodies) == 2  # 一次純文字、一次帶 schema
    assert "response_format" not in bodies[0]
    sent = bodies[1]["response_format"]["json_schema"]["schema"]
    assert not _has_key(sent, "oneOf") and _has_key(sent, "anyOf")


def test_ping_reports_guided_json_when_response_format_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "response_format" in json.loads(request.content):
            return httpx.Response(400, json={"error": "unsupported"})
        return httpx.Response(200, json=ok_body("好"))

    code, out, _ = _ping(handler)
    assert code == 0
    assert "schema 寫法：guided_json" in out


def test_ping_reports_guided_json_even_if_reply_unparsable() -> None:
    """guided_json 被接受（200）但被忽略、模型回空內容：寫法仍是 guided_json，另註解析失敗。"""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "response_format" in body:
            return httpx.Response(400, json={"error": "unsupported"})
        if "guided_json" in body:
            return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
        return httpx.Response(200, json=ok_body("好"))

    code, out, _ = _ping(handler)
    assert code == 0
    assert "schema 寫法：guided_json（回覆解析失敗：" in out


def test_ping_reports_none_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "response_format" in body or "guided_json" in body:
            return httpx.Response(400, json={"error": "unsupported"})
        return httpx.Response(200, json=ok_body("好"))

    code, out, _ = _ping(handler)
    assert code == 0
    assert "schema 寫法：都不接受" in out
