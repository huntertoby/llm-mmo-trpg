"""效用評分 AI 與 4 種行為模式（6.1-13、6.2-6）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
    template,
)
from trpg.engine import Attack, BattleState, EndTurn, Move, Shove, state_to_json
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.rules.geometry import manhattan
from trpg.engine.runner import replay, run_battle
from trpg.shared.types import ObjectId, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))


def ai(profile: str | None = None) -> UtilityAI:
    return UtilityAI(library().ai_profiles, override=profile)


def _crossroads() -> BattleState:
    """同一場景：行動者（持弓）在 (2, 2)；盜賊 E1 在 (1, 2)，背後是深淵；遠處另一名盜賊；
    受傷的友方戰士在 (6, 4)；中央 (3..4, 1..2) 是高度 1 的高台。"""
    m = make_map(
        "0000000\n0001100\n0001100\n0000000\n0000000",
        "x......\nx......\nx......\nx......\nx......",
        ally=[(2, 2)],
        enemy=[(1, 2)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 2), "hero_archer"),
            spawn(Team.ALLY, (6, 4), template("hero_fighter")),
            spawn(Team.ENEMY, (1, 2), "bandit"),
            spawn(Team.ENEMY, (6, 0), "bandit"),
        ],
    )
    state = give_turn(state, "unit_0001")
    state.units[U2].hp = 10
    return state


def test_four_profiles_choose_differently_in_the_same_scene() -> None:
    state = _crossroads()
    choices = {p: ai(p)(state) for p in ("brute", "archer", "cunning", "guard")}
    # 莽夫：直接攻擊相鄰的敵人
    assert choices["brute"] == Attack(unit_id=U1, target_id=U3)
    # 狡猾：把敵人推進深淵（環境擊殺）
    assert choices["cunning"] == Shove(unit_id=U1, target_id=U3)
    # 弓手：拉開距離、站上高處
    archer = choices["archer"]
    assert isinstance(archer, Move)
    dest = (archer.dest.x, archer.dest.y)
    assert state.tile(*dest).height >= 1
    assert all(manhattan(dest, state.units[e].xy) > 2 for e in (U3, U4))
    # 守衛：靠近受傷的友方
    guard = choices["guard"]
    assert isinstance(guard, Move)
    before = manhattan(state.units[U1].xy, state.units[U2].xy)
    assert manhattan((guard.dest.x, guard.dest.y), state.units[U2].xy) < before
    assert len({type(c).__name__ + str(getattr(c, "dest", "")) for c in choices.values()}) == 4


def test_cunning_detonates_barrel_near_enemies() -> None:
    m = make_map(
        "0000000\n0000000\n0000000",
        objects=[(5, 1, "oil_barrel")],
        surfaces=[(5, 0, "oil"), (6, 1, "oil")],
        ally=[(0, 1)],
        enemy=[(5, 0)],
    )
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 1), "hero_mage"),
                spawn(Team.ENEMY, (5, 0), no_reactions()),
                spawn(Team.ENEMY, (6, 1), no_reactions()),
                spawn(Team.ENEMY, (4, 2), no_reactions()),
            ],
        ),
        U1,
    )
    assert ai("cunning")(state) == Attack(unit_id=U1, target_object_id=ObjectId("obj_0001"))
    # 狡猾對環境傷害的評分高於莽夫（同一動作）
    barrel = Attack(unit_id=U1, target_object_id=ObjectId("obj_0001"))
    scores = {
        p: next(s.score for s in ai(p).rank(state) if s.action == barrel)
        for p in ("cunning", "brute")
    }
    assert scores["cunning"] > scores["brute"]


def test_guard_holds_defend_point() -> None:
    m = make_map(
        "000000\n000000",
        objective={"kind": "defend", "rounds": 3, "tiles": [[4, 0]]},
        ally=[(0, 0)],
        enemy=[(5, 1)],
    )
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (5, 1), no_reactions())]
        ),
        U1,
    )
    action = ai("guard")(state)
    assert isinstance(action, Move)
    assert manhattan((action.dest.x, action.dest.y), (4, 0)) < manhattan((0, 0), (4, 0))


def test_archer_shoots_from_range_instead_of_closing_in() -> None:
    m = make_map("0" * 10, ally=[(0, 0)], enemy=[(7, 0)])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_archer"), spawn(Team.ENEMY, (7, 0))]), U1
    )
    assert ai("archer")(state) == Attack(unit_id=U1, target_id=U2)


def test_end_turn_when_nothing_is_worth_doing() -> None:
    m = make_map("000")
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (2, 0))]), U1
    )
    state.units[U1].ap = 0
    state.units[U1].move_points = 0
    assert ai()(state) == EndTurn(unit_id=U1)


def test_rank_follows_legal_action_order_and_is_deterministic() -> None:
    state = _crossroads()
    a = ai("brute")
    first = [(s.action, s.score) for s in a.rank(state)]
    second = [(s.action, s.score) for s in a.rank(state)]
    assert first == second
    before = state_to_json(state)
    a(state)
    assert state_to_json(state) == before


@pytest.mark.parametrize("map_id", ["test_heights_8x8", "test_flat_6x6"])
def test_utility_battle_finishes_and_replays(map_id: str) -> None:
    from trpg.engine import build_setup  # noqa: PLC0415

    setup = build_setup(
        library(),
        map_id,
        ["hero_fighter", "hero_archer", "hero_mage"],
        ["bandit", "bandit_archer", "bandit_boss"],
        max_rounds=30,
    )
    run = run_battle(setup, 3, ai())
    assert run.state.ended and run.state.winner is not None
    again = replay(setup, 3, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)


def test_profiles_default_by_weapon() -> None:
    m = make_map("00000")
    state = make_state(
        m, [spawn(Team.ALLY, (0, 0), "hero_archer"), spawn(Team.ENEMY, (4, 0), "bandit")]
    )
    assert state.units[U1].ai_profile == "archer" and state.units[U2].ai_profile == "brute"
    mage = make_state(
        make_map("000"), [spawn(Team.ALLY, (0, 0), "hero_mage"), spawn(Team.ENEMY, (2, 0))]
    )
    assert mage.units[U1].ai_profile == "cunning"
    _ = make_setup  # 保持匯入（其他測試共用）
