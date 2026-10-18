"""Phase 2E-3 5.1：層數（累積、上限、消耗、過期、施放需求、AI 偏好）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, EndTurn, UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, StacksChanged
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Team

PALM, THUNDER = "skill_static_palm", "skill_thunder_finisher"
SUNDER_HIT, BREAKER = "skill_sunder_strike", "skill_armor_breaker"
HIT = [(20, 19)]  # 命中、不暴擊


def scene(skills: list[str], *, base: str = "hero_mage", foe_hp: int = 999) -> BattleState:
    """U1 帶 ``skills``，在 (3, 3) 手上有回合；U2（敵人，沒有反應）在 (4, 3)。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    return give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (3, 3), caster_template(skills, base=base)),
                spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=foe_hp)),
            ],
        ),
        U1,
    )


def use(state: BattleState, skill: str, *, rolls: list[tuple[int, int]] | None = None):  # type: ignore[no-untyped-def]
    s = with_rolls(state, rolls if rolls is not None else HIT)
    return resolve(s, UseSkill(unit_id=U1, skill_id=skill, target_id=U2))


def skill(skill_id: str) -> SkillDef:
    return library().skills[skill_id]


def test_the_builder_adds_a_charge_to_the_caster_only_when_it_hits() -> None:
    state = scene([PALM])
    result = use(state, PALM)
    (changed,) = of(result, StacksChanged)
    assert (changed.unit_id, changed.stack_id, changed.before, changed.after, changed.reason) == (
        U1,
        "static_charge",
        0,
        1,
        "gained",
    )
    assert result.state.units[U1].stacks == {"static_charge": 1}
    missed = use(state, PALM, rolls=[(20, 2)])
    assert not of(missed, StacksChanged) and missed.state.units[U1].stacks == {}


def test_stacks_are_capped_at_the_maximum() -> None:
    state = scene([PALM])
    state.units[U1].stacks = {"static_charge": 5}
    result = use(state, PALM)
    assert result.state.units[U1].stacks == {"static_charge": 5}
    assert not of(result, StacksChanged)


def test_a_finisher_needs_the_required_stacks_to_be_cast() -> None:
    state = scene([THUNDER])
    assert skill(THUNDER).cost.stacks == 2
    assert not [a for a in legal_actions(state) if isinstance(a, UseSkill)]
    with pytest.raises(IllegalActionError):
        use(state, THUNDER)
    state.units[U1].stacks = {"static_charge": 1}
    with pytest.raises(IllegalActionError):
        use(state, THUNDER)
    state.units[U1].stacks = {"static_charge": 2}
    assert [a for a in legal_actions(state) if isinstance(a, UseSkill)]


def test_the_finisher_consumes_all_charges_and_boosts_its_damage() -> None:
    def damage(charges: int) -> DamageDealt:
        state = scene([THUNDER])
        state.units[U1].stacks = {"static_charge": charges}
        result = use(state, THUNDER, rolls=[(20, 19), (10, 5), (10, 5)])
        assert result.state.units[U1].stacks == {}
        (consumed,) = of(result, StacksChanged)
        assert (consumed.before, consumed.after, consumed.reason) == (charges, 0, "consumed")
        (dealt,) = of(result, DamageDealt)
        return dealt

    two, five = damage(2), damage(5)
    assert two.multiplier_permille == 1500 and five.multiplier_permille == 2250
    assert five.amount > two.amount


def test_stacks_on_the_target_are_added_and_consumed_from_the_target() -> None:
    state = scene([SUNDER_HIT, BREAKER], base="hero_fighter")
    first = use(state, SUNDER_HIT)
    assert first.state.units[U2].stacks == {"sunder": 1} and first.state.units[U1].stacks == {}
    state = give_turn(first.state, U1)
    state.units[U2].stacks = {"sunder": 3}
    result = use(state, BREAKER)
    assert result.state.units[U2].stacks == {}
    (dealt,) = of(result, DamageDealt)
    assert dealt.multiplier_permille == 2850  # 武器倍率 1500 × (1 + 3 層 × 30%)
    (consumed,) = of(result, StacksChanged)
    assert (consumed.unit_id, consumed.reason) == (U2, "consumed")


def test_a_target_finisher_works_with_no_stacks() -> None:
    result = use(scene([BREAKER], base="hero_fighter"), BREAKER)
    (dealt,) = of(result, DamageDealt)
    assert dealt.multiplier_permille == 1500 and not of(result, StacksChanged)


def test_target_stacks_expire_three_rounds_after_the_last_refresh() -> None:
    state = scene([SUNDER_HIT], base="hero_fighter")
    state = use(state, SUNDER_HIT).state
    assert state.units[U2].stack_expiry == {"sunder": state.round + 3}
    start = state.round
    seen: list[bool] = []
    while state.round < start + 3:
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state  # type: ignore[arg-type]
        seen.append("sunder" in state.units[U2].stacks)
    assert seen[0] and not seen[-1]
    assert state.units[U2].stacks == {} and state.units[U2].stack_expiry == {}


def test_a_refresh_extends_the_expiry() -> None:
    state = scene([SUNDER_HIT], base="hero_fighter")
    state.round = 2
    state = use(state, SUNDER_HIT).state
    assert state.units[U2].stack_expiry["sunder"] == 5
    state.round = 3
    state = use(give_turn(state, U1), SUNDER_HIT).state
    assert state.units[U2].stacks == {"sunder": 2} and state.units[U2].stack_expiry["sunder"] == 6


def test_the_ai_prefers_the_finisher_when_it_has_charges() -> None:
    state = scene([PALM, THUNDER])
    state.units[U1].stacks = {"static_charge": 4}
    state.units[U1].mana = 99
    ai = UtilityAI(library().ai_profiles)
    best = max(ai.rank(state), key=lambda s: s.score).action
    assert isinstance(best, UseSkill) and best.skill_id == THUNDER


def test_the_ai_builds_charges_when_it_cannot_finish() -> None:
    state = scene([PALM, THUNDER])
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == PALM


def test_a_builder_hit_that_defeats_the_target_still_adds_the_charge() -> None:
    state = scene([PALM], foe_hp=1)
    result = use(state, PALM)
    assert result.state.units[U2].downed
    assert result.state.units[U1].stacks == {"static_charge": 1}
