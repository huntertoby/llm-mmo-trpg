"""主題合併（R2）。

原 ``test_rune_snare_48f.py``：

Phase 3-48f：符文讀取示範被動「符紋絆腳」（玩法決定 #51）。

敵人站在你的符文上、被你的攻擊命中時，他被施加緩速；沒站在符文上、或站的是別人的符文則不會。
（守護符陣——回合開始時為 2 格內站在你符文上的友方加護盾——現有觸發組不出來，見完成報告。）

原 ``test_rune_ward_48h.py``：

Phase 3-48h：守護符陣（主動，玩法 PM 回覆 3-48f 的「守護符陣組不出來」）。

半徑 2 內、站在施放者自己符文上的友方獲得護盾；沒站在符文上、站的是別人的符文、在半徑外的不會。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from tests.engine.test_passive_triggers import always, attack, scene, triggered
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.effects import InscribeEffect, run_effects
from trpg.engine.events import ShieldGained, StatusApplied
from trpg.narrative.skills import skill_card
from trpg.shared.types import Element, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

# --- 原 test_rune_snare_48f.py ---

LIB = library()
SNARE: SkillDef = LIB.skills["skill_rune_snare"]
TEST_COPY = SNARE.model_copy(update={"id": "skill_t_rune_snare"})  # 場景會把技能加進規則集


def _with_rune(state: BattleState, owner: UnitId, xy: tuple[int, int]) -> BattleState:
    team = state.units[owner].team
    return run_effects(
        state, [InscribeEffect(source_id=owner, team=team, pos=xy, element=Element.LIGHTNING)]
    ).state


def test_rune_snare_is_a_valid_in_budget_demo() -> None:
    assert validate_skill(SNARE, LIB) == []
    report = skill_budget(SNARE, LIB)
    assert 0.7 <= float(report.ratio) <= 1.0


def test_enemy_standing_on_your_rune_is_slowed_when_you_hit_him(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = _with_rune(scene([TEST_COPY]), U1, (4, 3))
    result = attack(state)
    assert [e.trigger for e in triggered(result.events)] == ["on_hit"]
    applied = of(result, StatusApplied)
    assert [(a.target_id, a.status_id) for a in applied] == [(U2, "slow")]


def test_no_rune_or_someone_elses_rune_means_no_slow(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    plain = attack(scene([TEST_COPY]))
    assert not of(plain, StatusApplied)
    foes_rune = attack(_with_rune(scene([TEST_COPY]), U2, (4, 3)))
    assert not of(foes_rune, StatusApplied)
    elsewhere = attack(_with_rune(scene([TEST_COPY]), U1, (2, 3)))
    assert not of(elsewhere, StatusApplied)


def test_card_text_matches_the_behaviour() -> None:
    card = skill_card(LIB, SNARE)
    assert card.condition is not None and "符文" in card.condition
    assert any("緩速" in e for e in card.effects)


# --- 原 test_rune_ward_48h.py ---

LIB_48H = library()
WARD: SkillDef = LIB_48H.skills["skill_rune_ward"]
TEST_COPY_48H = WARD.model_copy(update={"id": SID})
U3 = UnitId("unit_0003")


def _rune(state: BattleState, owner: UnitId, team: Team, xy: tuple[int, int]) -> BattleState:
    return run_effects(
        state, [InscribeEffect(source_id=owner, team=team, pos=xy, element=Element.LIGHTNING)]
    ).state


def test_ward_is_an_active_in_budget_skill() -> None:
    assert WARD.kind == "active" and WARD.shape.type == "allies_in_radius"
    assert validate_skill(WARD, LIB_48H) == []
    assert 0.7 <= float(skill_budget(WARD, LIB_48H).ratio) <= 1.0


def test_only_allies_on_your_runes_inside_the_radius_get_a_shield() -> None:
    # 施放者 (3,3)；U2 在 (3,4) 站你的符文；U3 在 (4,3) 沒有符文；敵人在 (6,6)
    state = battle(TEST_COPY_48H, foes=[(6, 6)], allies=[(3, 4), (4, 3)])
    state = _rune(state, U1, Team.ALLY, (3, 4))
    result = cast(state)
    assert [e.unit_id for e in of(result, ShieldGained)] == [U2]


def test_someone_elses_rune_or_outside_the_radius_gives_nothing() -> None:
    state = battle(TEST_COPY_48H, foes=[(6, 6)], allies=[(3, 4), (3, 6)], caster=(3, 3))
    state = _rune(state, UnitId("unit_0004"), Team.ENEMY, (3, 4))  # 別人的符文
    state = _rune(state, U1, Team.ALLY, (3, 6))  # 你的符文，但在半徑 2 外
    result = cast(state)
    assert not of(result, ShieldGained)


def test_card_text_names_the_rune_condition_and_the_shield() -> None:
    card = skill_card(LIB_48H, WARD)
    text = "".join(card.effects) + "".join(c for c in (card.condition,) if c)
    assert "符文" in text and "護盾" in text
