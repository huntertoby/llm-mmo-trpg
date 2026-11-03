"""BAL-15c（玩法決定 #83，05 5.2.1）：裝了反應技時預設先用反應技、不自動格擋（敵我同樣）；
玩家可以在反應設定把格擋改回自動（格擋優先）。#84：隊友、敵人、召喚物每場開場法力滿。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.battle import ReactionRule, ReactionWhen
from trpg.engine import Attack, BattleState, SetReactionMode, resolve
from trpg.engine.events import ReactionTriggered
from trpg.engine.lifecycle import make_unit
from trpg.engine.state import UnitState
from trpg.shared.types import Attribute, Pos, Team, UnitId

RIPOSTE = "skill_riposte"


def _modes(unit: UnitState) -> dict[str, str]:
    return {rule.reaction: rule.mode for rule in unit.reactions}


def _duel(owner_team: Team = Team.ALLY, skills: tuple[str, ...] = (RIPOSTE,)) -> BattleState:
    """U1（戰士，範本沒寫反應規則＝預設規則）在 (3, 3)；U2（沒有反應的盜賊）在 (4, 3)。"""
    other = Team.ENEMY if owner_team is Team.ALLY else Team.ALLY
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = template("hero_fighter", max_hp=999, skills=list(skills))
    assert owner.reactions is None
    foe = no_reactions("bandit", max_hp=999)
    first = spawn(owner_team, (3, 3) if owner_team is Team.ALLY else (4, 3), owner)
    second = spawn(other, (4, 3) if owner_team is Team.ALLY else (3, 3), foe)
    units = [first, second] if owner_team is Team.ALLY else [second, first]
    return make_state(m, units)


def _owner(state: BattleState) -> UnitState:
    return next(u for u in state.units_sorted() if RIPOSTE in u.skills)


@pytest.mark.parametrize("team", [Team.ALLY, Team.ENEMY])
def test_a_reaction_skill_turns_the_default_block_off(team: Team) -> None:
    unit = _owner(_duel(team))
    assert unit.reactions[0].reaction == RIPOSTE  # 反應技的 auto 規則排最前面
    assert _modes(unit) == {RIPOSTE: "auto", "block": "off", "opportunity_attack": "auto"}


def test_without_a_reaction_skill_the_default_block_stays_on() -> None:
    unit = _duel(skills=())
    assert _modes(unit.units[U1]) == {"block": "auto", "opportunity_attack": "auto"}


def test_written_reaction_rules_are_left_alone() -> None:
    lib = library()
    written = (ReactionRule(reaction="block", when=ReactionWhen(event="targeted_by_attack")),)
    tmpl = template("hero_fighter", skills=[RIPOSTE], reactions=[written[0].model_dump()])
    unit = make_unit(
        UnitId("u9"),
        template=tmpl,
        weapon=lib.weapon_of(tmpl),
        team=Team.ENEMY,
        pos=Pos(x=0, y=0),
        name="測試",
        rules=lib.ruleset,
    )
    assert _modes(unit) == {RIPOSTE: "auto", "block": "auto"}


def test_riposte_fires_by_default_when_meleed(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = give_turn(_duel(), U2)
    (trig,) = of(resolve(state, Attack(unit_id=U2, target_id=U1)), ReactionTriggered)
    assert trig.reaction == RIPOSTE


def test_the_player_can_switch_back_to_block_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """反應設定把格擋改回自動：格擋在傷害前結算，先用掉本輪唯一的反應，還擊不觸發。"""
    always(monkeypatch)
    state = give_turn(_duel(), U1)
    switched = resolve(state, SetReactionMode(unit_id=U1, reaction="block", mode="auto")).state
    assert _modes(switched.units[U1])["block"] == "auto"
    result = resolve(give_turn(switched, U2), Attack(unit_id=U2, target_id=U1))
    assert [t.reaction for t in of(result, ReactionTriggered)] == ["block"]


def test_summons_enemies_and_allies_start_with_full_mana() -> None:
    """#84：法力只在營火回滿只限跨場延續的單位（主角）；其他單位每場新上場，開場法力滿。"""
    lib = library()
    state = _duel()
    for unit in state.units_sorted():
        assert unit.mana == unit.max_mana > 0
    summon = lib.ruleset.summons.by_id()["summon_fire_spirit"]
    caster_attrs = {a: 14 for a in Attribute}
    unit = make_unit(
        UnitId("s1"),
        template=summon.template,
        weapon=summon.weapon,
        team=Team.ALLY,
        pos=Pos(x=0, y=0),
        name="召喚物",
        rules=lib.ruleset,
        resource_attributes=caster_attrs,
    )
    assert unit.mana == unit.max_mana > 0
