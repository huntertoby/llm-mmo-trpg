"""持續區域的 AI（Phase 3D-5）：選位置的估計、收益、避開敵方的有害區域，以及整場戰鬥真的會用。"""

from __future__ import annotations

from functools import cache
from typing import Any

from tests.engine.helpers import library
from tests.engine.test_zones import MOVING, SID, TILE, U1, U2, arena, cast, of
from trpg.engine import UseSkill, preview
from trpg.engine.ai.utility import UtilityAI, position_value
from trpg.engine.ai.zone import hostile_zone_at, zone_estimate, zone_gains
from trpg.engine.events import ZoneCreated, ZoneTriggered
from trpg.engine.skills import shapes
from trpg.shared.types import Pos, Team


def test_the_estimate_counts_enemies_in_the_zone_and_on_its_path() -> None:
    state = arena(MOVING, foes=((2, 3), (5, 3)))
    unit = state.units[U1]
    east = shapes.DIRECTIONS["east"]
    tiles = ((1, 3), (2, 3))
    both = zone_estimate(state, unit, MOVING, tiles=tiles, direction=east, origin=(0, 3))
    north = zone_estimate(
        state, unit, MOVING, tiles=((0, 2), (0, 1)), direction=(0, -1), origin=(0, 3)
    )
    assert both == 5  # 格內 1 名 ×3 ＋ 路徑上 1 名 ×2（原點就是施放者所在格）
    assert north is None  # 沒有敵人會碰到


def test_the_gains_value_future_triggers_of_a_new_zone() -> None:
    state = arena(MOVING, foes=((4, 3),))
    action = UseSkill(unit_id=U1, skill_id=SID, direction="east")
    p = preview(state, action)
    profile = library().ai_profiles.by_id()["archer"]
    assert zone_gains(state, state.units[U1], p.min_events, profile) > 0
    away = preview(state, UseSkill(unit_id=U1, skill_id=SID, direction="north"))
    assert zone_gains(state, state.units[U1], away.min_events, profile) == 0


def test_the_ai_treats_an_enemy_harmful_zone_as_a_hazard() -> None:
    state = cast(arena(TILE, foes=((5, 5),)), target_pos=Pos(x=3, y=3)).state
    assert hostile_zone_at(state, (3, 3), Team.ENEMY)
    assert not hostile_zone_at(state, (3, 3), Team.ALLY)  # 自己陣營的區域（affects: enemies）
    assert not hostile_zone_at(state, (5, 5), Team.ENEMY)
    weights = library().ai_profiles.by_id()["brute"].weights
    inside = state.clone()
    inside.units[U2].pos = Pos(x=3, y=3)
    no_zone = inside.clone()
    no_zone.zones = []
    gap = position_value(no_zone, U2, weights) - position_value(inside, U2, weights)
    assert gap == weights.hazard  # 同一格：有敵方有害區域時扣 hazard


@cache
def _run(build: str, map_id: str, seed: int) -> tuple[Any, Any]:
    from trpg.engine.runner import run_battle  # noqa: PLC0415
    from trpg.engine.setup import build_setup  # noqa: PLC0415
    from trpg.sim.lineup import build_allies, default_lineup  # noqa: PLC0415

    lib, allies = build_allies(library(), [build])
    _, enemies = default_lineup(lib, map_id)
    setup = build_setup(lib, map_id, allies, enemies, max_rounds=30)
    return setup, run_battle(setup, seed, UtilityAI(lib.ai_profiles))


def test_the_ai_casts_the_fire_wall_and_it_moves_and_burns_enemies() -> None:
    _, run = _run("build_summoner", "swamp", 0)
    created = [e for e in of(run.events, ZoneCreated) if e.skill_id == "skill_fire_wall"]
    assert created and created[0].anchor == "moving"
    hits = [e for e in of(run.events, ZoneTriggered) if e.skill_id == "skill_fire_wall"]
    assert hits


def test_the_ai_casts_the_war_hymn_and_allies_walk_into_it() -> None:
    _, run = _run("build_support", "swamp", 1)
    hymn = [e for e in of(run.events, ZoneTriggered) if e.skill_id == "skill_war_hymn"]
    assert {e.cause for e in hymn} == {"enter", "turn_start"}
    assert len({e.unit_id for e in hymn}) >= 2


def test_a_zone_battle_replays_exactly() -> None:
    from trpg.engine import state_to_json  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run("build_summoner", "swamp", 0)
    again = replay(setup, 0, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
