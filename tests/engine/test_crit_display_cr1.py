"""暴擊傷害倍率的顯示（CR-1，``docs/design/05-戰鬥.md`` 5.4.2 第 8 點）：寫成百分比，例
「暴擊 19–20・250%」；200% 時預覽不另外顯示、技能卡照舊；「暴擊不加倍」改成「暴擊只放大骰子」。"""

from __future__ import annotations

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, UseSkill, preview
from trpg.engine.rules.combat import crit_text_zh
from trpg.narrative.skills import skill_card

BLADE = "skill_wild_blade"


def test_the_text_format() -> None:
    assert crit_text_zh(19, 2500) == "暴擊 19–20・250%"
    assert crit_text_zh(20, 1500) == "暴擊 20・150%"
    assert crit_text_zh(17, 2250) == "暴擊 17–20・225%"


def test_the_skill_card_shows_the_skill_multiplier() -> None:
    lib = library()
    plain = lib.skills[BLADE]
    (text,) = skill_card(lib, plain).effects
    assert "暴擊範圍 17–20" in text and "・" not in text  # 沒帶倍率：照舊
    wide = plain.model_copy(update={"crit_range": 19, "crit_permille": 2500})
    (text,) = skill_card(lib, wide).effects
    assert "暴擊 19–20・250%" in text and "暴擊範圍" not in text


def _spell() -> SkillDef:
    return SkillDef.model_validate(
        make_skill(
            SID,
            {"type": "single", "range": 5},
            [{"type": "damage", "dice": "1d6", "element": "fire"}],
        ).model_dump(mode="json")
    )


def _state(weapon_permille: int | None, skill: SkillDef | None = None) -> BattleState:
    state = battle(skill or _spell(), [(4, 3)])
    unit = state.units[U1]
    unit.weapon = unit.weapon.model_copy(update={"crit_permille": weapon_permille})
    return state


def _crit_notes(notes: tuple[str, ...]) -> list[str]:
    return [n for n in notes if n.startswith("暴擊 ")]


def test_the_attack_preview_shows_a_non_default_multiplier() -> None:
    state = _state(2500)
    crit_range = state.units[U1].weapon.crit_range
    notes = preview(state, Attack(unit_id=U1, target_id=U2)).notes
    assert _crit_notes(notes) == [crit_text_zh(crit_range, 2500)]


def test_the_preview_says_nothing_at_two_hundred_percent() -> None:
    for permille in (None, 2000):
        notes = preview(_state(permille), Attack(unit_id=U1, target_id=U2)).notes
        assert _crit_notes(notes) == []


def test_the_skill_preview_shows_the_skill_multiplier() -> None:
    skill = _spell().model_copy(update={"crit_permille": 2500, "crit_range": 19})
    state = _state(None, skill)
    notes = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).notes
    assert _crit_notes(notes) == ["暴擊 19–20・250%"]


def test_the_flat_bonus_wording() -> None:
    lib = library()
    spec = lib.ruleset.primitive_def("damage").params["flat_bonus"]
    assert "暴擊只放大骰子" in (spec.description_zh or "")
    assert "不加倍" not in (spec.description_zh or "")
