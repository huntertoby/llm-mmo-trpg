"""暫時障礙與煙霧表面（Phase 3-11）：到期自動移除、不算摧毀、預算、預告、煙霧的互動。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import library, make_map, make_skill, make_state, no_reactions, spawn
from tests.engine.skill_helpers import SID, U1, battle, cast, of
from trpg.engine import BattleState, EndTurn, resolve, telegraph
from trpg.engine.effects import (
    CreateObstacleEffect,
    CreateSurfaceEffect,
    DestroyObjectEffect,
    ElementTouchEffect,
    run_effects,
)
from trpg.engine.events import (
    EventBase,
    ObjectCreated,
    ObjectDestroyed,
    ObjectExpired,
    SurfaceChanged,
)
from trpg.engine.rules.geometry import blocks_sight_at
from trpg.engine.view import project_for
from trpg.narrative.telegraph import change_text
from trpg.shared.types import Element, ObjectId, Pos, Surface, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill


def _field() -> BattleState:
    m = make_map("00000\n00000\n00000", enemy=[(4, 2)])
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 2), no_reactions("hero_fighter", max_hp=500)),
            spawn(Team.ENEMY, (4, 2), no_reactions("bandit", max_hp=500)),
        ],
    )


def _finish_round(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    events: list[EventBase] = []
    start = state.round
    while state.round == start and not state.ended:
        assert state.active_unit is not None
        r = resolve(state, EndTurn(unit_id=state.active_unit))
        state, events = r.state, events + r.events
    return state, events


def _with_obstacle(kind: str, duration: int | None) -> BattleState:
    return run_effects(
        _field(), [CreateObstacleEffect(pos=(2, 0), object_kind=kind, duration=duration)]
    ).state


# ---------------------------------------------------------------------------
# 暫時障礙
# ---------------------------------------------------------------------------


def test_temporary_obstacle_expires_after_its_duration_without_being_destroyed() -> None:
    state = _with_obstacle("ice_wall", 2)
    oid = ObjectId("obj_0001")
    assert state.objects[oid].expires_in == 2 and state.object_at(2, 0) is not None
    state, events = _finish_round(state)
    assert not [e for e in events if isinstance(e, ObjectExpired)]
    assert state.objects[oid].expires_in == 1 and state.object_at(2, 0) is not None
    state, events = _finish_round(state)
    (expired,) = [e for e in events if isinstance(e, ObjectExpired)]
    assert (expired.object_id, expired.kind, (expired.pos.x, expired.pos.y)) == (
        oid,
        "ice_wall",
        (2, 0),
    )
    assert state.object_at(2, 0) is None and state.objects[oid].destroyed
    assert not [e for e in events if isinstance(e, ObjectDestroyed)]  # 不算被摧毀


def test_expiry_does_not_trigger_break_effects() -> None:
    # 油桶被打破會漏油；到期移除則不會（也不爆炸、不產生表面）
    state = _with_obstacle("oil_barrel", 1)
    state, events = _finish_round(state)
    assert [e for e in events if isinstance(e, ObjectExpired)]
    assert not [e for e in events if isinstance(e, ObjectDestroyed)]
    assert not [e for e in events if isinstance(e, SurfaceChanged)]
    assert state.tile(2, 0).surface is Surface.NONE
    # 對照：直接摧毀同樣的油桶會漏油
    broken = run_effects(
        _with_obstacle("oil_barrel", 1), [DestroyObjectEffect(object_id=ObjectId("obj_0001"))]
    )
    assert [e for e in broken.events if isinstance(e, ObjectDestroyed)]


def test_temporary_obstacle_can_still_be_broken_before_expiry() -> None:
    state = _with_obstacle("ice_wall", 3)
    state = run_effects(state, [DestroyObjectEffect(object_id=ObjectId("obj_0001"))]).state
    assert state.object_at(2, 0) is None
    state, events = _finish_round(state)
    assert not [e for e in events if isinstance(e, ObjectExpired)]  # 已被打破，不會再到期一次


def test_permanent_obstacle_never_expires() -> None:
    state = _with_obstacle("earth_wall", None)
    assert state.objects[ObjectId("obj_0001")].expires_in is None
    for _ in range(12):
        state, events = _finish_round(state)
        assert not [e for e in events if isinstance(e, ObjectExpired)]
    assert state.object_at(2, 0) is not None


def test_expiry_is_deterministic_for_replay() -> None:
    def run() -> list[dict[str, object]]:
        state = _with_obstacle("thorn_wall", 2)
        out: list[dict[str, object]] = []
        for _ in range(3):
            state, events = _finish_round(state)
            out += [e.model_dump(exclude={"seq"}) for e in events]
        return out

    assert run() == run()


def test_skill_creates_temporary_wall_and_view_reports_remaining_rounds() -> None:
    skill = make_skill(
        SID,
        {"type": "cross", "range": 4},
        [{"type": "create_obstacle", "object": "ice_wall", "duration": 3}],
    )
    result = cast(battle(skill), target_pos=Pos(x=2, y=2))
    assert of(result, ObjectCreated)
    view = project_for(result.state, Team.ALLY)
    assert view.objects and all(o.expires_in == 3 for o in view.objects)


def test_telegraph_announces_the_wall_will_vanish() -> None:
    state = _with_obstacle("ice_wall", 1)
    forecast = telegraph(state)
    (change,) = [c for c in forecast.changes if c.kind == "object_expired"]
    assert change.object_id == ObjectId("obj_0001") and (change.pos.x, change.pos.y) == (2, 0)  # type: ignore[union-attr]
    assert "冰牆" in change_text(state, change, lambda t: t) and "消失" in change_text(
        state, change, lambda t: t
    )
    assert state.object_at(2, 0) is not None  # 預告不改變原狀態
    # 還有 2 輪時預告沒有消失
    assert not [
        c for c in telegraph(_with_obstacle("ice_wall", 2)).changes if c.kind == "object_expired"
    ]


def test_ice_wall_melts_in_fire_and_thorn_wall_burns() -> None:
    state = _with_obstacle("ice_wall", 3)
    melted = run_effects(state, [ElementTouchEffect(pos=(2, 0), element=Element.FIRE)])
    assert [e for e in melted.events if isinstance(e, ObjectDestroyed)]
    assert melted.state.object_at(2, 0) is None
    thorn = _with_obstacle("thorn_wall", 2)
    burned = run_effects(thorn, [ElementTouchEffect(pos=(2, 0), element=Element.FIRE)]).state
    assert burned.objects[ObjectId("obj_0001")].burning is not None


def test_wall_sight_properties_match_the_spec() -> None:
    state = _with_obstacle("ice_wall", 3)
    assert blocks_sight_at(state, (2, 0))
    thorn = _with_obstacle("thorn_wall", 2)
    assert not blocks_sight_at(thorn, (2, 0))
    rules = library().ruleset
    assert {"blocks_move", "breakable"} <= set(rules.object_def("thorn_wall").tags)
    assert "flammable" in rules.object_def("thorn_wall").tags


# ---------------------------------------------------------------------------
# 預算
# ---------------------------------------------------------------------------


def _obstacle_skill(duration: int | None) -> object:
    effect: dict[str, object] = {"type": "create_obstacle", "object": "earth_wall"}
    if duration is not None:
        effect["duration"] = duration
    return make_skill(SID, {"type": "cross", "range": 4}, [effect])


def test_obstacle_budget_scales_with_duration_and_permanent_is_unchanged() -> None:
    lib = library()
    permille = lib.budget.obstacle_duration_permille
    assert len(permille) == 10 and permille[-1] == 1000
    assert list(permille) == sorted(permille)  # 越久越貴
    permanent = skill_budget(_obstacle_skill(None), lib).effects[0].points  # type: ignore[arg-type]
    assert permanent == Fraction(3) * Fraction(1800, 1000)  # 現狀：固定 3 點 × 十字形狀 1.8
    for n in (1, 2, 3, 5, 10):
        points = skill_budget(_obstacle_skill(n), lib).effects[0].points  # type: ignore[arg-type]
        assert points == permanent * Fraction(permille[n - 1], 1000)


def test_demo_skills_pass_budget_validation() -> None:
    lib = library()
    for sid in ("skill_ice_wall", "skill_thorn_wall", "skill_smoke_bomb"):
        assert validate_skill(lib.skills[sid], lib) == []
        assert skill_budget(lib.skills[sid], lib).ok


# ---------------------------------------------------------------------------
# 煙霧
# ---------------------------------------------------------------------------


def test_smoke_blocks_sight_conceals_and_has_no_element() -> None:
    smoke = library().ruleset.surface_def(Surface.SMOKE)
    assert smoke.blocks_sight and smoke.conceal and smoke.element is None
    assert smoke.duration == 3
    assert smoke.budget_points == library().ruleset.surface_def(Surface.DARKNESS).budget_points
    state = run_effects(
        _field(), [CreateSurfaceEffect(pos=(2, 1), surface=Surface.SMOKE, team=Team.ALLY)]
    ).state
    assert blocks_sight_at(state, (2, 1)) and state.tile(2, 1).surface_remaining == 3


def test_wind_disperses_smoke_but_holy_does_not() -> None:
    base = run_effects(_field(), [CreateSurfaceEffect(pos=(2, 1), surface=Surface.SMOKE)]).state
    holy = run_effects(base, [ElementTouchEffect(pos=(2, 1), element=Element.HOLY)]).state
    assert holy.tile(2, 1).surface is Surface.SMOKE
    wind = run_effects(base, [ElementTouchEffect(pos=(2, 1), element=Element.WIND)]).state
    assert wind.tile(2, 1).surface is Surface.NONE
    # 對照：聖光會驅散黑暗
    dark = run_effects(_field(), [CreateSurfaceEffect(pos=(2, 1), surface=Surface.DARKNESS)]).state
    cleared = run_effects(dark, [ElementTouchEffect(pos=(2, 1), element=Element.HOLY)]).state
    assert cleared.tile(2, 1).surface is Surface.NONE


def test_smoke_bomb_skill_creates_smoke_that_expires() -> None:
    demo = library().skills["skill_smoke_bomb"]
    (effect,) = demo.effects
    assert (effect.type, effect.surface) == ("create_surface", Surface.SMOKE)
    skill = make_skill(
        SID,
        {"type": "square3", "range": 5},
        [{"type": "create_surface", "surface": "smoke", "duration": 2}],
    )
    result = cast(battle(skill), target_pos=Pos(x=3, y=1))
    smoke_tiles = [
        (c.pos.x, c.pos.y) for c in of(result, SurfaceChanged) if c.after is Surface.SMOKE
    ]
    assert len(smoke_tiles) == 9 and all(blocks_sight_at(result.state, xy) for xy in smoke_tiles)
    state, _ = _finish_round(result.state)
    assert all(state.tile(*xy).surface_remaining == 1 for xy in smoke_tiles)
    state, _ = _finish_round(state)
    assert all(state.tile(*xy).surface is Surface.NONE for xy in smoke_tiles)
    assert U1 in state.units
