"""4-L5：模型回應的清理（``<think>`` 與程式碼框）。"""

from __future__ import annotations

import pytest

from trpg.llm.response import clean_response

BODY = '{"a": 1}'


@pytest.mark.parametrize(
    "raw",
    [
        BODY,
        f"  {BODY}\n",
        f"```json\n{BODY}\n```",
        f"```\n{BODY}\n```",
        f"<think>先想想……\n{{不是 JSON}}</think>\n{BODY}",
        f"<think>想</think>```json\n{BODY}\n```",
        f"只剩結尾標籤的思考</think>\n\n{BODY}",
        f"<THINK>a</THINK>{BODY}",
    ],
)
def test_clean_response(raw: str) -> None:
    assert clean_response(raw) == BODY


def test_unfinished_think_is_empty() -> None:
    assert clean_response("<think>想到一半被截斷") == ""


def test_inner_backticks_untouched() -> None:
    text = '{"concept": "用 ``` 包住"}'
    assert clean_response(text) == text
