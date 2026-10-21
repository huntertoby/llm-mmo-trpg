"""勝利條件輪替的模擬摘要表（Phase 3-22，``docs/phases/Phase3計畫.md`` 24.1 第 5 項）。

對每張有 ``alt_objectives`` 資料的地圖 × 撤離／守點，用地圖的標準陣容（``encounter``）與效用 AI 各跑
N 場，輸出我方勝率與平均輪數（並附同一陣容的「全滅」基準勝率供對照）。勝率 0% 的組合會標出。

用法::

    uv run python scripts/sim_objectives.py [--seeds 20] [--jobs 4] [--maps swamp,open_plain]
"""

from __future__ import annotations

import argparse
import sys

from trpg.content.library import load_library
from trpg.engine.setup import build_setup
from trpg.sim.batch import BatchSpec, UtilityPolicyFactory, run_batches

KINDS = ("eliminate", "escape", "defend")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--maps", default=None, help="地圖 ID，以逗號分隔（預設：全部有資料的）")
    args = parser.parse_args(argv)
    library = load_library()
    wanted = args.maps.split(",") if args.maps else None
    maps = sorted(
        m.id
        for m in library.maps.values()
        if m.alt_objectives is not None and (wanted is None or m.id in wanted)
    )
    seeds = tuple(range(args.seed_start, args.seed_start + args.seeds))
    specs: list[BatchSpec] = []
    keys: list[tuple[str, str]] = []
    for map_id in maps:
        map_def = library.map(map_id)
        encounter = map_def.encounter
        assert encounter is not None, map_id
        for kind in KINDS:
            if not map_def.supports_objective(kind):
                continue
            setup = build_setup(
                library,
                map_id,
                encounter.allies,
                encounter.enemies,
                max_rounds=library.roguelite.max_rounds,
                objective=map_def.objective_for(kind),
            )
            specs.append(
                BatchSpec(
                    name=f"{map_id}/{kind}",
                    setup=setup,
                    seeds=seeds,
                    policy_factory=UtilityPolicyFactory(library.ai_profiles),
                )
            )
            keys.append((map_id, kind))
    reports = run_batches(specs, jobs=args.jobs)
    by_key = dict(zip(keys, reports, strict=True))
    print(f"勝利條件模擬：標準陣容（encounter）＋效用 AI，{len(seeds)} 場／組合")
    print("| 地圖 | 條件 | 輪數 | 格子 | 我方勝率 | 平均輪數 | 全滅基準勝率 | 備註 |")
    print("|---|---|---|---|---|---|---|---|")
    for map_id, kind in keys:
        if kind == "eliminate":
            continue
        report = by_key[(map_id, kind)]
        objective = library.map(map_id).objective_for(kind)
        base = by_key[(map_id, "eliminate")].ally_win_rate
        note = "勝率 0%" if report.ally_wins == 0 else ""
        tiles = " ".join(f"({x},{y})" for x, y in objective.tiles)
        print(
            f"| {map_id} | {kind} | {objective.rounds} | {tiles} | "
            f"{report.ally_win_rate:.0%} | {report.rounds_mean:.1f} | {base:.0%} | {note} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
