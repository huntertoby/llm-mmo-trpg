"""RG-2（#162，05 5.7、06 6.3.1）：敵方陷阱的「可疑痕跡」與「看那一格一眼」。

規則（實際跑引擎）：玩家方單位移動抵達或回合開始時，``trap_trace_radius``（2）格內還沒揭露的敵方陷阱
記成痕跡（只知道格子）；3 格不出現；敵方看不到玩家陷阱的痕跡；痕跡不改可見性（AI、預覽照舊）；
揭露後轉成看清；觸發後消失；``trap_traced`` 只給玩家方看，``trap_glance`` 所有人看得到。
"""

from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from trpg.engine import EndTurn, Move, UseSkill, filter_events, project_for, resolve
from trpg.engine.context import Ctx
from trpg.engine.events import TrapGlance, TrapPlaced, TrapTraced, TrapTriggered, TurnStarted
from trpg.engine.state import BattleState, state_to_json
from trpg.engine.traps import (
    reveal_traps,
    strip_hidden_traps,
    trace_traps,
    trap_traces,
    visible_traps,
)
from trpg.shared.types import Pos, Team

BEAR = "skill_bear_trap"
TRAP = (4, 3)


def scene() -> BattleState:
    """U1（敵方，會放捕獸夾）在 (6, 3)；U2（我方）在 (0, 3)；U3（我方）在 (4, 6)。"""
    m = make_map(FLAT7, ally=[(0, 3), (4, 6)], enemy=[(6, 3)])
    return make_state(
        m,
        [
            spawn(Team.ENEMY, (6, 3), caster_template([BEAR])),
            spawn(Team.ALLY, (0, 3), no_reactions(max_hp=999)),
            spawn(Team.ALLY, (4, 6), no_reactions(max_hp=999)),
        ],
    )


def enemy_trap() -> tuple[BattleState, list[object]]:
    """U1 在 (4, 3) 放捕獸夾。"""
    result = resolve(
        give_turn(scene(), U1), UseSkill(unit_id=U1, skill_id=BEAR, target_pos=Pos(x=4, y=3))
    )
    return result.state, list(result.events)


def walk(state: BattleState, unit: str, *cells: tuple[int, int]):  # type: ignore[no-untyped-def]
    """``unit`` 從目前位置照 ``cells`` 走（路徑含起點）。"""
    start = state.units[unit].pos  # type: ignore[index]
    path = (start, *(Pos(x=x, y=y) for x, y in cells))
    return resolve(give_turn(state, unit), Move(unit_id=unit, path=path))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 看那一格一眼
# ---------------------------------------------------------------------------


def test_enemy_placing_a_trap_glances_at_the_tile_but_leaves_no_trace() -> None:
    state, events = enemy_trap()
    glances = [e for e in events if isinstance(e, TrapGlance)]
    assert [(g.owner_id, (g.pos.x, g.pos.y)) for g in glances] == [(U1, TRAP)]
    placed = next(i for i, e in enumerate(events) if isinstance(e, TrapPlaced))
    assert events.index(glances[0]) == placed + 1  # 緊接在放置之後
    # 放的那一刻不變成痕跡（只看距離；U3 在 3 格外、U2 在 4 格外）
    assert not any(isinstance(e, TrapTraced) for e in events)
    assert state.traps[0].traced_by == ()
    assert project_for(state, Team.ALLY).trap_traces is None


def test_glance_is_visible_to_everyone_and_does_not_turn_the_placer() -> None:
    before = give_turn(scene(), U1)
    facing = before.units[U1].facing
    state, events = enemy_trap()
    for team in (Team.ALLY, Team.ENEMY):
        seen = filter_events(events, state, team)  # type: ignore[arg-type]
        assert any(isinstance(e, TrapGlance) for e in seen)
    assert not any(isinstance(e, TrapPlaced) for e in filter_events(events, state, Team.ALLY))  # type: ignore[arg-type]
    # 頭轉向那一格是畫面演出（RG-3）；引擎不改面向（面向影響背刺）
    assert state.units[U1].facing == facing


def test_ally_placing_a_trap_does_not_glance() -> None:
    m = make_map(FLAT7, ally=[(2, 3)], enemy=[(6, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 3), caster_template([BEAR])),
            spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=999)),
        ],
    )
    result = resolve(
        give_turn(state, U1), UseSkill(unit_id=U1, skill_id=BEAR, target_pos=Pos(x=4, y=3))
    )
    assert of(result, TrapPlaced) and not of(result, TrapGlance)


