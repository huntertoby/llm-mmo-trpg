"""看門狗的假卡住測試（QF-3a）：**預設不會被收集**。

檔名不符合 ``test_*.py``，pytest 平常不收集；另外沒設 ``TRPG_WATCHDOG_DEMO=1`` 時整個檔案跳過，
推送前檢查不會跑到。手動驗證看門狗::

    TRPG_WATCHDOG_DEMO=1 uv run python scripts/run_pytest.py --stall-minutes 0.5 \\
        tests/infra/stuck_suite/hang_case.py -n 2 -p no:cacheprovider

預期：卡住 → 只結束自己那棵程序樹 → 重跑 → 再卡住 → 結束碼 124，``stuck.txt`` 寫出
``test_hangs_forever``。
"""

from __future__ import annotations

import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRPG_WATCHDOG_DEMO") != "1",
    reason="看門狗示範用，只在 TRPG_WATCHDOG_DEMO=1 時跑",
)


def test_quick_one() -> None:
    assert True


def test_quick_two() -> None:
    assert True


@pytest.mark.timeout(0)  # 關掉 pytest-timeout，只靠看門狗
def test_hangs_forever() -> None:
    while True:
        time.sleep(1)
