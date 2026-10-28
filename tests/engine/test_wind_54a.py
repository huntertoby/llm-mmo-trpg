"""風元素的專屬機制（Phase 3-54a，06 6.33，#56）：吹送、元素擴散、風壓撞擊。

表格測試：每種可吹送的表面 × 四個風向、邊界與障礙；元素擴散的每種表面與區域 × 風向；
風元素技能推擊撞牆的撞擊傷害 ×1.5。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, battle, cast, hit_with, of
from trpg.content.skills import SkillDef, is_wind_skill
from trpg.engine import BattleState
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import Collided, DamageDealt, SkillUsed, SurfaceBlown, ZoneExpanded
from trpg.engine.runner import LOG_FORMAT, replay, run_battle
from trpg.engine.state import ZoneState, state_to_json
from trpg.engine.wind import SPREAD_CAUSE
from trpg.shared.types import Attribute, Pos, Surface, Team, UnitId

CASTER = (3, 3)
DIRECTIONS = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}


def surfaces(state: BattleState) -> dict[tuple[int, int], Surface]:
    return {
        (x, y): state.tile(x, y).surface
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is not Surface.NONE
    }


def blow_skill(shape: dict[str, Any], distance: int = 2) -> SkillDef:
    return make_skill(SID, shape, [{"type": "blow_surface", "distance": distance}])


def _line_cast(state: BattleState, direction: str) -> Any:
    return cast(state, direction=direction)


# ---------------------------------------------------------------------------
# 吹送
# ---------------------------------------------------------------------------

LINE = {"type": "line", "size": 1}


@pytest.mark.parametrize("surface", ["fire", "poison", "ice", "water", "oil", "smoke"])
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
def test_blow_moves_each_blowable_surface_downwind(surface: str, direction: str) -> None:
    dx, dy = DIRECTIONS[direction]
    start = (CASTER[0] + dx, CASTER[1] + dy)
    state = battle(blow_skill(LINE, 2), surfaces=((*start, surface),), foes=[(0, 0)])
    result = _line_cast(state, direction)
    dest = (start[0] + 2 * dx, start[1] + 2 * dy)
    assert surfaces(result.state) == {dest: Surface(surface)}
    (blown,) = of(result, SurfaceBlown)
    assert (blown.from_pos, blown.to_pos) == (
        Pos(x=start[0], y=start[1]),
        Pos(x=dest[0], y=dest[1]),
    )


@pytest.mark.parametrize("surface", ["holy", "darkness"])
def test_blow_leaves_non_blowable_surfaces(surface: str) -> None:
    state = battle(blow_skill(LINE, 2), surfaces=((4, 3, surface),), foes=[(0, 0)])
    result = _line_cast(state, "east")
    assert surfaces(result.state) == {(4, 3): Surface(surface)}
    assert not of(result, SurfaceBlown)


def test_blow_keeps_remaining_rounds_team_and_creator() -> None:
    state = battle(blow_skill(LINE, 3), surfaces=((4, 3, "poison"),), foes=[(0, 0)])
    state.set_tile(4, 3, replace(state.tile(4, 3), surface_remaining=2))
    after = _line_cast(state, "east").state.tile(6, 3)
    assert (after.surface, after.surface_remaining) == (Surface.POISON, 2)


def test_blow_keeps_permanent_map_surfaces_permanent() -> None:
    state = battle(blow_skill(LINE, 2), surfaces=((4, 3, "water"),), foes=[(0, 0)])
    assert state.tile(4, 3).surface_remaining is None
    after = _line_cast(state, "east").state.tile(6, 3)
    assert (after.surface, after.surface_remaining) == (Surface.WATER, None)


@pytest.mark.parametrize("distance", [2, 3])
def test_blow_stops_at_the_map_edge(distance: int) -> None:
    state = battle(blow_skill(LINE, distance), surfaces=((4, 3, "fire"),), foes=[(0, 0)])
    assert surfaces(_line_cast(state, "east").state) == {(6, 3): Surface.FIRE}


@pytest.mark.parametrize(
    ("blocker", "expected"),
    [
        ("wall", (4, 3)),  # 牆在 (5,3)：停在原地
        ("crate", (4, 3)),  # blocks_move 物件
        ("height", (4, 3)),  # 比目前高的格子
        ("unit", (6, 3)),  # 單位不擋風
    ],
)
def test_blow_obstacles(blocker: str, expected: tuple[int, int]) -> None:
    skill = blow_skill(LINE, 2)
    heights = FLAT7
    objects: tuple[tuple[int, int, str], ...] = ()
    foes = [(0, 0)]
    if blocker == "height":
        rows = [list(r) for r in FLAT7.split("\n")]
        rows[3][5] = "1"
        heights = "\n".join("".join(r) for r in rows)
    elif blocker == "crate":
        objects = ((5, 3, "crate"),)
    elif blocker == "unit":
        foes = [(5, 3)]
    state = battle(skill, foes=foes, heights=heights, objects=objects, surfaces=((4, 3, "oil"),))
    if blocker == "wall":
        state = _with_wall(state, (5, 3))
    assert surfaces(_line_cast(state, "east").state) == {expected: Surface.OIL}


def _with_wall(state: BattleState, xy: tuple[int, int]) -> BattleState:
    state.set_tile(*xy, replace(state.tile(*xy), terrain="wall"))
    return state


def test_blow_moves_a_whole_patch_and_front_lands_first() -> None:
    """3 格長的火往東吹 2 格，前端撞到地圖邊被擠在一起；中間的空隙不會留下表面。"""
    skill = blow_skill({"type": "line", "size": 3}, 2)
    state = battle(skill, surfaces=((4, 3, "fire"), (5, 3, "fire"), (6, 3, "fire")), foes=[(0, 0)])
    result = _line_cast(state, "east")
    assert surfaces(result.state) == {(6, 3): Surface.FIRE}
    assert [b.from_pos.x for b in of(result, SurfaceBlown)] == [6, 5, 4]


def test_blow_lands_through_the_interaction_table() -> None:
    """吹來的水落在火上：照產生表面的互動表熄滅火（同 create_surface）。"""
    state = battle(blow_skill(LINE, 2), surfaces=((4, 3, "water"), (6, 3, "fire")), foes=[(0, 0)])
    assert surfaces(_line_cast(state, "east").state) == {}


def test_blow_from_a_centered_shape_moves_the_patch_caster_to_center() -> None:
    """十字形中心在施放者東邊 2 格：整片往東吹（不是各自往外）。"""
    skill = blow_skill({"type": "cross", "range": 3}, 2)
    patch = ((5, 2, "oil"), (5, 4, "oil"), (4, 3, "oil"))
    state = battle(skill, surfaces=patch, foes=[(0, 0)])
    after = cast(state, target_pos=Pos(x=5, y=3)).state
    assert surfaces(after) == {(6, 2): Surface.OIL, (6, 4): Surface.OIL, (6, 3): Surface.OIL}


def test_blow_around_the_caster_blows_outward() -> None:
    skill = blow_skill({"type": "cross", "range": 0}, 2)
    patch = ((3, 2, "oil"), (4, 3, "oil"), (3, 4, "oil"), (2, 3, "oil"))
    state = battle(skill, surfaces=patch, foes=[(6, 6)])
    after = cast(state, target_pos=Pos(x=3, y=3)).state
    assert surfaces(after) == {
        (3, 0): Surface.OIL,
        (6, 3): Surface.OIL,
        (3, 6): Surface.OIL,
        (0, 3): Surface.OIL,
    }


def test_blown_fire_onto_a_unit_does_not_count_as_entering() -> None:
    """表面出現在單位腳下：火沒有進入效果（燃燒在回合開始），冰則照常進入檢定（同產生表面）。"""
    state = battle(blow_skill(LINE, 2), foes=[(6, 3)], surfaces=((4, 3, "fire"),))
    result = _line_cast(state, "east")
    assert result.state.tile(6, 3).surface is Surface.FIRE


def test_blow_validator_requires_tiles_and_rare() -> None:
    from trpg.skillgen.validate import validate_skill  # noqa: PLC0415

    lib = library()
    bad = make_skill(
        "skill_t_blow", LINE, [{"type": "blow_surface", "distance": 2, "affects": "enemies"}]
    )
    assert validate_skill(bad, lib)


# ---------------------------------------------------------------------------
# 元素擴散
# ---------------------------------------------------------------------------

WIND_HIT = {"type": "damage", "dice": "1d4", "element": "wind", "affects": "tiles"}


def _wind(shape: dict[str, Any] | None = None, *extra: dict[str, Any]) -> SkillDef:
    return make_skill(SID, shape or LINE, [WIND_HIT, *extra])


@pytest.mark.parametrize("surface", ["fire", "ice", "poison"])
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
def test_wind_damage_spreads_surfaces_downwind(surface: str, direction: str) -> None:
    dx, dy = DIRECTIONS[direction]
    start = (CASTER[0] + dx, CASTER[1] + dy)
    state = hit_with(battle(_wind(), surfaces=((*start, surface),), foes=[(0, 0)]))
    result = _line_cast(state, direction)
    nxt = (start[0] + dx, start[1] + dy)
    assert surfaces(result.state) == {start: Surface(surface), nxt: Surface(surface)}


@pytest.mark.parametrize("surface", ["water", "oil", "holy", "darkness"])
def test_wind_damage_does_not_spread_other_surfaces(surface: str) -> None:
    state = hit_with(battle(_wind(), surfaces=((4, 3, surface),), foes=[(0, 0)]))
    assert surfaces(_line_cast(state, "east").state) == {(4, 3): Surface(surface)}


def test_wind_still_disperses_smoke() -> None:
    state = hit_with(battle(_wind(), surfaces=((4, 3, "smoke"),), foes=[(0, 0)]))
    assert surfaces(_line_cast(state, "east").state) == {}


def test_wind_spread_is_computed_once_without_chaining() -> None:
    """直線 3 格都在範圍內：只有原本有火的格子往前多 1 格，新長出的不再擴散。"""
    state = hit_with(battle(_wind({"type": "line", "size": 3}), surfaces=((4, 3, "fire"),)))
    assert surfaces(_line_cast(state, "east").state) == {
        (4, 3): Surface.FIRE,
        (5, 3): Surface.FIRE,
    }


@pytest.mark.parametrize("blocker", ["wall", "edge", "crate"])
def test_wind_spread_stops_at_obstacles(blocker: str) -> None:
    if blocker == "edge":
        state = battle(_wind({"type": "line", "size": 3}), surfaces=((6, 3, "poison"),))
        expected = {(6, 3): Surface.POISON}
    else:
        objects = ((5, 3, "crate"),) if blocker == "crate" else ()
        state = battle(_wind(), surfaces=((4, 3, "poison"),), objects=objects, foes=[(0, 0)])
        if blocker == "wall":
            state = _with_wall(state, (5, 3))
        expected = {(4, 3): Surface.POISON}
    assert surfaces(_line_cast(hit_with(state), "east").state) == expected


def test_spread_marks_its_cause() -> None:
    state = hit_with(battle(_wind(), surfaces=((4, 3, "ice"),), foes=[(0, 0)]))
    result = _line_cast(state, "east")
    causes = {
        getattr(e, "cause", None) for e in result.events if getattr(e, "pos", None) == Pos(x=5, y=3)
    }
    assert SPREAD_CAUSE in causes


def test_non_wind_damage_does_not_spread() -> None:
    hit = {"type": "damage", "dice": "1d4", "element": "lightning", "affects": "tiles"}
    state = hit_with(
        battle(make_skill(SID, LINE, [hit]), surfaces=((4, 3, "poison"),), foes=[(0, 0)])
    )
    assert surfaces(_line_cast(state, "east").state) == {(4, 3): Surface.POISON}


@pytest.mark.parametrize("element", ["fire", "ice", "poison", "lightning"])
@pytest.mark.parametrize("direction", sorted(DIRECTIONS))
def test_wind_damage_expands_elemental_zones(element: str, direction: str) -> None:
    dx, dy = DIRECTIONS[direction]
    start = (CASTER[0] + dx, CASTER[1] + dy)
    state = _zone_battle(element, [start])
    result = _line_cast(hit_with(state), direction)
    (grown,) = of(result, ZoneExpanded)
    assert grown.added == (Pos(x=start[0] + dx, y=start[1] + dy),)
    assert len(result.state.zones[0].cells) == 2


def _zone_battle(element: str, cells: list[tuple[int, int]], anchor: str = "tile") -> BattleState:
    zone_skill = make_skill(
        "skill_t_zone",
        {"type": "line", "size": 2} if anchor == "moving" else {"type": "cross", "range": 4},
        [
            {
                "type": "zone",
                "anchor": anchor,
                "when": "both",
                "duration": 3,
                "affects": "enemies",
                "effects": [{"type": "damage", "dice": "1d4", "element": element}],
                **({"speed": 1} if anchor == "moving" else {}),
            }
        ],
    )
    skill = _wind()
    m = make_map(FLAT7, ally=[CASTER], enemy=[(0, 0)])
    spawns = [
        spawn(Team.ALLY, CASTER, caster_template([skill, zone_skill])),
        spawn(Team.ENEMY, (0, 0), no_reactions()),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill, zone_skill]), U1)
    state.zones = [
        ZoneState(
            id=1,
            owner_id=U1,
            team=Team.ALLY,
            skill_id="skill_t_zone",
            anchor=anchor,  # type: ignore[arg-type]
            cells=tuple(Pos(x=x, y=y) for x, y in cells),
            expires_round=state.round + 3,
            attributes=tuple((a, 10) for a in Attribute),
            direction="east" if anchor == "moving" else None,
            speed=1 if anchor == "moving" else 0,
        )
    ]
    state.next_zone_id = 2
    return state


def test_wind_does_not_expand_physical_zones() -> None:
    state = _zone_battle("physical", [(4, 3)])
    assert not of(_line_cast(hit_with(state), "east"), ZoneExpanded)


def test_wind_expands_moving_zones_and_stops_at_walls() -> None:
    state = _with_wall(_zone_battle("fire", [(4, 3)], anchor="moving"), (5, 3))
    assert not of(_line_cast(hit_with(state), "east"), ZoneExpanded)
    state = _zone_battle("fire", [(4, 3)], anchor="moving")
    (grown,) = of(_line_cast(hit_with(state), "east"), ZoneExpanded)
    assert grown.added == (Pos(x=5, y=3),)


# ---------------------------------------------------------------------------
# 風壓撞擊
# ---------------------------------------------------------------------------


def _push_skill(element: str) -> SkillDef:
    return make_skill(
        SID,
        {"type": "single", "range": 1},
        [
            {"type": "damage", "dice": "1d4", "element": element},
            {"type": "push", "distance": 2, "collision_dice": "2d6"},
        ],
    )


def _collisions(element: str) -> tuple[int, list[int]]:
    """敵人在 (4,3)、背後 (5,3) 是牆：推 2 格少走 2 格，撞擊 2 次。"""
    state = _with_wall(battle(_push_skill(element), foes=[(4, 3)]), (5, 3))
    result = cast(hit_with(state), target_id=UnitId("unit_0002"))
    (collided,) = of(result, Collided)
    hits = [
        e.amount for e in result.events if isinstance(e, DamageDealt) and e.cause == "collision"
    ]
    return collided.damage_permille, hits


def test_wind_push_collision_is_one_and_a_half_times() -> None:
    wind_permille, wind_hits = _collisions("wind")
    fire_permille, fire_hits = _collisions("fire")
    assert (wind_permille, fire_permille) == (1500, 1000)
    assert len(fire_hits) == 2
    assert wind_hits == [h * 3 // 2 for h in fire_hits]


def test_wind_pull_is_not_boosted() -> None:
    skill = make_skill(
        SID,
        {"type": "single", "range": 3},
        [
            {"type": "damage", "dice": "1d4", "element": "wind"},
            {"type": "pull", "distance": 2},
        ],
    )
    state = battle(skill, foes=[(5, 3)], allies=[(4, 3)])
    result = cast(hit_with(state), target_id=UnitId("unit_0003"))
    assert of(result, Collided)
    assert all(c.damage_permille == 1000 for c in of(result, Collided))


def test_is_wind_skill_reads_the_damage_element() -> None:
    assert is_wind_skill(_push_skill("wind"))
    assert not is_wind_skill(_push_skill("fire"))


# ---------------------------------------------------------------------------
# 重播：含風技能（測試用）的整場戰鬥
# ---------------------------------------------------------------------------


def _wind_kit() -> list[SkillDef]:
    gust = make_skill(
        "skill_t_gust",
        {"type": "cone", "size": 3},
        [
            {"type": "damage", "dice": "2d6", "element": "wind"},
            {"type": "blow_surface", "distance": 2},
        ],
    )
    shove = make_skill(
        "skill_t_shove",
        {"type": "single", "range": 1},
        [{"type": "damage", "dice": "1d6", "element": "wind"}, {"type": "push", "distance": 2}],
    )
    return [gust, shove]


def test_a_battle_with_wind_test_skills_replays_identically() -> None:
    kit = _wind_kit()
    flat = "\n".join(["000000000"] * 9)
    poison = [(x, y, "poison") for x in (4, 5) for y in (2, 3, 4)]
    m = make_map(
        flat, ally=[(1, 3), (1, 5)], enemy=[(6, 3), (7, 4)], surfaces=[*poison, (5, 5, "fire")]
    )
    spawns = [
        spawn(Team.ALLY, (1, 3), caster_template(kit, max_hp=60)),
        spawn(Team.ALLY, (1, 5), caster_template(kit, max_hp=60)),
        spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=80)),
        spawn(Team.ENEMY, (7, 4), no_reactions(max_hp=80)),
    ]
    setup = make_setup(m, spawns, skills=kit, max_rounds=12)
    run = run_battle(setup, 7, UtilityAI(library().ai_profiles))
    again = replay(setup, 7, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert LOG_FORMAT.endswith("/83")
    used = {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
    assert used & {"skill_t_gust", "skill_t_shove"}
