"""Token 數的保守估算與提議 prompt 的上限（Phase 4-L4）。

放在 ``trpg.shared``：``trpg.skillgen`` 篩選 schema 子集時要用，但不得匯入 ``trpg.llm``；
``trpg.llm.prompts`` 重新匯出同一份，兩邊永遠一致。純函式、確定性。
"""

from __future__ import annotations

__all__ = ["PROMPT_TOKEN_BUDGET", "estimate_tokens"]

_ASCII_MAX = 127

PROMPT_TOKEN_BUDGET = 30_000
"""system ＋ user 訊息 ＋ JSON schema 的估算上限：32768 上下文扣掉 ``max_tokens`` 2048 與餘裕。"""


def estimate_tokens(text: str) -> int:
    """保守的 token 估算：ASCII 字元 ÷ 3 ＋ 非 ASCII 字元 × 1，向上取整。"""
    non_ascii = sum(1 for ch in text if ord(ch) > _ASCII_MAX)
    ascii_count = len(text) - non_ascii
    return -(-ascii_count // 3) + non_ascii
