"""測試留證（QF-3a）：記下每個行程正在跑哪個測試，快逾時時把所有執行緒的 stack 寫進檔案。

只在設了環境變數 ``TRPG_PYTEST_TRACE_DIR`` 時啟用（``scripts/run_pytest.py`` 會設）；沒設時什麼都
不做。``tests/conftest.py`` 匯入這裡的 hook。

每個跑測試的行程（xdist worker 或不平行時的主行程）在該資料夾寫兩個檔：

- ``<worker>-<pid>.trace``：每個測試開始寫一行 ``START\\t<epoch 秒>\\t<逾時秒>\\t<nodeid>``，結束寫
  ``END\\t<epoch 秒>\\t<nodeid>``。worker 被結束（逾時 ``os._exit``、被別的程序殺掉）時，最後一個
  只有 START 沒有 END 的就是當時在跑的測試。
- ``<worker>-<pid>.stacks``：``faulthandler`` 的輸出。行程致命錯誤（access violation 等）時的
  stack；另外每個測試在逾時前幾秒（見 :func:`dump_lead_seconds`）若還沒結束，先把所有執行緒的
  stack 寫進來（pytest-timeout 的 thread 方式逾時時只印到 worker 的 stderr，xdist 下會遺失）。

看門狗（``scripts/run_pytest.py``）用 START／END 判斷有沒有進展、卡在哪個測試。
"""

from __future__ import annotations

import faulthandler
import os
import time
from collections.abc import Generator
from typing import IO

import pytest

TRACE_DIR_ENV = "TRPG_PYTEST_TRACE_DIR"


class _Trace:
    def __init__(self, directory: str) -> None:
        worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
        stem = os.path.join(directory, f"{worker}-{os.getpid()}")
        os.makedirs(directory, exist_ok=True)
        # 行緩衝：每行立刻落地，行程被 os._exit 也不會掉。
        self.trace: IO[str] = open(f"{stem}.trace", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        self.stacks: IO[str] = open(f"{stem}.stacks", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        faulthandler.enable(file=self.stacks, all_threads=True)

    def start(self, nodeid: str, timeout: float) -> None:
        self.trace.write(f"START\t{time.time():.3f}\t{timeout:g}\t{nodeid}\n")  # noqa: TID251
        if timeout > 0:
            # 只有跑超過「逾時－提前秒數」的測試才會寫；stack 裡看得到測試函式名稱。
            faulthandler.dump_traceback_later(
                timeout - dump_lead_seconds(timeout), repeat=False, file=self.stacks
            )

    def end(self, nodeid: str) -> None:
        faulthandler.cancel_dump_traceback_later()
        self.trace.write(f"END\t{time.time():.3f}\t{nodeid}\n")  # noqa: TID251


_trace: _Trace | None = None


def dump_lead_seconds(timeout: float) -> float:
    """在逾時前幾秒寫 stack：5 秒，但逾時很短時取四分之一。"""
    return min(5.0, timeout / 4)


def item_timeout(item: pytest.Item) -> float:
    """這個測試的逾時秒數（``timeout`` marker → ``--timeout`` → ini ``timeout``；0 表示不限）。"""
    marker = item.get_closest_marker("timeout")
    if marker is not None:
        value = marker.args[0] if marker.args else marker.kwargs.get("timeout")
        if value is not None:
            return float(value)
    cli = item.config.getoption("timeout", None)
    if cli is not None:
        return float(cli)
    ini = item.config.getini("timeout")
    return float(ini) if ini not in (None, "") else 0.0


def _get_trace() -> _Trace | None:
    global _trace  # noqa: PLW0603
    if _trace is None and (directory := os.environ.get(TRACE_DIR_ENV)):
        _trace = _Trace(directory)
    return _trace


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Generator[None, object, object]:
    trace = _get_trace()
    if trace is None:
        return (yield)
    trace.start(item.nodeid, item_timeout(item))
    try:
        return (yield)
    finally:
        trace.end(item.nodeid)
