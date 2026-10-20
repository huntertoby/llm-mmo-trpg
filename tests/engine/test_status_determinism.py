"""Phase 2B-1 驗收 8：新狀態與抵抗判定下，重播與隨機合法動作仍然確定。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import answered, library, make_map, make_setup, spawn, template
from trpg.engine import (
    BattleSetup,
    begin_battle,
    legal_actions,
    resolve,
    state_to_json,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    EVENT_LIST_ADAPTER,
    Event,
    EventBase,
    StatusApplied,
    StatusSaveRolled,
    TurnSkipped,
)
from trpg.engine.runner import replay, run_battle
from trpg.shared.rng import Rng
from trpg.shared.types import Team

PROPERTY_SETTINGS = settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
FLAT = "\n".join(["00000000"] * 8)


def _setup(max_rounds: int = 20) -> BattleSetup:
    """法師（寒鎖、毒霧）、戰士（放血斬）對盾衛（盾擊）、頭目與盜賊：新狀態都有人會用。"""
    mage = template(
        "hero_mage",
        skills=["skill_fire_bolt", "skill_frost_shackle", "skill_venom_cloud", "skill_blink"],
    )
    ally_xy = [(0, 3), (0, 4), (1, 5)]
    enemy_xy = [(6, 3), (6, 4), (7, 5)]
    m = make_map(FLAT, ally=ally_xy, enemy=enemy_xy)
    spawns = [
        spawn(Team.ALLY, ally_xy[0], mage),
        spawn(Team.ALLY, ally_xy[1], template("hero_fighter")),
        spawn(Team.ALLY, ally_xy[2], template("hero_archer")),
        spawn(Team.ENEMY, enemy_xy[0], template("bandit_shieldbearer")),
        spawn(Team.ENEMY, enemy_xy[1], template("bandit_boss")),
        spawn(Team.ENEMY, enemy_xy[2], template("bandit_shieldbearer")),
    ]
    return make_setup(m, spawns, max_rounds=max_rounds)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _json(events: Sequence[EventBase]) -> str:
    return EVENT_LIST_ADAPTER.dump_json(cast("list[Event]", list(events))).decode()


def test_same_seed_same_battle_and_replay_with_the_new_statuses() -> None:
    applied: set[str] = set()
    kinds: set[type] = set()
    for seed in (7, 10):  # 這兩個種子的戰鬥裡會出現暈眩、抵抗判定與流血、中毒、易傷
        a = run_battle(_setup(), seed, _ai())
        b = run_battle(_setup(), seed, _ai())
        assert state_to_json(a.state) == state_to_json(b.state)
        assert _json(a.events) == _json(b.events)
        again = replay(_setup(), seed, a.actions)  # 重播不需要 AI
        assert state_to_json(again.state) == state_to_json(a.state)
        assert _json(again.events) == _json(a.events)
        applied |= {e.status_id for e in a.events if isinstance(e, StatusApplied)}
        kinds |= {type(e) for e in a.events}
    assert {"stun", "poison", "vulnerable", "bleed"} <= applied
    assert {StatusSaveRolled, TurnSkipped} <= kinds


@PROPERTY_SETTINGS
@given(seed=st.integers(0, 2**32))
def test_property_random_legal_actions_with_the_new_statuses(seed: int) -> None:
    rng = Rng(seed)
    state = begin_battle(_setup(), seed).state
    for _ in range(150):
        if state.ended:
            break
        action = rng.choice(legal_actions(state))
        before = state_to_json(state)
        first = resolve(state, action)
        second = resolve(state, action)
        assert state_to_json(state) == before  # 純函式：不修改輸入
        assert state_to_json(first.state) == state_to_json(second.state)
        assert _json(first.events) == _json(second.events)
        state = answered(first).state
        for unit in state.units.values():
            assert 0 <= unit.hp <= unit.max_hp
            assert all(v > 0 for v in unit.cooldowns.values())
            assert set(unit.control_dr) <= {"movement", "hard"}
        if state.active is not None:
            assert state.active.ap >= 0 and state.active.move_points >= 0
            assert not any(s.status_id == "stun" for s in state.active.statuses)  # 暈眩的回合被跳過
