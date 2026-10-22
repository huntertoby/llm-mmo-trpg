"""``trpg.sim.parallel``（Phase 3E-2c）：結果順序、jobs 檢查，工作行程異常結束時不卡住。"""

from __future__ import annotations

import os
from concurrent.futures.process import BrokenProcessPool

import pytest

from trpg.sim.parallel import run_tasks


def _double(context: int, task: int) -> int:
    return context * task


def _die(_context: int, _task: int) -> int:
    os._exit(1)


def test_in_process_and_pool_give_same_ordered_results() -> None:
    tasks = list(range(6))
    assert run_tasks(_double, 3, tasks, jobs=1) == [0, 3, 6, 9, 12, 15]
    assert run_tasks(_double, 3, tasks, jobs=2) == [0, 3, 6, 9, 12, 15]


def test_jobs_must_be_positive() -> None:
    with pytest.raises(ValueError, match="jobs"):
        run_tasks(_double, 1, [1], jobs=0)


@pytest.mark.timeout(60)
def test_a_crashing_worker_raises_instead_of_hanging() -> None:
    with pytest.raises(BrokenProcessPool):
        run_tasks(_die, 0, [1, 2, 3], jobs=2)
