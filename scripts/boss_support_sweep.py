"""Boss 戰護衛與援軍量測（BAL-7）：只在模擬覆寫，不改 content。

用法::

    uv run python scripts/boss_support_sweep.py \
        --configs "0,0,0;-1,0,0;0,4,0;0,-1,0" --boss-seeds 30 --runs 60 --jobs 8 \
        --out docs/phases/BAL-7/boss_support.md

每組設定 ``護衛人數差,援軍輪數,援軍人數差``（護衛差 ≤ 0；援軍輪數 0 ＝ 現行、-1 ＝ 無援軍；
人數差 ≤ 0）。邏輯在 ``trpg.sim.attrition``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trpg.content.library import load_library
from trpg.sim.attrition import (
    AttritionConfig,
    format_boss_rows,
    run_boss_config,
    run_config,
)


def parse_configs(spec: str) -> list[AttritionConfig]:
    configs = []
    for part in (p.strip() for p in spec.split(";")):
        if part:
            guards, rnd, count = (int(x) for x in part.split(","))
            configs.append(
                AttritionConfig(
                    boss_guards_delta=guards, boss_reinforce_round=rnd, boss_reinforce_delta=count
                )
            )
    return configs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", required=True)
    parser.add_argument("--boss-seeds", type=int, default=30)
    parser.add_argument("--runs", type=int, default=60)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    library = load_library()
    boss_seeds = list(range(args.boss_seeds))
    run_seeds = list(range(args.runs))
    boss, runs = [], []
    for config in parse_configs(args.configs):
        print(config.label, file=sys.stderr, flush=True)
        boss.append(run_boss_config(library, config, boss_seeds, jobs=args.jobs))
        runs.append(run_config(library, config, run_seeds, jobs=args.jobs))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(format_boss_rows(boss, runs), encoding="utf-8")
    print(format_boss_rows(boss, runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
