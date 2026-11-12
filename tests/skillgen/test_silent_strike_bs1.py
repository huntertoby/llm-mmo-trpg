"""BS-1：「無聲」的來源限制（#157，``docs/design/06-技能.md`` 6.21.1 C3）與 DD-3 的
``all_strikes_hit`` 只給手寫技能（#158）。

無聲只能放在隱蔽關鍵字的技能（被動常駐、主動技能給幾回合）：放到別的主題的技能、詞條（授予動作
給出會給無聲的技能）時驗證擋下——內容載入、技能驗證器、LLM 提議都走同一條
（``silent_strike.source``）。
「每一下都命中」不開放給 LLM schema、工坊選項，非內建的新技能用到時擋下。
"""

from __future__ import annotations

from functools import cache
from typing import Any

from tests.engine.helpers import library
from tests.skillgen.test_proposal import _models
from trpg.content.equipment import ActionAffix
from trpg.content.library import ContentLibrary
from trpg.content.library.gear_checks import _action_problems
from trpg.content.silent_strike import carries_silent, silent_strike_problems
from trpg.content.skills import SkillDef, granted_skill_problems, is_silent_grant
from trpg.shared.types import Element
from trpg.skillgen.keywords import keyword_pools
from trpg.skillgen.option_params import HANDWRITTEN_ONLY_CONDITION, condition_choice
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalResult,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers
from trpg.skillgen.validate import validate_skill

SILENT = "skill_silent_step"
BIND = "skill_shadow_bind"
FANG = "skill_twin_fang"


@cache
def lib() -> ContentLibrary:
    return library()


def skill(skill_id: str) -> SkillDef:
    return lib().skills[skill_id]


def fire_bind() -> SkillDef:
    """影纏改成火焰傷害：專屬關鍵字多了「點燃」，不再只是隱蔽主題。"""
    base = skill(BIND)
    damage = base.effects[0].model_copy(update={"element": Element.FIRE})
    return base.model_copy(update={"effects": (damage, *base.effects[1:]), "id": "skill_fire_bind"})


def fire_silent() -> SkillDef:
    """無聲步多一條「普攻帶火」：放在點燃主題的修正技能上。"""
    base = skill(SILENT)
    fire = base.modifiers[0].model_copy(
        update={
            "change": base.modifiers[0].change.model_copy(
                update={"silent_strike": None, "add_element": Element.FIRE}
            )
        }
    )
    return base.model_copy(update={"modifiers": (*base.modifiers, fire), "id": "skill_fire_silent"})


# ---------------------------------------------------------------------------
# 無聲的來源
# ---------------------------------------------------------------------------


def test_the_demo_skills_carry_silence_and_pass() -> None:
    skills, keywords = lib().skills, lib().keywords
    for sid in (SILENT, BIND):
        assert carries_silent(skill(sid), skills)
        assert silent_strike_problems(skill(sid), skills, keywords) == []
        assert validate_skill(skill(sid), lib()) == []
    assert is_silent_grant(skill(SILENT))
    assert not carries_silent(skill(FANG), skills)


def test_silence_on_a_skill_of_another_theme_is_rejected() -> None:
    skills, keywords = lib().skills, lib().keywords
    for bad in (fire_bind(), fire_silent()):
        problems = silent_strike_problems(bad, skills, keywords)
        assert problems and "隱蔽關鍵字" in problems[0]
        rules = {v.rule for v in validate_skill(bad, lib())}
        assert "silent_strike.source" in rules


def test_an_llm_proposal_that_grants_silence_off_theme_is_rejected() -> None:
    # LLM 的 grant_skill 可以選無聲步（和 granted_skill_problems 同一套）；放在隱蔽以外的技能就擋
    schema = _models().json_schema()
    granted = schema["$defs"]["Effect_grant_skill"]["properties"]["skill"]
    assert SILENT in str(granted)
    ctx = ProposalContext(tier=1, rarity="rare", rank=1)

    def round_trip(source: SkillDef) -> ProposalResult:
        full = source.model_dump(mode="json", exclude_defaults=True)
        _structure, removed = split_numbers(full, lib())
        proposal: dict[str, Any] = proposal_from_skill(source, lib())
        proposal["effects"][1]["condition"].pop("any_of", None)  # 提議格式沒有 any_of
        return evaluate_proposal(proposal, _models(), lib(), ctx, fill=fixed_filler(removed))

    bad = round_trip(fire_bind())
    assert bad.skill is None
    assert any(e.code == "silent_strike.source" for e in bad.errors)
    good = round_trip(skill(BIND))
    assert not any(e.code == "silent_strike.source" for e in good.errors)


def test_silence_cannot_come_from_an_affix() -> None:
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

    rules = lib().ruleset
    assert any("無聲" in p for p in _action_problems(affix(BIND), rules))
    assert _action_problems(affix("skill_cleave"), rules) == []


def test_only_silence_only_modifiers_can_be_granted() -> None:
    skills = dict(lib().skills)
    primitives = lib().ruleset.primitives.by_id()
    assert granted_skill_problems(skill(BIND), skills, primitives) == []
    other = skill(BIND)
    grant = other.effects[1].model_copy(update={"skill": "skill_attack_mastery"})
    wrong = other.model_copy(update={"effects": (other.effects[0], grant)})
    assert any("必須是主動技能" in p for p in granted_skill_problems(wrong, skills, primitives))


def test_silence_and_twin_fang_show_up_in_the_right_keyword_pools() -> None:
    pools = keyword_pools(lib())
    assert {SILENT, BIND} <= set(pools["concealed"])
    assert FANG in pools["poisoned"]


# ---------------------------------------------------------------------------
# 每一下都命中：只給手寫技能
# ---------------------------------------------------------------------------


def test_all_strikes_hit_is_not_in_the_llm_schema() -> None:
    schema = _models().json_schema()
    assert "Condition_all_strikes_hit" not in schema["$defs"]
    assert "all_strikes_hit" not in str(schema)


def test_all_strikes_hit_is_greyed_out_in_the_options() -> None:
    cond = lib().ruleset.conditions.by_id()["all_strikes_hit"]
    choice = condition_choice(cond, lib(), effect_level=True)
    assert choice.info["unavailable_zh"] == HANDWRITTEN_ONLY_CONDITION


def test_all_strikes_hit_is_rejected_on_new_skills() -> None:
    fang = skill(FANG)
    assert validate_skill(fang, lib()) == []
    for origin in ("workshop", "level_up", "drop"):
        made = fang.model_copy(
            update={"provenance": fang.provenance.model_copy(update={"origin": origin})}
        )
        assert "condition.handwritten_only" in {v.rule for v in validate_skill(made, lib())}
    evolved = fang.model_copy(
        update={
            "provenance": fang.provenance.model_copy(
                update={"origin": "level_up", "parents": (FANG,)}
            )
        }
    )
    assert "condition.handwritten_only" not in {v.rule for v in validate_skill(evolved, lib())}
