"""敵人 AI 避開冰面（#123，Phase 6E-2）：移動評分扣「滑倒的期望代價」，確定性。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from trpg.engine import BattleState, Move
from trpg.engine.ai.utility import UtilityAI, ice_slip_cost
from trpg.engine.ice_slide import path_slide_risks, slide_fail_chance
from trpg.shared.types import Pos, Team, UnitId

E1 = UnitId("unit_0002")


def _scene(ice: list[tuple[int, int]]) -> BattleState:
    """敵方盜賊在 (0, 1)，英雄在 (6, 1)；``ice`` 為冰面格。"""
    m = make_map(
        "0000000\n0000000\n0000000",
        surfaces=[(x, y, "ice") for x, y in ice],
        ally=[(6, 1)],
        enemy=[(0, 1)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (6, 1), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (0, 1), no_reactions()),
        ],
    )
    return give_turn(state, E1)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles, override="brute")


def _move(path: list[tuple[int, int]]) -> Move:
    return Move(unit_id=E1, path=tuple(Pos(x=x, y=y) for x, y in path))


def test_cost_is_zero_without_ice_and_follows_the_fail_chance() -> None:
    plain = _scene([])
    weights = next(p for p in library().ai_profiles.profiles if p.id == "brute").weights
    move = _move([(0, 1), (1, 1), (2, 1), (3, 1)])
    assert ice_slip_cost(plain, plain.units[E1], move, weights, 8) == 0
    icy = _scene([(1, 1), (2, 1)])
    unit = icy.units[E1]
    (risk,) = path_slide_risks(icy, unit, ((0, 1), (1, 1), (2, 1), (3, 1)))
    assert risk.index == 1 and risk.stop == (3, 1)  # 滑到冰面外的第一格
    chance = slide_fail_chance(icy, unit, (1, 1))
    assert 0 < chance < 1
    cost = ice_slip_cost(icy, unit, move, weights, 8)
    assert cost == chance * 8  # 停點就是終點：位置價值沒有損失，只有倒地的代價
    longer = _move([(0, 1), (1, 1), (2, 1)])  # 想停在冰上：失敗會滑到 (3, 1)
    assert ice_slip_cost(icy, unit, longer, weights, 8) >= chance * 8
    assert ice_slip_cost(icy, unit, move, weights, 0) == Fraction(0)


def test_ai_scores_icy_moves_lower_and_is_deterministic() -> None:
    plain, icy = _scene([]), _scene([(1, 1), (2, 1), (3, 1)])
    a = _ai()
    dry = {s.action: s.score for s in a.rank(plain)}
    wet = {s.action: s.score for s in a.rank(icy)}
    crossing = [
        m
        for m in wet
        if isinstance(m, Move) and any(p.y == 1 and 1 <= p.x <= 3 for p in m.path[1:])
    ]
    assert crossing
    for m in crossing:
        if m in dry:
            assert wet[m] < dry[m]
    assert [(s.action, s.score) for s in a.rank(icy)] == [(s.action, s.score) for s in a.rank(icy)]


@pytest.mark.parametrize(
    ("ice_row", "expected"), [(0, (5, 1)), (1, (4, 0))], ids=["ice_on_top", "ice_in_middle"]
)
def test_ai_takes_the_dry_approach_when_both_are_equally_good(
    ice_row: int, expected: tuple[int, int]
) -> None:
    """英雄在 (5, 0)：(4, 0) 與 (5, 1) 都相鄰、都走 5 步；冰面擋在其中一條路上時走另一條。"""
    m = make_map(
        "0000000\n0000000\n0000000",
        surfaces=[(x, ice_row, "ice") for x in range(1, 5)],
        ally=[(5, 0)],
        enemy=[(0, 1)],
    )
    spawns = [
        spawn(Team.ALLY, (5, 0), no_reactions("hero_fighter")),
        spawn(Team.ENEMY, (0, 1), no_reactions()),
    ]
    choice = _ai()(give_turn(make_state(m, spawns), E1))
    assert isinstance(choice, Move)
    assert (choice.dest.x, choice.dest.y) == expected
    assert all(p.y != ice_row or p.x == 0 for p in choice.path)
