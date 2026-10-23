"""``trpg llm ping``：送一則最小請求，檢查本機模型是否可用。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TextIO

import httpx

from trpg.llm import (
    ChatMessage,
    LLMConfigError,
    LLMError,
    OpenAICompatClient,
    load_llm_config,
)
from trpg.llm.errors import LLM_START_HINT

__all__ = ["cmd_llm_ping"]


def cmd_llm_ping(
    out: TextIO,
    err: TextIO,
    *,
    config_path: Path | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    try:
        config = load_llm_config(config_path)
    except LLMConfigError as exc:
        print(f"錯誤：{exc}", file=err)
        return 1
    client = OpenAICompatClient(config, transport=transport)
    messages = [ChatMessage(role="user", content="請只回覆「好」。")]
    start = time.perf_counter()
    try:
        reply = client.complete(messages)
    except LLMError as exc:
        print(f"錯誤：{exc}", file=err)
        if LLM_START_HINT not in str(exc):
            print(LLM_START_HINT, file=err)
        return 1
    finally:
        client.close()
    elapsed = time.perf_counter() - start
    print(f"模型：{config.model}（{config.base_url}）", file=out)
    print(f"回應時間：{elapsed:.2f} 秒", file=out)
    print(f"回應：{reply.strip()[:80]}", file=out)
    return 0
