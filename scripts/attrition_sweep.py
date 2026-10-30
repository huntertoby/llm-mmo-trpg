"""一輪消耗量測（BAL-6）：守點戰輪數／格子、第 3 場人數的模擬覆寫（不改 content）。

用法::

    uv run python scripts/attrition_sweep.py --configs "0,current,0;-1,current,0;0,current,3" \\
        --runs 60 --jobs 8 --out docs/phases/BAL-6/attrition_a.md

每組設定寫成 ``守點輪數差,格子模式,第3場人數``（格子模式見 ``trpg.sim.attrition.TILE_MODES``；
第 3 場人數 0 ＝ 不改）。邏輯在 ``trpg.sim.attrition``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trpg.content.library import load_library
from trpg.sim.attrition import TILE_MODES, AttritionConfig, format_rows, run_config


def parse_configs(spec: str) -> list[AttritionConfig]:
    configs = []
    for part in (p.strip() for p in spec.split(";")):
        if not part:
            continue
        delta, mode, third = (x.strip() for x in part.split(","))
        if mode not in TILE_MODES:
            raise ValueError(f"格子模式只能是 {', '.join(TILE_MODES)}（收到 {mode!r}）")
        configs.append(AttritionConfig(int(delta), mode, int(third)))
    return configs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", required=True)
    parser.add_argument("--runs", type=int, default=60)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    library = load_library()
    seeds = list(range(args.seed_start, args.seed_start + args.runs))
    results = []
    for config in parse_configs(args.configs):
        print(config.label, file=sys.stderr, flush=True)
        results.append(run_config(library, config, seeds, jobs=args.jobs))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(format_rows(results), encoding="utf-8")
    print(format_rows(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
