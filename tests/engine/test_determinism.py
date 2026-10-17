"""確定性、純函式、序列化、重播與合法動作的屬性測試（驗收條件 2、3、4、11）。"""

from __future__ import annotations

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.engine import (
    Action,
    Attack,
    BattleSetup,
    BattleState,
    Defend,
    EndTurn,
    Move,
    begin_battle,
    build_setup,
    legal_actions,
    resolve,
    state_from_json,
    state_to_json,
)
from trpg.engine.actions import ACTION_ADAPTER, STEP_ADAPTER, STEP_LIST_ADAPTER
from trpg.engine.battle import has_only_end_turn
from trpg.engine.events import EVENT_LIST_ADAPTER, EventBase
from trpg.engine.runner import BattleLog, BattleRun, replay, run_battle
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, UnitId

MAPS = ("test_heights_8x8", "test_flat_6x6")
PROPERTY_SETTINGS = settings(
    max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)


def demo_setup(map_id: str = "test_heights_8x8", max_rounds: int = 30) -> BattleSetup:
    return build_setup(library(), map_id, DEMO_ALLIES, DEMO_ENEMIES, max_rounds=max_rounds)


def events_json(events: list[EventBase]) -> str:
    return EVENT_LIST_ADAPTER.dump_json(events).decode()  # type: ignore[arg-type]


def assert_same_run(a: BattleRun, b: BattleRun) -> None:
    assert state_to_json(a.state) == state_to_json(b.state)
    assert events_json(a.events) == events_json(b.events)


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------


def test_state_json_round_trip_through_a_battle() -> None:
    run = run_battle(demo_setup(), 42)
    snapshots = [begin_battle(demo_setup(), 42).state, run.state]
    for state in snapshots:
        text = state_to_json(state)
        restored = state_from_json(text)
        assert restored == state
        assert state_to_json(restored) == text
        json.loads(text)  # 合法 JSON


def test_actions_and_events_round_trip() -> None:
    run = run_battle(demo_setup(), 7)
    text = STEP_LIST_ADAPTER.dump_json(run.actions)
    assert STEP_LIST_ADAPTER.validate_json(text) == run.actions
    for action in run.actions[:20]:
        assert STEP_ADAPTER.validate_json(STEP_ADAPTER.dump_json(action)) == action
    etext = events_json(run.events)
    restored = EVENT_LIST_ADAPTER.validate_json(etext)
    assert restored == run.events
    assert [e.seq for e in run.events] == list(range(len(run.events)))
    types = {getattr(e, "type", None) for e in run.events}
    assert {"attack_rolled", "damage_dealt", "unit_moved", "turn_started", "battle_ended"} <= types


def test_battle_log_round_trip() -> None:
    run = run_battle(demo_setup(), 3)
    log = run.to_log()
    restored = BattleLog.model_validate_json(log.model_dump_json())
    assert restored.actions == run.actions
    assert restored.final_state == run.state
    assert restored.setup == run.setup


# ---------------------------------------------------------------------------
# 純函式與確定性
# ---------------------------------------------------------------------------


def test_resolve_does_not_modify_input_state() -> None:
    setup = demo_setup()
    state = begin_battle(setup, 11).state
    rng = Rng(99)
    for _ in range(150):
        if state.ended:
            break
        actions = legal_actions(state)
        action = rng.choice(actions)
        before = state_to_json(state)
        result = resolve(state, action)
        assert state_to_json(state) == before
        assert result.state is not state
        assert result.pending is None
        state = result.state


def test_illegal_action_does_not_modify_state() -> None:
    state = begin_battle(demo_setup(), 5).state
    before = state_to_json(state)
    assert state.active_unit is not None
    with pytest.raises(IllegalActionError):
        resolve(state, Attack(unit_id=state.active_unit, target_id=state.active_unit))
    assert state_to_json(state) == before


@pytest.mark.parametrize("map_id", MAPS)
def test_same_seed_same_battle(map_id: str) -> None:
    a = run_battle(demo_setup(map_id), 42)
    b = run_battle(demo_setup(map_id), 42)
    assert_same_run(a, b)
    assert a.state.ended


