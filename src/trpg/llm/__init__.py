"""LLM 整合：``LLMClient`` 介面、``MockLLMClient``、本機 OpenAI 相容 client、設定、版本化 prompt。

- 守則：LLM 只能提議，不能裁決；輸出先經 pydantic 驗證，再由引擎檢查合法性。
  模型 ID 寫在設定檔（``config/llm.toml``）；所有測試不需網路與 API 金鑰。
"""

from trpg.llm.client import ChatMessage, LLMClient, MockLLMClient, OpenAICompatClient
from trpg.llm.config import LLMConfig, LLMConfigError, load_llm_config
from trpg.llm.errors import LLMBadResponse, LLMError, LLMTimeout, LLMUnavailable

__all__ = [
    "ChatMessage",
    "LLMBadResponse",
    "LLMClient",
    "LLMConfig",
    "LLMConfigError",
    "LLMError",
    "LLMTimeout",
    "LLMUnavailable",
    "MockLLMClient",
    "OpenAICompatClient",
    "load_llm_config",
]
