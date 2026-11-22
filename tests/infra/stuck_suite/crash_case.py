"""worker 掛掉後補排的示範（QF-3a）：**預設不會被收集**（檔名不符合 ``test_*.py``）。

``tests/infra/test_xdist_loadgroup.py`` 把這個檔案複製到暫存資料夾，用 ``-n 2 --dist loadgroup``
跑：``test_crash_once`` 讓 worker 直接結束（模擬 pytest-timeout 的 ``os._exit``），其他測試要在
補上的新 worker 上跑完。修正前（xdist 3.8 原本的排程）會永遠卡住。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRPG_WATCHDOG_DEMO") != "1", reason="示範用，只在 TRPG_WATCHDOG_DEMO=1 時跑"
)


def _crash(name: str) -> None:
    # 每次執行各寫一個檔（兩個行程同時用附加模式寫同一檔，在 Windows 會互相蓋掉）。
    runs = Path("crash_runs")
    runs.mkdir(exist_ok=True)
    (runs / f"{name}.{os.getpid()}").write_text("run", encoding="utf-8")
    os._exit(1)


def test_crash_once() -> None:
    _crash("once")


def test_a() -> None:
    assert True


def test_b() -> None:
    assert True


def test_c() -> None:
    assert True
