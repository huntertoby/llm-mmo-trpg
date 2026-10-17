"""簡易 AI 與自動對戰。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    DEMO_ALLIES,
    DEMO_ENEMIES,
    give_turn,
    library,
    make_map,
    make_state,
    spawn,
)
from trpg.engine import Attack, Defend, EndTurn, Move, build_setup, resolve
from trpg.engine.ai.simple import choose_action
from trpg.engine.runner import run_battle
from trpg.shared.errors import TrpgError
from trpg.shared.types import Pos, Team, UnitId

U1 = UnitId("unit_0001")


@pytest.mark.parametrize("map_id", ["test_heights_8x8", "test_flat_6x6"])
@pytest.mark.parametrize("seed", [0, 1, 42])
def test_demo_battles_finish_with_a_winner(map_id: str, seed: int) -> None:
    setup = build_setup(library(), map_id, DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    run = run_battle(setup, seed)
    assert run.state.ended
    assert run.state.end_reason == "eliminate" and run.state.winner is not None


def test_ai_attacks_adjacent_enemy_with_lowest_distance_then_hp() -> None:
    m = make_map("0000\n0000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 0), "hero_fighter"),
            spawn(Team.ENEMY, (2, 0), "bandit"),
            spawn(Team.ENEMY, (0, 0), "bandit"),
        ],
    )
    state = give_turn(state, "unit_0001")
    state.units[UnitId("unit_0003")].hp = 5
    action = choose_action(state)
    assert action == Attack(unit_id=U1, target_id=UnitId("unit_0003"))


def test_ai_moves_toward_enemy_then_defends() -> None:
    m = make_map("0" * 12)
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (11, 0), "bandit")]
        ),
        "unit_0001",
    )
    action = choose_action(state)
    assert isinstance(action, Move)
    assert action.dest == Pos(x=5, y=0)  # 速度 5，沿直線走到底
    s = resolve(state, action).state
    assert choose_action(s) == Defend(unit_id=U1)
    s = resolve(s, Defend(unit_id=U1)).state
    assert choose_action(s) == EndTurn(unit_id=U1)


def test_ranged_ai_stops_at_range() -> None:
    m = make_map("0" * 12)
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_mage"), spawn(Team.ENEMY, (9, 0), "bandit")]),
        "unit_0001",
    )
    action = choose_action(state)
    assert isinstance(action, Move) and action.dest == Pos(x=4, y=0)  # 火焰法杖射程 5


def test_max_actions_guard() -> None:
    setup = build_setup(library(), "test_flat_6x6", DEMO_ALLIES, DEMO_ENEMIES)
    with pytest.raises(TrpgError, match="仍未結束"):
        run_battle(setup, 0, max_actions=3)


def test_on_step_callback_sees_every_action() -> None:
    setup = build_setup(library(), "test_flat_6x6", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    seen: list[object] = []
    run = run_battle(setup, 5, on_step=lambda action, result: seen.append(action))
    assert seen[0] is None and seen[1:] == run.actions
