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
from hypothesis import example, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import give_turn, make_map, make_state, spawn, with_rolls
from trpg.engine import BattleState, Move, resolve
from trpg.engine.battle import simulate_branch, simulate_preview
from trpg.engine.context import CheckKind, CheckOverride, CheckRule, Ctx
from trpg.engine.events import CheckRolled, DamageDealt, StatusApplied, TrapTriggered
from trpg.engine.path_preview import PathEvent, PathPreview, _key, _merge_all, _trace, preview_path
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
        assert p.stops == (stop,)
        for step in p.steps:
            assert all(e.certain for e in step.events)
            assert _bare(step.events) == _bare(walked.by_step.get(step.index, []))
        return
    assert p.stops[0] == p.stop and p.worst_stop in p.stops
    assert stop in p.stops, (stop, p.stops)
    if len(p.stops) <= 2:  # 只有兩種停點時兩個欄位就涵蓋（6E-2b）
        assert stop in (p.stop, p.worst_stop)
    assert p.stop_certain is (len(p.stops) == 1)
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
    assert [s.reach for s in p.steps] == ["certain", "certain", "certain", "possible", "possible"]
    slid = [e for e in ice.events if e.kind == "displaced"]  # 失敗時滑到冰面外的第一格（#123）
    assert [(e.pos, e.detail, e.certain) for e in slid] == [((3, 0), "slide", False)]
    (run,) = p.slip_runs
    assert (run.start, run.end, run.fail_stop, run.stop_reason) == (2, 2, (3, 0), "off_ice")
    assert run.slide_path == ((2, 0), (3, 0))


