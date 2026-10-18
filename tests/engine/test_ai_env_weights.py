"""非狡猾型行為模式的基本環境權重（Phase 2C-4 3.2）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn
from trpg.engine import Attack, BattleState, Shove
from trpg.engine.ai.orders import TacticalOrder, UseEnvironment
from trpg.engine.ai.utility import ActionScore, UtilityAI
from trpg.shared.types import Team, UnitId

U1, U3 = UnitId("unit_0001"), UnitId("unit_0003")

ENV_FIELDS = ("env_damage", "env_kill", "push", "surface", "expose")
EXPECTED = {
    "brute": (3, 40, 4, 5, 10),
    "archer": (2, 20, 3, 5, 15),
    "guard": (1, 15, 4, 4, 5),
}


def _ai(profile: str, *orders: TacticalOrder) -> UtilityAI:
    return UtilityAI(
        library().ai_profiles, override=profile, orders=(lambda _s, _u: orders) if orders else None
    )


def _shove_scene() -> BattleState:
    """行動者在 (2, 2)；滿血的盜賊在 (1, 2)，背後（x = 0）是深淵：推擊能直接擊倒他。"""
    m = make_map(
        "0000000\n0000000\n0000000",
        "x......\nx......\nx......",
        ally=[(2, 1)],
        enemy=[(1, 1)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 1), "hero_fighter"),
            spawn(Team.ALLY, (6, 2), "hero_fighter"),
            spawn(Team.ENEMY, (1, 1), "bandit"),
        ],
    )
    return give_turn(state, U1)


def _best(scores: list[ActionScore], kind: type) -> Fraction:
    return max(s.score for s in scores if isinstance(s.action, kind))


@pytest.mark.parametrize("profile", sorted(EXPECTED))
def test_every_behavior_profile_has_all_environment_weights(profile: str) -> None:
    weights = library().ai_profiles.by_id()[profile].weights
    values = tuple(getattr(weights, f) for f in ENV_FIELDS)
    assert all(v > 0 for v in values)
    assert values == EXPECTED[profile]


def test_brute_shoves_an_enemy_into_the_chasm_instead_of_a_plain_attack() -> None:
    state = _shove_scene()
    scores = _ai("brute").rank(state)
    assert _best(scores, Shove) > _best(scores, Attack)
    assert _ai("brute")(state) == Shove(unit_id=U1, target_id=U3)


@pytest.mark.parametrize("profile", sorted(EXPECTED))
def test_use_environment_order_raises_the_environment_scores(profile: str) -> None:
    state = _shove_scene()
    plain = _best(_ai(profile).rank(state), Shove)
    ordered = _best(_ai(profile, UseEnvironment()).rank(state), Shove)
    assert ordered > plain
