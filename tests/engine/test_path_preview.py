"""路徑預覽（Phase 6A-4b）：表格測試「預覽＝實走」，以及預覽前後狀態與 ``rng_state`` 完全相同。

比對方式：預覽回傳的停點、每格事件，與實際 ``resolve`` 同一條（合法前段的）路徑之後的結果。
預覽沒有經過分歧點（``certain``）時必須完全一致；有分歧點時，實走的結果必須是兩個極端之一，
且預覽中「確定」的事件在實走中同一格都出現。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import give_turn, make_map, make_state, spawn, with_rolls
from trpg.engine import BattleState, Move, resolve
from trpg.engine.path_preview import PathEvent, PathPreview, _key, _trace, preview_path
from trpg.engine.state import TrapState, state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, Surface, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")

type XY = tuple[int, int]


def _pos(path: Sequence[XY]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in path)


def _battle(
    heights: str = "000000\n000000",
    terrain: str | None = None,
    *,
    surfaces: Sequence[tuple[int, int, str]] = (),
    ally: Sequence[XY] = ((0, 0),),
    enemy: Sequence[XY] = ((5, 1),),
) -> BattleState:
    m = make_map(heights, terrain, surfaces=surfaces, ally=ally, enemy=enemy)
    spawns = [spawn(Team.ALLY, xy, "hero_fighter") for xy in ally]
    spawns += [spawn(Team.ENEMY, xy, "bandit") for xy in enemy]
    return give_turn(make_state(m, spawns), U1)


def _enemy_trap(state: BattleState, xy: XY, *, revealed: bool) -> BattleState:
    s = state.clone()
    owner = next(u.id for u in s.units.values() if u.team is Team.ENEMY)
    s.traps = [
        TrapState(
            owner_id=owner,
            team=Team.ENEMY,
            pos=Pos(x=xy[0], y=xy[1]),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple((a, 10) for a in Attribute),
            revealed_to=(Team.ALLY,) if revealed else (),
        )
    ]
    return s


def _bare(events: Sequence[PathEvent]) -> list[tuple[object, ...]]:
    """比對用：事件的鍵與數值（不看 ``certain``）。"""
    return sorted((repr(_key(e)), e.amount_max, e.chance) for e in events)


def _assert_matches_walk(state: BattleState, p: PathPreview) -> None:
    """預覽＝實走：實際 ``resolve`` 合法前段之後的停點與每格事件。"""
    if p.legal_length == 0:
        return
    actual = resolve(state, Move(unit_id=p.unit_id, path=_pos(p.path[: p.legal_length])))
    walked = _trace(actual, p.unit_id, p.legal_length)
    stop = actual.state.units[p.unit_id].xy
    if p.certain:
        assert stop == p.stop == p.worst_stop
        for step in p.steps:
            assert all(e.certain for e in step.events)
            assert _bare(step.events) == _bare(walked.by_step.get(step.index, []))
        return
    assert stop in (p.stop, p.worst_stop)
    for step in p.steps:
        if step.reach != "certain":
            continue
        got = {_key(e) for e in walked.by_step.get(step.index, [])}
        for event in step.events:
            if event.certain and event.kind != "stopped":
                assert _key(event) in got, (step.index, event)


# ---------------------------------------------------------------------------
# 表格：預覽＝實走
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    name: str
    build: Callable[[], BattleState]
    path: tuple[XY, ...]
    certain: bool
    stop: XY
    worst_stop: XY
    reachable: bool = True
    check: Callable[[PathPreview], None] | None = None


def _plain_checks(p: PathPreview) -> None:
    assert [s.reach for s in p.steps] == ["certain"] * 4
    assert all(not s.events for s in p.steps)
    assert p.move_cost == 3


def _ice_checks(p: PathPreview) -> None:
    ice = p.steps[2]
    assert ice.surface is Surface.ICE
    kinds = [(e.kind, e.certain) for e in ice.events]
    assert ("surface", True) in kinds and ("slip_check", True) in kinds
    slip = next(e for e in ice.events if e.kind == "slip_check")
    assert slip.status_id == "prone" and slip.chance is not None and 0 < slip.chance < 1
    assert any(e.kind == "status" and e.status_id == "prone" and not e.certain for e in ice.events)
    stopped = next(e for e in ice.events if e.kind == "stopped")
    assert not stopped.certain and stopped.detail == "prone"
    assert [s.reach for s in p.steps] == ["certain", "certain", "certain", "possible"]


def _ice_ally_checks(p: PathPreview) -> None:
    displaced = [e for e in p.steps[1].events if e.kind == "displaced"]
    assert displaced and displaced[0].pos == (0, 0) and not displaced[0].certain


def _wall_checks(p: PathPreview) -> None:
    assert p.legal_length == 3 and p.reason is not None and "牆" in p.reason
    assert [s.reach for s in p.steps] == ["certain", "certain", "certain", "unreachable"]


def _enemy_block_checks(p: PathPreview) -> None:
    assert p.legal_length == 2 and p.reason is not None and "阻擋" in p.reason
    assert [s.reach for s in p.steps][2:] == ["unreachable", "unreachable"]


def _budget_checks(p: PathPreview) -> None:
    assert p.legal_length == 6 and "移動點數不足" in (p.reason or "")
    assert p.steps[-1].reach == "unreachable" and p.move_cost == 5


def _trap_checks(p: PathPreview) -> None:
    step = p.steps[2]
    assert step.trap
    trap = next(e for e in step.events if e.kind == "trap")
    assert trap.certain and trap.detail == "skill_bear_trap"
    damage = next(e for e in step.events if e.kind == "damage")
    assert damage.certain and damage.amount_min is not None and damage.amount_max is not None
    assert damage.amount_min < damage.amount_max
    assert any(e.kind == "status" and e.status_id == "root" for e in step.events)
    assert p.steps[3].reach in ("possible", "interrupted")


def _hidden_trap_checks(p: PathPreview) -> None:
    assert not any(s.trap for s in p.steps)
    assert all(e.kind != "trap" for s in p.steps for e in s.events)


def _fire_oil_checks(p: PathPreview) -> None:
    fire, oil = p.steps[1], p.steps[2]
    assert fire.surface is Surface.FIRE and oil.surface is Surface.OIL
    assert any(e.kind == "status" and e.status_id == "burning" and e.certain for e in fire.events)
    assert p.steps[3].surface is Surface.WATER  # 潮濕：畫面用格子的表面顯示


def _opportunity_checks(p: PathPreview) -> None:
    start = p.steps[0]  # 離開的那一格
    assert any(e.kind == "reaction" and e.other_id == U2 for e in start.events)
    assert any(e.kind == "damage" and not e.certain and e.amount_min is None for e in start.events)


CASES: tuple[Case, ...] = (
    Case(
        "plain_ground",
        _battle,
        ((0, 0), (1, 0), (2, 0), (3, 0)),
        True,
        (3, 0),
        (3, 0),
        check=_plain_checks,
    ),
    Case(
        "ice_slip_or_pass",
        lambda: _battle(surfaces=[(2, 0, "ice")]),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
        False,
        (3, 0),
        (2, 0),
        check=_ice_checks,
    ),
    Case(
        "ice_under_ally_slides_back",
        lambda: _battle(surfaces=[(1, 0, "ice")], ally=[(0, 0), (1, 0)]),
        ((0, 0), (1, 0), (2, 0)),
        False,
        (2, 0),
        (0, 0),
        check=_ice_ally_checks,
    ),
    Case(
        "ice_before_wall_unreachable",
        lambda: _battle(
            "000000\n000000", "...#..\n......", surfaces=[(2, 0, "ice")], enemy=[(5, 1)]
        ),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
        False,
        (2, 0),
        (2, 0),
        reachable=False,
        check=_wall_checks,
    ),
    Case(
        "blocked_by_enemy",
        lambda: _battle(enemy=[(2, 0)]),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
        True,
        (1, 0),
        (1, 0),
        reachable=False,
        check=_enemy_block_checks,
    ),
    Case(
        "out_of_move_points",
        lambda: _battle("0000000\n0000000", enemy=[(6, 1)]),
        tuple((x, 0) for x in range(7)),
        True,
        (5, 0),
        (5, 0),
        reachable=False,
        check=_budget_checks,
    ),
    Case(
        "revealed_trap",
        lambda: _enemy_trap(_battle(), (2, 0), revealed=True),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
        False,
        (3, 0),
        (2, 0),
        check=_trap_checks,
    ),
    Case(
        "fire_then_oil_then_water",
        lambda: _battle(surfaces=[(1, 0, "fire"), (2, 0, "oil"), (3, 0, "water")]),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
        True,
        (3, 0),
        (3, 0),
        check=_fire_oil_checks,
    ),
    Case(
        "leaving_an_adjacent_enemy",
        lambda: _battle(ally=[(1, 0)], enemy=[(1, 1)]),
        ((1, 0), (2, 0), (3, 0)),
        False,
        (3, 0),
        (3, 0),
        check=_opportunity_checks,
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_path_preview_table(case: Case) -> None:
    state = case.build()
    before = state_to_json(state)
    p = preview_path(state, U1, path=_pos(case.path))
    assert state_to_json(state) == before
    assert p.path == case.path
    assert p.certain is case.certain
    assert p.reachable is case.reachable
    assert (p.stop, p.worst_stop) == (case.stop, case.worst_stop)
    if case.check is not None:
        case.check(p)
    _assert_matches_walk(state, p)


@pytest.mark.parametrize(
    ("case_name", "roll", "expected"),
    [
        ("ice_slip_or_pass", 20, "stop"),
        ("ice_slip_or_pass", 1, "worst_stop"),
        ("ice_under_ally_slides_back", 20, "stop"),
        ("ice_under_ally_slides_back", 1, "worst_stop"),
    ],
)
def test_slip_check_extremes_match_the_walk(case_name: str, roll: int, expected: str) -> None:
    case = next(c for c in CASES if c.name == case_name)
    state = with_rolls(case.build(), [(20, roll)])
    p = preview_path(state, U1, path=_pos(case.path))
    actual = resolve(state, Move(unit_id=U1, path=_pos(case.path)))
    assert actual.state.units[U1].xy == getattr(p, expected)


def test_slip_chance_is_exact() -> None:
    case = CASES[1]
    state = case.build()
    p = preview_path(state, U1, path=_pos(case.path))
    slip = next(e for e in p.steps[2].events if e.kind == "slip_check")
    # 實際機率：窮舉 d20 的實走結果
    falls = 0
    for roll in range(1, 21):
        actual = resolve(with_rolls(state, [(20, roll)]), Move(unit_id=U1, path=_pos(case.path)))
        falls += actual.state.units[U1].has_status("prone")
    assert slip.chance == Fraction(falls, 20)


def test_hidden_trap_is_not_leaked() -> None:
    state = _enemy_trap(_battle(), (2, 0), revealed=False)
    p = preview_path(state, U1, path=_pos(((0, 0), (1, 0), (2, 0), (3, 0))))
    _hidden_trap_checks(p)
    assert p.certain and p.stop == (3, 0)


def test_dest_finds_the_shortest_path_and_marks_unreachable() -> None:
    state = _battle("0000000\n0000000", enemy=[(6, 1)])
    p = preview_path(state, U1, dest=Pos(x=3, y=0))
    assert p.path == ((0, 0), (1, 0), (2, 0), (3, 0)) and p.reachable
    far = preview_path(state, U1, dest=Pos(x=6, y=0))
    assert not far.reachable and far.legal_length == 6 and far.stop == (5, 0)
    walled = _battle("000\n000", "..#\n..#", enemy=[(0, 1)])
    none = preview_path(walled, U1, dest=Pos(x=2, y=0))
    assert none.path == ((0, 0), (2, 0)) and none.legal_length == 0 and none.stop == (0, 0)
    assert [s.reach for s in none.steps] == ["certain", "unreachable"]


def test_needs_exactly_one_of_path_or_dest_and_the_active_unit() -> None:
    state = _battle()
    with pytest.raises(IllegalActionError):
        preview_path(state, U1)
    with pytest.raises(IllegalActionError):
        preview_path(state, U1, path=_pos(((0, 0),)), dest=Pos(x=1, y=0))
    with pytest.raises(IllegalActionError):
        preview_path(state, U2, dest=Pos(x=4, y=1))


# ---------------------------------------------------------------------------
# 性質：預覽不改狀態與亂數；確定的預覽與實走一致
# ---------------------------------------------------------------------------

_SURFACES = ("none", "ice", "fire", "oil", "water", "poison")
_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@settings(max_examples=40, deadline=None)
@given(
    surfaces=st.lists(
        st.tuples(st.integers(0, 5), st.integers(0, 2), st.sampled_from(_SURFACES)), max_size=6
    ),
    moves=st.lists(st.sampled_from(_DIRS), min_size=1, max_size=7),
    seed=st.integers(0, 10_000),
    trap=st.booleans(),
)
def test_preview_never_changes_state_and_matches_when_certain(
    surfaces: list[tuple[int, int, str]], moves: list[XY], seed: int, trap: bool
) -> None:
    placed = [(x, y, k) for x, y, k in surfaces if k != "none" and (x, y) not in ((0, 0), (5, 2))]
    unique = list({(x, y): (x, y, k) for x, y, k in placed}.values())
    m = make_map("000000\n000000\n000000", surfaces=unique, enemy=[(5, 2)])
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (5, 2), "bandit")]
    state = give_turn(make_state(m, spawns, seed=seed), U1)
    if trap:
        state = _enemy_trap(state, (2, 1), revealed=seed % 2 == 0)
    path = [(0, 0)]
    for dx, dy in moves:  # 座標不能是負數（Pos 的驗證）；超出右、下邊界的交給引擎判不合法
        x, y = path[-1][0] + dx, path[-1][1] + dy
        if x >= 0 and y >= 0:
            path.append((x, y))
    before, rng = state_to_json(state), state.rng_state
    p = preview_path(state, U1, path=_pos(path))
    assert state_to_json(state) == before and state.rng_state == rng
    assert len(p.steps) == len(path)
    if not (trap and seed % 2):  # 看不見的陷阱：預覽刻意不知道，實走可能不同
        _assert_matches_walk(state, p)


# ---------------------------------------------------------------------------
# 連續冰面（6A-4f）：整段的滑倒機率與停點＝窮舉實走
# ---------------------------------------------------------------------------


def _exhaust_two_checks(state: BattleState, path: tuple[XY, ...]) -> tuple[Fraction, set[XY]]:
    """窮舉兩次 d20 檢定的實走：至少滑倒一次的機率、滑倒時的停點。"""
    falls = 0
    stops: set[XY] = set()
    for first in range(1, 21):
        for second in range(1, 21):
            rolled = with_rolls(state, [(20, first), (20, second)])
            actual = resolve(rolled, Move(unit_id=U1, path=_pos(path)))
            hero = actual.state.units[U1]
            if hero.has_status("prone"):
                falls += 1
                stops.add(hero.xy)
    return Fraction(falls, 400), stops


@pytest.mark.parametrize(
    ("ally", "expected_stops"),
    [(((0, 0),), ((1, 0), (2, 0))), (((0, 0), (2, 0)), ((1, 0),))],
    ids=["two_ice", "two_ice_ally_on_second"],
)
def test_ice_run_chance_and_stops_match_the_walk(
    ally: tuple[XY, ...], expected_stops: tuple[XY, ...]
) -> None:
    state = _battle(surfaces=[(1, 0, "ice"), (2, 0, "ice")], ally=ally)
    path = ((0, 0), (1, 0), (2, 0), (3, 0))
    before, rng = state_to_json(state), state.rng_state
    p = preview_path(state, U1, path=_pos(path))
    assert state_to_json(state) == before and state.rng_state == rng
    assert len(p.slip_runs) == 1
    run = p.slip_runs[0]
    assert (run.start, run.end, run.tiles, run.status_id) == (1, 2, 2, "prone")
    assert run.fail_stops == expected_stops
    chance, stops = _exhaust_two_checks(state, path)
    assert run.chance == chance
    assert set(run.fail_stops) == stops
    single = [next(e for e in p.steps[i].events if e.kind == "slip_check").chance for i in (1, 2)]
    assert single[0] is not None and single[1] is not None
    assert run.chance == 1 - (1 - single[0]) * (1 - single[1])


def test_ice_runs_split_on_plain_ground_and_keep_the_trap_after() -> None:
    split = _battle("000000\n000000", surfaces=[(1, 0, "ice"), (3, 0, "ice")])
    p = preview_path(split, U1, path=_pos(((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))))
    assert [(r.start, r.end, r.tiles) for r in p.slip_runs] == [(1, 1, 1), (3, 3, 1)]
    trap = _enemy_trap(_battle(surfaces=[(1, 0, "ice"), (2, 0, "ice")]), (3, 0), revealed=True)
    q = preview_path(trap, U1, path=_pos(((0, 0), (1, 0), (2, 0), (3, 0))))
    assert [(r.start, r.end) for r in q.slip_runs] == [(1, 2)]
    assert q.steps[3].trap and q.steps[3].reach == "possible"
    plain = preview_path(_battle(), U1, path=_pos(((0, 0), (1, 0), (2, 0))))
    assert plain.slip_runs == ()
