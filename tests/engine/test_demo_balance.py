"""示範地圖的平衡（docs/phases/Phase1C計畫.md 2.5 #4）：效用 AI 跑 20 個種子，
我方勝率 35%–65%、平均輪數 4–6。與 ``scripts/sim_demo_maps.py`` 相同的設定。

Phase 2A 決定 #2：勝率檢查標記為 ``slow``，預設不跑（``pytest -m slow`` 才會執行）；
技能加入後平衡由 2C 統一調整，勝率改由 ``scripts/sim_demo_maps.py`` 的報表檢查。
重播測試很快，仍然預設執行。
"""

from __future__ import annotations

import statistics
from concurrent.futures import ProcessPoolExecutor

import pytest

from tests.engine.helpers import library
from trpg.engine import build_setup, state_to_json
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import replay, run_battle
from trpg.shared.types import Team

DEMO_MAPS = ("bridge_chasm", "oil_depot", "swamp", "ruined_fort")
SEEDS = 20
MAX_ROUNDS = 30


def _simulate(map_id: str) -> tuple[str, int, list[int]]:
    lib = library()
    encounter = lib.map(map_id).encounter
    assert encounter is not None
    setup = build_setup(lib, map_id, encounter.allies, encounter.enemies, max_rounds=MAX_ROUNDS)
    ai = UtilityAI(lib.ai_profiles)
    wins = 0
    rounds: list[int] = []
    for seed in range(SEEDS):
        state = run_battle(setup, seed, ai).state
        wins += state.winner is Team.ALLY
        rounds.append(state.round)
    return map_id, wins, rounds


@pytest.fixture(scope="module")
def results() -> dict[str, tuple[int, list[int]]]:
    with ProcessPoolExecutor(max_workers=2) as pool:
        return {m: (w, r) for m, w, r in pool.map(_simulate, DEMO_MAPS)}


@pytest.mark.slow
@pytest.mark.parametrize("map_id", DEMO_MAPS)
def test_demo_map_win_rate_and_length(
    map_id: str, results: dict[str, tuple[int, list[int]]]
) -> None:
    wins, rounds = results[map_id]
    assert 0.35 <= wins / SEEDS <= 0.65, f"{map_id} 我方勝率 {wins}/{SEEDS}"
    assert 4 <= statistics.mean(rounds) <= 6, f"{map_id} 平均輪數 {statistics.mean(rounds)}"


@pytest.mark.parametrize("map_id", DEMO_MAPS)
def test_utility_demo_battle_replays(map_id: str) -> None:
    lib = library()
    encounter = lib.map(map_id).encounter
    assert encounter is not None
    setup = build_setup(lib, map_id, encounter.allies, encounter.enemies, max_rounds=MAX_ROUNDS)
    run = run_battle(setup, 42, UtilityAI(lib.ai_profiles))
    assert run.state.ended and run.state.winner is not None
    again = replay(setup, 42, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