# ---------------------------------------------------------------------------
# 可疑痕跡：距離、陣營、可見性
# ---------------------------------------------------------------------------


def test_trace_appears_within_two_tiles_but_not_three() -> None:
    state, _ = enemy_trap()
    three = walk(state, U2, (1, 3))  # 到 (4, 3) 3 格
    assert not of(three, TrapTraced)
    assert project_for(three.state, Team.ALLY).trap_traces is None
    two = walk(three.state, U2, (2, 3))  # 2 格
    (traced,) = of(two, TrapTraced)
    assert (traced.unit_id, traced.team, (traced.pos.x, traced.pos.y)) == (U2, Team.ALLY, TRAP)
    assert two.state.traps[0].traced_by == (Team.ALLY,)
    assert project_for(two.state, Team.ALLY).trap_traces == (Pos(x=4, y=3),)


def test_trace_is_recorded_once_and_stays_when_walking_away() -> None:
    state, _ = enemy_trap()
    near = walk(state, U2, (1, 3), (2, 3), (3, 3))
    assert len(of(near, TrapTraced)) == 1  # 一路都在 2 格內也只記一次
    away = walk(near.state, U2, (3, 2), (2, 2), (1, 2))
    assert not of(away, TrapTraced)
    assert project_for(away.state, Team.ALLY).trap_traces == (Pos(x=4, y=3),)  # 看到就留著


def test_trace_at_turn_start() -> None:
    """U3 站在 (4, 5)（距陷阱 2 格）：放置當下不記，輪到 U3 開始回合時才記。"""
    state, _ = enemy_trap()
    moved = state.clone()
    moved.units[U3].pos = Pos(x=4, y=5)
    assert moved.traps[0].traced_by == ()
    events: list[object] = []
    current = moved
    for _ in range(6):
        result = resolve(current, EndTurn(unit_id=current.active_unit))  # type: ignore[arg-type]
        current = result.state
        events += result.events
        if any(isinstance(e, TurnStarted) and e.unit_id == U3 for e in result.events):
            break
    started = next(
        i for i, e in enumerate(events) if isinstance(e, TurnStarted) and e.unit_id == U3
    )
    traced = [e for e in events if isinstance(e, TrapTraced)]
    assert [t.unit_id for t in traced] == [U3]
    assert events.index(traced[0]) > started
    assert current.traps[0].traced_by == (Team.ALLY,)


def test_enemy_never_sees_traces_of_player_traps() -> None:
    m = make_map(FLAT7, ally=[(2, 3)], enemy=[(6, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 3), caster_template([BEAR])),
            spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=999)),
        ],
    )
    placed = resolve(
        give_turn(state, U1), UseSkill(unit_id=U1, skill_id=BEAR, target_pos=Pos(x=4, y=3))
    ).state
    near = walk(placed, U2, (5, 3), (5, 2))  # 敵人走到玩家陷阱旁邊
    assert not of(near, TrapTraced)
    assert near.state.traps[0].traced_by == ()
    assert project_for(near.state, Team.ENEMY).trap_traces is None
    # 敵方的路徑與 AI 照舊看不到玩家的陷阱
    assert visible_traps(near.state, Team.ENEMY) == []
    assert strip_hidden_traps(near.state, Team.ENEMY).traps == []


def test_trace_does_not_make_the_trap_visible_to_player_ai_or_preview() -> None:
    state, _ = enemy_trap()
    traced = walk(state, U2, (1, 3), (2, 3)).state
    assert traced.traps[0].traced_by == (Team.ALLY,)
    assert visible_traps(traced, Team.ALLY) == []  # 我方 AI 不因痕跡繞路
    assert strip_hidden_traps(traced, Team.ALLY).traps == []  # 預覽不洩漏種類
    view = project_for(traced, Team.ALLY)
    assert view.traps == () and view.trap_traces == (Pos(x=4, y=3),)
    dumped = view.model_dump(mode="json")
    assert dumped["trap_traces"] == [{"x": 4, "y": 3}]
    assert BEAR not in json.dumps(dumped)  # 痕跡不帶技能


