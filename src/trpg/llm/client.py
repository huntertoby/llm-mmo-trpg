"""``LLMClient`` 介面、``MockLLMClient`` 與本機 OpenAI 相容 client（vLLM）。

LLM 只能提議：``complete`` 回傳原始字串，解析與驗證由呼叫端負責。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypedDict, runtime_checkable

import httpx

from trpg.llm.config import LLMConfig
from trpg.llm.errors import (
    LLM_START_HINT,
    LLMBadResponse,
    LLMTimeout,
    LLMUnavailable,
)

__all__ = ["ChatMessage", "LLMClient", "MockLLMClient", "OpenAICompatClient"]

SCHEMA_REJECTED_STATUSES = (400, 422)
SERVER_ERROR_MIN = 500
CLIENT_ERROR_MIN = 400


class ChatMessage(TypedDict):
    role: str
    content: str


@runtime_checkable
class LLMClient(Protocol):
    def complete(
        self, messages: Sequence[ChatMessage], *, json_schema: Mapping[str, Any] | None = None
    ) -> str:
        """送出對話並回傳模型的原始文字。"""
        ...


class MockLLMClient:
    """依序回傳預設回應並記錄收到的 messages；回應若是例外實例則改為拋出。"""

    def __init__(self, responses: Sequence[str | Exception] = ()) -> None:
        self._responses = list(responses)
        self.calls: list[list[ChatMessage]] = []
        self.schemas: list[Mapping[str, Any] | None] = []

    def complete(
        self, messages: Sequence[ChatMessage], *, json_schema: Mapping[str, Any] | None = None
    ) -> str:
        self.calls.append([ChatMessage(role=m["role"], content=m["content"]) for m in messages])
        self.schemas.append(json_schema)
        index = len(self.calls) - 1
        if index >= len(self._responses):
            raise LLMUnavailable("MockLLMClient 的預設回應已用完。")
        response = self._responses[index]
        if isinstance(response, Exception):
            raise response
        return response


class _SchemaRejectedError(Exception):
    """伺服器不接受這種 JSON schema 寫法（HTTP 400／422）。"""


class OpenAICompatClient:
    """``POST {base_url}/chat/completions``（vLLM 的 OpenAI 相容 API）。"""

    def __init__(self, config: LLMConfig, *, transport: httpx.BaseTransport | None = None) -> None:
        self.config = config
        self._http = httpx.Client(transport=transport, timeout=config.timeout_s)
        # auto 模式下記住被伺服器接受的寫法，避免每次都先試被拒絕的那種。
        self._modes: tuple[str, ...] = {
            "auto": ("response_format", "guided_json"),
            "response_format": ("response_format",),
            "guided_json": ("guided_json",),
            "none": (),
        }[config.json_schema_mode]

    def close(self) -> None:
        self._http.close()

    def complete(
        self, messages: Sequence[ChatMessage], *, json_schema: Mapping[str, Any] | None = None
    ) -> str:
        if json_schema is None or not self._modes:
            return self._post(messages, None, None)
        for mode in self._modes:
            try:
                text = self._post(messages, mode, json_schema)
            except _SchemaRejectedError:
                continue
            self._modes = (mode,)
            return text
        raise LLMBadResponse("本機模型的伺服器拒絕了所有 JSON schema 約束寫法（HTTP 400／422）。")

    def _body(
        self, messages: Sequence[ChatMessage], mode: str | None, schema: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if mode == "response_format":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": dict(schema or {}), "strict": True},
            }
        elif mode == "guided_json":
            body["guided_json"] = dict(schema or {})
        return body

    def _post(
        self, messages: Sequence[ChatMessage], mode: str | None, schema: Mapping[str, Any] | None
    ) -> str:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        try:
            response = self._http.post(
                url,
                json=self._body(messages, mode, schema),
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeout(
                f"本機模型在 {self.config.timeout_s:g} 秒內沒有回應。{LLM_START_HINT}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"連不上本機模型（{url}）：{exc}。{LLM_START_HINT}") from exc
        status = response.status_code
        if mode is not None and status in SCHEMA_REJECTED_STATUSES:
            raise _SchemaRejectedError(f"HTTP {status}")
        if status >= SERVER_ERROR_MIN:
            raise LLMUnavailable(f"本機模型服務錯誤（HTTP {status}）。{LLM_START_HINT}")
        if status >= CLIENT_ERROR_MIN:
            raise LLMBadResponse(f"本機模型拒絕請求（HTTP {status}）：{response.text[:200]}")
        return _extract_content(response)


def _extract_content(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMBadResponse("本機模型的回應不是 JSON。") from exc
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMBadResponse("本機模型的回應缺少 choices[0].message.content。") from exc
    if not isinstance(content, str):
        raise LLMBadResponse("本機模型的回應內容不是文字（content 為空）。")
    return content
