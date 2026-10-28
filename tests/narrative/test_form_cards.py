"""Phase 3J-1a：形態技能的卡片句與戰鬥紀錄全部由 ``content/forms.yaml`` 產生。"""

from __future__ import annotations

from trpg.content.form_text import form_sentence
from trpg.content.library import load_library
from trpg.narrative.skills import skill_card

LIB = load_library()


def test_the_bear_card_sentence_comes_from_the_form_data() -> None:
    card = skill_card(LIB, LIB.ruleset.skill_def("skill_form_bear"))
    assert card.effects == (
        "化身為熊（物理形態，持續到取消）：普攻改用熊爪 1d8 近戰（力量／體質取較高 × 0.3）；"
        "形態中：最大 HP +15%、防禦 +10%、移動 −1；進入時：護盾＝最大 HP 的 10%（2 回合）；"
        "每回合開始 −8 耐力（不夠就自動解除）；離開後這個形態冷卻 2 回合",
    )
    assert card.formula_lines[-1] == "天生武器（普攻）：熊爪 1d8 近戰（力量／體質取較高 × 0.3）"


def test_every_form_skill_card_follows_its_form() -> None:
    rules = LIB.ruleset
    for form in rules.forms.forms:
        skill = rules.skill_def(f"skill_form_{form.id}")
        card = skill_card(LIB, skill)
        assert card.effects == (form_sentence(rules.forms, form, rules.core),)
        assert form.natural_weapon.name_zh in card.formula_lines[-1]
        upkeep = "法力" if form.category == "mental" else "耐力"
        assert f"−{rules.forms.upkeep(form)[1]} {upkeep}" in card.effects[0]


def test_changing_the_data_changes_the_text() -> None:
    rules = LIB.ruleset
    bear = rules.form_def("bear")
    tweaked = bear.model_copy(
        update={"effects": bear.effects.model_copy(update={"move": 0, "defense_permille": 250})}
    )
    text = form_sentence(rules.forms, tweaked, rules.core)
    assert "防禦 +25%" in text and "移動" not in text
