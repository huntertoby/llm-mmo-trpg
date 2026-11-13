"""網頁版 LLM 開關的來源（Phase 4-L6b）：檢查本機模型連不連得到，並建立候選用的提議器。

- :class:`LlmProvider`：``POST /api/runs`` 的 ``llm: true`` 用它判斷「這一輪能不能開 LLM 生成」。
  :meth:`probe` 回傳 ``None`` ＝ 可用；否則回傳要顯示給玩家的提示（連不到模型**不報錯**，那一輪
  自動當作關閉）。:meth:`proposer` 建立候選產生器的提議器、:meth:`flash_source` 建立閃現變化提議
  的來源工廠（Phase 3W-5 接 3W-7；都經 ``trpg.roguelite.llm_hook`` 掛接）。6L-2：
  :meth:`story_proposer` 建立大世界劇情技能（換元素、名稱、描述）的提議器。WP-1：:meth:`wish_source`
  建立許願池的來源（對關鍵字＋把願望放進 ``<player_input>`` 的技能提議器）。
- :class:`LocalLlmProvider`：讀 ``config/llm.toml``，連線檢查有逾時（``probe_timeout_s``），
  不會卡住開局。
- :class:`MockLlmProvider`：測試與離線預覽用（``MockLLMClient``，不連任何位址）。
- 大世界（Phase 5B-5）：:meth:`LlmProvider.generate_default` 是伺服器設定（``generate``），大世界的
  LLM 開關預設跟著它；:meth:`LlmProvider.story_client` 是說書人與情境提議用的 client。

LLM 只提議；數值一律來自預算器（守則 3）。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import httpx

from trpg.content.library import ContentLibrary
from trpg.llm import LLMConfig, LLMConfigError, OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import make_proposer, mock_proposer
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_source
from trpg.llm.story_skill import StoryProposer, make_story_proposer, mock_story_proposer
from trpg.llm.wish import WishSource, mock_wish_client
from trpg.roguelite.llm_hook import FlashSourceFactory
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
LLM_OFF_NOTICE = "連不到本機模型，這一輪改用一般技能生成。"
"""連不到本機模型時顯示的提示（這一輪自動當作關閉，照常開局）。"""
_SERVER_ERROR_MIN = 500


class LlmProvider(Protocol):
    def probe(self) -> str | None:
        """可用回傳 ``None``，否則回傳提示文字；不得丟例外、不得卡住（要有逾時）。"""
        ...

    def proposer(self, library: ContentLibrary) -> LlmProposer | None:
        """建立候選用的提議器；設定壞掉等做不到時回傳 ``None``（該輪不使用 LLM）。"""
        ...

    def flash_source(self, library: ContentLibrary) -> FlashSourceFactory | None:
        """建立閃現變化提議的來源工廠（3W-5）；做不到時回傳 ``None``（閃現只用模板）。"""
        ...

    def story_proposer(self, library: ContentLibrary) -> StoryProposer | None:
        """大世界劇情技能換元素與文字的提議器（6L-2）；做不到時回傳 ``None``（用內容版）。"""
        ...

    def wish_source(self, library: ContentLibrary) -> WishSource | None:
        """許願池的來源（WP-1）；做不到時回傳 ``None``（文字許願被拒，請玩家改用選單）。"""
        ...

    def alert_permille(self) -> int:
        """退回率提醒線（千分比）。"""
        ...

    def generate_default(self) -> bool:
        """伺服器設定的 LLM 生成開關（``config/llm.toml`` 的 ``generate``；5B-5 大世界的預設）。"""
        ...

    def story_client(self) -> LLMClient | None:
        """大世界說書人與情境提議用的 client（5B-5）；設定壞掉時 ``None``（一律降級）。"""
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

    def flash_source(self, library: ContentLibrary) -> FlashSourceFactory | None:
        config = self._config()
        if config is None:
            return None
        client = OpenAICompatClient(config, transport=self._transport)
        # LF-1：同一個 client 也為大變化與轉型命名（名稱與描述進遊戲、記進日誌）
        return lambda sink: LlmFlashSource(
            client, max_attempts=config.max_retries, sink=sink, naming=client
        )

    def story_proposer(self, library: ContentLibrary) -> StoryProposer | None:
        config = self._config()
        if config is None:
            return None
        client = OpenAICompatClient(config, transport=self._transport)
        return make_story_proposer(client, library, max_attempts=config.max_retries)

    def wish_source(self, library: ContentLibrary) -> WishSource | None:
        config = self._config()
        if config is None:
            return None
        client = OpenAICompatClient(config, transport=self._transport)
        # WP-1：同一個 client 對關鍵字、提議技能（願望在 <player_input>）、命名
        return WishSource(
            client=client,
            proposer=lambda wish: make_proposer(
                client, library, max_attempts=config.max_retries, naming=client, player_text=wish
            ),
            max_attempts=config.max_retries,
        )

    def alert_permille(self) -> int:
        config = self._config()
        return DEFAULT_ALERT_PERMILLE if config is None else config.fallback_alert_permille

    def generate_default(self) -> bool:
        config = self._config()
        return config is not None and config.generate

    def story_client(self) -> LLMClient | None:
        config = self._config()
        return None if config is None else OpenAICompatClient(config, transport=self._transport)


class MockLlmProvider:
    """測試用：``reachable`` 為假時模擬「本機模型未啟動」；為真時用 Mock 提議器（不連網路）。"""

    def __init__(
        self,
        *,
        reachable: bool = True,
        alert_permille: int = DEFAULT_ALERT_PERMILLE,
        generate: bool = False,
        story_responses: Sequence[str | Exception] = (),
        flash_naming: bool = False,
    ) -> None:
        self.reachable = reachable
        self._alert = alert_permille
        self.probes = 0
        self.generate = generate
        self.flash_naming = flash_naming
        """LF-1：閃現的大變化與轉型用 Mock 命名（預設關，不動既有測試）。"""
        self.story = MockLLMClient(story_responses)
        """大世界說書人與情境提議共用的 Mock（依序回應；用完拋 ``LLMUnavailable`` → 降級）。"""

    def probe(self) -> str | None:
        self.probes += 1
        return None if self.reachable else LLM_OFF_NOTICE

    def proposer(self, library: ContentLibrary) -> LlmProposer | None:
        return mock_proposer(library, naming=True)

    def flash_source(self, library: ContentLibrary) -> FlashSourceFactory | None:
        naming = self.flash_naming
        return lambda sink: mock_flash_source(library, sink=sink, naming=naming)

    def story_proposer(self, library: ContentLibrary) -> StoryProposer | None:
        return mock_story_proposer(library)

    def wish_source(self, library: ContentLibrary) -> WishSource | None:
        return WishSource(
            client=lambda wish, menu: mock_wish_client(library, wish, menu),
            proposer=lambda _wish: mock_proposer(library, naming=True),
        )

    def alert_permille(self) -> int:
        return self._alert

    def generate_default(self) -> bool:
        return self.generate

    def story_client(self) -> LLMClient | None:
        return self.story
