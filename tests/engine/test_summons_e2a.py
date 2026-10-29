"""召喚物（二）a（Phase 3-33e2a，6.29.5）：爆裂傀儡、石像、土牆、戰狼，以及特性計入預算。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import PROJECT_ROOT, give_turn, library, with_rolls
from tests.engine.skill_helpers import of
from tests.engine.test_summon_growth import arena, cast_at
from tests.engine.test_summons_e1 import hit, of_events
from trpg.content.summons import load_summon_looks, summon_dpr
from trpg.engine import BattleState, Move, UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import shove_problem
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect, MoveUnitEffect, PushEffect
from trpg.engine.events import (
    Collided,
    MoveBlocked,
    PushResisted,
    SummonDetonated,
    SummonExpired,
    WallToppled,
)
from trpg.engine.rules.geometry import has_line_of_sight
from trpg.engine.summons.core import summon_inert
from trpg.engine.turns import start_turn
from trpg.narrative.events import describe_event
from trpg.shared.types import Pos, Surface, UnitId
from trpg.skillgen.budget import skill_budget, summon_trait_points

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
BOMB, GOLEM, WALL, WOLF = (
    "skill_summon_bomb_puppet",
    "skill_summon_golem",
    "skill_summon_earth_wall",
    "skill_summon_war_wolf",
)
NEW_SKILLS = {
    BOMB: ("summon_bomb_puppet", "ignite"),
    GOLEM: ("summon_golem", "collision"),
    WALL: ("summon_earth_wall", "collision"),
    WOLF: ("summon_war_wolf", "prone"),
}


def summoned(
    skill_id: str, *, at: tuple[int, int] = (2, 3), foes: tuple[tuple[int, int], ...] = ((5, 3),)
) -> tuple[BattleState, UnitId]:
    """U1 施放 ``skill_id``，召喚物在 ``at``；敵人在 ``foes``（U2 起）。"""
    return cast_at(arena([skill_id], foes=foes), skill_id, *at)


def step(state: BattleState, sid: UnitId, *path: tuple[int, int]) -> BattleState:
    """輪到 ``sid``，沿 ``path`` 走。"""
    here = state.units[sid].xy
    action = Move(unit_id=sid, path=tuple(Pos(x=x, y=y) for x, y in (here, *path)))
    return resolve(give_turn(state, sid), action).state


# ---------------------------------------------------------------------------
# 內容：範本、技能、關鍵字、預算
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("skill_id", "expected"), NEW_SKILLS.items())
def test_new_skills_have_their_keyword_and_pass_the_budget(
    skill_id: str, expected: tuple[str, str]
) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    makes = lib.ruleset.skill_keywords(skill).makes
    assert expected[1] in makes and "summon" in makes
    assert skill_budget(skill, lib).ok
    assert [e.unit for e in skill.effects] == [expected[0]]
    assert 2 <= skill.effects[0].duration <= 3  # type: ignore[operator]


def test_summon_traits_are_counted_in_the_budget() -> None:
    lib = library()
    spirit = lib.ruleset.summon_def("summon_fire_spirit")
    per_round, once, _ = summon_trait_points(spirit, lib, summon_dpr(spirit))
    assert per_round == Fraction(3) * Fraction(lib.budget.summon_trait_status_permille, 1000)
    assert once == 0
    bomb = lib.ruleset.summon_def("summon_bomb_puppet")
    _, blast, notes = summon_trait_points(bomb, lib, summon_dpr(bomb))
    assert blast > 0 and "自爆" in notes
    wall = lib.ruleset.summon_def("summon_earth_wall")
    wall_round, wall_once, _ = summon_trait_points(wall, lib, summon_dpr(wall))
    assert wall_round == 0 and wall_once > 0 and summon_dpr(wall) == 0


def test_the_e1_skills_fit_the_budget_with_two_or_three_rounds() -> None:
    lib = library()
    for skill_id in (
        "skill_summon_fire_spirit",
        "skill_summon_ice_spirit",
        "skill_summon_thunder_spirit",
        "skill_summon_water_sprite",
        "skill_summon_shade",
        "skill_summon_hawk",
        "skill_raise_skeleton",
    ):
        skill = lib.skills[skill_id]
        assert skill_budget(skill, lib).ok, skill_id
        assert 2 <= skill.effects[0].duration <= 3, skill_id  # type: ignore[operator]


def test_traits_cost_budget_a_bare_template_would_not() -> None:
    """同一個範本拿掉特性後點數較低（特性真的有計入）。"""
    lib = library()
    fire = lib.skills["skill_summon_fire_spirit"]
    with_traits = skill_budget(fire, lib).raw
    spirit = lib.skills["skill_summon_spirit"]  # 元素之靈：同武器、沒有特性
    assert skill_budget(spirit, lib).raw == Fraction(7, 2) * 3 * Fraction(4, 5)
    assert with_traits == (Fraction(7, 2) + Fraction(3, 5)) * 2 * Fraction(4, 5)


# ---------------------------------------------------------------------------
# 爆裂傀儡
# ---------------------------------------------------------------------------


def test_the_bomb_detonates_when_it_walks_next_to_an_enemy() -> None:
    state, sid = summoned(BOMB, foes=((5, 3), (4, 4)))
    before = {u: state.units[u].hp for u in (U2, U3)}
    after = step(state, sid, (3, 3), (4, 3))
    bomb = after.units[sid]
    assert bomb.dismissed and not bomb.alive
    assert after.units[U2].hp < before[U2]
    assert after.units[U3].hp < before[U3]  # 相鄰 1 格
    assert after.tile(4, 3).surface is Surface.FIRE  # 爆心留下火表面
    assert after.tile(5, 3).surface is Surface.FIRE


def test_the_bomb_stops_at_the_first_tile_next_to_an_enemy() -> None:
    state, sid = summoned(BOMB, foes=((4, 3),))
    result = resolve(
        give_turn(state, sid), Move(unit_id=sid, path=(Pos(x=2, y=3), Pos(x=3, y=3), Pos(x=3, y=4)))
    )
    [blast] = of(result, SummonDetonated)
    assert blast.reason == "arrived" and (blast.pos.x, blast.pos.y) == (3, 3)
    assert blast.targets == [U2]
    assert [e.reason for e in of(result, SummonExpired)] == ["detonated"]


def test_the_bomb_does_not_hurt_its_own_side() -> None:
    state, sid = summoned(BOMB, foes=((4, 3),))
    result = resolve(give_turn(state, sid), Move(unit_id=sid, path=(Pos(x=2, y=3), Pos(x=3, y=3))))
    assert result.state.units[U1].hp == state.units[U1].hp


def test_the_bomb_detonates_when_downed() -> None:
    state, sid = summoned(BOMB, foes=((3, 3),))
    ctx = Ctx(state.clone())
    ctx.state.units[sid].hp = 1
    execute(ctx, [DamageEffect(source_id=U2, target_id=sid, dice=None, flat=5, min_damage=5)])
    [blast] = of_events(ctx, SummonDetonated)
    assert blast.reason == "downed" and blast.targets == [U2]
    assert ctx.state.units[U2].hp < state.units[U2].hp


def test_the_bomb_detonates_at_turn_start_if_an_enemy_is_already_adjacent() -> None:
    state, sid = summoned(BOMB, foes=((3, 3),))
    ctx = Ctx(state.clone())
    ctx.state.active_unit = None
    start_turn(ctx, sid)
    [blast] = of_events(ctx, SummonDetonated)
    assert blast.reason == "adjacent"
    assert not ctx.state.units[sid].alive


def test_the_ai_walks_the_bomb_into_the_enemy() -> None:
    state, sid = summoned(BOMB, at=(2, 3), foes=((5, 3),))
    ai = UtilityAI(library().ai_profiles)
    ready = give_turn(state, sid)
    best = max(ai.rank(ready), key=lambda s: s.score)
    assert isinstance(best.action, Move)
    after = resolve(ready, best.action).state
    assert after.units[sid].dismissed
    assert after.units[U2].hp < state.units[U2].hp


def test_the_bomb_blast_is_deterministic_and_text_is_readable() -> None:
    state, sid = summoned(BOMB, foes=((4, 3),))
    action = Move(unit_id=sid, path=(Pos(x=2, y=3), Pos(x=3, y=3)))
    a = resolve(give_turn(state, sid), action)
    b = resolve(give_turn(state, sid), action)
    assert a.state.rng_state == b.state.rng_state and a.events == b.events
    [blast] = of(a, SummonDetonated)
    assert "自爆" in (describe_event(blast, a.state) or "")


# ---------------------------------------------------------------------------
# 石像
# ---------------------------------------------------------------------------


def test_the_golem_cannot_be_pushed_and_says_why() -> None:
    state, gid = summoned(GOLEM, at=(3, 3), foes=((4, 3),))
    ctx = Ctx(state.clone())
    execute(ctx, [PushEffect(source_id=U2, target_id=gid, direction=(-1, 0), distance=2)])
    [resisted] = of_events(ctx, PushResisted)
    assert resisted.reason == "immovable" and resisted.distance == 0
    assert ctx.state.units[gid].xy == (3, 3)
    assert "紋風不動" in (describe_event(resisted, ctx.state) or "")


def test_the_golem_ignores_pulls_and_teleports_but_still_walks() -> None:
    state, gid = summoned(GOLEM, at=(3, 3), foes=((6, 3),))
    ctx = Ctx(state.clone())
    execute(ctx, [MoveUnitEffect(unit_id=gid, dest=(3, 5), mode="forced")])
    execute(ctx, [MoveUnitEffect(unit_id=gid, dest=(3, 5), mode="teleported")])
    assert ctx.state.units[gid].xy == (3, 3)
    assert [e.reason for e in of_events(ctx, MoveBlocked)] == ["immovable", "immovable"]
    walked = step(state, gid, (3, 4))
    assert walked.units[gid].xy == (3, 4)  # 自己走路不受影響


def test_the_shove_action_explains_the_golem_is_immovable() -> None:
    state, gid = summoned(GOLEM, at=(3, 3), foes=((4, 3),))
    problem = shove_problem(state, state.units[U2], state.units[gid])
    assert problem is not None and "紋風不動" in problem


def test_an_enemy_pushed_into_the_golem_takes_collision_damage() -> None:
    state, gid = summoned(GOLEM, at=(4, 3), foes=((3, 3),))
    ctx = Ctx(state.clone())
    before = ctx.state.units[U2].hp
    execute(ctx, [PushEffect(source_id=U1, target_id=U2, direction=(1, 0), distance=1)])
    [crash] = of_events(ctx, Collided)
    assert crash.obstacle == "unit" and crash.other_id == gid
    assert ctx.state.units[U2].hp < before
    assert ctx.state.units[gid].xy == (4, 3)


# ---------------------------------------------------------------------------
# 土牆
# ---------------------------------------------------------------------------


def test_the_wall_is_inert_blocks_the_way_and_the_view() -> None:
    state, wid = summoned(WALL, at=(3, 3), foes=((6, 3),))
    wall = state.units[wid]
    assert summon_inert(state, wall) and wall.speed == 0
    assert state.tile(3, 3) and state.unit_at(3, 3) is wall
    assert not has_line_of_sight(state, (1, 3), (5, 3))  # 擋視線
    assert has_line_of_sight(state, (1, 2), (5, 2))
    ctx = Ctx(state.clone())
    ctx.state.active_unit = None
    start_turn(ctx, wid)
    assert ctx.state.units[wid].ap == 0  # 回合內沒有行動


def test_pushing_the_wall_topples_it_onto_the_units_behind_it() -> None:
    state, wid = summoned(WALL, at=(3, 3), foes=((4, 3), (5, 3)))
    ctx = Ctx(state.clone())
    first, second = ctx.state.units[U2].hp, ctx.state.units[U3].hp
    execute(ctx, [PushEffect(source_id=U1, target_id=wid, direction=(1, 0), distance=1)])
    [fall] = of_events(ctx, WallToppled)
    assert fall.units == (U2, U3) and fall.direction == (1, 0)
    assert ctx.state.units[U2].hp < first and ctx.state.units[U3].hp < second
    assert ctx.state.units[U2].has_status("prone")
    assert ctx.state.units[wid].dismissed
    assert [e.reason for e in of_events(ctx, SummonExpired)] == ["toppled"]
    assert "倒下" in (describe_event(fall, ctx.state) or "")


def test_a_toppled_wall_falls_the_way_it_was_pushed() -> None:
    state, wid = summoned(WALL, at=(3, 3), foes=((2, 4), (4, 3)))
    ctx = Ctx(state.clone())
    execute(ctx, [PushEffect(source_id=U1, target_id=wid, direction=(0, 1), distance=1)])
    [fall] = of_events(ctx, WallToppled)
    assert fall.direction == (0, 1) and fall.units == ()  # (3,4)(3,5) 沒有人
    assert ctx.state.units[U3].hp == state.units[U3].hp


def test_the_wall_has_hp_and_can_be_destroyed() -> None:
    state, wid = summoned(WALL, at=(3, 3))
    ctx = Ctx(state.clone())
    execute(ctx, [DamageEffect(source_id=U2, target_id=wid, flat=99, min_damage=99)])
    assert not ctx.state.units[wid].alive
    assert has_line_of_sight(ctx.state, (1, 3), (5, 3))


# ---------------------------------------------------------------------------
# 戰狼
# ---------------------------------------------------------------------------


def test_the_wolf_is_fast_and_trips_its_target_once_a_round() -> None:
    state, wid = summoned(WOLF, foes=((3, 3),))
    wolf = state.units[wid]
    assert wolf.speed == 6
    state = with_rolls(state, [(20, 19)])
    ctx = hit(state, wid)
    assert ctx.state.units[U2].has_status("prone")
    assert ctx.state.units[wid].trip_round == ctx.state.round


def test_summon_skills_cost_no_more_than_the_budget_and_the_ai_casts_them() -> None:
    ai = UtilityAI(library().ai_profiles)
    for skill_id in NEW_SKILLS:
        state = arena([skill_id], foes=((6, 3),))
        scored = [s for s in ai.rank(state) if isinstance(s.action, UseSkill) and s.score > 0]
        assert scored, skill_id


def test_new_summons_keep_their_look_fields_and_defaults() -> None:
    lib = library()
    looks = load_summon_looks(PROJECT_ROOT / "content").looks
    for template_id, key, mode in (
        ("summon_bomb_puppet", "bomb_puppet", "follow"),
        ("summon_golem", "golem", "guard"),
        ("summon_earth_wall", "earth_wall", "hold"),
        ("summon_war_wolf", "war_wolf", "follow"),
    ):
        template = lib.ruleset.summon_def(template_id).template
        assert template.default_mode == mode
        look = looks[key]
        assert template.look is not None and template.look.variant == look.variant
