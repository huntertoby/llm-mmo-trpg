"""全面基線報表（BAL-3）：重用既有模擬，一次輸出 Markdown 總表與 CSV（只量不調）。

用法::

    uv run python scripts/balance_baseline.py --jobs 8 --out docs/phases/BAL-3
    uv run python scripts/balance_baseline.py --preset tiny --jobs 1 --out <dir>

``--preset medium``（預設）是 BAL-3 的中等規模；``tiny`` 只為煙霧測試。個別場數可用
``--map-seeds`` 等覆寫。邏輯在 ``trpg.sim.baseline``；不改任何規則或數值。
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

from trpg.cli.sim import default_sim_maps
from trpg.content.library import load_library
from trpg.sim.baseline import SECTIONS, BaselineSizes, format_baseline, rows_csv, run_baseline

TINY = BaselineSizes(
    map_seeds=1,
    matrix_seeds=1,
    weapon_seeds=1,
    boss_seeds=1,
    summon_seeds=1,
    resource_seeds=1,
    run_seeds=1,
    maps=("open_plain",),
    builds=("build_push", "build_fire"),
    weapon_builds=("build_blank_warrior", "build_blank_fist"),
    packs=("dev_summoner", "dev_bulwark"),
    scenarios=("single",),
    resource_builds=("build_push",),
    summon_maps=("open_plain",),
)
FIELDS = ("map", "matrix", "weapon", "boss", "summon", "resource", "run")


def build_sizes(args: argparse.Namespace) -> BaselineSizes:
    sizes = TINY if args.preset == "tiny" else BaselineSizes()
    updates: dict[str, object] = {"seed_start": args.seed_start}
    for name in FIELDS:
        value = getattr(args, f"{name}_seeds")
        if value is not None:
            updates[f"{name}_seeds"] = value
    if args.sections:
        updates["sections"] = tuple(args.sections.split(","))
    return dataclasses.replace(sizes, **updates)  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=("medium", "tiny"), default="medium")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--sections", default="", help=f"逗號分隔，預設全部：{','.join(SECTIONS)}")
    for name in FIELDS:
        parser.add_argument(f"--{name}-seeds", type=int, default=None)
    parser.add_argument(
        "--out", type=Path, default=None, help="輸出資料夾（baseline.md／baseline.csv）"
    )
    args = parser.parse_args(argv)
    sizes = build_sizes(args)
    library = load_library()
    started = time.perf_counter()

    def progress(name: str) -> None:
        print(f"[{time.perf_counter() - started:7.1f}s] {name}", file=sys.stderr)

    result = run_baseline(
        library, default_sim_maps(library), sizes, jobs=args.jobs, progress=progress
    )
    text = format_baseline(result, sizes_text=f"規模：{sizes}")
    if args.out is None:
        print(text)
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "baseline.md").write_text(text, encoding="utf-8")
        (args.out / "baseline.csv").write_text(rows_csv(result), encoding="utf-8")
        print(f"已寫入 {args.out}", file=sys.stderr)
    print(f"執行時間 {time.perf_counter() - started:.1f} 秒", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
