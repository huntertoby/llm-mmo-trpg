"""LW-1（BAL-21c 候選 B）：碎晶之主被定身時不能放「界隙閃擊」，AI 改選別的招；只限這一招。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn
from tests.engine.skill_helpers import FLAT7, U2
from trpg.content.skills import ConditionSpec
from trpg.engine import BattleState, UseSkill, legal_actions
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team
from trpg.world.battle import grow_enemy

FLICK = "skill_rift_flicker"


def _arena(skills: tuple[str, ...] = (FLICK,)) -> BattleState:
    lib = library()
    tpl = lib.enemy_catalog().template("rift_shard_lord")
    tpl = tpl.model_copy(update={"skills": skills, "phases": ()})
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(4, 3)])
    spawns = [spawn(Team.ALLY, (1, 3), "hero_fighter", skills=None), spawn(Team.ENEMY, (4, 3), tpl)]
    return give_turn(make_state(m, spawns), U2)


def _rooted(state: BattleState) -> BattleState:
    state = state.clone()
    state.units[U2].statuses.append(StatusInstance("root", 1))
    return state


def _flickers(state: BattleState) -> list[UseSkill]:
    return [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == FLICK]


def test_the_skill_carries_the_condition_and_keeps_its_budget() -> None:
    skill = library().skills[FLICK]
    assert skill.condition == ConditionSpec(type="self_lacks_status", status="root")
    definition = library().ruleset.conditions.by_id()["self_lacks_status"]
    assert definition.enemy_only and definition.budget_permille == 1000  # 加條件不改預算


def test_upgraded_versions_keep_the_condition() -> None:
    """實戰放的是升階版（``_t3``），條件要一起帶過去。"""
    lib = library()
    _grown, skills = grow_enemy(lib, lib.unit("rift_shard_lord"), 10)
    flickers = [s for s in skills if s.id.startswith(FLICK)]
    assert flickers
    assert all(s.condition == library().skills[FLICK].condition for s in flickers)


def test_flicker_is_legal_unless_rooted() -> None:
    state = _arena()
    assert _flickers(state)
    assert _flickers(_rooted(state)) == []


@pytest.mark.parametrize("status", ["slow", "weaken"])
def test_other_statuses_do_not_block_it(status: str) -> None:
    state = _arena()
    state.units[U2].statuses.append(StatusInstance(status, 1))
    assert _flickers(state)


def test_teleports_are_still_not_blocked_by_root_in_general() -> None:
    """不是「定身擋所有自身傳送」：只有界隙閃擊帶條件，其他傳送招沒有。"""
    lib = library()
    for skill in lib.skills.values():
        if skill.id == FLICK:
            continue
        conditions = [skill.condition] if skill.condition is not None else []
        assert all(c.type != "self_lacks_status" for c in conditions), skill.id


def test_rooted_ai_picks_something_else() -> None:
    state = _rooted(_arena((FLICK, "skill_rift_shatter")))
    ai = UtilityAI(library().ai_profiles)
    action = ai(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == FLICK)
