"""BAL-19e（玩法決定 #110，06 6.27.4）：手寫反應 +8（感知、意志各至少 2，含法術
反應，觸發事件分散）、姿態感知／意志各 2；新技能過預算與驗證，並在引擎裡真的會觸發。"""

from __future__ import annotations

from collections import Counter

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.engine import Attack, BattleState, UseSkill, resolve
from trpg.engine.events import DamageDealt, ReactionTriggered, ShieldGained
from trpg.shared.types import Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

LIB = library()
REACTIONS = sorted(s for s in LIB.skills if s.startswith("skill_rx_"))
STANCES = sorted(s for s in LIB.skills if s.startswith("skill_st_"))


def test_eight_reactions_spread_over_events_and_attributes() -> None:
    assert len(REACTIONS) == 8
    skills = [LIB.skills[s] for s in REACTIONS]
    assert all(s.kind == "reaction" and s.reaction is not None for s in skills)
    events = Counter(s.reaction.event for s in skills if s.reaction is not None)
    assert len(events) >= 6 and max(events.values()) <= 2  # 不是全都同一種還擊
    attrs = Counter(s.scaling_attr.value for s in skills)
    assert attrs["wis"] >= 2 and attrs["wil"] >= 2
    spells = {s.scaling_attr.value for s in skills if s.category == "spell"}
    assert {"wis", "wil"} <= spells  # 含法術反應


def test_two_wisdom_and_two_will_stances() -> None:
    skills = [LIB.skills[s] for s in STANCES]
    assert all(s.kind == "stance" and s.shape.type == "self" for s in skills)
    assert Counter(s.scaling_attr.value for s in skills) == {"wis": 2, "wil": 2}
    for skill in skills:
        status = skill.effects[0].status
        assert status is not None and LIB.ruleset.status_def(status).stance


@pytest.mark.parametrize("skill_id", [*REACTIONS, *STANCES])
def test_new_skills_pass_validation_and_budget(skill_id: str) -> None:
    skill = LIB.skills[skill_id]
    assert validate_skill(skill, LIB) == []
    assert 0.7 <= float(skill_budget(skill, LIB).ratio) <= 1.0


def _duel(skill_id: str, *, foe: str, foe_xy: tuple[int, int]) -> BattleState:
    """U1（反應技持有者，法師）在 (3, 3)；U2（敵人）在 ``foe_xy``，輪到敵人。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[foe_xy])
    owner = caster_template([skill_id], base="hero_mage", max_hp=999)
    spawns = [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, foe_xy, foe_template(foe))]
    return give_turn(make_state(m, spawns), U2)


def foe_template(foe: str):  # type: ignore[no-untyped-def]
    if foe == "mage":
        return caster_template(["skill_fire_bolt"], base="hero_mage", max_hp=999)
    return no_reactions(foe, max_hp=999)


def test_spell_ward_shields_before_the_spell_lands(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _duel("skill_rx_spell_ward", foe="mage", foe_xy=(5, 3))
    result = resolve(state, UseSkill(unit_id=U2, skill_id="skill_fire_bolt", target_id=U1))
    (trig,) = of(result, ReactionTriggered)
    assert trig.reaction == "skill_rx_spell_ward"
    names = [type(e) for e in result.events]
    assert names.index(ShieldGained) < names.index(DamageDealt)


def test_frost_backlash_hurts_the_melee_attacker(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _duel("skill_rx_frost_backlash", foe="bandit", foe_xy=(4, 3))
    hp = state.units[U2].hp
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    (trig,) = of(result, ReactionTriggered)
    assert (trig.reaction, trig.trigger_unit_id) == ("skill_rx_frost_backlash", U2)
    assert result.state.units[U2].hp < hp


def test_slip_away_hides_and_hastes_the_owner_when_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _duel("skill_rx_slip_away", foe="bandit", foe_xy=(4, 3))
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    (trig,) = of(result, ReactionTriggered)
    assert trig.reaction == "skill_rx_slip_away"
    statuses = {s.status_id for s in result.state.units[U1].statuses}
    assert {"concealed", "hasted"} <= statuses