def _ice_ally_checks(p: PathPreview) -> None:
    displaced = [e for e in p.steps[1].events if e.kind == "displaced"]
    assert displaced and displaced[0].pos == (0, 0) and not displaced[0].certain
    (run,) = p.slip_runs
    assert (run.fail_stop, run.slide_path, run.stop_reason) == ((0, 0), ((1, 0),), "wall")


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
        ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0)),
        False,
        (4, 0),
        (3, 0),
        check=_ice_checks,
    ),
    Case(
        # 第一格冰上有友軍、下一格是牆（一格都沒滑）：倒在友軍格上，滑回最近的空格
        "ice_under_ally_slides_back",
        lambda: _battle(
            "000000\n000000", "..#...\n......", surfaces=[(1, 0, "ice")], ally=[(0, 0), (1, 0)]
        ),
        ((0, 0), (1, 0), (1, 1)),
        False,
        (1, 1),
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
# 6E-2b 回歸：冰面最後一格有陷阱，最多後果被定身不滑，實走「陷阱抵抗成功＋冰面失敗」滑到冰外
@example(surfaces=[(2, 1, "ice")], moves=[(1, 0), (1, 0), (0, 1)], seed=0, trap=True)
# 6E-2b：冰在陷阱前，「過了冰＋陷阱定身」停在陷阱格（三種停點）
@example(surfaces=[(1, 0, "ice")], moves=[(1, 0), (1, 0), (0, 1), (0, 1)], seed=0, trap=True)
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
# 連續冰面（6A-4f；#123 起整段只在第一格檢定一次）：滑倒機率與停點＝窮舉實走
# ---------------------------------------------------------------------------


def _exhaust_check(state: BattleState, path: tuple[XY, ...]) -> tuple[Fraction, set[XY], int]:
    """窮舉 d20 的實走：滑倒的機率、滑倒時的停點、最多擲了幾次檢定。"""
    falls = 0
    stops: set[XY] = set()
    checks = 0
    for roll in range(1, 21):
        actual = resolve(with_rolls(state, [(20, roll)]), Move(unit_id=U1, path=_pos(path)))
        checks = max(checks, sum(isinstance(e, CheckRolled) for e in actual.events))
        hero = actual.state.units[U1]
        if hero.has_status("prone"):
            falls += 1
            stops.add(hero.xy)
    return Fraction(falls, 20), stops, checks


@pytest.mark.parametrize(
    ("ally", "expected_stop", "expected_slide", "reason"),
    [
        (((0, 0),), (3, 0), ((1, 0), (2, 0), (3, 0)), "off_ice"),
        (((0, 0), (2, 0)), (1, 0), ((1, 0),), "unit"),
    ],
    ids=["two_ice", "two_ice_ally_on_second"],
)
def test_ice_run_chance_and_stop_match_the_walk(
    ally: tuple[XY, ...], expected_stop: XY, expected_slide: tuple[XY, ...], reason: str
) -> None:
    state = _battle(surfaces=[(1, 0, "ice"), (2, 0, "ice")], ally=ally)
    path = ((0, 0), (1, 0), (2, 0), (3, 0))
    before, rng = state_to_json(state), state.rng_state
    p = preview_path(state, U1, path=_pos(path))
    assert state_to_json(state) == before and state.rng_state == rng
    assert len(p.slip_runs) == 1
    run = p.slip_runs[0]
    assert (run.start, run.end, run.tiles, run.status_id) == (1, 2, 2, "prone")
    assert (run.fail_stop, run.slide_path, run.stop_reason) == (
        expected_stop,
        expected_slide,
        reason,
    )
    chance, stops, checks = _exhaust_check(state, path)
    assert checks == 1  # 同一段冰只擲一次
    assert run.chance == chance and stops == {run.fail_stop}
    assert [e.kind for e in p.steps[2].events].count("slip_check") == 0


def test_ice_runs_split_on_plain_ground_and_keep_the_trap_after() -> None:
    split = _battle("000000\n000000", surfaces=[(1, 0, "ice"), (3, 0, "ice")])
    p = preview_path(split, U1, path=_pos(((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))))
    assert [(r.start, r.end, r.tiles) for r in p.slip_runs] == [(1, 1, 1), (3, 3, 1)]
    assert [(r.fail_stop, r.stop_reason) for r in p.slip_runs] == [((2, 0), "off_ice")] * 1 + [
        ((4, 0), "off_ice")
    ]
    trap = _enemy_trap(_battle(surfaces=[(1, 0, "ice"), (2, 0, "ice")]), (3, 0), revealed=True)
    q = preview_path(trap, U1, path=_pos(((0, 0), (1, 0), (2, 0), (3, 0))))
    assert [(r.start, r.end) for r in q.slip_runs] == [(1, 2)]
    assert q.steps[3].trap and q.steps[3].reach == "possible"
    # 滑到冰面外的陷阱格：停點是陷阱格（陷阱的抵抗在預覽取有利，停下原因是滑出冰面）
    assert q.slip_runs[0].fail_stop == (3, 0)
    plain = preview_path(_battle(), U1, path=_pos(((0, 0), (1, 0), (2, 0))))
    assert plain.slip_runs == ()


# ---------------------------------------------------------------------------
# 冰面檢定 × 其他分歧點（6E-2b）：所有實走停點都在 ``stops`` 裡
# ---------------------------------------------------------------------------


def _ice_trap_state(ice: Sequence[XY], seed: int) -> BattleState:
    m = make_map("000000\n000000\n000000", surfaces=[(x, y, "ice") for x, y in ice], enemy=[(5, 2)])
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (5, 2), "bandit")]
    return _enemy_trap(give_turn(make_state(m, spawns, seed=seed), U1), (2, 1), revealed=True)


@pytest.mark.parametrize(
    ("ice", "path", "stops", "worst_stop"),
    [
        # 陷阱在冰的最後一格：最多後果被定身不滑；「抵抗成功＋冰面失敗」滑到冰外 (2, 2)
        (((2, 1),), ((0, 0), (1, 0), (2, 0), (2, 1)), ((2, 1), (2, 2)), (2, 2)),
        # 冰在陷阱前：全過、冰面失敗（最多後果）、「過了冰＋陷阱定身」三種停點
        (((1, 0),), ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2)), ((2, 2), (2, 0), (2, 1)), (2, 0)),
        # 兩段冰中間有陷阱：第二段冰失敗（撞地圖邊緣，倒在 (2, 2)）也要算進去
        (
            ((1, 0), (2, 2)),
            ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (3, 2)),
            ((3, 2), (2, 0), (2, 1), (2, 2)),
            (2, 0),
        ),
    ],
    ids=["trap_on_last_ice", "ice_then_trap", "ice_trap_ice"],
)
def test_ice_branches_cover_every_walked_stop(
    ice: tuple[XY, ...], path: tuple[XY, ...], stops: tuple[XY, ...], worst_stop: XY
) -> None:
    p = preview_path(_ice_trap_state(ice, 0), U1, path=_pos(path))
    assert set(p.stops) == set(stops) and p.worst_stop == worst_stop
    assert not p.stop_certain
    walked = {
        resolve(_ice_trap_state(ice, seed), Move(unit_id=U1, path=_pos(path))).state.units[U1].xy
        for seed in range(120)
    }
    assert walked == set(p.stops)


