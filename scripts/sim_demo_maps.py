"""示範地圖的批次模擬：效用 AI 對戰 N 個種子的我方勝率與輪數（Phase 1C 決定 #4）。

用法::

    uv run python scripts/sim_demo_maps.py [--seeds 20] [--maps bridge_chasm,oil_depot]

每張地圖使用地圖檔的預設陣容（``encounter``）、``max_rounds=30``、種子 ``0 … N−1``。
目標（docs/phases/Phase1C計畫.md 2.5 #4）：我方勝率 35%–65%、平均輪數 4–6。
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time

from trpg.content.library import load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import Team

DEMO_MAPS = ("bridge_chasm", "oil_depot", "swamp", "ruined_fort")
MAX_ROUNDS = 30


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="示範地圖的批次模擬")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--maps", default=",".join(DEMO_MAPS))
    args = parser.parse_args(argv)
    library = load_library()
    ai = UtilityAI(library.ai_profiles)
    print(f"效用 AI，種子 0–{args.seeds - 1}，max_rounds={MAX_ROUNDS}")
    print("| 地圖 | 我方勝 | 敵方勝 | 平手 | 我方勝率 | 平均輪數 | 輪數範圍 | 每場時間 |")
    print("|---|---|---|---|---|---|---|---|")
    for map_id in args.maps.split(","):
        encounter = library.map(map_id).encounter
        if encounter is None:
            raise SystemExit(f"{map_id} 沒有預設陣容（encounter）")
        setup = build_setup(
            library, map_id, encounter.allies, encounter.enemies, max_rounds=MAX_ROUNDS
        )
        wins = {Team.ALLY: 0, Team.ENEMY: 0, None: 0}
        rounds: list[int] = []
        start = time.perf_counter()
        for seed in range(args.seeds):
            state = run_battle(setup, seed, ai).state
            wins[state.winner] += 1
            rounds.append(state.round)
        elapsed = (time.perf_counter() - start) / args.seeds
        rate = wins[Team.ALLY] / args.seeds
        print(
            f"| {map_id} | {wins[Team.ALLY]} | {wins[Team.ENEMY]} | {wins[None]} | "
            f"{rate:.0%} | {statistics.mean(rounds):.2f} | {min(rounds)}–{max(rounds)} | "
            f"{elapsed * 1000:.0f} ms |",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
