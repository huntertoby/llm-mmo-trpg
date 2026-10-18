"""``trpg sim matrix`` 與 ``trpg sim skills`` 的實作（Phase 2C-3 5.4、5.5）。

與 ``trpg sim maps`` 一樣：標準輸出只有報表（相同的參數必得逐字相同的輸出，且與 ``--jobs`` 無關），
執行時間與 ``--json`` 的寫入訊息印在標準錯誤。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TextIO

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary
from trpg.shared.errors import TrpgError
from trpg.sim.matrix import MATRIX_ADAPTER, format_matrix, run_matrix
from trpg.sim.skill_report import (
    SkillCase,
    SkillsReport,
    demo_cases,
    format_skill_report,
    random_cases,
    run_skill_report,
)

__all__ = ["cmd_sim_matrix", "cmd_sim_skills"]


def cmd_sim_matrix(
    library: ContentLibrary,
    *,
    builds: list[str] | None,
    maps: list[str] | None,
    seeds: int,
    seed_start: int,
    jobs: int,
    json_path: Path | None,
    out: TextIO,
    err: TextIO,
) -> int:
    build_ids = [b.id for b in library.builds.builds] if builds is None else builds
    map_ids = default_sim_maps(library) if maps is None else maps
    seed_list = tuple(range(seed_start, seed_start + seeds))
    started = time.perf_counter()
    try:
        report = run_matrix(library, build_ids, map_ids, seed_list, jobs=jobs)
    except (ValueError, KeyError) as exc:
        message = exc.args[0] if isinstance(exc, KeyError) else str(exc)
        print(f"錯誤：{message}", file=err)
        return 2
    elapsed = time.perf_counter() - started
    print(format_matrix(report), file=out)
    if json_path is not None:
        json_path.write_bytes(MATRIX_ADAPTER.dump_json(report, indent=2) + b"\n")
        print(f"已寫入 {json_path}", file=err)
    battles = len(build_ids) * len(map_ids) * len(seed_list)
    print(f"執行時間 {elapsed:.1f} 秒（{battles} 場，--jobs {jobs}）", file=err)
    return 0


def cmd_sim_skills(
    library: ContentLibrary,
    *,
    demo: bool,
    random_count: int,
    seeds: int,
    seed_start: int,
    jobs: int,
    json_path: Path | None,
    out: TextIO,
    err: TextIO,
) -> int:
    cases: list[SkillCase] = []
    if demo:
        cases += demo_cases(library)
    try:
        if random_count:
            cases += random_cases(library, random_count)
    except TrpgError as exc:
        print(f"錯誤：{exc}", file=err)
        return 2
    if not cases:
        print("錯誤：請指定 --demo 或 --random N", file=err)
        return 2
    seed_list = tuple(range(seed_start, seed_start + seeds))
    started = time.perf_counter()
    report: SkillsReport = run_skill_report(library, cases, seed_list, jobs=jobs)
    elapsed = time.perf_counter() - started
    print(format_skill_report(report), file=out)
    if json_path is not None:
        json_path.write_bytes(report.model_dump_json(indent=2).encode() + b"\n")
        print(f"已寫入 {json_path}", file=err)
    print(f"執行時間 {elapsed:.1f} 秒（{len(cases) * len(seed_list)} 場，--jobs {jobs}）", file=err)
    return 0
