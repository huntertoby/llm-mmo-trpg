"""Phase 2E-2 4.3／4.5：姿態（進入花 AP、單一姿態、取代、取消免費、倒下移除、AI）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.rules import SkillSlots
from trpg.engine import (
    Attack,
    BattleState,
    EndStance,
    EndTurn,
    UseSkill,
    legal_actions,
    resolve,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, StatusApplied, StatusRemoved
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.state import StatusInstance
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Team, UnitId

FURY, BULWARK = "skill_fury_stance", "skill_bulwark_stance"
# 內容裡的姿態欄位只有 1 個；測試取代與「不重進」時放寬到 2
TWO_STANCES = SkillSlots(active=6, passive=2, reaction=1, stance=2)


def scene(extra: list[str] | None = None, *, hp: int = 999) -> BattleState:
    """U1（戰士，帶兩個姿態）在 (3, 3) 手上有回合；U2（敵人）在 (4, 3)。"""
    skills = [FURY, BULWARK, *(extra or [])]
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template(skills, base="hero_fighter", max_hp=hp)
    foe = no_reactions(max_hp=999)
    state = make_state(
        m,
        [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), foe)],
        skill_slots=TWO_STANCES,  # type: ignore[arg-type]
    )
    return give_turn(state, U1)


def stances(state: BattleState, uid: UnitId = U1) -> list[str]:
    return [s.status_id for s in state.units[uid].statuses if s.status_id.startswith("stance_")]


def test_entering_a_stance_costs_the_core_stance_ap_and_applies_the_status() -> None:
    state = scene()
    cost = state.ruleset.core.stance_ap_cost
    assert cost == 1 and state.ruleset.skill_def(FURY).ap_cost is None
    result = resolve(state, UseSkill(unit_id=U1, skill_id=FURY))
    assert result.state.units[U1].ap == state.units[U1].ap - cost
    assert stances(result.state) == ["stance_fury"]
    (applied,) = of(result, StatusApplied)
    assert applied.status_id == "stance_fury"
    stance = next(s for s in result.state.units[U1].statuses if s.status_id == "stance_fury")
    assert stance.remaining is None  # 不倒數，直到取消


def test_a_stance_stays_across_rounds() -> None:
    state = resolve(scene(), UseSkill(unit_id=U1, skill_id=FURY)).state
    ended = resolve(state, EndTurn(unit_id=U1)).state
    assert stances(ended) == ["stance_fury"]


def test_a_new_stance_replaces_the_old_one() -> None:
    state = resolve(scene(), UseSkill(unit_id=U1, skill_id=FURY)).state
    result = resolve(state, UseSkill(unit_id=U1, skill_id=BULWARK))
    assert stances(result.state) == ["stance_bulwark"]
    removed = of(result, StatusRemoved)
    assert [(r.status_id, r.reason) for r in removed] == [("stance_fury", "replaced")]


def test_the_same_stance_cannot_be_entered_twice() -> None:
    state = resolve(scene(), UseSkill(unit_id=U1, skill_id=FURY)).state
    ids = [a.skill_id for a in legal_actions(state) if isinstance(a, UseSkill)]
    assert FURY not in ids and BULWARK in ids
    with pytest.raises(IllegalActionError):
        resolve(state, UseSkill(unit_id=U1, skill_id=FURY))


def test_end_stance_is_free_and_only_legal_with_a_stance() -> None:
    state = scene()
    assert not [a for a in legal_actions(state) if isinstance(a, EndStance)]
    with pytest.raises(IllegalActionError):
        resolve(state, EndStance(unit_id=U1))
    entered = resolve(state, UseSkill(unit_id=U1, skill_id=BULWARK)).state
    assert [a for a in legal_actions(entered) if isinstance(a, EndStance)]
    result = resolve(entered, EndStance(unit_id=U1))
    assert result.state.units[U1].ap == entered.units[U1].ap  # 免費
    assert stances(result.state) == []
    (removed,) = of(result, StatusRemoved)
    assert removed.reason == "stance_ended"


def test_a_stance_is_not_removed_by_cleanse() -> None:
    purify = make_skill(
        "skill_t_cleanse_self",
        {"type": "self"},
        [{"type": "cleanse", "affects": "self"}],
        category="weapon",
    )
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([FURY, purify], base="hero_fighter")
    state = give_turn(
        make_state(
            m,
            [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions())],
            skills=[purify],
        ),
        U1,
    )
    state = resolve(state, UseSkill(unit_id=U1, skill_id=FURY)).state
    state.units[U1].statuses.append(StatusInstance("burning", 2, U2))
    result = resolve(state, UseSkill(unit_id=U1, skill_id=purify.id))
    assert stances(result.state) == ["stance_fury"]
    assert not any(s.status_id == "burning" for s in result.state.units[U1].statuses)


def test_a_stance_is_removed_when_the_unit_goes_down(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=19, die=8)
    state = resolve(scene(hp=5), UseSkill(unit_id=U1, skill_id=BULWARK)).state
    state = give_turn(state, U2)
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert result.state.units[U1].downed
    assert stances(result.state) == []
    assert ("stance_bulwark", "downed") in [
        (r.status_id, r.reason) for r in of(result, StatusRemoved)
    ]


def test_stance_effects_change_damage_taken_and_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19, die=6)

    def taken(stance: str | None) -> int:
        state = scene()
        if stance is not None:
            state = resolve(state, UseSkill(unit_id=U1, skill_id=stance)).state
        result = resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U1))
        return sum(e.amount for e in of(result, DamageDealt))

    plain, fury, bulwark = taken(None), taken(FURY), taken(BULWARK)
    assert bulwark < plain < fury
    state = resolve(scene(), UseSkill(unit_id=U1, skill_id=FURY)).state
    base = scene()
    rules = state.ruleset
    assert effective_attribute(rules, state.units[U1], Attribute.STR) == (
        effective_attribute(rules, base.units[U1], Attribute.STR) + 2
    )


def test_the_ai_does_not_cancel_or_reenter_a_stance() -> None:
    ai = UtilityAI(library().ai_profiles)
    state = resolve(scene(), UseSkill(unit_id=U1, skill_id=FURY)).state
    for _ in range(3):
        action = ai(state)
        assert not isinstance(action, EndStance)
        assert not (isinstance(action, UseSkill) and action.skill_id == FURY)
        break
    scores = ai.rank(state)
    assert not any(isinstance(s.action, UseSkill) and s.action.skill_id == FURY for s in scores)
    assert not any(isinstance(s.action, EndStance) for s in scores)


def test_the_ai_values_entering_a_stance_when_it_has_nothing_better() -> None:
    state = scene()
    state.units[U1].ap = 1
    state.units[U2].pos = type(state.units[U2].pos)(x=6, y=6)
    state.units[U1].move_points = 0
    scores = UtilityAI(library().ai_profiles).rank(state)
    assert any(
        isinstance(s.action, UseSkill) and s.action.skill_id in (FURY, BULWARK) for s in scores
    )
