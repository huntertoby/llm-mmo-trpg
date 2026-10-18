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
from trpg.engine.rules.geometry import manhattan
from trpg.engine.runner import run_battle
from trpg.engine.state import StatusInstance
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


def _river(*, island: bool = False) -> BattleState:
    """深淵把戰場切成兩半（x = 3），只有最下面一列（y = 4）連通：莽夫與盜賊的曼哈頓距離只有 2，
    但走路要繞 8 步。``island`` 時連最下面一列也封住，兩邊完全不連通。"""
    rows = ["...x..."] * 4 + ["...x..." if island else "......."]
    m = make_map("\n".join(["0" * 7] * 5), "\n".join(rows), ally=[(2, 1)], enemy=[(4, 1)])
    state = make_state(
        m, [spawn(Team.ALLY, (2, 1), "hero_fighter"), spawn(Team.ENEMY, (4, 1), "bandit")]
    )
    return give_turn(state, U1)


def test_a_melee_unit_walks_around_a_chasm_even_though_it_first_gets_farther_away() -> None:
    """曼哈頓距離會讓每一步繞路都變成負分；走路步數讓繞路的第一步有正分。"""
    state = _river()
    action = UtilityAI(library().ai_profiles, override="brute")(state)
    assert isinstance(action, Move)
    assert action.dest.y > state.units[U1].pos.y  # 往連通的那一列走，而不是原地防禦


def test_walking_distance_falls_back_to_manhattan_when_the_enemy_is_unreachable() -> None:
    state = _river(island=True)
    ai = UtilityAI(library().ai_profiles, override="brute")
    ranked = ai.rank(state)  # 不會出錯
    moves = [s for s in ranked if isinstance(s.action, Move)]
    best = max(moves, key=lambda s: s.score)
    assert best.score <= 0  # 已經貼著深淵，曼哈頓距離也無法再接近


def _hidden_archers() -> BattleState:
    """兩名弓手相距 4，敵方隱蔽（只有 2 格內才能被選為目標）。"""
    m = make_map("\n".join(["0" * 8] * 3), ally=[(1, 1)], enemy=[(5, 1)])
    state = make_state(
        m, [spawn(Team.ALLY, (1, 1), "hero_archer"), spawn(Team.ENEMY, (5, 1), "bandit_archer")]
    )
    state.units[U2].statuses = [StatusInstance(status_id="concealed", remaining=9)]
    return give_turn(state, U1)


def test_an_archer_steps_within_two_tiles_to_attack_a_concealed_enemy() -> None:
    """隱蔽的敵人要走到 2 格內才打得到：keep_distance 不能因此把弓手擋在外面。"""
    state = _hidden_archers()
    action = UtilityAI(library().ai_profiles, override="archer")(state)
    assert isinstance(action, Move)
    assert manhattan((action.dest.x, action.dest.y), state.units[U2].xy) <= 2


def test_keep_distance_still_applies_to_visible_enemies() -> None:
    state = _hidden_archers()
    state.units[U2].statuses = []
    archer = library().ai_profiles.by_id()["archer"].weights
    near = state.clone()
    near.units[U1].pos = near.units[U1].pos.model_copy(update={"x": 4})  # 距離 1
    assert position_value(near, U1, archer) < position_value(state, U1, archer)
