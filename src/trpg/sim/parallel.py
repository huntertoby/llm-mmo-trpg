"""模擬用的平行執行：``ProcessPoolExecutor`` ＋ spawn，批次模擬共用（Phase 3E-2c）。

舊做法是 ``multiprocessing.Pool``：工作行程在初始化或執行中異常結束時，``Pool`` 會無限重開
新的行程，``map`` 永不返回，pytest 因此卡在 97～99%。``ProcessPoolExecutor`` 遇到行程異常結束時
會讓所有等待中的工作丟出 ``BrokenProcessPool``，呼叫端立刻看到錯誤而不是卡住。
"""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from typing import Any

_FN: Callable[[Any, Any], Any] | None = None
_CONTEXT: Any = None


def _init(fn: Callable[[Any, Any], Any], context: Any) -> None:
    global _FN, _CONTEXT  # noqa: PLW0603 - 行程初始化：每個工作行程只收一次共用內容
    _FN = fn
    _CONTEXT = context


def _call(task: Any) -> Any:
    assert _FN is not None
    return _FN(_CONTEXT, task)


def run_tasks[C, T, R](
    fn: Callable[[C, T], R], context: C, tasks: Sequence[T], *, jobs: int
) -> list[R]:
    """對每個 task 執行 ``fn(context, task)``，回傳與 ``tasks`` 同順序的結果。

    ``jobs == 1`` 或工作不多於一件時在本行程執行；否則用 spawn 的行程池，``context`` 只送
    各工作行程一次。``fn`` 必須是模組頂層函式（可 pickle）。工作行程異常結束時丟出
    ``concurrent.futures.process.BrokenProcessPool``。
    """
    if jobs < 1:
        raise ValueError("jobs 必須 >= 1")
    if jobs == 1 or len(tasks) <= 1:
        return [fn(context, task) for task in tasks]
    with ProcessPoolExecutor(
        max_workers=min(jobs, len(tasks)),
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_init,
        initargs=(fn, context),
    ) as pool:
        return list(pool.map(_call, tasks, chunksize=1))
