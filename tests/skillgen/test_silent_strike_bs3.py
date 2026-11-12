"""BS-3：無聲的來源規則放寬（``docs/design/06-技能.md`` 6.21.1「BS-1 後的細節」第 2 點）。

「技能要帶隱蔽關鍵字，可以同時帶別的關鍵字」：毒＋隱蔽帶無聲通過；只有毒帶無聲、火焰版影纏仍擋；
詞條（授予動作）給出會給無聲的技能，不分主題一律擋。內容載入與 ``validate_skill`` 共用
``silent_strike_problems``，詞條走 ``gear_checks._action_problems``。
"""

from __future__ import annotations

from functools import cache

from tests.engine.helpers import library
from trpg.content.equipment import ActionAffix
from trpg.content.library import ContentLibrary
from trpg.content.library.gear_checks import _action_problems
from trpg.content.silent_strike import silent_strike_problems
from trpg.content.skills import EffectSpec, SkillDef
from trpg.shared.types import Element
from trpg.skillgen.validate import validate_skill

SILENT = "skill_silent_step"
BIND = "skill_shadow_bind"


@cache
def lib() -> ContentLibrary:
    return library()


def _poison() -> EffectSpec:
    return EffectSpec.model_validate({"type": "apply_status", "status": "poison", "duration": 2})


def poison_only_bind() -> SkillDef:
    """影纏多上一層毒：除了無聲以外的專屬關鍵字只有「中毒」。"""
    base = lib().skills[BIND]
    return base.model_copy(
        update={"effects": (base.effects[0], _poison(), base.effects[1]), "id": "skill_poison_bind"}
    )


def poison_concealed_bind() -> SkillDef:
    """毒＋隱蔽：暗影傷害（隱蔽）＋上毒（中毒），再給無聲。"""
    base = poison_only_bind()
    damage = base.effects[0].model_copy(update={"element": Element.SHADOW})
    return base.model_copy(
        update={"effects": (damage, *base.effects[1:]), "id": "skill_poison_shade_bind"}
    )


def _problems(skill: SkillDef) -> list[str]:
    return silent_strike_problems(skill, lib().skills, lib().keywords)


def _rules(skill: SkillDef) -> set[str]:
    return {v.rule for v in validate_skill(skill, lib())}


def test_poison_plus_concealed_with_silence_passes() -> None:
    skill = poison_concealed_bind()
    assert _problems(skill) == []
    assert "silent_strike.source" not in _rules(skill)


def test_poison_only_with_silence_is_rejected() -> None:
    skill = poison_only_bind()
    problems = _problems(skill)
    assert problems and "隱蔽關鍵字" in problems[0] and "中毒" in problems[0]
    assert "silent_strike.source" in _rules(skill)


def test_fire_plus_concealed_passes_but_fire_only_does_not() -> None:
    base = lib().skills[BIND]
    fire = base.effects[0].model_copy(update={"element": Element.FIRE})
    fire_only = base.model_copy(
        update={"effects": (fire, base.effects[1]), "id": "skill_fire_bind"}
    )
    assert _problems(fire_only)
    smoke = EffectSpec.model_validate(
        {"type": "apply_status", "status": "concealed", "duration": 1, "affects": "self"}
    )
    both = fire_only.model_copy(
        update={"effects": (fire, smoke, base.effects[1]), "id": "skill_fire_shade_bind"}
    )
    assert _problems(both) == []
    assert "silent_strike.source" not in _rules(both)


def test_a_fire_modifier_on_the_silent_passive_is_still_rejected() -> None:
    base = lib().skills[SILENT]
    rule = base.modifiers[0]
    change = rule.change.model_copy(update={"silent_strike": None, "add_element": Element.FIRE})
    fire = rule.model_copy(update={"change": change})
    fire_silent = base.model_copy(update={"modifiers": (rule, fire), "id": "skill_fire_silent"})
    assert _problems(fire_silent)


def test_the_demo_skills_still_pass() -> None:
    for sid in (SILENT, BIND):
        assert _problems(lib().skills[sid]) == []


def test_an_affix_granting_a_concealed_silent_skill_is_still_rejected() -> None:
    # 詞條不能給無聲：就算給出的技能是隱蔽主題（影纏）也擋
    ruleset = lib().ruleset

    def affix(granted: str) -> ActionAffix:
        return ActionAffix.model_validate(
            {
                "id": "affix_test_grant",
                "name_zh": "測試",
                "category": "action",
                "slots": ["weapon"],
                "skill": granted,
            }
        )

    assert any("無聲" in p for p in _action_problems(affix(BIND), ruleset))
    assert _action_problems(affix("skill_cleave"), ruleset) == []