def test_different_seeds_differ() -> None:
    a = run_battle(demo_setup(), 1)
    b = run_battle(demo_setup(), 2)
    assert events_json(a.events) != events_json(b.events)


@pytest.mark.parametrize("map_id", MAPS)
def test_replay_matches(map_id: str) -> None:
    run = run_battle(demo_setup(map_id), 42)
    assert_same_run(run, replay(run.setup, run.seed, run.actions))


def test_replay_from_serialized_log() -> None:
    run = run_battle(demo_setup(), 42)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    again = replay(log.setup, log.seed, log.actions)
    assert state_to_json(again.state) == state_to_json(log.final_state)
    assert events_json(again.events) == events_json(log.events)  # type: ignore[arg-type]


@PROPERTY_SETTINGS
@given(seed=st.integers(min_value=0, max_value=2**64 - 1), map_index=st.integers(0, 1))
def test_property_random_seed_battle_replays(seed: int, map_index: int) -> None:
    setup = demo_setup(MAPS[map_index], max_rounds=12)
    run = run_battle(setup, seed)
    assert run.state.ended
    assert_same_run(run, replay(setup, seed, run.actions))


# ---------------------------------------------------------------------------
# 合法動作
# ---------------------------------------------------------------------------


def _random_walk(setup: BattleSetup, seed: int, steps: int) -> list[BattleState]:
    """以亂數策略推進，收集途中的狀態（比簡易 AI 走過更多樣的局面）。"""
    rng = Rng(seed)
    state = begin_battle(setup, seed).state
    states = [state]
    for _ in range(steps):
        if state.ended:
            break
        actions = legal_actions(state)
        # 偏向攻擊，讓戰鬥有進展
        attacks = [a for a in actions if isinstance(a, Attack)]
        pool = attacks if attacks and rng.chance_permille(600) else actions
        state = resolve(state, rng.choice(pool)).state
        states.append(state)
    return states


@PROPERTY_SETTINGS
@given(seed=st.integers(min_value=0, max_value=2**32), map_index=st.integers(0, 1))
def test_property_every_legal_action_resolves(seed: int, map_index: int) -> None:
    setup = demo_setup(MAPS[map_index], max_rounds=6)
    for state in _random_walk(setup, seed, 60)[::3]:
        actions = legal_actions(state)
        if state.ended:
            assert actions == []
            continue
        assert isinstance(actions[-1], EndTurn)
        assert len(actions) == len({ACTION_ADAPTER.dump_json(a) for a in actions})
        assert has_only_end_turn(state) == (len(actions) == 1)
        for action in actions:
            resolve(state, action)  # 不得拋出例外


@st.composite
def _arbitrary_action(draw: st.DrawFn, state: BattleState) -> Action:
    unit_ids = [*sorted(state.units), "unit_9999"]
    actor = UnitId(draw(st.sampled_from(unit_ids)))
    kind = draw(st.sampled_from(["move", "attack", "defend", "end_turn"]))
    if kind == "move":
        cells = st.builds(
            lambda x, y: Pos(x=x, y=y), st.integers(0, state.width + 1), st.integers(0, 9)
        )
        path = draw(st.lists(cells, min_size=1, max_size=7))
        if draw(st.booleans()) and actor in state.units:
            path[0] = state.units[actor].pos
        return Move(unit_id=actor, path=tuple(path))
    if kind == "attack":
        return Attack(unit_id=actor, target_id=UnitId(draw(st.sampled_from(unit_ids))))
    if kind == "defend":
        return Defend(unit_id=actor)
    return EndTurn(unit_id=actor)


@PROPERTY_SETTINGS
@given(data=st.data(), seed=st.integers(0, 1000))
def test_property_arbitrary_actions_are_legal_or_rejected(data: st.DataObject, seed: int) -> None:
    states = _random_walk(demo_setup(max_rounds=4), seed, 30)
    legal_states = [s for s in states if not s.ended]
    for state in legal_states[::5]:
        for _ in range(10):
            action = data.draw(_arbitrary_action(state))
            before = state_to_json(state)
            try:
                resolve(state, action)
            except IllegalActionError as exc:
                assert str(exc)  # 有中文原因
            assert state_to_json(state) == before
