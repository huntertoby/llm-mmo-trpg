"""``trpg sim completion`` 的實作（Phase 2C-4 3.4）。

標準輸出只有報表（相同參數必得逐字相同的輸出，且與 ``--jobs`` 無關）；執行時間印在標準錯誤。
有任何異常時結束碼為 1。
"""

from __future__ import annotations

import time
from typing import TextIO

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary
from trpg.sim.completion import format_completion, run_completion

__all__ = ["cmd_sim_completion"]


def cmd_sim_completion(
    library: ContentLibrary,
    *,
    maps: list[str] | None,
    seeds: int,
    seed_start: int,
    jobs: int,
    out: TextIO,
    err: TextIO,
) -> int:
    map_ids = default_sim_maps(library) if maps is None else maps
    unknown = [m for m in map_ids if m not in library.maps]
    if unknown:
        print(f"錯誤：沒有這些地圖：{', '.join(unknown)}", file=err)
        return 2
    started = time.perf_counter()
    try:
        report = run_completion(library, map_ids, range(seed_start, seed_start + seeds), jobs=jobs)
    except ValueError as exc:
        print(f"錯誤：{exc}", file=err)
        return 2
    elapsed = time.perf_counter() - started
    print(format_completion(report), file=out)
    battles = len(report.configs) * len(report.maps) * seeds
    print(f"執行時間 {elapsed:.1f} 秒（{battles} 場，--jobs {jobs}）", file=err)
    return 0 if report.clean else 1
