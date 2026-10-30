"""``trpg sim flash`` 的實作（Phase 3W-8）。

標準輸出只有 Markdown 報表（相同參數必得逐字相同的輸出，且與 ``--jobs`` 無關）；執行時間印在
標準錯誤。
"""

from __future__ import annotations

import time
from typing import TextIO

from trpg.content.library import ContentLibrary
from trpg.roguelite.auto import FLASH_POLICIES, FlashPolicy
from trpg.sim.flash_economy import format_economy_report, parse_economy, run_economy_sweep
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
    economy: str | None = None,
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
    if economy is not None:
        return _economy(
            library,
            economy,
            policies=chosen,
            sizes=(seeds, seed_start, jobs),
            out=out,
            err=err,
            started=started,
        )
    results = run_flash_sim(library, chosen, range(seed_start, seed_start + seeds), jobs=jobs)
    elapsed = time.perf_counter() - started
    print(format_flash_report(results), file=out, end="")
    print(f"執行時間 {elapsed:.1f} 秒（{len(results)} 輪，--jobs {jobs}）", file=err)
    return 0


def _economy(
    library: ContentLibrary,
    spec: str,
    *,
    policies: list[FlashPolicy],
    sizes: tuple[int, int, int],
    out: TextIO,
    err: TextIO,
    started: float,
) -> int:
    seeds, seed_start, jobs = sizes
    try:
        economies = parse_economy(library, spec)
    except ValueError as exc:
        print(f"錯誤：{exc}", file=err)
        return 2
    rows = run_economy_sweep(
        library, economies, policies, range(seed_start, seed_start + seeds), jobs=jobs
    )
    elapsed = time.perf_counter() - started
    print(format_economy_report(rows), file=out, end="")
    print(
        f"執行時間 {elapsed:.1f} 秒（{len(economies)} 組合 × {len(policies)} 策略 × {seeds} 種子，"
        f"--jobs {jobs}）",
        file=err,
    )
    return 0
