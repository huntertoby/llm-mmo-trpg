"""AI 僵局的回歸測試（Phase 2C-4 3.1）：``lava_crossing`` 種子 19 曾打滿 30 輪平手。

根本原因：雙方弓手各躲在半掩護物件後，彼此距離 10、都在弓的射程（8）之外；位置價值把「有掩護」
算成 ``cover`` 權重 12，而離開掩護後 ``approach`` 每格只有 1，所以任何接近的移動分數都 ≤ 0。
修正：掩護只算射程內的敵人（對方打不到自己時，掩護沒有意義）。
"""

from __future__ import annotations

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn
from trpg.cli.battle import default_lineup
from trpg.engine import BattleState, Move, build_setup
from trpg.engine.ai.utility import UtilityAI, position_value
from trpg.engine.runner import run_battle
from trpg.shared.types import Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def test_lava_crossing_seed_19_finishes_with_a_winner() -> None:
    lib = library()
    allies, enemies = default_lineup(lib, "lava_crossing")
    setup = build_setup(lib, "lava_crossing", allies, enemies, max_rounds=30)
    run = run_battle(setup, 19, UtilityAI(lib.ai_profiles))
    assert run.state.winner is not None
    assert run.state.round < 30


def _standoff() -> BattleState:
    """兩名弓手各躲在矮牆後，距離 11（弓射程 8）：以前誰也不會接近。"""
    m = make_map(
        "\n".join(["0" * 14] * 3),
        ally=[(0, 1)],
        enemy=[(13, 1)],
        objects=[(1, 1, "low_wall"), (12, 1, "low_wall")],
    )
    state = make_state(
        m, [spawn(Team.ALLY, (0, 1), "hero_archer"), spawn(Team.ENEMY, (13, 1), "bandit_archer")]
    )
    return give_turn(state, U1)


def test_archers_out_of_range_of_each_other_still_approach() -> None:
    state = _standoff()
    action = UtilityAI(library().ai_profiles, override="archer")(state)
    assert isinstance(action, Move)
    assert action.dest.x > state.units[U1].pos.x


def test_cover_counts_only_enemies_that_can_reach_the_unit() -> None:
    state = _standoff()
    weights = library().ai_profiles.by_id()["archer"].weights
    far = position_value(state, U1, weights)
    no_cover = weights.model_copy(update={"cover": 0})
    assert far == position_value(state, U1, no_cover)
