"""本機模型的健康檢查（Phase 5E-3，計畫 31.4；專案計畫 3.1「模型不可用時遊戲要能降級」）。

- 伺服器啟動時 ping 一次（:meth:`LlmProvider.probe`，有逾時、不丟例外），之後每 ``interval_s`` 秒在
  背景執行緒 ping。時鐘是伺服器的，不進引擎（守則 1）。
- 不可用時 :class:`~trpg.api.world_flow.WorldLlm` 的 ``client()`` 回 ``None``：大世界的說書人、
  情境、聊天全部走模板；``GET /api/world/llm`` 標示 ``model_available``。
- 狀態改變時寫 log（管理者看伺服器視窗就知道）。
- 只在 ``active()`` 為真（大世界的 LLM 開關開著）時 ping：開關關著本來就全部走模板，不必連模型
  （也讓測試與沒有模型的機器不去連本機埠；代決 5E3-8）。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Final

from trpg.api.llm_source import LlmProvider
from trpg.server.clock import unix_now

__all__ = ["DOWN_LOG", "UNAVAILABLE_NOTICE", "UP_LOG", "LlmHealth"]

LOGGER: Final = logging.getLogger("trpg.llm_health")
DOWN_LOG: Final = "本機模型不可用，大世界的說書人全部改用模板（%s）"
UP_LOG: Final = "本機模型恢復可用"
UNAVAILABLE_NOTICE: Final = "本機模型目前連不到，大世界的敘述暫時改用模板。"


class LlmHealth:
    """本機模型目前可不可用。``available`` 為 ``None``＝還沒檢查過。"""

    def __init__(
        self,
        provider: LlmProvider | None,
        *,
        interval_s: int,
        clock: Callable[[], int] = unix_now,
        active: Callable[[], bool] = lambda: True,
    ) -> None:
        self._provider = provider
        self.active = active
        """要不要 ping（大世界的 LLM 開關開著才 ping）。"""
        self.interval_s = interval_s
        self._clock = clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.available: bool | None = None
        self.checked_at: int | None = None
        self.detail: str | None = None

    def check(self) -> bool:
        """ping 一次並更新狀態；回傳現在是否可用。"""
        notice = self._provider.probe() if self._provider is not None else "沒有設定模型"
        ok = notice is None
        with self._lock:
            before = self.available
            self.available = ok
            self.checked_at = self._clock()
            self.detail = notice
        if before is not ok:
            if ok:
                LOGGER.info(UP_LOG)
            else:
                LOGGER.warning(DOWN_LOG, notice)
        return ok

    @property
    def usable(self) -> bool:
        """還沒檢查過時當作可用（照舊由開關決定；第一次 ping 在啟動時就做）。"""
        return self.available is not False

    def tick(self) -> None:
        """定期檢查的一次：``active()`` 為真才 ping。"""
        if self.active():
            self.check()

    def start(self) -> None:
        """啟動時 ping 一次（``active()`` 為真才 ping）；``interval_s`` > 0 時開背景執行緒定期
        ping。"""
        self.tick()
        if self.interval_s <= 0 or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="llm-health", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            self.tick()

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5)
