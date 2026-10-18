"""戰鬥效能基準（Phase 1A 報告的「效能基準」一節，之後最佳化的比較基準）。

用法::

    uv run python scripts/bench_battle.py [--repeat 20]

量測情境（預設陣容、種子 42）：

1. **1A 示範戰鬥（簡易 AI）**：地圖 test_heights_8x8，與 Phase 1A 基準相同的設定，可直接比較。
2. **1A 10 輪戰鬥（簡易 AI）**：同一陣容但所有單位 HP ×5、``max_rounds=10``。
3. **效用 AI**：test_heights_8x8 與四張示範地圖（與 ``trpg battle --map <id> --seed 42`` 相同）。

每種情境回報：輪數、動作數、事件數、整場時間（含 AI 決策）、重播時間（只有
``begin_battle`` ＋ 逐一 ``resolve``）、每個 ``resolve`` 的平均時間，以及每個動作（含 AI 決策與
``resolve``）的平均與中位數。整場與重播取 ``--repeat`` 次中的中位數；每個動作的中位數取所有重複
的所有動作合併後的中位數（Phase 1C 決定 #1 的目標：效用 AI 在示範地圖上 ≤ 5 ms）。
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.actions import Action
from trpg.engine.ai import Policy
from trpg.engine.ai.orders import (
    FocusTarget,
    HoldPosition,
    Protect,
    RetreatTo,
    TacticalOrder,
    UseEnvironment,
)
from trpg.engine.ai.simple import choose_action
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import BattleRun, replay, run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup
from trpg.engine.state import BattleState
from trpg.shared.types import UnitId
from trpg.sim.commanders import build_commanded_ai

ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
ENEMIES = ("bandit", "bandit_archer", "bandit_boss")
MAP_ID = "test_heights_8x8"
SEED = 42
HP_SCALE = 5
DEMO_MAPS = ("bridge_chasm", "oil_depot", "swamp", "ruined_fort")


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


def _timed_run(
    setup: BattleSetup, policy: Policy | FreshPolicy, repeat: int
) -> tuple[BattleRun, float, float]:
    """跑 ``repeat`` 次：回傳（結果、整場時間中位數、每個動作時間的中位數）。

    ``policy`` 可以是 ``Policy``，或 :class:`FreshPolicy`（每次重複新建一個 policy；指揮官有
    跨決策的狀態）。"""
    totals: list[float] = []
    per_action: list[float] = []
    run: BattleRun | None = None
    for _ in range(repeat):
        last = [0.0]

        def on_step(step: object, result: object, last: list[float] = last) -> None:
            now = time.perf_counter()
            if step is not None:
                per_action.append(now - last[0])
            last[0] = now

        start = time.perf_counter()
        last[0] = start
        current = policy.fresh() if isinstance(policy, FreshPolicy) else policy
        run = run_battle(setup, SEED, current, on_step=on_step)
        totals.append(time.perf_counter() - start)
    assert run is not None
    return run, statistics.median(totals), statistics.median(per_action)


@dataclass(frozen=True)
class FreshPolicy:
    """每次重複新建 policy（Phase 2C-2：戰術指令的效能比較）。"""

    fresh: Callable[[], Policy]

    def __call__(self, state: BattleState) -> Action:  # 只為了符合 Policy 型別
        raise NotImplementedError


def _report(
    title: str, setup: BattleSetup, repeat: int, policy: Policy | FreshPolicy = choose_action
) -> None:
    run, full, median_action = _timed_run(setup, policy, repeat)
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
    print(f"  每個動作中位數（含 AI）：{median_action * 1e6:.0f} µs")


def _decision_bench(library: ContentLibrary, map_id: str, rounds: int) -> None:
    """同一批決策狀態，有無戰術指令的單次決策時間（交錯計時，取中位數）。

    狀態取自一場無指令的效用 AI 戰鬥；每種指令各測一次（集火＝最低 HP 的敵人，撤退＝(0, 0)），
    「四種合併」同時給集火、守位、保護、利用環境（最重的組合）。
    """
    setup = _demo(library, map_id)
    states: list[BattleState] = []
    base = UtilityAI(library.ai_profiles)

    def collect(state: BattleState) -> Action:
        states.append(state.clone())
        return base(state)

    run_battle(setup, SEED, collect)

    def focus(state: BattleState, uid: UnitId) -> tuple[TacticalOrder, ...]:
        me = state.units[uid]
        foes = [u for u in state.living_units() if u.team is not me.team]
        return (FocusTarget(target=min(foes, key=lambda u: (u.hp, u.id)).id),) if foes else ()

    def hold(state: BattleState, uid: UnitId) -> tuple[TacticalOrder, ...]:
        return (HoldPosition(at=state.units[uid].xy),)

    def retreat(state: BattleState, uid: UnitId) -> tuple[TacticalOrder, ...]:
        return (RetreatTo(at=(0, 0)),)

    def protect(state: BattleState, uid: UnitId) -> tuple[TacticalOrder, ...]:
        me = state.units[uid]
        allies = [u for u in state.living_units() if u.team is me.team and u.id != uid]
        return (Protect(ward=allies[0].id),) if allies else ()

    def environment(state: BattleState, uid: UnitId) -> tuple[TacticalOrder, ...]:
        return (UseEnvironment(),)

    def everything(state: BattleState, uid: UnitId) -> tuple[TacticalOrder, ...]:
        return (*focus(state, uid), *hold(state, uid), *protect(state, uid), UseEnvironment())

    plain = UtilityAI(library.ai_profiles)
    sources = {
        "集火": focus,
        "守位": hold,
        "撤退": retreat,
        "保護": protect,
        "利用環境": environment,
        "四種合併": everything,
    }
    variants = {
        name: UtilityAI(library.ai_profiles, orders=source) for name, source in sources.items()
    }
    samples: dict[str, list[float]] = {"無指令": [], **{name: [] for name in variants}}
    for _ in range(rounds):
        for state in states:
            for name, policy in (("無指令", plain), *variants.items()):
                start = time.perf_counter()
                policy(state)
                samples[name].append(time.perf_counter() - start)
    base_median = statistics.median(samples["無指令"])
    print(f"[決策時間：{map_id}（{len(states)} 個決策 × {rounds} 次）]")
    for name, values in samples.items():
        median = statistics.median(values)
        print(f"  {name}：中位數 {median * 1e6:.0f} µs（{median / base_median - 1:+.1%}）")


def _check_same(a: BattleRun, b: BattleRun) -> None:
    if a.state != b.state:
        raise SystemExit("重播結果不一致")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="戰鬥效能基準")
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--utility-repeat", type=int, default=3)
    parser.add_argument("--decision-repeat", type=int, default=3)
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
        if map_id not in library.maps:
            continue
        _report(f"效用 AI：{map_id}", _demo(library, map_id), args.utility_repeat, ai)
    for map_id in DEMO_MAPS:
        if map_id in library.maps:
            _decision_bench(library, map_id, args.decision_repeat)
    commanded = FreshPolicy(
        lambda: build_commanded_ai(
            library.ai_profiles, ally="focus_lowest_hp", enemy="focus_lowest_hp"
        )
    )
    for map_id in DEMO_MAPS:
        if map_id not in library.maps:
            continue
        title = f"效用 AI＋指揮官（雙方 focus_lowest_hp）：{map_id}"
        _report(title, _demo(library, map_id), args.utility_repeat, commanded)
    return 0


def _demo(library: ContentLibrary, map_id: str) -> BattleSetup:
    encounter = library.map(map_id).encounter
    assert encounter is not None
    return build_setup(library, map_id, encounter.allies, encounter.enemies, max_rounds=30)


if __name__ == "__main__":
    sys.exit(main())
