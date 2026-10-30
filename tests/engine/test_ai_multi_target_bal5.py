"""BAL-5 B1：範圍技每多打到一名敵人的加分。

權重是 ``multi_target``，寫在 ``content/ai_profiles.yaml`` 的 ``skill_ai``。
"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import library
from tests.engine.test_weapons_24a2 import U1, armed, foe, state_of, weapon
from trpg.content.environment import AiProfile
from trpg.engine import UseSkill, legal_actions
from trpg.engine.ai.utility import extra_targets, score_action
from trpg.engine.preview import preview
from trpg.shared.types import Team

PIERCE = "skill_piercing_shot"


def _archer() -> AiProfile:
    return next(p for p in library().ai_profiles.profiles if p.id == "archer")


def _state(*foes: tuple[int, int]):  # type: ignore[no-untyped-def]
    hero = armed(Team.ALLY, (1, 2), weapon("bow"), skills=[PIERCE], max_mana=30)
    return state_of([hero, *(foe(xy, max_hp=200) for xy in foes)])


def _pierce_actions(state) -> list[UseSkill]:  # type: ignore[no-untyped-def]
    return [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == PIERCE]


def test_every_profile_gets_the_shared_multi_target_weight() -> None:
    for p in library().ai_profiles.profiles:
        if p.id != "idle":
            assert p.weights.multi_target > 0, p.id


def test_extra_targets_counts_expected_enemies_beyond_the_first() -> None:
    state = _state((4, 2), (5, 2))
    best = max(
        (extra_targets(state, state.units[U1], preview(state, a)) for a in _pierce_actions(state)),
        default=Fraction(0),
    )
    assert Fraction(0) < best <= 1
    single = _state((4, 2))
    assert all(
        extra_targets(single, single.units[U1], preview(single, a)) == 0
        for a in _pierce_actions(single)
    )


def test_multi_target_raises_the_score_of_an_area_skill_hitting_two() -> None:
    state = _state((4, 2), (5, 2))
    p = _archer()
    zero = p.model_copy(update={"weights": p.weights.model_copy(update={"multi_target": 0})})
    action = max(
        _pierce_actions(state),
        key=lambda a: extra_targets(state, state.units[U1], preview(state, a)),
    )
    extra = extra_targets(state, state.units[U1], preview(state, action))
    diff = score_action(state, action, p).score - score_action(state, action, zero).score
    assert diff == p.weights.multi_target * extra
