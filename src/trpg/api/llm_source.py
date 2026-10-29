"""網頁版 LLM 開關的來源（Phase 4-L6b）：檢查本機模型連不連得到，並建立候選用的提議器。

- :class:`LlmProvider`：``POST /api/runs`` 的 ``llm: true`` 用它判斷「這一輪能不能開 LLM 生成」。
  :meth:`probe` 回傳 ``None`` ＝ 可用；否則回傳要顯示給玩家的提示（連不到模型**不報錯**，那一輪
  自動當作關閉）。:meth:`proposer` 建立候選產生器的提議器（經 ``trpg.roguelite.llm_hook`` 掛接）。
- :class:`LocalLlmProvider`：讀 ``config/llm.toml``，連線檢查有逾時（``probe_timeout_s``），
  不會卡住開局。
- :class:`MockLlmProvider`：測試與離線預覽用（``MockLLMClient``，不連任何位址）。

LLM 只提議；數值一律來自預算器（守則 3）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import httpx

from trpg.content.library import ContentLibrary
from trpg.llm import LLMConfig, LLMConfigError, OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import make_proposer, mock_proposer
from trpg.skillgen.proposal_topic import LlmProposer

__all__ = [
    "DEFAULT_ALERT_PERMILLE",
    "DEFAULT_PROBE_TIMEOUT_S",
    "LLM_OFF_NOTICE",
    "LlmProvider",
    "LocalLlmProvider",
    "MockLlmProvider",
]

DEFAULT_ALERT_PERMILLE = 200
DEFAULT_PROBE_TIMEOUT_S = 3.0
LLM_OFF_NOTICE = "本機模型未啟動，這一輪使用一般技能生成。"
"""連不到本機模型時顯示的提示（這一輪自動當作關閉，照常開局）。"""
_SERVER_ERROR_MIN = 500


class LlmProvider(Protocol):
    def probe(self) -> str | None:
        """可用回傳 ``None``，否則回傳提示文字；不得丟例外、不得卡住（要有逾時）。"""
        ...

    def proposer(self, library: ContentLibrary) -> LlmProposer | None:
        """建立候選用的提議器；設定壞掉等做不到時回傳 ``None``（該輪不使用 LLM）。"""
        ...

    def alert_permille(self) -> int:
        """退回率提醒線（千分比）。"""
        ...


class LocalLlmProvider:
    """本機模型（``config/llm.toml``）。連線檢查：``GET {base_url}/models``，逾時
    ``probe_timeout_s``。"""

    def __init__(
        self,
        *,
        config_path: Path | None = None,
        probe_timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config_path = config_path
        self._timeout = probe_timeout_s
        self._transport = transport

    def _config(self) -> LLMConfig | None:
        try:
            return load_llm_config(self._config_path)
        except LLMConfigError:
            return None

    def probe(self) -> str | None:
        config = self._config()
        if config is None:
            return LLM_OFF_NOTICE
        url = config.base_url.rstrip("/") + "/models"
        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout) as http:
                response = http.get(url, headers={"Authorization": f"Bearer {config.api_key}"})
        except httpx.HTTPError:  # 含逾時、拒絕連線、DNS
            return LLM_OFF_NOTICE
        return LLM_OFF_NOTICE if response.status_code >= _SERVER_ERROR_MIN else None

    def proposer(self, library: ContentLibrary) -> LlmProposer | None:
        config = self._config()
        if config is None:
            return None
        client = OpenAICompatClient(config, transport=self._transport)
        return make_proposer(client, library, max_attempts=config.max_retries, naming=client)

    def alert_permille(self) -> int:
        config = self._config()
        return DEFAULT_ALERT_PERMILLE if config is None else config.fallback_alert_permille


class MockLlmProvider:
    """測試用：``reachable`` 為假時模擬「本機模型未啟動」；為真時用 Mock 提議器（不連網路）。"""

    def __init__(
        self, *, reachable: bool = True, alert_permille: int = DEFAULT_ALERT_PERMILLE
    ) -> None:
        self.reachable = reachable
        self._alert = alert_permille
        self.probes = 0

    def probe(self) -> str | None:
        self.probes += 1
        return None if self.reachable else LLM_OFF_NOTICE

    def proposer(self, library: ContentLibrary) -> LlmProposer | None:
        return mock_proposer(library, naming=True)

    def alert_permille(self) -> int:
        return self._alert
