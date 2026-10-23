"""Phase 3-48f：符文讀取示範被動「符紋絆腳」（玩法決定 #51）。

敵人站在你的符文上、被你的攻擊命中時，他被施加緩速；沒站在符文上、或站的是別人的符文則不會。
（守護符陣——回合開始時為 2 格內站在你符文上的友方加護盾——現有觸發組不出來，見完成報告。）
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import U1, U2, of
from tests.engine.test_passive_triggers import always, attack, scene, triggered
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.effects import InscribeEffect, run_effects
from trpg.engine.events import StatusApplied
from trpg.narrative.skills import skill_card
from trpg.shared.types import Element, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

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
