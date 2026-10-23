"""模型回應的清理（Phase 4-L5）：去掉 ``<think>…</think>`` 與 Markdown 程式碼框，留下 JSON 本文。

開了思考的 Qwen3 會在內容前面放 ``<think>…</think>``；有些模型即使有 JSON schema 約束也會把輸出
包在 ```` ```json … ``` ```` 裡。清理只去掉這些外框，不修改 JSON 本身；解析與驗證仍由
:func:`trpg.skillgen.proposal.evaluate_proposal` 負責。
"""

from __future__ import annotations

import json
import re
from typing import Any

from trpg.content.skills import true_only_params

__all__ = ["clean_response", "drop_false_flags"]

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


def _drop(node: Any, flags: dict[str, frozenset[str]]) -> tuple[Any, bool]:
    """遞迴去掉「只能填 true」的開關裡值為 ``false`` 的鍵；回傳（新節點, 是否有改）。"""
    if isinstance(node, list):
        items = [_drop(v, flags) for v in node]
        return [v for v, _ in items], any(changed for _, changed in items)
    if not isinstance(node, dict):
        return node, False
    names = flags.get(str(node.get("type")), frozenset())
    out: dict[str, Any] = {}
    changed = False
    for key, value in node.items():
        if key in names and value is False:
            changed = True
            continue
        new, sub = _drop(value, flags)
        out[key] = new
        changed = changed or sub
    return out, changed


def drop_false_flags(text: str) -> str:
    """把「只能填 true」的開關（資料見 ``true_only_params``）中填 ``false`` 的鍵視為省略
    （4-L5c；schema 已限制為 ``true``，這是約束解碼之外的雙保險）。
    不是合法 JSON 時原樣回傳。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    new, changed = _drop(data, true_only_params())
    return json.dumps(new, ensure_ascii=False) if changed else text
