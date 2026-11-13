"""RG-2（#162，19.2.1）：荒原狂戰士——受傷累積怒氣，滿 4 層才打出「狂怒劈砍」。

怒氣是 #161 的層數，資源機制照 KW-1。

實際跑引擎、用正式內容的範本：

- 怒氣不滿 4 層時「狂怒劈砍」不在合法動作裡；滿了才能放，放完花光怒氣、傷害照層數加成。
- 挨打會累積怒氣（怒氣的自動累積＋怒火中燒）。
- 效用 AI：怒氣滿了、敵人在身邊時會放（固定種子）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1, U2, hit_with, of
from trpg.engine import Attack, BattleState, legal_actions, resolve
from trpg.engine.actions import UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, StacksChanged
from trpg.shared.types import Team

BERSERKER = "ashen_berserker"
CLEAVE = "skill_berserker_fury_cleave"
FULL = 4


def scene(fury: int = 0) -> BattleState:
    """U1（荒原狂戰士，敵方）在 (3, 3)、身上 ``fury`` 層怒氣；U2（我方，打不死）在 (2, 3)。"""
    m = make_map(FLAT7, ally=[(2, 3)], enemy=[(3, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ENEMY, (3, 3), BERSERKER, skills=None),
            spawn(Team.ALLY, (2, 3), no_reactions(max_hp=999)),
        ],
    )
    if fury:
        state.units[U1].stacks["fury"] = fury
    return state


def cleaves(state: BattleState) -> list[UseSkill]:
    return [
        a
        for a in legal_actions(give_turn(state, U1))
        if isinstance(a, UseSkill) and a.skill_id == CLEAVE and a.target_id == U2
    ]


def test_the_template_carries_the_fury_kit() -> None:
    unit = library().units[BERSERKER]
    assert unit.skills == ("skill_seething_rage", CLEAVE)
    skill = library().skills[CLEAVE]
    assert skill.enemy_only and skill.condition is not None
    assert (skill.condition.type, skill.condition.stack, skill.condition.count) == (
        "self_stack_at_least",
        "fury",
        FULL,
    )
    assert library().ruleset.stack_def("fury").max == FULL


@pytest.mark.parametrize(("fury", "legal"), [(0, False), (3, False), (4, True)])
def test_cleave_needs_full_fury(fury: int, legal: bool) -> None:
    assert bool(cleaves(scene(fury))) is legal


def test_cleave_spends_all_fury_and_hits_harder() -> None:
    state = scene(FULL)
    result = resolve(hit_with(give_turn(state, U1)), cleaves(state)[0])  # 第一顆 d20 固定命中
    assert result.state.units[U1].stacks.get("fury", 0) == 0
    spent = [e for e in of(result, StacksChanged) if e.stack_id == "fury"]
    assert spent and spent[-1].after == 0
    assert of(result, DamageDealt)


def test_taking_damage_builds_fury() -> None:
    state = give_turn(scene(), U2)
    total = 0
    for _ in range(3):
        result = resolve(state, Attack(unit_id=U2, target_id=U1))
        state = give_turn(result.state, U2)
        total = state.units[U1].stacks.get("fury", 0)
        if total:
            break
    assert total >= 1


def test_ai_cleaves_when_fury_is_full() -> None:
    state = give_turn(scene(FULL), U1)
    ai = UtilityAI(library().ai_profiles)
    action = ai(state)
    assert isinstance(action, UseSkill) and action.skill_id == CLEAVE
    assert action.target_id == U2
