"""KW-1 的性質測試（hypothesis）：同種子同結果；雙匕首每次出招最多 +1 連擊點；「層數達 N」只看
施放開始時的層數。

場景沿用 :mod:`tests.engine.test_stack_condition_kw1`：U1 拿雙匕首、帶連擊終結（所以命中會自動
累積），對相鄰敵人施放單體武器技。種子與開場層數由 hypothesis 產生，骰子不改。
"""

from __future__ import annotations

import os

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.engine.skill_helpers import U1, U2
from tests.engine.test_stack_condition_kw1 import FINISH, STRIKE, scene, weapon_skill
from trpg.engine import BattleState, resolve, state_to_json
from trpg.engine.actions import UseSkill
from trpg.engine.events import EVENT_LIST_ADAPTER, ShieldGained, StacksChanged
from trpg.engine.results import ResolveResult
from trpg.shared.rng import Rng

SETTINGS = settings(
    max_examples=40 if os.environ.get("TRPG_FULL") == "1" else 12,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
SID = "skill_t_prim"


def seeded(state: BattleState, seed: int) -> BattleState:
    s = state.clone()
    s.rng_state = Rng(seed).get_state()
    return s


def cast(state: BattleState) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))


def snapshot(result: ResolveResult) -> tuple[str, str]:
    events = EVENT_LIST_ADAPTER.dump_json(result.events).decode()  # type: ignore[arg-type]
    return events, state_to_json(result.state)


@SETTINGS
@given(seed=st.integers(0, 2**32), combo=st.integers(0, 5), finisher=st.booleans())
def test_the_same_seed_gives_the_same_result(seed: int, combo: int, finisher: bool) -> None:
    skill = weapon_skill(FINISH if finisher else STRIKE)
    state = seeded(scene(skill, combo=combo, weapon="dual_dagger"), seed)
    assert snapshot(cast(state)) == snapshot(cast(state))


@SETTINGS
@given(seed=st.integers(0, 2**32), combo=st.integers(0, 4))
def test_dual_daggers_gain_at_most_one_combo_point_per_cast(seed: int, combo: int) -> None:
    state = seeded(scene(weapon_skill(STRIKE), combo=combo, weapon="dual_dagger"), seed)
    result = cast(state)
    gained = [e for e in result.events if isinstance(e, StacksChanged) and e.reason == "gained"]
    assert len(gained) <= 1
    after = result.state.units[U1].stacks.get("combo_point", 0)
    assert after - combo == len(gained)


@SETTINGS
@given(seed=st.integers(0, 2**32), combo=st.integers(0, 5))
def test_the_stack_condition_reads_the_stacks_at_cast_start(seed: int, combo: int) -> None:
    """終結技先花光層數；「滿 3 層」的護盾只看開場的層數（打中與否都一樣，護盾對自己）。"""
    state = seeded(scene(weapon_skill(FINISH), combo=combo, weapon="dual_dagger"), seed)
    result = cast(state)
    shielded = any(isinstance(e, ShieldGained) for e in result.events)
    assert shielded is (combo >= 3)
