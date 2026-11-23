"""QF-6（佇列 (p)，E5 裁定 6）：AI 的便宜估計（``skill_estimate``）知道裝備變形閘門的降傷。

估計用和結算同一份閘門資料（:func:`trpg.engine.modifiers.reshape_damage_permille`，查規則包的
``reshape_gates``），沒有另外算一套。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import library
from tests.engine.skill_helpers import U1
from tests.engine.test_reshape_gate_e5 import BOUNCE, STRIKE, gear_library, scene
from trpg.engine import BattleState, UseSkill
from trpg.engine.ai.utility.position import _scene, position_value
from trpg.engine.ai.utility.skill_estimate import skill_estimate
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.modifiers import reshape_damage_permille
from trpg.engine.reshape_gate import FULL, gate_key


def _estimates(state: BattleState) -> list[Fraction]:
    """U1 用 ``STRIKE`` 打敵人的每個選取的估計（依合法動作順序）。"""
    unit = state.units[U1]
    weights = library().ai_profiles.profiles[0]
    actions, areas = legal_actions_with_areas(state, expand_copy=True)
    scene_data = _scene(state, unit)
    before = position_value(state, unit.id, weights.weights)
    out: list[Fraction] = []
    for action in actions:
        if isinstance(action, UseSkill) and action.skill_id == STRIKE and action.target_id != U1:
            est = skill_estimate(
                state,
                unit,
                action,
                areas[id(action)],
                scene_data,
                weights.weights,
                before,
                trap=weights.trap,
            )
            assert est is not None
            out.append(est)
    return out


def _ungated(state: BattleState) -> BattleState:
    """同一個局面，但閘門表把 ``BOUNCE`` 套在 ``STRIKE`` 上改成不降傷（1000‰）。"""
    s = state.clone()
    gates = {**s.ruleset.reshape_gates, gate_key(BOUNCE, STRIKE): FULL}
    s.ruleset = s.ruleset.model_copy(update={"reshape_gates": gates})
    return s


def test_gate_lowers_the_cheap_estimate() -> None:
    gated = scene(gear_library())
    permille = reshape_damage_permille(gated, gated.units[U1], gated.ruleset.skill_def(STRIKE))
    assert 0 < permille < FULL  # 閘門有降傷
    full = _ungated(gated)
    assert reshape_damage_permille(full, full.units[U1], full.ruleset.skill_def(STRIKE)) == FULL
    low, high = _estimates(gated), _estimates(full)
    assert low
    assert len(low) == len(high)
    assert all(a < b for a, b in zip(low, high, strict=True))


def test_no_gear_reshape_leaves_the_estimate_unchanged() -> None:
    plain = scene(gear_library(), gear=())
    assert reshape_damage_permille(plain, plain.units[U1], plain.ruleset.skill_def(STRIKE)) == FULL
    assert _estimates(plain) == _estimates(_ungated(plain))
