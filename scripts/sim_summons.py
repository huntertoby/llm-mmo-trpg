"""召喚物現況模擬（Phase 3-33a）：開發者起始包 × 地圖 × 種子，輸出召喚物統計摘要表。

用法::

    uv run python scripts/sim_summons.py [--packs a,b] [--maps a,b] [--seeds 4] [--jobs 4]

預設：喚靈（dev_spirit）與 3 個對照包，5 張正式地圖，每格 4 個種子。邏輯在
``trpg.sim.summon_report``；不改任何規則或數值。
"""

from __future__ import annotations

import argparse

from trpg.content.library import load_library
from trpg.sim.summon_report import (
    DEFAULT_PACKS,
    SUMMON_MAPS,
    format_summons,
    run_summon_sim,
    summarize,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packs", default=",".join(DEFAULT_PACKS), help="起始包 ID，逗號分隔")
    parser.add_argument("--maps", default=",".join(SUMMON_MAPS), help="地圖 ID，逗號分隔")
    parser.add_argument("--seeds", type=int, default=4, help="每格種子數（預設 4）")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1, help="平行行程數（預設 1）")
    args = parser.parse_args()
    library = load_library()
    samples = run_summon_sim(
        library,
        packs=args.packs.split(","),
        maps=args.maps.split(","),
        seeds=args.seeds,
        seed_start=args.seed_start,
        jobs=args.jobs,
    )
    labels = {p.id: p.label_zh for p in library.dev_starters.packs}
    print(format_summons(summarize(samples), labels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
