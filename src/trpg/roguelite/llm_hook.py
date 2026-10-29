"""LLM 提議器的掛接點（Phase 4-L6；閃現來源 Phase 3W-5）。

``trpg.roguelite`` 不得匯入 ``trpg.llm``（import-linter 契約），所以真正呼叫模型的 **提議器**
（:data:`~trpg.skillgen.proposal_topic.LlmProposer`）由外層（CLI、API）建立，用 :func:`use_proposer`
裝在目前的執行緒／協程情境（``ContextVar``）；``make_offer`` 讀 :func:`current_proposer`。

閃現的變化提議（3W-7 ``trpg.llm.flash_propose``）同理：外層用 :func:`use_flash_source` 裝上
**來源工廠**（:data:`FlashSourceFactory`：給一個收紀錄的函式，回傳
:class:`~trpg.skillgen.flash_offer.FlashOptionSource`），一輪出閃現題目時讀
:func:`current_flash_source`。

只有 ``RunState.llm`` 為真 **而且** 裝了提議器時才會用到 LLM；其他情況（包含讀檔重播）完全不呼叫，
行為與沒有這個功能時逐字相同。生成的技能與閃現選項存在 run 裡（候選節點、``generated_skills``、
``pending_flash``），重播與讀檔直接用，不再呼叫 LLM。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import BaseModel

from trpg.skillgen.flash_offer import FlashOptionSource
from trpg.skillgen.proposal_topic import LlmProposer

__all__ = [
    "FlashSourceFactory",
    "current_flash_source",
    "current_proposer",
    "use_flash_source",
    "use_proposer",
]

type FlashSourceFactory = Callable[[Callable[[BaseModel], None]], FlashOptionSource]
"""閃現選項來源的工廠：參數是收提議紀錄（``FlashProposalRecord``）的函式。"""

_PROPOSER: ContextVar[LlmProposer | None] = ContextVar("trpg_llm_proposer", default=None)
_FLASH: ContextVar[FlashSourceFactory | None] = ContextVar("trpg_flash_source", default=None)


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


def current_flash_source() -> FlashSourceFactory | None:
    """目前裝上的閃現選項來源工廠（沒有為 ``None``）。"""
    return _FLASH.get()


@contextmanager
def use_flash_source(factory: FlashSourceFactory | None) -> Iterator[None]:
    """在 ``with`` 區塊內裝上閃現選項來源工廠（離開時還原）。"""
    token = _FLASH.set(factory)
    try:
        yield
    finally:
        _FLASH.reset(token)
