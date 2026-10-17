"""技能的確定性與重播（docs/phases/Phase2A計畫.md 5.5 第 8 條）。"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import DEMO_ALLIES, library
from trpg.engine import (
    Action,
    UseSkill,
    begin_battle,
    build_setup,
    legal_actions,
    resolve,
    state_to_json,
)
from trpg.engine.actions import ACTION_ADAPTER, STEP_LIST_ADAPTER
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import has_only_end_turn
from trpg.engine.events import EVENT_LIST_ADAPTER, SkillUsed
from trpg.engine.runner import replay, run_battle
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng

PROPERTY_SETTINGS = settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
SKILLED_ENEMIES = ("hero_fighter", "hero_stormcaller", "hero_archer")
MAPS = ("test_flat_6x6", "oil_depot", "test_heights_8x8")


def _setup(map_id: str, max_rounds: int = 8):  # type: ignore[no-untyped-def]
    return build_setup(library(), map_id, DEMO_ALLIES, SKILLED_ENEMIES, max_rounds=max_rounds)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _events_json(events) -> str:  # type: ignore[no-untyped-def]
    return EVENT_LIST_ADAPTER.dump_json(events).decode()


@pytest.mark.parametrize("map_id", MAPS)
def test_same_seed_same_battle_with_skills(map_id: str) -> None:
    a = run_battle(_setup(map_id, 30), 42, _ai())
    b = run_battle(_setup(map_id, 30), 42, _ai())
    assert state_to_json(a.state) == state_to_json(b.state)
    assert _events_json(a.events) == _events_json(b.events)
    assert any(isinstance(e, SkillUsed) for e in a.events)


def test_use_skill_actions_round_trip_and_replay_reproduces_the_battle() -> None:
    setup = _setup("oil_depot", 30)
    run = run_battle(setup, 42, _ai())
    skill_steps = [s for s in run.actions if isinstance(s, UseSkill)]
    assert skill_steps
    for step in skill_steps:
        assert ACTION_ADAPTER.validate_json(ACTION_ADAPTER.dump_json(step)) == step
    text = STEP_LIST_ADAPTER.dump_json(run.actions)
    assert STEP_LIST_ADAPTER.validate_json(text) == run.actions
    again = replay(setup, 42, run.actions)  # 重播不需要 AI
    assert state_to_json(again.state) == state_to_json(run.state)
    assert _events_json(again.events) == _events_json(run.events)


@PROPERTY_SETTINGS
@given(
    seed=st.integers(0, 2**32),
    map_index=st.integers(0, len(MAPS) - 1),
    skill_bias=st.integers(300, 900),
)
def test_property_random_legal_actions_with_skills_never_raise(
    seed: int, map_index: int, skill_bias: int
) -> None:
    setup = _setup(MAPS[map_index])
    rng = Rng(seed)
    state = begin_battle(setup, seed).state
    for _ in range(120):
        if state.ended:
            break
        actions = legal_actions(state)
        assert has_only_end_turn(state) == (len(actions) == 1)
        skills: list[Action] = [a for a in actions if isinstance(a, UseSkill)]
        pool = skills if skills and rng.chance_permille(skill_bias) else actions
        action = rng.choice(pool)
        before = state_to_json(state)
        result = resolve(state, action)
        assert state_to_json(state) == before
        state = result.state
        for unit in state.units.values():
            assert 0 <= unit.mana <= unit.max_mana
            assert 0 <= unit.hp <= unit.max_hp
            assert all(v > 0 for v in unit.cooldowns.values())


@PROPERTY_SETTINGS
@given(seed=st.integers(0, 2**32), map_index=st.integers(0, len(MAPS) - 1))
def test_property_every_listed_skill_action_resolves_and_replays(seed: int, map_index: int) -> None:
    setup = _setup(MAPS[map_index])
    rng = Rng(seed)
    state = begin_battle(setup, seed).state
    for _ in range(40):
        if state.ended:
            break
        actions = legal_actions(state)
        for action in actions:
            if isinstance(action, UseSkill):
                first = resolve(state, action)
                second = resolve(state, action)  # 相同輸入必得相同結果
                assert state_to_json(first.state) == state_to_json(second.state)
                assert _events_json(first.events) == _events_json(second.events)
        skills = [a for a in actions if isinstance(a, UseSkill)]
        state = resolve(state, rng.choice(skills or actions)).state


def test_illegal_use_skill_leaves_the_state_untouched() -> None:
    state = begin_battle(_setup("test_flat_6x6"), 3).state
    unit = state.active
    assert unit is not None
    before = state_to_json(state)
    with pytest.raises(IllegalActionError):
        resolve(state, UseSkill(unit_id=unit.id, skill_id="skill_not_equipped", direction="east"))
    assert state_to_json(state) == before
