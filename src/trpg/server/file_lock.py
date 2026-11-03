"""跨程序的檔案鎖（Phase 5D-R2）：遊戲伺服器與 Discord Bot 是兩個程序、共用帳號資料夾。

只用標準函式庫：Windows ``msvcrt.locking``、macOS／Linux ``fcntl.flock``。鎖檔本身不放資料，
鎖住它的第 1 個位元組。等待時會一直等到拿到為止（另一個程序持有的時間只有讀寫一個小 JSON）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import TracebackType
from typing import IO, Final

__all__ = ["FileLock"]

_RETRY_WAIT_S: Final = 0.01


class FileLock:
    """``with FileLock(path):`` 期間其他程序（與同程序另開的 :class:`FileLock`）拿不到同一把鎖。

    不可重入：同一個物件不要巢狀使用（呼叫者自己記深度）。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: IO[bytes] | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            _lock(handle)
        except BaseException:
            handle.close()
            raise
        self._handle = handle

    def release(self) -> None:
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            _unlock(handle)
        finally:
            handle.close()

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


if sys.platform == "win32":
    import msvcrt
    import threading

    def _lock(handle: IO[bytes]) -> None:
        wait = threading.Event()
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                wait.wait(_RETRY_WAIT_S)  # 另一個程序持有：稍等再試
                continue
            return

    def _unlock(handle: IO[bytes]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def _unlock(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
