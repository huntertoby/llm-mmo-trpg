"""登入嘗試次數限制（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.7）。

- 只算 **失敗**（帳號或密碼錯）；同一帳號名稱（不分大小寫，帳號不存在也算，不透露存在）或
  同一 IP 在視窗內失敗達上限 → :class:`LoginRateLimitError`（429），連密碼都不比對。
- 成功登入清掉該帳號名稱的紀錄（IP 的不清）。
- 記憶體計數（伺服器重啟歸零）；時鐘可注入。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

from trpg.shared.errors import TrpgError

__all__ = ["LoginLimiter", "LoginRateLimitError"]


class LoginRateLimitError(TrpgError):
    """登入失敗次數過多（429）。"""


def _now() -> float:
    return time.monotonic()


class LoginLimiter:
    """依帳號名稱與 IP 各自計算視窗內的登入失敗次數。執行緒安全。"""

    def __init__(
        self,
        *,
        max_failures: int = 5,
        ip_max_failures: int = 5,
        window_s: int = 900,
        clock: Callable[[], float] = _now,
    ) -> None:
        self.max_failures = max_failures
        self.ip_max_failures = ip_max_failures
        self.window_s = window_s
        self.clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        times = self._failures.get(key)
        if times is None:
            return deque()
        while times and times[0] <= now - self.window_s:
            times.popleft()
        if not times:
            del self._failures[key]
        return times

    def check(self, username: str, ip: str | None) -> None:
        """失敗達上限就拋 :class:`LoginRateLimitError`。"""
        now = self.clock()
        with self._lock:
            if len(self._recent(_user_key(username), now)) >= self.max_failures:
                raise LoginRateLimitError("登入嘗試次數過多，請稍後再試")
            if ip is not None and len(self._recent(_ip_key(ip), now)) >= self.ip_max_failures:
                raise LoginRateLimitError("登入嘗試次數過多，請稍後再試")

    def failed(self, username: str, ip: str | None) -> None:
        now = self.clock()
        with self._lock:
            keys = [_user_key(username)] + ([_ip_key(ip)] if ip is not None else [])
            for key in keys:
                self._recent(key, now)
                self._failures.setdefault(key, deque()).append(now)

    def succeeded(self, username: str) -> None:
        with self._lock:
            self._failures.pop(_user_key(username), None)


def _user_key(username: str) -> str:
    return "u:" + username.strip().lower()


def _ip_key(ip: str) -> str:
    return "ip:" + ip
