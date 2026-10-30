"""BAL-5 B5：召喚物特性的 AI 估值（護盾、拉扯、纏繞、高台）與灌注省下的 AP。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import library
from tests.engine.test_weapons_24a2 import armed, foe, state_of, weapon
from trpg.content.environment import AiProfile
from trpg.engine.ai.infuse import ap_ratio, infuse_value
from trpg.engine.ai.summon import _value
from trpg.engine.state import BattleState
from trpg.shared.types import Team

_ZERO = {
    "shield_round_permille": 0,
    "pull_round_points": 0,
    "snare_likelihood_permille": 0,
    "platform_points": 0,
}


def _profile(zero: bool = False) -> AiProfile:
    p = next(p for p in library().ai_profiles.profiles if p.id == "archer")
    if zero:
        return p.model_copy(update={"summon": p.summon.model_copy(update=_ZERO)})
    return p


def _state(ranged_allies: int = 1) -> BattleState:
    spawns = [armed(Team.ALLY, (1, 2), weapon("bow" if ranged_allies else "one_handed_sword"))]
    return state_of([*spawns, foe((6, 2))])


def _worth(template: str, *, zero: bool = False, state: BattleState | None = None) -> Fraction:
    s = state or _state()
    return _value(s, template, 2, xy=(2, 2), team=Team.ALLY, profile=_profile(zero))


def test_the_trait_weights_are_data_and_nonzero() -> None:
    rules = _profile().summon
    assert rules.shield_round_permille > 0
    assert rules.pull_round_points > 0
    assert rules.snare_likelihood_permille > 0
    assert rules.platform_points > 0
    assert rules.infuse_value_permille == 1300  # 玩法 PM BAL-5：灌注優先於直接施放


@pytest.mark.parametrize(
    "template",
    ["summon_guardian_spirit", "summon_pull_totem", "summon_vine", "summon_plateau_totem"],
)
def test_each_trait_summon_is_worth_more_than_without_trait_values(template: str) -> None:
    assert _worth(template) > _worth(template, zero=True)


def test_a_plain_attacker_summon_is_unchanged() -> None:
    assert _worth("summon_skeleton_warrior") == _worth("summon_skeleton_warrior", zero=True)


def test_the_platform_is_worth_nothing_without_ranged_allies() -> None:
    melee = _state(ranged_allies=0)
    assert _worth("summon_plateau_totem", state=melee) == _worth(
        "summon_plateau_totem", zero=True, state=melee
    )


def test_infusing_a_two_ap_skill_counts_the_saved_ap() -> None:
    state = _state()
    assert ap_ratio(state, "skill_fire_bolt") == 1  # 1 AP 的技能：不省 AP
    assert state.ruleset.skill_def("skill_air_burst").ap_cost == 2
    assert ap_ratio(state, "skill_air_burst") == 2
    rules = _profile().summon
    scale = Fraction(rules.infuse_value_permille, 1000)
    assert infuse_value(Fraction(10), Fraction(1), rules, Fraction(2)) == 20 * scale
