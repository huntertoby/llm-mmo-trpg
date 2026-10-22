"""普攻流對照模擬（Phase 3-32a）：普攻流弓手 vs 技能流弓手 × 三種情境，輸出摘要表。

用法::

    uv run python scripts/sim_attack_flow.py [--seeds 20] [--jobs 4]

情境：長戰單體、範圍戰、Boss 戰。邏輯在 ``trpg.sim.attack_flow_report``；不改任何規則或數值。
"""

from __future__ import annotations

import argparse

from trpg.content.library import load_library
from trpg.sim.attack_flow_report import (
    SCENARIOS,
    format_attack_flow,
    run_attack_flow,
    summarize,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20, help="每格種子數（預設 20）")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1, help="平行行程數（預設 1）")
    args = parser.parse_args()
    library = load_library()
    samples = run_attack_flow(library, seeds=args.seeds, seed_start=args.seed_start, jobs=args.jobs)
    labels = {s.id: s.label_zh for s in SCENARIOS}
    builds = {b.id: b.name_zh for b in library.builds.builds}
    print(format_attack_flow(summarize(samples), labels, builds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
