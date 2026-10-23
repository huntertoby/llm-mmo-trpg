"""模型回應的清理（Phase 4-L5）：去掉 ``<think>…</think>`` 與 Markdown 程式碼框，留下 JSON 本文。

開了思考的 Qwen3 會在內容前面放 ``<think>…</think>``；有些模型即使有 JSON schema 約束也會把輸出
包在 ```` ```json … ``` ```` 裡。清理只去掉這些外框，不修改 JSON 本身；解析與驗證仍由
:func:`trpg.skillgen.proposal.evaluate_proposal` 負責。
"""

from __future__ import annotations

import re

__all__ = ["clean_response"]

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK = re.compile(r"^\s*<think>.*", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"^```[A-Za-z0-9_-]*[ \t]*\r?\n(.*?)\r?\n?```$", re.DOTALL)


def clean_response(text: str) -> str:
    """去掉 ``<think>…</think>``（含只有結尾標籤的情況）與包住整段的 ```` ``` ```` 程式碼框。"""
    out = _THINK.sub("", text)
    if "</think>" in out.lower():  # 聊天範本有時把開頭的 <think> 放在 prompt 裡，只剩結尾標籤
        out = out[out.lower().rindex("</think>") + len("</think>") :]
    out = _UNCLOSED_THINK.sub("", out)  # 思考沒寫完就被截斷：沒有任何內容
    out = out.strip()
    match = _FENCE.match(out)
    if match is not None:
        out = match.group(1).strip()
    return out
