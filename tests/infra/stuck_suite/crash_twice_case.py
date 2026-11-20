"""兩個 worker 接連掛掉的示範（QF-3a）：**預設不會被收集**（檔名不符合 ``test_*.py``）。

``tests/infra/test_xdist_loadgroup.py`` 把這個檔案複製到暫存資料夾，用 ``-n 2 --dist loadgroup``
跑：兩個 worker 幾乎同時結束，xdist 補上兩個新 worker；一個先收集完時，xdist 3.8 原本的排程會對
另一個還沒收集完的 worker 排工作而 ``KeyError``（INTERNALERROR）。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRPG_WATCHDOG_DEMO") != "1", reason="示範用，只在 TRPG_WATCHDOG_DEMO=1 時跑"
)


def _crash(name: str) -> None:
    with Path("crash_runs.txt").open("a", encoding="utf-8") as file:
        file.write(f"{name}\n")
    os._exit(1)


def test_crash_first() -> None:
    _crash("first")


def test_crash_second() -> None:
    _crash("second")


def test_a() -> None:
    assert True


def test_b() -> None:
    assert True


def test_c() -> None:
    assert True
