"""逾時留證的示範（QF-3a）：**預設不會被收集**（檔名不符合 ``test_*.py``）。

``tests/infra/test_xdist_loadgroup.py`` 把這個檔案複製到暫存資料夾，用 ``-n 2`` 跑：
``test_sleeps_past_timeout`` 超過 4 秒逾時，pytest-timeout（thread 方式）結束 worker；
``tests/pytest_trace.py`` 要在逾時前把 stack 寫進 ``.stacks``。
"""

from __future__ import annotations

import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRPG_WATCHDOG_DEMO") != "1", reason="示範用，只在 TRPG_WATCHDOG_DEMO=1 時跑"
)


def _sleep_somewhere_recognizable() -> None:
    time.sleep(60)


@pytest.mark.timeout(4)
def test_sleeps_past_timeout() -> None:
    _sleep_somewhere_recognizable()


def test_other() -> None:
    assert True
