"""修正 pytest-xdist 3.8 ``--dist loadgroup`` 在 worker 掛掉後卡死的問題（QF-3a）。

``tests/conftest.py`` 匯入本模組的 :func:`pytest_xdist_make_scheduler`，``--dist loadgroup`` 時
改用 :class:`SafeLoadGroupScheduling`。

xdist 原本的 ``LoadScopeScheduling``（``loadgroup`` 的父類別）有兩個問題，在 Windows 實測重現：

1. **補上的新 worker 永遠不開始跑**：worker 掛掉後，xdist 把它沒跑完的工作放回佇列，再補一個
   新 worker。新 worker 收集完時，``schedule()`` 只對每個 worker 呼叫一次 ``_reschedule``，新
   worker 只拿到一個工作單位。``loadgroup`` 下沒標 ``xdist_group`` 的測試，一個測試就是一個
   單位，所以新 worker 手上只有 1 個測試。xdist 的 worker 要知道「下一個測試」（或收到
   shutdown）才會開始跑手上的測試（為了 teardown 的 nextitem），於是新 worker 一直等，
   master 也一直等它回報，整組不再前進。
2. **掛掉時正在跑的測試會被重跑**：``remove_node`` 把整個工作單位（包含掛掉時那一個測試）
   放回佇列。逾時（pytest-timeout 的 thread 方式會 ``os._exit``）造成的掛掉，重跑時通常又卡滿
   逾時秒數；``--dist load`` 不會重跑，這裡改成一致。

修法：掛掉的那個測試照樣回報失敗，但標成已完成、不再排；``schedule()`` 補排時每個 worker 呼叫
兩次 ``_reschedule``（和 xdist 第一次分配時一樣，#277），佇列空了就送 shutdown，讓 worker
開始跑最後一個測試。
"""

from __future__ import annotations

from typing import Any

import pytest
from xdist.scheduler import LoadGroupScheduling  # type: ignore[import-untyped]


class SafeLoadGroupScheduling(LoadGroupScheduling):  # type: ignore[misc]
    """``LoadGroupScheduling``，修正 worker 掛掉後的補排（見模組說明）。"""

    def remove_node(self, node: Any) -> str | None:
        workload: dict[str, dict[str, bool]] = self.assigned_work.pop(node)
        crashitem = next(
            (nodeid for unit in workload.values() for nodeid, done in unit.items() if not done),
            None,
        )
        if crashitem is None:
            return None
        # 掛掉時正在跑的測試：由 xdist 回報為失敗，不再重跑。
        workload[self._split_scope(crashitem)][crashitem] = True
        self.workqueue.update(
            {scope: unit for scope, unit in workload.items() if not all(unit.values())}
        )
        for other in self.assigned_work:
            self._reschedule(other)
        return crashitem

    def schedule(self) -> None:
        if self.collection is None:
            super().schedule()
            return
        # 補上新 worker 之後：每個 worker 排兩次，確保手上至少 2 個測試或已收到 shutdown。
        for node in self.nodes:
            self._reschedule(node)
            self._reschedule(node)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(config: pytest.Config, log: Any) -> Any:
    """``--dist loadgroup`` 時改用 :class:`SafeLoadGroupScheduling`；其他分配方式照 xdist 預設。"""
    if config.getvalue("dist") == "loadgroup":
        return SafeLoadGroupScheduling(config, log)
    return None
