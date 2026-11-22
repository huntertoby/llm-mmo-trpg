"""加暴擊傷害倍率的來源（CR-1，``docs/design/05-戰鬥.md`` 5.4.2 第 3、4 點）：裝備數值詞條「暴擊傷害
+N%」（遞減）、修正技、技能自帶的倍率；全部相加後套全身上下限。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle
from tests.engine.test_gear import _unit
from trpg.content.equipment import StatAffix
from trpg.content.skills import SkillDef
from trpg.content.skills.limits import skill_limit_problems
from trpg.engine import BattleState
from trpg.engine import modifiers as mods
from trpg.engine.crit_damage import crit_damage_permille
from trpg.engine.gear.core import gear_crit_damage_permille
from trpg.engine.skills.conditions import Subject
from trpg.narrative.skills import modifier_summary
from trpg.skillgen.budget import skill_budget

AFFIX = "affix_crit_damage"


# ---------------------------------------------------------------------------
# 裝備數值詞條
# ---------------------------------------------------------------------------


def test_the_affix_is_defined_and_held_back_from_the_generator() -> None:
    lib = library()
    affix = lib.affixes[AFFIX]
    assert isinstance(affix, StatAffix) and affix.stat == "crit_damage"
    assert affix.value is not None and affix.value.min == 100  # 初值 +10%
    gen = lib.item_gen
    assert gen is not None
    assert gen.stat_prices["crit_damage"].of(100) == 3  # 算 3 點
    assert AFFIX in gen.held_back_affixes


def test_one_affix_adds_its_value() -> None:
    unit = _unit({"main_hand": [(AFFIX, 100)]})
    assert gear_crit_damage_permille(unit) == 100
    assert dict(unit.gear.merged) == {}  # 不併進範本，戰鬥中查詢


def test_the_same_affix_diminishes() -> None:
    """同一詞條第 2 條 50%、第 3 條 25%（08 8.21.5.3）。"""
    unit = _unit(
        {
            "main_hand": [(AFFIX, 100)],
            "head": [(AFFIX, 100)],
            "body": [(AFFIX, 100)],
        }
    )
    assert gear_crit_damage_permille(unit) == 100 + 50 + 25


def test_the_affix_needs_a_permille_unit() -> None:
    data = library().affixes[AFFIX].model_dump(mode="json")
    data["value_unit"] = "flat"
    with pytest.raises(ValidationError, match="permille"):
        StatAffix.model_validate(data)


# ---------------------------------------------------------------------------
# 修正技與技能自帶
# ---------------------------------------------------------------------------


def _modifier(change: int, target: dict[str, Any] | None = None) -> SkillDef:
    data = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    data.update(
        id=SID,
        name_zh="暴擊專精",
        modifiers=[
            {
                "applies_to": target or {"all_attacks": True},
                "change": {"crit_damage_permille": change},
            }
        ],
    )
    return SkillDef.model_validate(data)


def _with(skill: SkillDef) -> BattleState:
    return battle(skill, [(4, 3)])


def _attack(state: BattleState) -> int:
    unit, target = state.units[U1], state.units[U2]
    return crit_damage_permille(state, unit, use=mods.ATTACK, subject=Subject(target, target.xy))


@pytest.mark.parametrize(("change", "expected"), [(250, 2250), (-300, 1700), (1000, 3000)])
def test_a_modifier_adds_to_attacks(change: int, expected: int) -> None:
    assert _attack(_with(_modifier(change))) == expected


def test_a_modifier_only_counts_for_modified_uses() -> None:
    """被動觸發等不受修正的施放（``use=None``）不算修正技的加成。"""
    state = _with(_modifier(250))
    assert crit_damage_permille(state, state.units[U1]) == 2000


def test_the_modifier_text_and_budget() -> None:
    skill = _modifier(250)
    lib = library()
    text = modifier_summary(lib, skill, skill.modifiers[0])
    assert "暴擊傷害 +25%" in text and "暴擊只放大骰子" in text
    assert skill_budget(skill, lib).total > 0


def _spell(**fields: Any) -> SkillDef:
    data = make_skill(
        SID, {"type": "single", "range": 5}, [{"type": "damage", "dice": "1d6", "element": "fire"}]
    ).model_dump(mode="json")
    data.update(fields)
    return SkillDef.model_validate(data)


def test_a_skill_brings_its_own_multiplier() -> None:
    skill = _spell(crit_permille=2500)
    state = _with(skill)
    unit = state.units[U1]
    assert crit_damage_permille(state, unit, skill=skill) == 2500
    assert crit_damage_permille(state, unit, skill=_spell()) == 2000


def test_everything_adds_up_and_then_the_cap_applies() -> None:
    """武器 2500 ＋ 技能自帶 +500 ＋ 修正技 +250 ＝ 3250 → 全身上限 3000。"""
    skill = _spell(crit_permille=2500)
    state = _with(skill)
    unit = state.units[U1]
    unit.weapon = unit.weapon.model_copy(update={"crit_permille": 2500})
    weapon_skill = skill.model_copy(update={"category": "weapon"})
    assert crit_damage_permille(state, unit, skill=weapon_skill) == 3000
    assert crit_damage_permille(state, unit, skill=skill) == 2500  # 法術不看武器


def test_a_skill_multiplier_needs_an_active_damage_skill() -> None:
    with pytest.raises(ValidationError, match="crit_permille"):
        _spell(crit_permille=2500, effects=[{"type": "heal", "dice": "1d6"}])


def test_the_skill_multiplier_range_is_a_rule() -> None:
    limits = library().ruleset.core.skill_limits
    assert limits.min_crit_permille == 1500 and limits.max_crit_permille == 3000
    assert skill_limit_problems(_spell(crit_permille=3500), limits)
    assert not skill_limit_problems(_spell(crit_permille=2500), limits)


def test_serialization_is_unchanged_without_the_new_fields() -> None:
    assert "crit_permille" not in _spell().model_dump(mode="json")
    mastery = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    assert "crit_damage_permille" not in str(mastery)
