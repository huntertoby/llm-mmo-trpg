"""Phase 3-48h：守護符陣（主動，玩法 PM 回覆 3-48f 的「守護符陣組不出來」）。

半徑 2 內、站在施放者自己符文上的友方獲得護盾；沒站在符文上、站的是別人的符文、在半徑外的不會。
"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.effects import InscribeEffect, run_effects
from trpg.engine.events import ShieldGained
from trpg.narrative.skills import skill_card
from trpg.shared.types import Element, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

LIB = library()
WARD: SkillDef = LIB.skills["skill_rune_ward"]
TEST_COPY = WARD.model_copy(update={"id": SID})
U3 = UnitId("unit_0003")


def _rune(state: BattleState, owner: UnitId, team: Team, xy: tuple[int, int]) -> BattleState:
    return run_effects(
        state, [InscribeEffect(source_id=owner, team=team, pos=xy, element=Element.LIGHTNING)]
    ).state


def test_ward_is_an_active_in_budget_skill() -> None:
    assert WARD.kind == "active" and WARD.shape.type == "allies_in_radius"
    assert validate_skill(WARD, LIB) == []
    assert 0.7 <= float(skill_budget(WARD, LIB).ratio) <= 1.0


def test_only_allies_on_your_runes_inside_the_radius_get_a_shield() -> None:
    # 施放者 (3,3)；U2 在 (3,4) 站你的符文；U3 在 (4,3) 沒有符文；敵人在 (6,6)
    state = battle(TEST_COPY, foes=[(6, 6)], allies=[(3, 4), (4, 3)])
    state = _rune(state, U1, Team.ALLY, (3, 4))
    result = cast(state)
    assert [e.unit_id for e in of(result, ShieldGained)] == [U2]


def test_someone_elses_rune_or_outside_the_radius_gives_nothing() -> None:
    state = battle(TEST_COPY, foes=[(6, 6)], allies=[(3, 4), (3, 6)], caster=(3, 3))
    state = _rune(state, UnitId("unit_0004"), Team.ENEMY, (3, 4))  # 別人的符文
    state = _rune(state, U1, Team.ALLY, (3, 6))  # 你的符文，但在半徑 2 外
    result = cast(state)
    assert not of(result, ShieldGained)


def test_card_text_names_the_rune_condition_and_the_shield() -> None:
    card = skill_card(LIB, WARD)
    text = "".join(card.effects) + "".join(c for c in (card.condition,) if c)
    assert "符文" in text and "護盾" in text
