"""``trpg sim maps`` 的實作（Phase 2C-1 3.5）。

標準輸出只有報表（相同的參數必得逐字相同的輸出，且與 ``--jobs`` 無關）；執行時間與
``--json`` 的寫入訊息印在標準錯誤。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TextIO

from trpg.content.library import ContentLibrary
from trpg.content.maps import TRAINING_ARCHETYPE
from trpg.sim.batch import (
    DEFAULT_MAX_ROUNDS,
    REPORT_LIST_ADAPTER,
    format_report,
    map_spec,
    run_batches,
)
from trpg.sim.commanders import describe_commander
from trpg.sim.lineup import build_allies

__all__ = ["cmd_sim_maps", "default_sim_maps"]

TEST_MAP_PREFIX = "test_"


def default_sim_maps(library: ContentLibrary) -> list[str]:
    """預設要模擬的地圖：有 ``encounter`` 的地圖，測試地圖（``test_*``）與技能工坊的靶場（地圖類型
    ``training``，Phase 3F-1）除外，依 ID 排序。"""
    return sorted(
        map_id
        for map_id, map_def in library.maps.items()
        if map_def.encounter is not None
        and not map_id.startswith(TEST_MAP_PREFIX)
        and map_def.archetype != TRAINING_ARCHETYPE
    )


def cmd_sim_maps(
    library: ContentLibrary,
    *,
    maps: list[str] | None,
    seeds: int,
    seed_start: int,
    jobs: int,
    json_path: Path | None,
    out: TextIO,
    err: TextIO,
    ally_commander: str | None = None,
    enemy_commander: str | None = None,
    ally_builds: list[str] | None = None,
) -> int:
    map_ids = default_sim_maps(library) if maps is None else maps
    seed_list = tuple(range(seed_start, seed_start + seeds))
    try:
        allies: list[str] | None = None
        if ally_builds:  # 我方改用 build 英雄（Phase 3C-5b；不足 3 人以標準隊友補齊）
            library, allies = build_allies(library, ally_builds)
        specs = [
            map_spec(
                library,
                map_id,
                seed_list,
                ally_commander=ally_commander,
                enemy_commander=enemy_commander,
                allies=allies,
            )
            for map_id in map_ids
        ]
    except ValueError as exc:
        print(f"錯誤：{exc}", file=err)
        return 2
    started = time.perf_counter()
    reports = run_batches(specs, jobs=jobs)
    elapsed = time.perf_counter() - started
    print(
        f"批次模擬：效用 AI，種子 {seed_list[0]}–{seed_list[-1]}（{len(seed_list)} 場／地圖），"
        f"max_rounds={DEFAULT_MAX_ROUNDS}",
        file=out,
    )
    if ally_builds:
        print(f"我方 build：{'、'.join(ally_builds)}（不足 3 人以標準隊友補齊）", file=out)
    for label, commander_id in (("我方", ally_commander), ("敵方", enemy_commander)):
        if commander_id is not None:
            print(f"{label}指揮官：{commander_id}（{describe_commander(commander_id)}）", file=out)
    for report in reports:
        print("", file=out)
        print(format_report(report), file=out)
    if json_path is not None:
        json_path.write_bytes(REPORT_LIST_ADAPTER.dump_json(reports, indent=2) + b"\n")
        print(f"已寫入 {json_path}", file=err)
    battles = len(specs) * len(seed_list)
    print(
        f"執行時間 {elapsed:.1f} 秒（{battles} 場，--jobs {jobs}）",
        file=err,
    )
    return 0
