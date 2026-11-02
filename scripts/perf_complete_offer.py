"""PERF-2：量完整技能三選一（``make_offer(..., "complete")``）的時間，並可用 cProfile 找熱點。

用法::

    uv run python scripts/perf_complete_offer.py              # 時間表 ＋ 結果摘要（sha256）
    uv run python scripts/perf_complete_offer.py --profile 25 # 另印 cProfile 前 25 名（累積時間）

每組（build、種子、等級）各跑一次（內容庫只載入一次；第一組含暖身成本，另列）。摘要是三張候選
``model_dump_json`` 的 sha256 前 12 碼：改快取前後相同＝結果沒變。
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import pstats
import sys
import time

from trpg.content.library import ContentLibrary, load_library
from trpg.roguelite.offers import make_offer
from trpg.roguelite.start import new_run
from trpg.roguelite.state import RunState

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
    parser.add_argument("--repeat", type=int, default=1, help="同一組重跑次數（看快取命中後）")
    args = parser.parse_args()
    library = load_library()
    profiler = cProfile.Profile() if args.profile else None
    print(f"{'build':<16}{'seed':>5}{'lv':>4}  {'秒':>7}  digest")
    total = 0.0
    for build, seed, level in CASES:
        run = _run(library, build, seed, level)
        for _ in range(args.repeat):
            start = time.perf_counter()
            if profiler is not None:
                profiler.enable()
            digest = _digest(library, run)
            if profiler is not None:
                profiler.disable()
            spent = time.perf_counter() - start
            total += spent
            print(f"{build:<16}{seed:>5}{level:>4}  {spent:7.2f}  {digest}")
    print(f"合計 {total:.2f} 秒；平均 {total / (len(CASES) * args.repeat):.2f} 秒")
    if profiler is not None:
        stats = pstats.Stats(profiler, stream=sys.stdout)
        stats.sort_stats("cumulative").print_stats(args.profile)
        stats.sort_stats("tottime").print_stats(args.profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
