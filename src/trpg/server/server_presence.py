"""遊戲伺服器的心跳檔（Phase 5F-R1）：讓命令列的季末重置知道伺服器開著。

遊戲伺服器（:class:`~trpg.api.world.WorldStore`）把世界、角色、日誌放在記憶體快取裡；伺服器開著時
從命令列重置，伺服器的下一個寫入會用舊快取把新一季蓋掉。所以：

- 伺服器啟動時在世界資料夾寫 ``server.lock``（:data:`~trpg.world.layout.SERVER_LOCK_FILE`，JSON：
  PID、啟動時間、最後心跳時間），之後每 :data:`HEARTBEAT_INTERVAL_S` 秒更新一次心跳；
  正常關閉時移除。
- :func:`running_server` 讀這個檔：心跳在 :data:`STALE_AFTER_S` 秒內＝伺服器在跑。伺服器當掉、檔案
  留著也沒關係，心跳過期就視為不在。
- 只看心跳時間，不查 PID 是否存活：標準函式庫在 Windows 沒有安全的查法（``os.kill(pid, 0)`` 在
  Windows 是送 CTRL_C_EVENT），而且 PID 會被重用。

為什麼不是「WorldStore 的寫入與重置拿同一把檔案鎖」：鎖只能讓兩邊不同時寫，擋不住伺服器在重置
**之後**用記憶體裡的舊快取寫回去；要安全，伺服器開著時根本就不該從外面重置。

檔名結尾是 ``.lock``，季末重置的備份照樣略過它（``*.lock``）。只用標準函式庫，
Windows 與 macOS 相同。
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from trpg.world.layout import SERVER_LOCK_FILE
from trpg.world.save import write_atomic

__all__ = [
    "HEARTBEAT_INTERVAL_S",
    "PRESENCE_FORMAT",
    "STALE_AFTER_S",
    "ServerPresence",
    "ServerPresenceInfo",
    "running_server",
]

PRESENCE_FORMAT: Final = "trpg-server-presence/1"
HEARTBEAT_INTERVAL_S: Final = 30.0
STALE_AFTER_S: Final = 120
"""心跳超過這麼多秒沒更新＝伺服器不在（4 次心跳的時間，容得下一時卡住）。"""


@dataclass(frozen=True)
class ServerPresenceInfo:
    pid: int
    started_at: int
    heartbeat_at: int


def _read(path: Path) -> ServerPresenceInfo | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != PRESENCE_FORMAT:
            return None
        return ServerPresenceInfo(
            pid=int(data["pid"]),
            started_at=int(data["started_at"]),
            heartbeat_at=int(data["heartbeat_at"]),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def running_server(
    world_dir: Path, now: int, *, stale_after_s: int = STALE_AFTER_S
) -> ServerPresenceInfo | None:
    """世界資料夾有沒有開著的遊戲伺服器（心跳在 ``stale_after_s`` 秒內）；沒有＝``None``。

    心跳時間比 ``now`` 晚（時鐘調過）也算在跑（保守）。讀不了或格式不對＝不在。"""
    info = _read(world_dir / SERVER_LOCK_FILE)
    if info is None or now - info.heartbeat_at > stale_after_s:
        return None
    return info


class ServerPresence:
    """伺服器持有的心跳檔。``start`` 寫檔並開背景執行緒更新心跳，``stop`` 停掉並移除檔案。"""

    def __init__(
        self,
        world_dir: Path,
        *,
        interval_s: float = HEARTBEAT_INTERVAL_S,
        clock: Callable[[], int] = lambda: int(time.time()),
    ) -> None:
        self.path = world_dir / SERVER_LOCK_FILE
        self.interval_s = interval_s
        self.clock = clock
        self.pid = os.getpid()
        self._started_at: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def beat(self) -> None:
        """寫一次心跳。"""
        if self._started_at is None:
            return
        data = {
            "format": PRESENCE_FORMAT,
            "pid": self.pid,
            "started_at": self._started_at,
            "heartbeat_at": self.clock(),
        }
        with contextlib.suppress(OSError):  # 心跳寫不了不影響遊戲；過期後命令列視為伺服器不在
            write_atomic(self.path, json.dumps(data) + "\n")

    def start(self) -> None:
        if self._started_at is not None:
            return
        self._started_at = self.clock()
        self._stop.clear()
        self.beat()
        if self.interval_s > 0:
            self._thread = threading.Thread(
                target=self._loop, name="trpg-server-presence", daemon=True
            )
            self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            self.beat()

    def stop(self) -> None:
        if self._started_at is None:
            return
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5)
        self._started_at = None
        info = _read(self.path)
        if info is not None and info.pid == self.pid:  # 只移除自己寫的
            with contextlib.suppress(OSError):
                self.path.unlink()