def test_trap_traced_event_is_only_for_the_player_side() -> None:
    state, _ = enemy_trap()
    result = walk(state, U2, (1, 3), (2, 3))
    events = list(result.events)
    assert any(isinstance(e, TrapTraced) for e in filter_events(events, result.state, Team.ALLY))
    assert not any(
        isinstance(e, TrapTraced) for e in filter_events(events, result.state, Team.ENEMY)
    )


# ---------------------------------------------------------------------------
# 揭露、觸發
# ---------------------------------------------------------------------------


def test_revealing_turns_the_trace_into_a_seen_trap() -> None:
    state, _ = enemy_trap()
    traced = walk(state, U2, (1, 3), (2, 3)).state
    ctx = Ctx(traced.clone())
    reveal_traps(ctx, ctx.state.units[U2], [TRAP])
    (trap,) = ctx.state.traps
    assert trap.revealed_to == (Team.ALLY,) and trap.traced_by == ()
    view = project_for(ctx.state, Team.ALLY)
    assert view.trap_traces is None
    assert [(t.pos.x, t.pos.y, t.skill_id) for t in view.traps] == [(4, 3, BEAR)]
    # 揭露過的不會再記成痕跡
    again = Ctx(ctx.state.clone())
    trace_traps(again, again.state.units[U2])
    assert again.events == [] and again.state.traps[0].traced_by == ()


def test_trace_disappears_when_the_trap_triggers() -> None:
    state, _ = enemy_trap()
    traced = walk(state, U2, (1, 3), (2, 3)).state
    stepped = walk(traced, U2, (3, 3), (4, 3))
    assert of(stepped, TrapTriggered)
    assert stepped.state.traps == []
    assert project_for(stepped.state, Team.ALLY).trap_traces is None


def test_zero_radius_shows_no_traces() -> None:
    state, _ = enemy_trap()
    core = state.ruleset.core.model_copy(update={"trap_trace_radius": 0})
    state.ruleset = state.ruleset.model_copy(update={"core": core})
    result = walk(state, U2, (1, 3), (2, 3), (3, 3))
    assert not of(result, TrapTraced)


def test_traced_by_is_not_serialized_when_empty() -> None:
    state, _ = enemy_trap()
    assert "traced_by" not in json.dumps(json.loads(state_to_json(state))["traps"])
    traced = walk(state, U2, (1, 3), (2, 3)).state
    assert json.loads(state_to_json(traced))["traps"][0]["traced_by"] == ["ally"]


# ---------------------------------------------------------------------------
# 性質測試
# ---------------------------------------------------------------------------


@settings(max_examples=40, deadline=None)
@given(
    x=st.integers(min_value=0, max_value=6),
    y=st.integers(min_value=0, max_value=6),
    radius=st.integers(min_value=0, max_value=4),
    enemy_side=st.booleans(),
)
def test_trace_iff_player_side_and_within_radius(
    x: int, y: int, radius: int, enemy_side: bool
) -> None:
    """任意位置與半徑：只有玩家方、曼哈頓距離 ≤ 半徑時記痕跡；同樣輸入兩次結果逐字相同。"""
    state, _ = enemy_trap()
    core = state.ruleset.core.model_copy(update={"trap_trace_radius": radius})
    state.ruleset = state.ruleset.model_copy(update={"core": core})
    who = U1 if enemy_side else U2
    if (x, y) != state.units[who].xy and state.unit_at(x, y) is not None:
        return

    def run() -> tuple[str, str]:
        ctx = Ctx(state.clone())
        unit = ctx.state.units[who]
        unit.pos = Pos(x=x, y=y)
        trace_traps(ctx, unit)
        events = json.dumps([e.model_dump(mode="json") for e in ctx.events])
        return events, state_to_json(ctx.state)

    first, second = run(), run()
    assert first == second
    distance = abs(x - TRAP[0]) + abs(y - TRAP[1])
    expected = (not enemy_side) and distance <= radius
    traced = json.loads(first[1])["traps"][0].get("traced_by", [])
    assert traced == (["ally"] if expected else [])
    assert ('"trap_traced"' in first[0]) is expected
    assert trap_traces(json_state(first[1]), Team.ENEMY) == ()


def json_state(text: str) -> BattleState:
    from trpg.engine.state import state_from_json  # noqa: PLC0415

    return state_from_json(text)
