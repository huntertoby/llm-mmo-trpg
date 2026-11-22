"""暴擊傷害倍率的技能預算（CR-1，``docs/design/05-戰鬥.md`` 5.4.2 第 7 點）：擴大暴擊範圍的點數＝
額外暴擊率 ×（倍率 − 100%）× 骰子占比；技能自帶倍率另加 基礎暴擊率 5% ×（自帶 − 基礎）× 骰子占比。
200% 時和改版前相同（442 招逐招預算的比對見 CR-1 報告）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import skill_budget

BLADE = "skill_wild_blade"  # 武器技：暴擊 17–20、爆骰、基礎傷害 ×0.75


def _blade(**update: object) -> SkillDef:
    return library().ruleset.skill_def(BLADE).model_copy(update=update)


def _note(skill: SkillDef) -> str:
    return skill_budget(skill, library()).effects[0].note


def _points(skill: SkillDef) -> Fraction:
    return skill_budget(skill, library()).effects[0].points


def test_at_two_hundred_percent_nothing_changes() -> None:
    """沒帶倍率（照基礎 200%）：「暴擊 17–20 ×1.105」＝ 1 ＋ 3/20 × 100% × 0.7，和改版前一樣。"""
    plain = _blade()
    assert "暴擊 17–20 ×1.105" in _note(plain)
    assert "暴擊傷害" not in _note(plain)


def test_two_hundred_fifty_percent_on_the_skill() -> None:
    """這招自帶 250%：擴大範圍 1 ＋ 3/20 × 150% × 0.7 ＝ 1.1575；自帶另加 1 ＋ 1/20 × 50% × 0.7
    ＝ 1.0175。"""
    plain, wide = _blade(), _blade(crit_permille=2500)
    note = _note(wide)
    assert "暴擊 17–20・250% ×1.1575" in note
    assert "暴擊傷害 250% ×1.0175" in note
    ratio = _points(wide) / _points(plain)
    assert ratio == Fraction(11575, 11050) * Fraction(10175, 10000)


def test_an_explicit_two_hundred_percent_costs_the_same() -> None:
    assert _points(_blade(crit_permille=2000)) == _points(_blade())


@pytest.mark.parametrize(("permille", "cheaper"), [(1500, True), (3000, False)])
def test_a_lower_multiplier_is_cheaper(permille: int, cheaper: bool) -> None:
    assert (_points(_blade(crit_permille=permille)) < _points(_blade())) is cheaper


def test_a_spell_counts_its_whole_damage_as_dice() -> None:
    """法術技的骰子占比是 100%：自帶 250% ＝ ×（1 ＋ 1/20 × 50%）＝ ×1.025。"""
    spell = library().ruleset.skill_def("skill_fire_bolt")
    assert spell.category == "spell" and spell.crit_range is None
    boosted = spell.model_copy(update={"crit_permille": 2500})
    assert _points(boosted) / _points(spell) == Fraction(41, 40)
