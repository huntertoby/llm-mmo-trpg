"""冰面滑倒並滑行（#123，Phase 6E-2）：每種停止條件、同一段冰只擲一次、剩餘點數作廢、滑過的陷阱與
表面照常觸發、被推進冰面不滑；並逐一比對路徑預覽的停點＝實走。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from tests.engine.race_helpers import race_state
from trpg.engine import BattleState, Move, resolve
from trpg.engine.effects import run_effects
from trpg.engine.effects.models import MoveUnitEffect
from trpg.engine.events import CheckRolled, StatusApplied, TrapTriggered, UnitMoved, UnitSlid
from trpg.engine.path_preview import preview_path
from trpg.engine.state import TrapState
from trpg.shared.types import Attribute, Pos, Surface, Team, UnitId

U1 = UnitId("unit_0001")

type XY = tuple[int, int]

FAIL = [(20, 1)]
PASS = [(20, 20)]


def _pos(path: Sequence[XY]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in path)


def _battle(
    heights: str,
    terrain: str | None = None,
    *,
    ice: Sequence[XY],
    others: Sequence[tuple[XY, Team]] = (),
    objects: Sequence[tuple[int, int, str]] = (),
    surfaces: Sequence[tuple[int, int, str]] = (),
    hero: str = "hero_fighter",
) -> BattleState:
    enemy = [xy for xy, team in others if team is Team.ENEMY] or [(5, 3)]
    ally = [(0, 0), *(xy for xy, team in others if team is Team.ALLY)]
    m = make_map(
        heights,
        terrain,
        surfaces=[*((x, y, "ice") for x, y in ice), *surfaces],
        ally=ally,
        enemy=enemy,
        objects=objects,
    )
    spawns = [spawn(Team.ALLY, (0, 0), template(hero, reactions=[]))]
    spawns += [spawn(Team.ALLY, xy, template("hero_archer", reactions=[])) for xy in ally[1:]]
    spawns += [spawn(Team.ENEMY, xy, template("bandit", reactions=[])) for xy in enemy]
    return give_turn(make_state(m, spawns), U1)


_ROW = "000000\n000000\n000000\n000000"


@dataclass(frozen=True)
class Case:
    name: str
    state: BattleState
    path: tuple[XY, ...]
    stop: XY
    slide: tuple[XY, ...]
    reason: str


CASES = (
    Case(
        "off_ice",
        _battle(_ROW, ice=[(1, 0)]),
        ((0, 0), (1, 0), (2, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "off_ice",
    ),
    Case(
        "max_tiles_stays_on_ice",
        _battle(_ROW, ice=[(1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]),
        ((0, 0), (1, 0)),
        (4, 0),
        ((1, 0), (2, 0), (3, 0), (4, 0)),
        "max_tiles",
    ),
    Case(
        "wall",
        _battle(_ROW, "...#..\n......\n......\n......", ice=[(1, 0), (2, 0)]),
        ((0, 0), (1, 0), (1, 1)),
        (2, 0),
        ((1, 0), (2, 0)),
        "wall",
    ),
    Case(
        "object",
        _battle(_ROW, ice=[(1, 0), (2, 0)], objects=[(3, 0, "crate")]),
        ((0, 0), (1, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "object",
    ),
    Case(
        "enemy_unit",
        _battle(_ROW, ice=[(1, 0), (2, 0)], others=[((3, 0), Team.ENEMY)]),
        ((0, 0), (1, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "unit",
    ),
    Case(
        "ally_unit",
        _battle(_ROW, ice=[(1, 0), (2, 0)], others=[((3, 0), Team.ALLY)]),
        ((0, 0), (1, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "unit",
    ),
    Case(
        "map_edge",
        _battle("000\n000\n000\n000", ice=[(1, 0), (2, 0)], others=[((0, 3), Team.ENEMY)]),
        ((0, 0), (1, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "edge",
    ),
    Case(
        "height_up",
        _battle("001000\n000000\n000000\n000000", ice=[(1, 0)]),
        ((0, 0), (1, 0)),
        (1, 0),
        ((1, 0),),
        "height",
    ),
    Case(
        "height_down",
        _battle("110000\n110000\n000000\n000000", ice=[(1, 0)]),
        ((0, 0), (1, 0)),
        (1, 0),
        ((1, 0),),
        "height",
    ),
    Case(
        "chasm",
        _battle(_ROW, "..x...\n......\n......\n......", ice=[(1, 0)]),
        ((0, 0), (1, 0)),
        (1, 0),
        ((1, 0),),
        "deadly",
    ),
    Case(
        "lava",
        _battle(_ROW, "...~..\n......\n......\n......", ice=[(1, 0), (2, 0)]),
        ((0, 0), (1, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "deadly",
    ),
    Case(
        "slides_into_fire",
        _battle(_ROW, ice=[(1, 0)], surfaces=[(2, 0, "fire")]),
        ((0, 0), (1, 0)),
        (2, 0),
        ((1, 0), (2, 0)),
        "off_ice",
    ),
    Case(
        "vertical",
        _battle(_ROW, ice=[(0, 1), (0, 2)]),
        ((0, 0), (0, 1)),
        (0, 3),
        ((0, 1), (0, 2), (0, 3)),
        "off_ice",
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_slide_stop_conditions_and_preview_matches(case: Case) -> None:
    state = with_rolls(case.state, FAIL)
    result = resolve(state, Move(unit_id=U1, path=_pos(case.path)))
    hero = result.state.units[U1]
    assert hero.xy == case.stop and hero.has_status("prone")
    assert hero.move_points == 0  # 這次移動剩下的點數作廢
    (slid,) = [e for e in result.events if isinstance(e, UnitSlid)]
    assert tuple((p.x, p.y) for p in slid.path) == case.slide
    assert slid.stop_reason == case.reason
    moves = [e for e in result.events if isinstance(e, UnitMoved) and e.mode == "slide"]
    assert [(e.to_pos.x, e.to_pos.y) for e in moves] == list(case.slide[1:])
    # 倒地在滑行停下之後
    prone = next(
        e for e in result.events if isinstance(e, StatusApplied) and e.status_id == "prone"
    )
    assert prone.seq > slid.seq
    assert not any(e.mode == "forced" for e in result.events if isinstance(e, UnitMoved))
    # 預覽：單一停點與滑行路徑＝實走
    p = preview_path(case.state, U1, path=_pos(case.path))
    (run,) = p.slip_runs
    assert (run.fail_stop, run.slide_path, run.stop_reason) == (case.stop, case.slide, case.reason)


def test_slides_into_fire_burns() -> None:
    case = next(c for c in CASES if c.name == "slides_into_fire")
    result = resolve(with_rolls(case.state, FAIL), Move(unit_id=U1, path=_pos(case.path)))
    assert result.state.units[U1].has_status("burning")


def test_one_roll_per_run_and_success_walks_on() -> None:
    state = _battle(_ROW, ice=[(1, 0), (2, 0), (3, 0)])
    path = ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))
    result = resolve(with_rolls(state, PASS), Move(unit_id=U1, path=_pos(path)))
    checks = [e for e in result.events if isinstance(e, CheckRolled)]
    assert len(checks) == 1 and checks[0].success and checks[0].slide
    assert result.state.units[U1].xy == (4, 0) and not result.state.units[U1].has_status("prone")
    assert not any(isinstance(e, UnitSlid) for e in result.events)


def test_stop_on_ice_after_success_is_allowed() -> None:
    state = _battle(_ROW, ice=[(1, 0), (2, 0)])
    result = resolve(with_rolls(state, PASS), Move(unit_id=U1, path=_pos(((0, 0), (1, 0)))))
    assert result.state.units[U1].xy == (1, 0) and result.state.units[U1].move_points > 0


def test_two_separate_runs_roll_twice() -> None:
    state = _battle(_ROW, ice=[(1, 0), (3, 0)])
    path = ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))
    result = resolve(with_rolls(state, [(20, 20), (20, 20)]), Move(unit_id=U1, path=_pos(path)))
    assert sum(isinstance(e, CheckRolled) for e in result.events) == 2


def test_starting_on_ice_continues_the_same_run() -> None:
    state = _battle(_ROW, ice=[(0, 0), (1, 0), (2, 0)])
    result = resolve(state, Move(unit_id=U1, path=_pos(((0, 0), (1, 0), (2, 0), (3, 0)))))
    assert not any(isinstance(e, CheckRolled) for e in result.events)


def test_failed_slide_discards_rest_of_the_path() -> None:
    state = _battle(_ROW, ice=[(1, 0)])
    path = ((0, 0), (1, 0), (1, 1), (1, 2))
    result = resolve(with_rolls(state, FAIL), Move(unit_id=U1, path=_pos(path)))
    hero = result.state.units[U1]
    assert hero.xy == (2, 0) and hero.move_points == 0


def test_slide_over_a_trap_triggers_and_stops_there() -> None:
    base = _battle(_ROW, ice=[(1, 0), (2, 0), (3, 0)])
    owner = next(u.id for u in base.units.values() if u.team is Team.ENEMY)
    base.traps = [
        TrapState(
            owner_id=owner,
            team=Team.ENEMY,
            pos=Pos(x=2, y=0),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple((a, 10) for a in Attribute),
            revealed_to=(Team.ALLY,),
        )
    ]
    state = with_rolls(base, [(20, 1), (8, 1), (20, 1)])
    result = resolve(state, Move(unit_id=U1, path=_pos(((0, 0), (1, 0)))))
    assert any(isinstance(e, TrapTriggered) for e in result.events)
    (slid,) = [e for e in result.events if isinstance(e, UnitSlid)]
    hero = result.state.units[U1]
    if hero.has_status("root"):
        assert hero.xy == (2, 0) and slid.stop_reason == "interrupted"
    else:  # 抵抗成功：照常滑到冰面外
        assert hero.xy == (4, 0)
    assert hero.has_status("prone")


def test_pushed_onto_ice_checks_but_does_not_slide() -> None:
    state = with_rolls(_battle(_ROW, ice=[(1, 0), (2, 0)]), FAIL)
    result = run_effects(state, [MoveUnitEffect(unit_id=U1, dest=(1, 0), mode="forced")])
    hero = result.state.units[U1]
    assert hero.xy == (1, 0) and hero.has_status("prone")
    checks = [e for e in result.events if isinstance(e, CheckRolled)]
    assert len(checks) == 1 and not checks[0].slide
    assert not any(isinstance(e, UnitSlid) for e in result.events)


def test_slide_is_deterministic() -> None:
    state = _battle(_ROW, ice=[(1, 0), (2, 0)])
    move = Move(unit_id=U1, path=_pos(((0, 0), (1, 0))))
    first = [e.model_dump() for e in resolve(state, move).events]
    second = [e.model_dump() for e in resolve(state, move).events]
    assert first == second


def test_preview_marks_slip_immune_runs() -> None:
    """矮人、鱗族：小牌寫「冰 N 格・不會滑倒」（05 5.10）——預覽給 ``immune`` 的段、不擲不滑。"""
    state = race_state("dwarf", foes=((6, 6),), surfaces=[(4, 3, "ice"), (5, 3, "ice")])
    p = preview_path(state, U1, path=_pos(((3, 3), (4, 3), (5, 3), (6, 3))))
    (run,) = p.slip_runs
    assert run.immune and run.chance == 0 and (run.start, run.end) == (1, 2)
    assert run.slide_path == ((4, 3),) and run.status_id is None
    human = preview_path(
        race_state(None, foes=((6, 6),), surfaces=[(4, 3, "ice")]),
        U1,
        path=_pos(((3, 3), (4, 3))),
    )
    assert [r.immune for r in human.slip_runs] == [False]


def test_preview_flags_a_trap_or_surface_at_the_stop() -> None:
    base = _battle(_ROW, ice=[(1, 0)])
    owner = next(u.id for u in base.units.values() if u.team is Team.ENEMY)
    base.traps = [
        TrapState(
            owner_id=owner,
            team=Team.ENEMY,
            pos=Pos(x=2, y=0),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple((a, 10) for a in Attribute),
            revealed_to=(Team.ALLY,),
        )
    ]
    (run,) = preview_path(base, U1, path=_pos(((0, 0), (1, 0)))).slip_runs
    assert run.fail_stop == (2, 0) and run.stop_trap and run.stop_surface is None
    fire = preview_path(
        _battle(_ROW, ice=[(0, 1)], surfaces=[(0, 2, "fire")]), U1, path=_pos(((0, 0), (0, 1)))
    )
    assert [(r.fail_stop, r.stop_trap, r.stop_surface) for r in fire.slip_runs] == [
        ((0, 2), False, Surface.FIRE)
    ]
