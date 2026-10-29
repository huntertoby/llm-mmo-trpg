"""LLM 提議器的掛接點（Phase 4-L6）。

``trpg.roguelite`` 不得匯入 ``trpg.llm``（import-linter 契約），所以真正呼叫模型的 **提議器**
（:data:`~trpg.skillgen.proposal_topic.LlmProposer`）由外層（CLI、API）建立，用 :func:`use_proposer`
裝在目前的執行緒／協程情境（``ContextVar``）；``make_offer`` 讀 :func:`current_proposer`。

只有 ``RunState.llm`` 為真 **而且** 裝了提議器時才會用到 LLM；其他情況（包含讀檔重播）完全不呼叫，
行為與沒有這個功能時逐字相同。生成的技能存在 run 裡（候選節點與 ``generated_skills``），重播與讀檔
直接用，不再呼叫 LLM。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from trpg.skillgen.proposal_topic import LlmProposer

__all__ = ["current_proposer", "use_proposer"]

_PROPOSER: ContextVar[LlmProposer | None] = ContextVar("trpg_llm_proposer", default=None)


def current_proposer() -> LlmProposer | None:
    """目前裝上的提議器（沒有為 ``None``）。"""
    return _PROPOSER.get()


@contextmanager
def use_proposer(proposer: LlmProposer | None) -> Iterator[None]:
    """在 ``with`` 區塊內裝上提議器（離開時還原）。"""
    token = _PROPOSER.set(proposer)
    try:
        yield
    finally:
        _PROPOSER.reset(token)
