"""資源不足回合比例（Phase 3H-2）：技能流、普攻流、召喚流（另加近戰技能流）× 三種情境，輸出摘要表。

用法::

    uv run python scripts/sim_resources.py [--seeds 20] [--jobs 8]

情境：長戰單體、範圍戰、Boss 戰（同 ``scripts/sim_attack_flow.py``）。邏輯在
``trpg.sim.resource_report``；只量不調，不改任何規則或數值。
"""

from __future__ import annotations

import argparse

from trpg.content.library import load_library
from trpg.sim.attack_flow_report import SCENARIOS
from trpg.sim.resource_report import format_resources, run_resources, summarize_resources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20, help="每格種子數（預設 20）")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1, help="平行行程數（預設 1）")
    args = parser.parse_args()
    library = load_library()
    samples = run_resources(library, seeds=args.seeds, seed_start=args.seed_start, jobs=args.jobs)
    labels = {s.id: s.label_zh for s in SCENARIOS}
    builds = {b.id: b.name_zh for b in library.builds.builds}
    print(format_resources(summarize_resources(samples), labels, builds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
