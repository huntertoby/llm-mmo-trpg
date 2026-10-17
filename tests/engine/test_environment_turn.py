"""環境回合、環境預告（telegraph）、天氣、地圖事件（6.1-5～8、6.2-2 火勢蔓延與預告一致）。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from trpg.engine import (
    BattleState,
    Decision,
    EndTurn,
    begin_battle,
    build_setup,
    resolve,
    resume,
    telegraph,
)
from trpg.engine.events import (
    EnvironmentEnded,
    EnvironmentStarted,
    EventBase,
    MapEventTriggered,
    ObjectDestroyed,
    ObjectExploded,
    ObjectIgnited,
    SurfaceChanged,
    TerrainChanged,
    UnitSpawned,
)
from trpg.engine.runner import run_battle
from trpg.shared.types import ObjectId, Surface, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")


def _strip(events: Sequence[Any]) -> list[dict[str, Any]]:
    return [e.model_dump(exclude={"seq"}) for e in events]


def _env_events(events: list[EventBase]) -> list[EventBase]:
    start = next(i for i, e in enumerate(events) if isinstance(e, EnvironmentStarted))
    end = next(i for i, e in enumerate(events) if isinstance(e, EnvironmentEnded))
    return events[start : end + 1]


def _finish_round(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    """所有單位依序結束回合，直到環境回合結束、下一輪開始。"""
    events: list[EventBase] = []
    start_round = state.round
    while state.round == start_round and not state.ended:
        assert state.active_unit is not None
        r = resolve(state, EndTurn(unit_id=state.active_unit))
        state, events = r.state, events + r.events
    return state, events


def _fire_field(**kw: Any) -> BattleState:
    """火 (0, 0)；油 (1, 0)、(2, 0)；草叢 (0, 1)；油桶 (3, 0)。"""
    m = make_map(
        "000000\n000000\n000000",
        surfaces=[(0, 0, "fire"), (1, 0, "oil"), (2, 0, "oil")],
        objects=[(0, 1, "grass"), (3, 0, "oil_barrel")],
        ally=[(5, 2)],
        enemy=[(4, 2)],
        **kw,
    )
    return make_state(
        m,
        [
            spawn(Team.ALLY, (5, 2), no_reactions("hero_fighter", max_hp=500)),
            spawn(Team.ENEMY, (4, 2), no_reactions("bandit", max_hp=500)),
        ],
    )


def test_fire_spreads_round_by_round_and_telegraph_matches() -> None:
    state = _fire_field()
    history: list[dict[tuple[int, int], Surface]] = []
    for _ in range(3):
        forecast = telegraph(state)
        assert forecast.round == state.round
        # 本輪中途再預告一次（最後一位行動前），結果相同
        mid = state
        while len(mid.turn_order) - 1 > mid.turn_pos:
            mid = resolve(mid, EndTurn(unit_id=mid.active_unit)).state  # type: ignore[arg-type]
        assert _strip(telegraph(mid).events) == _strip(forecast.events)
        state, events = _finish_round(state)
        actual = _env_events(events)
        assert _strip(actual) == _strip(forecast.events)
        history.append(
            {
                (x, y): state.tile(x, y).surface
                for y in range(3)
                for x in range(6)
                if state.tile(x, y).surface is not Surface.NONE
            }
        )
    # 第 1 輪：火蔓延到油 (1, 0) 與草叢 (0, 1)
    assert history[0][(1, 0)] is Surface.FIRE and history[0][(0, 1)] is Surface.FIRE
    assert history[0][(2, 0)] is Surface.OIL
    # 第 2 輪：(2, 0) 著火；草叢在第 2 次環境回合燒毀
    assert history[1][(2, 0)] is Surface.FIRE
    assert state.objects[ObjectId("obj_0001")].destroyed
    # 第 3 輪：火勢延燒到油桶 → 爆炸
    assert state.objects[ObjectId("obj_0002")].destroyed


def test_telegraph_lists_changes() -> None:
    state = _fire_field()
    forecast = telegraph(state)
    kinds = {
        (c.kind, c.pos.x if c.pos else None, c.pos.y if c.pos else None) for c in forecast.changes
    }
    assert ("surface", 1, 0) in kinds and ("object_ignited", 0, 1) in kinds
    # 預告不改變原狀態
    assert state.tile(1, 0).surface is Surface.OIL
    # 草叢著火後，預告顯示「還能撐幾次環境回合」
    state, _ = _finish_round(state)
    assert telegraph(state).burning == ((ObjectId("obj_0001"), 1),)
    destroyed = [c for c in telegraph(state).changes if c.kind == "object_destroyed"]
    assert destroyed and destroyed[0].object_id == ObjectId("obj_0001")


def test_surface_duration_and_expiry() -> None:
    m = make_map("0000", enemy=[(3, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (3, 0), no_reactions()),
        ],
    )
    from trpg.engine.effects import CreateSurfaceEffect, run_effects  # noqa: PLC0415

    state = run_effects(
        state,
        [
            CreateSurfaceEffect(pos=(1, 0), surface=Surface.ICE),  # 3 輪，到期變水
            CreateSurfaceEffect(pos=(2, 0), surface=Surface.POISON, duration=1),
        ],
    ).state
    assert state.tile(1, 0).surface_remaining == 3
    state, events = _finish_round(state)
    expired = [e for e in events if isinstance(e, SurfaceChanged) and e.cause == "expired"]
    assert [(e.pos.x, e.before, e.after) for e in expired] == [(2, Surface.POISON, Surface.NONE)]
    for _ in range(2):
        state, events = _finish_round(state)
    assert state.tile(1, 0).surface is Surface.WATER and state.tile(1, 0).surface_remaining is None


def test_rain_creates_puddles_and_telegraph_matches() -> None:
    m = make_map("0000\n0000\n0000", enemy=[(3, 2)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (3, 2), no_reactions()),
        ],
        weather="rain",
        seed=5,
    )
    forecast = telegraph(state)
    state, events = _finish_round(state)
    actual = _env_events(events)
    assert _strip(actual) == _strip(forecast.events)
    puddles = [e for e in actual if isinstance(e, SurfaceChanged) and e.after is Surface.WATER]
    assert len(puddles) == 2 and all(e.cause == "weather" for e in puddles)


def test_environment_rng_is_independent_of_player_actions() -> None:
    """環境回合的亂數只由種子與輪數決定：本輪消耗多少戰鬥亂數都不影響水窪位置。"""
    m = make_map("00000\n00000\n00000", enemy=[(4, 2)])
    spawns = [
        spawn(Team.ALLY, (0, 0), no_reactions("hero_archer")),
        spawn(Team.ENEMY, (4, 2), no_reactions(max_hp=900)),
    ]
    a = make_state(m, spawns, weather="rain", seed=9)
    forecast = telegraph(a)
    a = give_turn(a, "unit_0001")
    from trpg.engine import Attack  # noqa: PLC0415

    for _ in range(3):
        a = resolve(a, Attack(unit_id=U1, target_id=U2)).state
    assert _strip(telegraph(a).events) != []
    assert [c for c in telegraph(a).changes if c.kind == "surface"] == [
        c for c in forecast.changes if c.kind == "surface"
    ]


def test_map_events_spawn_units_and_change_terrain() -> None:
    m = make_map(
        "0000\n0000",
        enemy=[(3, 1)],
        events=[
            {
                "kind": "terrain_change",
                "round": 1,
                "tiles": [{"at": [1, 0], "height": 2}, {"at": [2, 0], "surface": "water"}],
            },
            {"kind": "spawn_units", "round": 2, "units": [{"template": "bandit", "at": [3, 0]}]},
        ],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (3, 1), no_reactions()),
        ],
        spawn_templates=["bandit"],
    )
    forecast = telegraph(state)
    assert [e.kind for e in forecast.upcoming] == ["spawn_units"]  # 提前一輪預告
    assert {c.kind for c in forecast.changes} >= {"terrain", "surface"}
    state, events = _finish_round(state)
    assert any(isinstance(e, MapEventTriggered) and e.kind == "terrain_change" for e in events)
    assert any(isinstance(e, TerrainChanged) and e.height_after == 2 for e in events)
    assert state.tile(1, 0).height == 2 and state.tile(2, 0).surface is Surface.WATER
    forecast2 = telegraph(state)
    assert any(c.kind == "unit_spawned" for c in forecast2.changes)
    state, events = _finish_round(state)
    spawned = [e for e in events if isinstance(e, UnitSpawned)]
    assert len(spawned) == 1 and spawned[0].unit_id == U3 and spawned[0].team is Team.ENEMY
    assert state.turn_order[-1] == U3 and state.units[U3].name_zh == "盜賊2"
    assert state.units[U3].alive


def test_spawn_on_occupied_tile_moves_to_nearest_free_tile() -> None:
    m = make_map(
        "0000\n0000",
        enemy=[(3, 0)],
        events=[
            {"kind": "spawn_units", "round": 1, "units": [{"template": "bandit", "at": [3, 0]}]}
        ],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (3, 0), no_reactions()),
        ],
        spawn_templates=["bandit"],
    )
    state, _ = _finish_round(state)
    assert state.units[U3].pos.x == 2 and state.units[U3].pos.y == 0


def test_explosion_during_environment_is_telegraphed() -> None:
    m = make_map(
        "0000\n0000",
        surfaces=[(0, 0, "fire")],
        objects=[(1, 0, "oil_barrel")],
        enemy=[(2, 1)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 1), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (2, 1), template("bandit", reactions=[], max_hp=300)),
        ],
    )
    forecast = telegraph(state)
    assert any(c.kind == "object_exploded" for c in forecast.changes)
    assert any(c.kind == "unit_damaged" and c.unit_id == U2 for c in forecast.changes)
    state, events = _finish_round(state)
    assert _strip(_env_events(events)) == _strip(forecast.events)
    assert any(isinstance(e, ObjectExploded) for e in events)
    assert any(isinstance(e, ObjectIgnited) for e in events) is False
    assert any(isinstance(e, ObjectDestroyed) for e in events)


@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(min_value=0, max_value=2**32), map_index=st.integers(0, 2))
def test_property_telegraph_matches_every_environment_turn_on_demo_maps(
    seed: int, map_index: int
) -> None:
    """三張示範地圖的整場對戰：每一次環境回合，都與「本輪最後一個 EndTurn 之前」的預告完全相同。

    （預告是在本輪最後一個動作之前取得；之後狀態不再改變時，預告必須與實際一致。）
    """
    lib = library()
    map_id = ("bridge_chasm", "oil_depot", "swamp")[map_index]
    encounter = lib.map(map_id).encounter
    assert encounter is not None
    setup = build_setup(lib, map_id, encounter.allies, encounter.enemies, max_rounds=8)
    run = run_battle(setup, seed)
    state = begin_battle(setup, seed).state
    environment_turns = 0
    for step in run.actions:
        forecast = telegraph(state) if isinstance(step, EndTurn) else None
        result = resume(state, step) if isinstance(step, Decision) else resolve(state, step)
        if forecast is not None and any(isinstance(e, EnvironmentStarted) for e in result.events):
            environment_turns += 1
            assert _strip(_env_events(result.events)) == _strip(forecast.events)
        state = result.state
    assert environment_turns >= 1 or state.round == 1
