"""``trpg sim flash`` 的實作（Phase 3W-8）。

標準輸出只有 Markdown 報表（相同參數必得逐字相同的輸出，且與 ``--jobs`` 無關）；執行時間印在
標準錯誤。
"""

from __future__ import annotations

import time
from typing import TextIO

from trpg.content.library import ContentLibrary
from trpg.roguelite.auto import FLASH_POLICIES, FlashPolicy
from trpg.sim.flash_report import format_flash_report, run_flash_sim

__all__ = ["cmd_sim_flash"]


def cmd_sim_flash(
    library: ContentLibrary,
    *,
    policies: list[str] | None,
    seeds: int,
    seed_start: int,
    jobs: int,
    out: TextIO,
    err: TextIO,
) -> int:
    names = list(FLASH_POLICIES) if policies is None else policies
    unknown = [p for p in names if p not in FLASH_POLICIES]
    if unknown or not names:
        print(
            f"錯誤：--policies 只能是 {', '.join(FLASH_POLICIES)}（收到 {unknown or '空'}）",
            file=err,
        )
        return 2
    chosen: list[FlashPolicy] = [p for p in FLASH_POLICIES if p in names]
    started = time.perf_counter()
    results = run_flash_sim(library, chosen, range(seed_start, seed_start + seeds), jobs=jobs)
    elapsed = time.perf_counter() - started
    print(format_flash_report(results), file=out, end="")
    print(f"執行時間 {elapsed:.1f} 秒（{len(results)} 輪，--jobs {jobs}）", file=err)
    return 0
