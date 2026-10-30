"""難度與法力旋鈕掃描（BAL-4）：只量不調。

用法::

    # 第一階段：單一旋鈕（每個旋鈕的值見 trpg.sim.difficulty_sweep.SINGLE_GRID）
    uv run python scripts/difficulty_sweep.py --stage singles --jobs 8 --out docs/phases/BAL-4
    # 第二階段：小組合（逗號分隔旋鈕、分號分隔組合）
    uv run python scripts/difficulty_sweep.py --stage combos --jobs 8 --out docs/phases/BAL-4 \\
        --combos "enemy_hp=1200,boss_hp=900;mana_cap=1200,mana_cost=900"
    # 彙整：把各階段 CSV 合併成 sweep.md
    uv run python scripts/difficulty_sweep.py --report --out docs/phases/BAL-4

每階段寫 ``stage_<名稱>.csv``。邏輯在 ``trpg.sim.difficulty_sweep``；不改任何規則或數值。
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from trpg.cli.sim import default_sim_maps
from trpg.content.library import load_library
from trpg.sim.difficulty import NEUTRAL, Difficulty
from trpg.sim.difficulty_sweep import (
    KNOB_NAMES,
    SINGLE_GRID,
    Measure,
    SweepSizes,
    format_sweep,
    parse_combo,
    run_sweep,
    sweep_csv,
)

NEUTRAL_PERMILLE = 1000
_INT_FIELDS = {"maps_ok", "maps_total", "run_n", "run_boss_n"}


def single_configs() -> list[Difficulty]:
    """baseline ＋ 每個旋鈕的非 1000 值（依旋鈕順序）。"""
    configs = [NEUTRAL]
    for knob, values in SINGLE_GRID.items():
        configs += [Difficulty(**{knob: v}) for v in values if v != NEUTRAL_PERMILLE]
    return configs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("singles", "combos"), default=None)
    parser.add_argument("--combos", default="")
    parser.add_argument("--name", default=None, help="階段檔名（預設同 --stage）")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--map-seeds", type=int, default=8)
    parser.add_argument("--boss-seeds", type=int, default=20)
    parser.add_argument("--resource-seeds", type=int, default=20)
    parser.add_argument("--run-seeds", type=int, default=16)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--maps", default="", help="逗號分隔；預設全部示範地圖")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.report:
        return report(args.out)
    if args.stage is None:
        parser.error("需要 --stage 或 --report")
    configs = (
        single_configs()
        if args.stage == "singles"
        else [parse_combo(c) for c in args.combos.split(";") if c.strip()]
    )
    sizes = SweepSizes(
        map_seeds=args.map_seeds,
        boss_seeds=args.boss_seeds,
        resource_seeds=args.resource_seeds,
        run_seeds=args.run_seeds,
        seed_start=args.seed_start,
        maps=tuple(m for m in args.maps.split(",") if m),
    )
    library = load_library()
    started = time.perf_counter()

    def progress(name: str) -> None:
        print(f"[{time.perf_counter() - started:7.1f}s] {name}", file=sys.stderr, flush=True)

    measures = run_sweep(
        library, configs, default_sim_maps(library), sizes, jobs=args.jobs, progress=progress
    )
    name = args.name or args.stage
    (args.out / f"stage_{name}.csv").write_text(sweep_csv(measures), encoding="utf-8")
    print(f"已寫入 stage_{name}.csv；{time.perf_counter() - started:.1f} 秒", file=sys.stderr)
    return 0


def report(out: Path) -> int:
    """合併 ``stage_*.csv`` 成 ``sweep.md``（依階段檔名排序）。"""
    sections: list[str] = [
        "# BAL-4 難度與法力旋鈕掃描",
        "",
        "旋鈕單位為千分比（1000 ＝ 現行）。地圖達標數 ＝ 勝率落在 35–65% 的示範地圖數；"
        "短缺 ＝ Boss 戰情境該 build 的法力不足回合比例；一輪／一輪 Boss 勝率括號為樣本數。",
        "",
    ]
    for path in sorted(out.glob("stage_*.csv"), key=lambda p: (p.stem != "stage_singles", p.name)):
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        measures = [
            Measure(
                difficulty=Difficulty(**{k: int(r[k]) for k in KNOB_NAMES}),
                **{  # type: ignore[arg-type]
                    k: (int(r[k]) if k in _INT_FIELDS else float(r[k]))
                    for k in r
                    if k not in KNOB_NAMES
                },
            )
            for r in rows
        ]
        sections.append(format_sweep(path.stem.removeprefix("stage_"), measures))
    (out / "sweep.md").write_text("\n".join(sections), encoding="utf-8")
    print(f"已寫入 {out / 'sweep.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