# ---------------------------------------------------------------------------
# 冰後陷阱的傷害範圍與定身（6A-4f 待決 1，Phase 6P-1）＝窮舉實走
# ---------------------------------------------------------------------------


def _two_ice_trap_state(seed: int) -> BattleState:
    """6A-4f 的例子：兩格冰 (1,0)(2,0)，後方 (3,0) 有看得見的陷阱。"""
    m = make_map("000000\n000000", surfaces=[(1, 0, "ice"), (2, 0, "ice")], enemy=[(5, 1)])
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (5, 1), "bandit")]
    return _enemy_trap(give_turn(make_state(m, spawns, seed=seed), U1), (3, 0), revealed=True)


def _walked_trap(result_events: Sequence[object]) -> tuple[int, bool] | None:
    """實走在陷阱觸發前沒有滑倒時：``(陷阱造成的傷害, 有沒有定身)``；其他情況 ``None``。"""
    hit = next((i for i, e in enumerate(result_events) if isinstance(e, TrapTriggered)), None)
    if hit is None:
        return None
    before = result_events[:hit]
    if any(isinstance(e, CheckRolled) and e.slide and not e.success for e in before):
        return None
    after = result_events[hit:]
    damage = sum(
        e.hp_before - e.hp_after
        for e in after
        if isinstance(e, DamageDealt) and e.target_id == U1 and e.cause == "attack"
    )
    root = any(isinstance(e, StatusApplied) and e.status_id == "root" for e in after)
    return damage, root


@pytest.mark.parametrize(
    ("build", "path", "trap_index"),
    [
        (
            lambda seed: _ice_trap_state(((1, 0),), seed),
            ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2)),
            3,
        ),
        (
            lambda seed: _ice_trap_state(((1, 0), (2, 2)), seed),
            ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (3, 2)),
            3,
        ),
        (_two_ice_trap_state, ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0)), 3),
    ],
    ids=["ice_then_trap", "ice_trap_ice", "two_ice_then_trap"],
)
def test_trap_after_ice_damage_range_matches_the_walk(
    build: Callable[[int], BattleState], path: tuple[XY, ...], trap_index: int
) -> None:
    state = build(0)
    before, rng = state_to_json(state), state.rng_state
    p = preview_path(state, U1, path=_pos(path))
    assert state_to_json(state) == before and state.rng_state == rng
    events = p.steps[trap_index].events
    trap = next(e for e in events if e.kind == "trap")
    damage = next(e for e in events if e.kind == "damage" and e.other_id == trap.other_id)
    root = next(e for e in events if e.kind == "status" and e.status_id == "root")
    walks = [
        _walked_trap(resolve(build(seed), Move(unit_id=U1, path=_pos(path))).events)
        for seed in range(300)
    ]
    passed = [w for w in walks if w is not None]
    assert passed and len(passed) < len(walks)  # 有過了冰的，也有滑倒走不到的
    amounts = {d for d, _ in passed}
    assert (damage.amount_min, damage.amount_max) == (min(amounts), max(amounts))
    roots = {r for _, r in passed}
    assert roots == {True, False} and not root.certain  # 定身是「可能」
    assert not trap.certain and not damage.certain


# ---------------------------------------------------------------------------
# 冰面檢定覆寫（Phase 6P-1 的 SlideOverride，Phase 7 前置泛化成 CheckOverride）：純預覽參數，
# 正式結算不受影響
# ---------------------------------------------------------------------------

_SLIDE: tuple[CheckKind, ...] = ("slide",)


def test_check_rule_outcomes() -> None:
    worst_at = CheckOverride.worst_at
    assert [worst_at(2).rules[0].outcome(i) for i in range(4)] == ["best", "best", "worst", None]
    assert [worst_at(0, rest="best").rules[0].outcome(i) for i in range(3)] == [
        "worst",
        "best",
        "best",
    ]
    assert CheckRule(rest="best").outcome(5) == "best"
    assert CheckRule().outcome(0) is None


def test_check_override_is_preview_only() -> None:
    state = _ice_trap_state(((1, 0),), 0)
    with pytest.raises(ValueError, match="check_override"):
        Ctx(state.clone(), check_override=CheckOverride.of(_SLIDE, rest="best"))
    assert Ctx(state.clone()).check_override is None


