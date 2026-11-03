"""BAL-4c：``mana_cost_permille`` 在施放時套用，扣費、施放檢查、事件、AI 估價一致，技能資料保持原始
費用。BAL-15b（玩法決定 #80）起敵我同一套：敵方施放者也打折（BAL-4c 時敵方原價）。"""

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
)
from tests.engine.skill_helpers import FLAT7
from trpg.engine import UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import skill_cost
from trpg.engine.events import SkillUsed
from trpg.engine.skills.targeting import resource_problem, skill_mana_cost
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
FIRE_BOLT = "skill_fire_bolt"


def _state(caster_team: Team, mana: int | None = None) -> BattleState:
    """``caster_team`` 的法師在 (1, 3) 對 3 格外的對手施放火焰箭。"""
    other = Team.ENEMY if caster_team is Team.ALLY else Team.ALLY
    zones = ([(1, 3)], [(4, 3)]) if caster_team is Team.ALLY else ([(4, 3)], [(1, 3)])
    m = make_map(FLAT7, ally=zones[0], enemy=zones[1])
    spawns = [
        spawn(caster_team, (1, 3), caster_template([FIRE_BOLT])),
        spawn(other, (4, 3), no_reactions(max_hp=99)),
    ]
    state = give_turn(make_state(m, spawns), U1)
    if mana is not None:
        state.units[U1].mana = mana
    return state


def _raw() -> int:
    return library().skills[FIRE_BOLT].cost.mana


def _ally() -> int:
    return library().ruleset.core.mana_cost(_raw())


def test_content_has_a_real_discount_for_the_test_skill() -> None:
    assert library().ruleset.core.mana_cost_permille == 800
    assert library().ruleset.skill_def(FIRE_BOLT).cost.mana == _raw()  # 規則包也是原始費用
    assert _ally() < _raw()  # 八折後仍比原始費用少（讀 content，不寫死）


@pytest.mark.parametrize("team", [Team.ALLY, Team.ENEMY])
def test_casting_pays_the_discounted_cost_for_both_teams(team: Team) -> None:
    state = _state(team)
    expected = _ally()
    skill = state.ruleset.skill_def(FIRE_BOLT)
    assert skill_mana_cost(state.ruleset.core, state.units[U1], skill) == expected
    before = state.units[U1].mana
    result = resolve(state, UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2))
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    assert used.mana == expected
    assert result.state.units[U1].mana == before - expected == used.mana_after


@pytest.mark.parametrize("team", [Team.ALLY, Team.ENEMY])
def test_cast_check_uses_the_discounted_cost_for_both_teams(team: Team) -> None:
    skill = library().ruleset.skill_def(FIRE_BOLT)
    enough = _state(team, mana=_ally())
    assert resource_problem(enough, enough.units[U1], skill) is None
    assert any(isinstance(a, UseSkill) and a.skill_id == FIRE_BOLT for a in legal_actions(enough))
    short = _state(team, mana=_ally() - 1)
    problem = resource_problem(short, short.units[U1], skill)
    assert problem == f"法力不足：需要 {_ally()}，剩餘 {_ally() - 1}"
    assert not any(
        isinstance(a, UseSkill) and a.skill_id == FIRE_BOLT for a in legal_actions(short)
    )


def test_ai_values_the_mana_it_actually_pays() -> None:
    profile = library().ai_profiles.by_id()["brute"]
    action = UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2)
    ally, enemy = _state(Team.ALLY), _state(Team.ENEMY)
    ally_cost = skill_cost(ally, ally.units[U1], action, profile.weights, profile.status_values)
    enemy_cost = skill_cost(enemy, enemy.units[U1], action, profile.weights, profile.status_values)
    assert enemy_cost == ally_cost  # 敵我同一套（BAL-15b）


def test_neutral_permille_means_no_discount() -> None:
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (1, 3), caster_template([FIRE_BOLT])),
        spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=99)),
    ]
    state = give_turn(make_state(m, spawns, mana_cost_permille=1000), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2))
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    assert used.mana == _raw()
