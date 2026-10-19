"""持續區域（Phase 3D-5，``docs/phases/Phase3D計畫.md`` 5）：三種錨點、進入與回合開始的結算、
移動、留下表面、到期、施放者倒下、上限、環境預告、既有觸發、序列化與重播。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.test_passive_triggers import passive
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.engine import (
    BattleState,
    EndTurn,
    Move,
    ResolveResult,
    UseSkill,
    preview,
    project_for,
    resolve,
    state_from_json,
    state_to_json,
)
from trpg.engine.context import Ctx
from trpg.engine.environment import run_environment, telegraph
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    SkillTriggered,
    StatusApplied,
    SurfaceChanged,
    TriggerLimitReached,
    ZoneCreated,
    ZoneExpired,
    ZoneMoved,
    ZoneTriggered,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.turns import start_turn
from trpg.engine.zones import next_zone_cells, zone_cells
from trpg.shared.types import Pos, Surface, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
SID = "skill_t_zone"
FLAT = "\n".join(["0000000"] * 7)
FIRE = {"type": "damage", "dice": "1d4", "element": "fire"}
BUFF = {"type": "apply_status", "status": "empowered", "duration": 1}


def zone_skill(
    shape: dict[str, Any],
    *,
    anchor: str = "tile",
    when: str = "both",
    duration: int = 2,
    affects: str = "enemies",
    effects: Sequence[dict[str, Any]] = (FIRE,),
    **extra: Any,
) -> SkillDef:
    effect: dict[str, Any] = {
        "type": "zone",
        "anchor": anchor,
        "when": when,
        "duration": duration,
        "affects": affects,
        "effects": list(effects),
        **extra,
    }
    return make_skill(SID, shape, [effect])


TILE = zone_skill({"type": "cross", "range": 4})
CASTER = zone_skill(
    {"type": "allies_in_radius", "radius": 1}, anchor="caster", affects="allies", effects=[BUFF]
)
MOVING = zone_skill({"type": "line", "size": 2}, anchor="moving", speed=1, duration=3)


def arena(
    skill: SkillDef = TILE,
    *,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    allies: Sequence[tuple[int, int]] = (),
    terrain: str | None = None,
    foe_skills: Sequence[SkillDef] = (),
    owner_skills: Sequence[SkillDef] = (),
    max_trigger_depth: int | None = None,
) -> BattleState:
    """U1 施放者（我方法師，(0, 3)）；之後依序是 ``foes``（敵人，不反應）、``allies``（友方）。"""
    m = make_map(FLAT, terrain, ally=[(0, 3), *allies], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([skill.id, *(s.id for s in owner_skills)]))]
    foe_ids = [s.id for s in foe_skills]
    for xy in foes:
        spawns.append(spawn(Team.ENEMY, xy, no_reactions(max_hp=200, skills=foe_ids)))
    for xy in allies:
        spawns.append(spawn(Team.ALLY, xy, no_reactions("hero_fighter", max_hp=200)))
    skills = [skill, *foe_skills, *owner_skills]
    core: dict[str, Any] = {}
    if max_trigger_depth is not None:
        core["max_trigger_depth"] = max_trigger_depth
    return give_turn(make_state(m, spawns, skills=skills, **core), U1)


def of[E: EventBase](events: Sequence[EventBase] | ResolveResult, kind: type[E]) -> list[E]:
    items = events.events if isinstance(events, ResolveResult) else events
    return [e for e in items if isinstance(e, kind)]


def cast(state: BattleState, **target: Any) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, **target))


def at(x: int, y: int) -> dict[str, Pos]:
    return {"target_pos": Pos(x=x, y=y)}


def walk(state: BattleState, unit: UnitId, *path: tuple[int, int]) -> ResolveResult:
    s = give_turn(state, unit)
    start = s.units[unit].pos
    return resolve(s, Move(unit_id=unit, path=(start, *(Pos(x=x, y=y) for x, y in path))))


def ctx_run(state: BattleState, fn: Any, *args: Any) -> tuple[BattleState, list[EventBase]]:
    ctx = Ctx(state.clone())
    fn(ctx, *args)
    return ctx.state, ctx.events


def triggers(events: Sequence[EventBase]) -> list[tuple[UnitId, str]]:
    return [(e.unit_id, e.cause) for e in of(events, ZoneTriggered)]


# ---------------------------------------------------------------------------
# 固定型：建立、進入、回合開始、到期
# ---------------------------------------------------------------------------


def test_a_tile_zone_covers_the_skill_area_and_hits_enemies_already_inside() -> None:
    result = cast(arena(foes=((3, 3), (6, 6))), **at(3, 3))
    [created] = of(result, ZoneCreated)
    assert created.anchor == "tile" and created.affects == "enemies" and created.when == "both"
    assert {(p.x, p.y) for p in created.cells} == {(3, 3), (3, 2), (4, 3), (3, 4), (2, 3)}
    assert created.expires_round == result.state.round + 2
    assert triggers(result.events) == [(U2, "enter")]
    [hit] = of(result, DamageDealt)
    assert hit.target_id == U2 and hit.source_id == U1
    assert of(result, ZoneTriggered)[0].trigger_depth == 1
    [zone] = result.state.zones
    assert zone.id == 1 and zone.owner_id == U1 and result.state.next_zone_id == 2


def test_walking_into_the_zone_triggers_once_and_moving_inside_does_not_retrigger() -> None:
    state = cast(arena(foes=((6, 3),)), **at(3, 3)).state
    result = walk(state, U2, (5, 3), (4, 3), (3, 3), (2, 3))
    assert triggers(result.events) == [(U2, "enter")]  # 進入 (4, 3)，之後在區域內移動不再結算
    out = walk(result.state, U2, (2, 2), (2, 1))  # 走出去
    assert triggers(out.events) == []
    back = walk(out.state, U2, (2, 2), (2, 3))  # 再走回來：新的進入
    assert triggers(back.events) == [(U2, "enter")]


def test_turn_start_inside_the_zone_triggers_and_the_enter_only_zone_does_not() -> None:
    for when, expected in (("turn_start", [(U2, "turn_start")]), ("enter", [])):
        skill = zone_skill({"type": "cross", "range": 4}, when=when)
        result = cast(arena(skill, foes=((3, 3),)), **at(3, 3))
        assert triggers(result.events) == ([(U2, "enter")] if when == "enter" else [])
        _, events = ctx_run(result.state, start_turn, U2)
        assert triggers(events) == expected


def test_a_zone_does_not_affect_the_wrong_side() -> None:
    result = cast(arena(foes=((6, 6),), allies=((3, 3),)), **at(3, 3))
    assert triggers(result.events) == []  # 友方站在敵方區域裡（affects: enemies）不受影響
    _, events = ctx_run(result.state, start_turn, U3)
    assert triggers(events) == []


def test_the_zone_expires_at_the_owners_turn_end_after_duration_rounds() -> None:
    state = cast(arena(), **at(3, 3)).state
    created = state.round
    for _ in range(2):  # 施放輪與下一輪的回合結束：還在
        assert state.zones
        state = give_turn(resolve(state, EndTurn(unit_id=U1)).state, U1)
        state.round += 1
    result = resolve(give_turn(state, U1), EndTurn(unit_id=U1))
    assert state.round == created + 2
    [expired] = of(result, ZoneExpired)
    assert expired.reason == "timeout" and not result.state.zones


# ---------------------------------------------------------------------------
# 跟隨型
# ---------------------------------------------------------------------------


def test_a_caster_zone_follows_the_caster_and_covers_allies_it_reaches() -> None:
    result = cast(arena(CASTER, allies=((3, 3),)))
    assert triggers(result.events) == [(U1, "enter")]  # 建立時施放者自己就在區域內
    state = result.state
    assert set(zone_cells(state, state.zones[0])) == {(0, 3), (1, 3), (0, 2), (0, 4)}
    moved = walk(state, U1, (1, 3), (2, 3))
    assert triggers(moved.events) == [(U3, "enter")]  # 區域跟著施放者移到隊友身上
    applied = of(moved, StatusApplied)
    assert [(e.target_id, e.status_id) for e in applied] == [(U3, "empowered")]
    assert set(zone_cells(moved.state, moved.state.zones[0])) == {
        (2, 3),
        (1, 3),
        (3, 3),
        (2, 2),
        (2, 4),
    }


def test_the_caster_never_enters_its_own_following_zone() -> None:
    state = cast(arena(CASTER)).state
    moved = walk(state, U1, (1, 3), (2, 3), (3, 3))
    assert triggers(moved.events) == []


def test_downing_the_caster_removes_a_following_zone_but_keeps_a_tile_zone() -> None:
    state = cast(arena(CASTER)).state
    state, events = ctx_run(state, lambda ctx: down_unit(ctx, ctx.state.units[U1]))
    assert [(e.reason, e.skill_id) for e in of(events, ZoneExpired)] == [("owner_gone", SID)]
    assert not state.zones
    tile_state = cast(arena(), **at(3, 3)).state
    tile_state, events = ctx_run(tile_state, lambda ctx: down_unit(ctx, ctx.state.units[U1]))
    assert not of(events, ZoneExpired) and tile_state.zones
    tile_state.round = tile_state.zones[0].expires_round  # 施放者不在：那一輪的環境回合消失
    _, events = ctx_run(tile_state, run_environment)
    assert [e.reason for e in of(events, ZoneExpired)] == ["timeout"]


# ---------------------------------------------------------------------------
# 移動型與表面
# ---------------------------------------------------------------------------


def test_a_moving_zone_advances_each_environment_turn_and_hits_units_it_reaches() -> None:
    result = cast(arena(MOVING, foes=((4, 3),)), direction="east")
    state = result.state
    assert set(zone_cells(state, state.zones[0])) == {(1, 3), (2, 3)}
    assert next_zone_cells(state, state.zones[0]) == ((2, 3), (3, 3))
    state, events = ctx_run(state, run_environment)
    [moved] = of(events, ZoneMoved)
    assert moved.direction == "east" and {(p.x, p.y) for p in moved.cells} == {(2, 3), (3, 3)}
    assert triggers(events) == []
    state, events = ctx_run(state, run_environment)
    assert triggers(events) == [(U2, "enter")]  # 前進到 (4, 3)：掃到站著不動的敵人
    assert of(events, DamageDealt)[0].target_id == U2


def test_a_moving_zone_with_speed_two_steps_cell_by_cell() -> None:
    skill = zone_skill({"type": "line", "size": 1}, anchor="moving", speed=2, duration=3)
    state = cast(arena(skill, foes=((2, 3),)), direction="east").state
    _, events = ctx_run(state, run_environment)
    assert len(of(events, ZoneMoved)) == 2
    assert triggers(events) == [(U2, "enter")]  # 中間經過的格子也算


def test_a_moving_zone_loses_cells_at_walls_and_expires_when_blocked() -> None:
    terrain = "\n".join(
        [".......", ".......", ".......", "...#...", ".......", ".......", "......."]
    )
    state = cast(arena(MOVING, terrain=terrain), direction="east").state
    state, events = ctx_run(state, run_environment)
    assert {(p.x, p.y) for p in of(events, ZoneMoved)[0].cells} == {(2, 3)}  # (3, 3) 是牆
    state, events = ctx_run(state, run_environment)
    assert [e.reason for e in of(events, ZoneExpired)] == ["blocked"] and not state.zones


def test_a_moving_zone_leaves_its_surface_on_every_newly_covered_tile() -> None:
    skill = zone_skill(
        {"type": "line", "size": 2}, anchor="moving", speed=1, duration=3, surface="oil"
    )
    state = cast(arena(skill), direction="east").state
    assert [(x, y) for x, y in ((1, 3), (2, 3)) if state.tile(x, y).surface is Surface.OIL]
    assert state.tile(1, 3).surface_creator == U1
    state, events = ctx_run(state, run_environment)
    changed = [(e.pos.x, e.pos.y) for e in of(events, SurfaceChanged) if e.after is Surface.OIL]
    assert changed == [(3, 3)] and state.tile(3, 3).surface_creator == U1


def test_the_zone_limit_removes_the_oldest_zone() -> None:
    state = arena(foes=((6, 6),))
    for i, xy in enumerate(((1, 1), (3, 3), (1, 5))):
        s = give_turn(state, U1)
        s.units[U1].cooldowns = {}
        result = cast(s, **at(*xy))
        state = result.state
        if i == 2:
            [expired] = of(result, ZoneExpired)
            assert (expired.zone_id, expired.reason) == (1, "limit")
    assert [z.id for z in state.zones] == [2, 3]


# ---------------------------------------------------------------------------
# 預告、視圖、預覽
# ---------------------------------------------------------------------------


def test_the_telegraph_shows_where_the_zone_moves_next_and_matches_the_real_move() -> None:
    state = cast(arena(MOVING, foes=((3, 3),)), direction="east").state
    forecast = telegraph(state)
    [change] = [c for c in forecast.changes if c.kind == "zone_moved"]
    predicted = {(p.x, p.y) for p in change.tiles}
    assert change.before == "east" and change.after == SID and change.amount == 1
    assert predicted == set(next_zone_cells(state, state.zones[0]) or ())
    after, events = ctx_run(state, run_environment)
    assert predicted == set(zone_cells(after, after.zones[0]))
    damaged = [c.unit_id for c in forecast.changes if c.kind == "unit_damaged"]
    assert damaged == [U2] == [e.target_id for e in of(events, DamageDealt)]


def test_the_view_lists_zones_for_both_sides() -> None:
    state = cast(arena(MOVING), direction="east").state
    for team in (Team.ALLY, Team.ENEMY):
        [view] = project_for(state, team).zones
        assert (view.anchor, view.direction, view.speed, view.harmful) == (
            "moving",
            "east",
            1,
            True,
        )
        assert [(p.x, p.y) for p in view.cells] == [(1, 3), (2, 3)]
        assert view.next_cells is not None and [(p.x, p.y) for p in view.next_cells] == [
            (2, 3),
            (3, 3),
        ]
        assert view.expires_round == state.round + 3 and view.name_zh == "測試技 t_zone"
    buff = project_for(cast(arena(CASTER)).state, Team.ALLY).zones[0]
    assert (buff.anchor, buff.harmful, buff.next_cells, buff.affects) == (
        "caster",
        False,
        None,
        "allies",
    )


def test_the_preview_shows_zone_damage_to_units_already_inside() -> None:
    state = arena(foes=((3, 3),))
    p = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=3, y=3)))
    assert any(isinstance(e, ZoneCreated) for e in p.min_events)
    lo = sum(e.amount for e in p.min_events if isinstance(e, DamageDealt))
    hi = sum(e.amount for e in p.max_events if isinstance(e, DamageDealt))
    assert 0 < lo < hi


# ---------------------------------------------------------------------------
# 既有觸發（驗收 2）
# ---------------------------------------------------------------------------


def test_zone_damage_triggers_on_damaged_once_per_entry() -> None:
    hurt = passive(
        "skill_t_hurt",
        "on_damaged",
        target="self",
        max_per_round=3,
        effects=[{"type": "heal", "dice": "1d4", "affects": "self"}],
    )
    state = cast(arena(foes=((6, 3),), foe_skills=[hurt]), **at(3, 3)).state
    result = walk(state, U2, (5, 3), (4, 3), (3, 3))
    assert triggers(result.events) == [(U2, "enter")]
    fired = [e for e in of(result, SkillTriggered) if e.skill_id == "skill_t_hurt"]
    assert len(fired) == 1 and fired[0].trigger == "on_damaged"


def test_entering_a_zone_is_not_entering_a_surface() -> None:
    base = passive("skill_t_enter", "on_hit", target="other")
    trigger = TriggerSpec.model_validate(
        {"event": "on_enter_surface", "target": "other", "max_per_round": 3}
    )
    enter = base.model_copy(update={"trigger": trigger})
    state = cast(arena(foes=((6, 3),), owner_skills=[enter]), **at(3, 3)).state
    result = walk(state, U2, (5, 3), (4, 3))
    assert triggers(result.events) == [(U2, "enter")]
    assert not [e for e in of(result, SkillTriggered) if e.skill_id == "skill_t_enter"]


def test_zone_triggers_respect_the_trigger_depth_limit() -> None:
    result = cast(arena(foes=((3, 3),), max_trigger_depth=0), **at(3, 3))
    assert triggers(result.events) == [] and not of(result, DamageDealt)
    [limit] = of(result, TriggerLimitReached)
    assert (limit.unit_id, limit.skill_id, limit.depth) == (U1, SID, 1)


# ---------------------------------------------------------------------------
# 序列化、驗證
# ---------------------------------------------------------------------------


def test_zones_survive_serialization() -> None:
    state = cast(arena(MOVING), direction="east").state
    restored = state_from_json(state_to_json(state))
    assert restored.zones == state.zones and restored.next_zone_id == state.next_zone_id
    assert state_to_json(restored) == state_to_json(state)


@pytest.mark.parametrize(
    ("shape", "change", "message"),
    [
        ({"type": "line", "size": 2}, {"anchor": "moving"}, "必須填 speed"),
        ({"type": "cross", "range": 3}, {"anchor": "moving", "speed": 1}, "形狀必須是 line"),
        ({"type": "cross", "range": 3}, {"anchor": "caster"}, "形狀必須是 self"),
        ({"type": "cross", "range": 3}, {"speed": 1}, "只有 anchor: moving 使用 speed"),
        ({"type": "cross", "range": 3}, {"affects": "self"}, "affects 必須明寫"),
        ({"type": "cross", "range": 3}, {"effects": []}, "1 到 2 個效果"),
        ({"type": "cross", "range": 3}, {"effects": [{"type": "push", "distance": 1}]}, "只能使用"),
        (
            {"type": "cross", "range": 3},
            {"effects": [{**FIRE, "affects": "all"}]},
            "不可自帶 affects",
        ),
    ],
)
def test_zone_structure_errors(shape: dict[str, Any], change: dict[str, Any], message: str) -> None:
    effect: dict[str, Any] = {
        "type": "zone",
        "anchor": "tile",
        "when": "both",
        "duration": 2,
        "affects": "enemies",
        "effects": [FIRE],
        **change,
    }
    with pytest.raises(ValueError, match=message):
        make_skill(SID, shape, [effect])


def test_zone_must_be_the_only_effect_and_zone_fields_belong_to_zone() -> None:
    effect: dict[str, Any] = {
        "type": "zone",
        "anchor": "tile",
        "when": "both",
        "duration": 2,
        "affects": "enemies",
        "effects": [FIRE],
    }
    with pytest.raises(ValueError, match="唯一的效果"):
        make_skill(SID, {"type": "cross", "range": 3}, [effect, FIRE])
    with pytest.raises(ValueError, match="只有 zone 使用"):
        make_skill(SID, {"type": "single", "range": 3}, [{**FIRE, "anchor": "tile"}])


def test_the_demo_zone_skills_are_valid_and_equipped() -> None:
    from trpg.skillgen.validate import validate_skill  # noqa: PLC0415

    lib = library()
    for skill_id in ("skill_war_hymn", "skill_fire_wall"):
        assert validate_skill(lib.skills[skill_id], lib) == []
    builds = lib.builds.by_id()
    assert "skill_war_hymn" in builds["build_support"].hero.skills
    assert "skill_fire_wall" in builds["build_summoner"].hero.skills
    hymn = lib.skills["skill_war_hymn"].effects[0]
    wall = lib.skills["skill_fire_wall"].effects[0]
    assert (hymn.anchor, hymn.affects) == ("caster", "allies")
    assert (wall.anchor, wall.surface) == ("moving", Surface.FIRE)
