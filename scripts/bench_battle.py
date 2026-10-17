"""戰鬥效能基準（Phase 1A 報告的「效能基準」一節，之後最佳化的比較基準）。

用法::

    uv run python scripts/bench_battle.py [--repeat 20]

量測情境（預設陣容、種子 42）：

1. **1A 示範戰鬥（簡易 AI）**：地圖 test_heights_8x8，與 Phase 1A 基準相同的設定，可直接比較。
2. **1A 10 輪戰鬥（簡易 AI）**：同一陣容但所有單位 HP ×5、``max_rounds=10``。
3. **效用 AI**：test_heights_8x8 與三張示範地圖（與 ``trpg battle --map <id> --seed 42`` 相同）。

每種情境回報：輪數、動作數、事件數、整場時間（含簡易 AI 決策）、重播時間（只有
``begin_battle`` ＋ 逐一 ``resolve``）與每個 ``resolve`` 的平均時間。取 ``--repeat`` 次中的中位數。
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections.abc import Callable

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ai import Policy
from trpg.engine.ai.simple import choose_action
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import BattleRun, replay, run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup

ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
ENEMIES = ("bandit", "bandit_archer", "bandit_boss")
MAP_ID = "test_heights_8x8"
SEED = 42
HP_SCALE = 5
DEMO_MAPS = ("bridge_chasm", "oil_depot", "swamp")


def _timed[T](fn: Callable[[], T], repeat: int) -> tuple[T, float]:
    samples = []
    result: T | None = None
    for _ in range(repeat):
        start = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - start)
    assert result is not None
    return result, statistics.median(samples)


def _scale_hp(setup: BattleSetup, factor: int) -> BattleSetup:
    units = tuple(
        UnitSpawn(
            template=u.template.model_copy(update={"max_hp": u.template.max_hp * factor}),
            weapon=u.weapon,
            team=u.team,
            position=u.position,
        )
        for u in setup.units
    )
    return setup.model_copy(update={"units": units, "max_rounds": 10})


def _report(title: str, setup: BattleSetup, repeat: int, policy: Policy = choose_action) -> None:
    run, full = _timed(lambda: run_battle(setup, SEED, policy), repeat)
    replayed, resolve_only = _timed(lambda: replay(setup, SEED, run.actions), repeat)
    _check_same(run, replayed)
    n = len(run.actions)
    print(f"[{title}]")
    print(
        f"  輪數 {run.state.round}，動作 {n}，事件 {len(run.events)}，結果 {run.state.end_reason}"
    )
    print(f"  整場（含 AI）：{full * 1000:.1f} ms")
    print(f"  重播（begin_battle ＋ {n} 次 resolve）：{resolve_only * 1000:.1f} ms")
    print(f"  每個 resolve 平均：{resolve_only / n * 1e6:.0f} µs")
    print(f"  每個動作平均（含 AI）：{full / n * 1e6:.0f} µs")


def _check_same(a: BattleRun, b: BattleRun) -> None:
    if a.state != b.state:
        raise SystemExit("重播結果不一致")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="戰鬥效能基準")
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--utility-repeat", type=int, default=3)
    args = parser.parse_args(argv)
    library = load_library()
    setup = build_setup(library, MAP_ID, ALLIES, ENEMIES, max_rounds=30)
    print(
        f"Python {sys.version.split()[0]}，重複 {args.repeat} 次取中位數"
        f"（效用 AI {args.utility_repeat} 次）"
    )
    _report("1A 示範戰鬥（簡易 AI）", setup, args.repeat)
    _report(f"1A 10 輪戰鬥（簡易 AI，HP ×{HP_SCALE}）", _scale_hp(setup, HP_SCALE), args.repeat)
    ai = UtilityAI(library.ai_profiles)
    _report(f"效用 AI：{MAP_ID}", setup, args.utility_repeat, ai)
    for map_id in DEMO_MAPS:
        _report(f"效用 AI：{map_id}", _demo(library, map_id), args.utility_repeat, ai)
    return 0


def _demo(library: ContentLibrary, map_id: str) -> BattleSetup:
    encounter = library.map(map_id).encounter
    assert encounter is not None
    return build_setup(library, map_id, encounter.allies, encounter.enemies, max_rounds=30)


if __name__ == "__main__":
    sys.exit(main())
