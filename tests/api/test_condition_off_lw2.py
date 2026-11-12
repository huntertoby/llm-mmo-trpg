"""LW-2 戰鬥中標灰（06 6.37「提示與標灰」，#156）：:func:`trpg.api.condition_off.skills_off`。

獨行時沒有標灰；帶隊友開戰時，帶獨狼條件的技能列出、分清「整招」與「只有一部分」；沒帶獨狼條件的
技能不列；``any_of`` 混了會變動的分支不標。
"""

from __future__ import annotations

from tests.engine.helpers import make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1
from trpg.api.condition_off import OFF_REASON_ZH, skills_off, sticky_conditions, sticky_kinds
from trpg.api.schemas import BattleResponse, SkillOffOut
from trpg.content.library import ContentLibrary
from trpg.content.skills import ConditionSpec
from trpg.engine import BattleState
from trpg.shared.types import Team

POUNCE = "skill_lone_wolf_pounce"
SHOT = "skill_unguarded_shot"
STRIDER = "skill_lone_strider"
PLAIN = "skill_veiled_shot"
ARCHER = "hero_archer"


def _state(allies: int, skills: tuple[str, ...], template: str = ARCHER) -> BattleState:
    spots = [(1, 1), (1, 3)]
    m = make_map(FLAT7, ally=spots[: 1 + allies], enemy=[(5, 3)])
    units = [spawn(Team.ALLY, spots[0], template, skills=skills)]
    units += [spawn(Team.ALLY, spots[1], "bandit")] * allies
    units += [spawn(Team.ENEMY, (5, 3), no_reactions("bandit"))]
    return make_state(m, units)


def test_nothing_is_greyed_when_going_alone() -> None:
    state = _state(0, (SHOT, STRIDER, PLAIN))
    assert state.units[U1].lone_wolf
    assert skills_off(state, U1) is None


def test_lone_wolf_skills_are_greyed_with_a_reason_when_a_teammate_came_along() -> None:
    reason = OFF_REASON_ZH["lone_wolf"]
    archer = skills_off(_state(1, (SHOT, STRIDER, PLAIN)), U1)
    assert archer == (
        SkillOffOut(skill_id=STRIDER, conditions=("lone_wolf",), whole=True, reason_zh=reason),
        SkillOffOut(skill_id=SHOT, conditions=("lone_wolf",), whole=False, reason_zh=reason),
    )
    fighter = skills_off(_state(1, (POUNCE,), "hero_fighter"), U1)
    assert fighter == (
        SkillOffOut(skill_id=POUNCE, conditions=("lone_wolf",), whole=False, reason_zh=reason),
    )


def test_unknown_unit_gives_nothing() -> None:
    assert skills_off(_state(1, (SHOT,)), "nobody") is None  # type: ignore[arg-type]


def test_mixed_any_of_is_not_sticky(library: ContentLibrary) -> None:
    """「獨狼，或第一輪」之後還可能成立，不標灰；全是獨狼的 ``any_of`` 照標。"""
    pounce = library.skills[POUNCE]
    mixed = ConditionSpec(type="lone_wolf", any_of=(ConditionSpec(type="first_round"),))
    assert (
        sticky_kinds(pounce.model_copy(update={"condition": mixed, "effects": pounce.effects[:1]}))
        == ()
    )
    lone = ConditionSpec(type="lone_wolf", any_of=(ConditionSpec(type="lone_wolf"),))
    found = sticky_conditions(pounce.model_copy(update={"condition": lone}))
    assert [whole for _, whole in found] == [True, False]


def test_battle_response_field_is_optional() -> None:
    """選用欄位：舊的回應（沒有這個鍵）照樣能讀，前端型別是可省略。"""
    field = BattleResponse.model_fields["skills_off"]
    assert field.default is None and not field.is_required()