def test_formal_resolve_ignores_previews() -> None:
    """同一個種子：做過各種預覽（含冰面分支）之後正式結算的事件與狀態完全相同。"""
    path = _pos(((0, 0), (1, 0), (2, 0), (2, 1), (2, 2)))
    for seed in range(20):
        state = _ice_trap_state(((1, 0),), seed)
        first = resolve(state, Move(unit_id=U1, path=path))
        preview_path(state, U1, path=path)
        again = resolve(state, Move(unit_id=U1, path=path))
        assert repr(first.events) == repr(again.events)
        assert state_to_json(first.state) == state_to_json(again.state)


def test_slide_override_only_forces_slide_checks() -> None:
    """全部通過 × 最少後果＝最少後果（最少後果的冰面本來就通過）；全部通過 × 最多後果不滑倒。"""
    state = _ice_trap_state(((1, 0),), 0)
    move = Move(unit_id=U1, path=_pos(((0, 0), (1, 0), (2, 0), (2, 1), (2, 2))))
    low, high = simulate_preview(state, move)
    all_pass = CheckOverride.of(_SLIDE, rest="best")
    passed_min = simulate_branch(state, move, override=all_pass)[0]
    assert repr(passed_min.events) == repr(low.events)
    passed_max = simulate_branch(state, move, "max", override=all_pass)[0]
    checks = [e for e in passed_max.events if isinstance(e, CheckRolled) and e.slide]
    assert len(checks) == 1 and checks[0].success
    assert passed_max.state.units[U1].xy == (2, 1)  # 過了冰、被陷阱定身
    assert high.state.units[U1].xy != passed_max.state.units[U1].xy


# ---------------------------------------------------------------------------
# 事件合併（6R-P：_merge／_fold／_paired／_widen 合成一個 fold）
# ---------------------------------------------------------------------------


def _hit(amount: int, source: str = "e1") -> PathEvent:
    return PathEvent(
        "damage", True, other_id=UnitId(source), amount_min=amount, amount_max=amount, detail="trap"
    )


type _Range = tuple[int | None, int | None, bool]

_MERGE_CASES: list[tuple[str, list[list[PathEvent]], list[_Range]]] = [
    ("same_damage", [[_hit(5)], [_hit(5)]], [(5, 5, True)]),
    ("low_less_than_high", [[_hit(4)], [_hit(9)]], [(4, 9, True)]),
    ("low_more_than_high", [[_hit(9)], [_hit(4)]], [(4, 9, True)]),
    ("only_in_high", [[], [_hit(7)]], [(None, 7, False)]),
    ("only_in_low", [[_hit(3)], []], [(3, 3, False)]),
    ("extra_branch_lower", [[_hit(4)], [_hit(9)], [_hit(2)]], [(2, 9, True)]),
    ("extra_branch_higher", [[_hit(4)], [_hit(9)], [_hit(12)]], [(4, 12, True)]),
    ("extra_branch_missing", [[_hit(4)], [_hit(9)], []], [(4, 9, False)]),
    # 只在最多後果出現（沒有最小值）、之後的分支也有：最小值取那個分支的
    ("high_only_then_extra", [[], [_hit(9)], [_hit(6)]], [(6, 9, False)]),
    (
        "only_in_extra",
        [[_hit(4)], [_hit(9)], [_hit(4), _hit(8, "e2")]],
        [(4, 9, True), (None, 8, False)],
    ),
    (
        "two_sources",
        [[_hit(4), _hit(1, "e2")], [_hit(9), _hit(3, "e2")]],
        [(4, 9, True), (1, 3, True)],
    ),
]


@pytest.mark.parametrize(
    ("sims", "expected"), [c[1:] for c in _MERGE_CASES], ids=[c[0] for c in _MERGE_CASES]
)
def test_merge_gives_the_damage_range_of_every_branch(
    sims: list[list[PathEvent]], expected: list[_Range]
) -> None:
    """同一格各分支的傷害：上下限取所有分支的聯集，缺了的分支讓事件變「可能」。"""
    merged = _merge_all(sims)
    assert [(e.amount_min, e.amount_max, e.certain) for e in merged] == expected


def test_merge_keeps_non_damage_events_and_stopped_reasons() -> None:
    root = PathEvent("status", True, status_id="root")
    low = [PathEvent("stopped", True, detail="prone"), root]
    high = [PathEvent("stopped", True, detail="downed"), root]
    merged = _merge_all([low, high])
    assert [(e.kind, e.certain, e.detail) for e in merged] == [
        ("stopped", False, "prone"),
        ("status", True, None),
    ]
