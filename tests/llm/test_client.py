"""4-L1：MockLLMClient、設定讀取、OpenAICompatClient（假 transport）、CLI ping。不需網路。"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from trpg.cli.llm import cmd_llm_ping
from trpg.cli.main import main
from trpg.llm import (
    ChatMessage,
    LLMBadResponse,
    LLMClient,
    LLMConfig,
    LLMConfigError,
    LLMTimeout,
    LLMUnavailable,
    MockLLMClient,
    OpenAICompatClient,
    load_llm_config,
)
from trpg.llm.config import DEFAULT_CONFIG_PATH

MSGS = [ChatMessage(role="user", content="哈囉")]
SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}}


def ok_body(text: str = "好") -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def client_with(handler: Any, **cfg: Any) -> OpenAICompatClient:
    return OpenAICompatClient(LLMConfig(**cfg), transport=httpx.MockTransport(handler))


# ---- Mock ----


def test_mock_returns_in_order_and_records() -> None:
    mock = MockLLMClient(["一", "二"])
    assert isinstance(mock, LLMClient)
    assert mock.complete(MSGS, json_schema=SCHEMA) == "一"
    assert mock.complete(MSGS) == "二"
    assert mock.calls == [MSGS, MSGS]
    assert mock.schemas == [SCHEMA, None]
    with pytest.raises(LLMUnavailable):
        mock.complete(MSGS)


def test_mock_can_raise_errors() -> None:
    mock = MockLLMClient([LLMTimeout("逾時"), "好"])
    with pytest.raises(LLMTimeout):
        mock.complete(MSGS)
    assert mock.complete(MSGS) == "好"


# ---- 設定 ----


def test_default_config_file_loads() -> None:
    cfg = load_llm_config(DEFAULT_CONFIG_PATH, env={})
    assert cfg.base_url == "http://localhost:8001/v1"
    assert cfg.model == "swift"
    assert cfg.api_key == "local"
    assert cfg.max_retries == 3
    assert cfg.fallback_alert_permille == 200


def test_config_env_override(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('base_url = "http://a/v1"\nmodel = "m1"\ntimeout_s = 5\n', encoding="utf-8")
    cfg = load_llm_config(path, env={})
    assert (cfg.base_url, cfg.model, cfg.timeout_s) == ("http://a/v1", "m1", 5.0)
    env = {
        "TRPG_LLM_BASE_URL": "http://b/v1",
        "TRPG_LLM_MODEL": "m2",
        "TRPG_LLM_TIMEOUT_S": "9.5",
        "TRPG_LLM_API_KEY": "k",
    }
    cfg = load_llm_config(path, env=env)
    assert (cfg.base_url, cfg.model, cfg.timeout_s, cfg.api_key) == ("http://b/v1", "m2", 9.5, "k")


def test_config_path_from_env_and_errors(tmp_path: Path) -> None:
    path = tmp_path / "x.toml"
    path.write_text('model = "z"\n', encoding="utf-8")
    assert load_llm_config(env={"TRPG_LLM_CONFIG": str(path)}).model == "z"
    with pytest.raises(LLMConfigError):
        load_llm_config(tmp_path / "missing.toml", env={})
    path.write_text("unknown_key = 1\n", encoding="utf-8")
    with pytest.raises(LLMConfigError):
        load_llm_config(path, env={})
    path.write_text("not toml [[[", encoding="utf-8")
    with pytest.raises(LLMConfigError):
        load_llm_config(path, env={})
    with pytest.raises(LLMConfigError):
        load_llm_config(DEFAULT_CONFIG_PATH, env={"TRPG_LLM_TIMEOUT_S": "abc"})


# ---- OpenAI 相容 client ----


def test_request_format() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ok_body("你好"))

    client = client_with(handler, base_url="http://h:1/v1/", temperature=0.2, max_tokens=77)
    assert client.complete(MSGS) == "你好"
    req = seen[0]
    assert str(req.url) == "http://h:1/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer local"
    body = json.loads(req.content)
    assert body == {
        "model": "swift",
        "messages": [{"role": "user", "content": "哈囉"}],
        "temperature": 0.2,
        "max_tokens": 77,
    }


def test_json_schema_uses_response_format() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=ok_body("{}"))

    client_with(handler).complete(MSGS, json_schema=SCHEMA)
    rf = bodies[0]["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"] == SCHEMA
    assert "guided_json" not in bodies[0]


def test_auto_falls_back_to_guided_json_and_remembers() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "response_format" in body:
            return httpx.Response(400, json={"error": "unsupported"})
        return httpx.Response(200, json=ok_body("{}"))

    client = client_with(handler)
    assert client.complete(MSGS, json_schema=SCHEMA) == "{}"
    assert bodies[1]["guided_json"] == SCHEMA
    client.complete(MSGS, json_schema=SCHEMA)
    assert len(bodies) == 3  # 第二次直接用 guided_json
    assert "guided_json" in bodies[2]


def test_schema_rejected_everywhere_is_bad_response() -> None:
    client = client_with(lambda r: httpx.Response(422, json={}))
    with pytest.raises(LLMBadResponse):
        client.complete(MSGS, json_schema=SCHEMA)


def test_schema_mode_none_and_forced() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=ok_body())

    client_with(handler, json_schema_mode="none").complete(MSGS, json_schema=SCHEMA)
    assert "response_format" not in bodies[0]
    assert "guided_json" not in bodies[0]
    client_with(handler, json_schema_mode="guided_json").complete(MSGS, json_schema=SCHEMA)
    assert bodies[1]["guided_json"] == SCHEMA


def test_error_classification() -> None:
    def raising(exc: Exception) -> Any:
        def handler(request: httpx.Request) -> httpx.Response:
            raise exc

        return handler

    with pytest.raises(LLMUnavailable, match=r"start.bat"):
        client_with(raising(httpx.ConnectError("refused"))).complete(MSGS)
    with pytest.raises(LLMTimeout, match=r"start.bat"):
        client_with(raising(httpx.ReadTimeout("slow"))).complete(MSGS)
    with pytest.raises(LLMUnavailable):
        client_with(lambda r: httpx.Response(503)).complete(MSGS)
    with pytest.raises(LLMBadResponse):
        client_with(lambda r: httpx.Response(404, text="nope")).complete(MSGS)
    with pytest.raises(LLMBadResponse, match="不是 JSON"):
        client_with(lambda r: httpx.Response(200, text="<html>")).complete(MSGS)
    with pytest.raises(LLMBadResponse, match="choices"):
        client_with(lambda r: httpx.Response(200, json={"choices": []})).complete(MSGS)
    with pytest.raises(LLMBadResponse):
        client_with(
            lambda r: httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
        ).complete(MSGS)


# ---- CLI ping ----


def test_ping_success() -> None:
    out, err = io.StringIO(), io.StringIO()
    code = cmd_llm_ping(
        out, err, transport=httpx.MockTransport(lambda r: httpx.Response(200, json=ok_body()))
    )
    assert code == 0
    assert "模型：swift" in out.getvalue()
    assert "回應時間" in out.getvalue()
    assert err.getvalue() == ""


def test_ping_failure_message_has_no_traceback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    out, err = io.StringIO(), io.StringIO()
    assert cmd_llm_ping(out, err, transport=httpx.MockTransport(handler)) == 1
    assert "start.bat" in err.getvalue()
    assert "Traceback" not in err.getvalue()


def test_ping_bad_config_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["llm", "ping", "--config", str(tmp_path / "none.toml")]) == 1
    assert "找不到 LLM 設定檔" in capsys.readouterr().err


# ---- 真模型（預設不跑）----


@pytest.mark.llm
def test_real_model_ping() -> None:
    """需先用 F:\\WSL\\start.bat 啟動本機模型，並把 PORT 設成與 config/llm.toml 一致。"""
    client = OpenAICompatClient(load_llm_config())
    try:
        assert client.complete(MSGS).strip() != ""
    finally:
        client.close()
