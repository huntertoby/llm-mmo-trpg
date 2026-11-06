"""LLM 呼叫的例外分類（訊息為繁體中文，呼叫端可直接顯示）。"""

from __future__ import annotations

__all__ = ["LLM_START_HINT", "LLMBadResponse", "LLMError", "LLMTimeout", "LLMUnavailable"]

LLM_START_HINT = (
    "請確認本機模型服務（LM Studio 或其他 OpenAI 相容伺服器）已啟動，"
    "且連接埠與設定檔（config/llm.toml）一致。"
)


class LLMError(Exception):
    """所有 LLM 呼叫錯誤的基底類別。"""


class LLMUnavailable(LLMError):
    """連不上模型服務（拒絕連線、DNS、5xx 等）。"""


class LLMTimeout(LLMError):
    """模型服務在逾時內沒有回應。"""


class LLMBadResponse(LLMError):
    """回應不是預期的格式（非 JSON、缺少 choices、4xx 等）。"""
