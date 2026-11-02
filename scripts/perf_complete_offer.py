"""PERF-2：量完整技能三選一（``make_offer(..., "complete")``）的時間，並可用 cProfile 找熱點。

用法::

    uv run python scripts/perf_complete_offer.py               # 時間表 ＋ 結果摘要
    uv run python scripts/perf_complete_offer.py --cold        # 每組之前清空組合器快取（最壞情況）
    uv run python scripts/perf_complete_offer.py --rounds 2    # 第 2 輪換種子（快取已熱）
    uv run python scripts/perf_complete_offer.py --profile 25  # 另印 cProfile 前 25 名（累積時間）

每組（build、種子、等級）各跑一次（內容庫只載入一次）。第 ``r`` 輪的種子是 ``種子 ＋ 1000 × r``。
摘要是三張候選 ``model_dump_json`` 的 sha256 前 12 碼：改快取前後相同＝結果沒變。
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import pstats
import statistics
import sys
import time

from trpg.content.library import ContentLibrary, load_library
from trpg.roguelite.offers import make_offer
from trpg.roguelite.start import new_run
from trpg.roguelite.state import RunState
from trpg.skillgen import memo

CASES: tuple[tuple[str, int, int], ...] = (
    ("build_fire", 1, 1),
    ("build_storm", 7, 4),
    ("build_tank", 3, 7),
    ("build_assassin", 11, 4),
    ("build_healer", 5, 10),
    ("build_warlock", 2, 7),
)


def _run(library: ContentLibrary, build: str, seed: int, level: int) -> RunState:
    run = new_run(library, build, seed)
    return run.model_copy(update={"level": level, "offers_made": 2})


def _digest(library: ContentLibrary, run: RunState) -> str:
    offer = make_offer(library, run, "complete")
    text = "".join(s.model_dump_json() for s in offer.candidates)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=int, default=0, help="印 cProfile 前 N 名")
    parser.add_argument("--rounds", type=int, default=1, help="輪數（每輪換種子）")
    parser.add_argument("--cold", action="store_true", help="每組之前清空組合器快取")
    args = parser.parse_args()
    library = load_library()
    profiler = cProfile.Profile() if args.profile else None
    print(f"{'build':<16}{'seed':>6}{'lv':>4}  {'秒':>7}  digest")
    for round_index in range(args.rounds):
        spent_all: list[float] = []
        for build, seed, level in CASES:
            run = _run(library, build, seed + 1000 * round_index, level)
            if args.cold:
                memo.clear_memos()
            start = time.perf_counter()
            if profiler is not None:
                profiler.enable()
            digest = _digest(library, run)
            if profiler is not None:
                profiler.disable()
            spent = time.perf_counter() - start
            spent_all.append(spent)
            print(f"{build:<16}{run.seed:>6}{level:>4}  {spent:7.2f}  {digest}")
        print(
            f"第 {round_index + 1} 輪：平均 {statistics.mean(spent_all):.2f} 秒、"
            f"中位數 {statistics.median(spent_all):.2f} 秒、最長 {max(spent_all):.2f} 秒"
        )
    if profiler is not None:
        stats = pstats.Stats(profiler, stream=sys.stdout)
        stats.sort_stats("cumulative").print_stats(args.profile)
        stats.sort_stats("tottime").print_stats(args.profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
