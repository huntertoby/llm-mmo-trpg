"""Phase 3-52b：工坊選層數時，事前停用「這招不能消耗的層數」，並與驗證器同源；氣的治療加成預算。"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from tests.engine.helpers import library
from trpg.content.library import skill_reference_problems
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.option_effect_rules import stack_unavailable_reason
from trpg.skillgen.option_models import Choice
from trpg.skillgen.options import draft_options

LIB = library()


def _stack_choices(draft: dict[str, Any]) -> dict[str, Choice]:
    """效果步驟裡 ``consume_stack`` 選項的層數子選項（值 → 選項）。"""
    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "effects")
    field = next(f for f in step.fields if f.field == "effects")
    consume = next(c for c in field.choices if c.value == "consume_stack")
    stack = next(p for p in consume.params if p.field == "stack")
    return {str(c.value): c for c in stack.choices}


def _draft_of(skill_id: str, drop: str | None = None) -> dict[str, Any]:
    data = LIB.skills[skill_id].model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    data["effects"] = [e for e in data["effects"] if e["type"] != drop]
    for key in ("id", "provenance", "narrative", "tags"):
        data.pop(key, None)
    data["kind"] = "active"
    return data


def _reason(choices: dict[str, Choice], stack: str) -> object:
    return choices[stack].info.get("unavailable_zh")


def test_a_damage_only_draft_cannot_pick_heal_or_shield_stacks() -> None:
    choices = _stack_choices(_draft_of("skill_combo_finisher", drop="consume_stack"))
    reason = _reason(choices, "holy_power")
    assert isinstance(reason, str) and "治療" in reason and "護盾" in reason
    assert "先加入" in reason  # 白話：怎麼改
    assert _reason(choices, "combo_point") is None  # 傷害技可以（標籤不明時先視為符合）
    assert _reason(choices, "focus") is None
    assert _reason(choices, "static_charge") is None  # 舊層數沒有消耗規則


def test_a_heal_only_draft_cannot_pick_damage_only_stacks() -> None:
    choices = _stack_choices(_draft_of("skill_sanctified_ward", drop="consume_stack"))
    assert _reason(choices, "holy_power") is None
    reason = _reason(choices, "focus")
    assert isinstance(reason, str) and "傷害" in reason
    # 氣只加成「治療自己」：這招的護盾／別人的治療不算
    ki = _reason(choices, "ki")
    assert isinstance(ki, str) and "治療自己" in ki


def test_a_self_heal_makes_ki_available() -> None:
    choices = _stack_choices(_draft_of("skill_qi_breath", drop="consume_stack"))
    assert _reason(choices, "ki") is None


def test_an_ally_heal_does_not_make_ki_available() -> None:
    draft = _draft_of("skill_qi_breath", drop="consume_stack")
    draft["effects"][0]["affects"] = "allies"
    assert isinstance(_reason(_stack_choices(draft), "ki"), str)


def test_element_requirements_are_checked_against_the_draft_effects() -> None:
    fire = _draft_of("skill_shatter_frost", drop="consume_stack")
    for effect in fire["effects"]:
        if effect["type"] == "damage":
            effect["element"] = "fire"
    reason = _reason(_stack_choices(fire), "hoarfrost")
    assert isinstance(reason, str) and "冰霜傷害" in reason
    ice = _stack_choices(_draft_of("skill_shatter_frost", drop="consume_stack"))
    assert _reason(ice, "hoarfrost") is None


def test_the_options_agree_with_the_validator_for_every_stack() -> None:
    """同源：選項說可以的組合，驗證器的消耗規則不報錯；說不行的，驗證器一定報錯。"""
    stacks = LIB.ruleset.stacks.by_id()
    for skill_id in ("skill_combo_finisher", "skill_sanctified_ward", "skill_shatter_frost"):
        base = LIB.skills[skill_id]
        for stack_id, stack in sorted(stacks.items()):
            owner = "self" if stack.owner == "self" else "enemies"
            consume = next(e for e in base.effects if e.type == "consume_stack").model_copy(
                update={"stack": stack_id, "affects": owner}
            )
            effects = (*(e for e in base.effects if e.type != "consume_stack"), consume)
            skill: SkillDef = base.model_copy(update={"effects": effects})
            reason = stack_unavailable_reason(skill, stack_id, LIB)
            problems = [
                p
                for p in skill_reference_problems(skill, LIB.ruleset, LIB.skills)
                if "消耗層數" in p or "只有符合條件的技能可以消耗" in p
            ]
            assert (reason is None) == (problems == []), (skill_id, stack_id, reason, problems)


def test_the_chosen_stack_stays_selectable() -> None:
    """已經選了的層數不被停用（前端的規則；違規由檢查面板說明）：後端照實標，前端放行。"""
    choices = _stack_choices(_draft_of("skill_combo_finisher", drop="consume_stack"))
    assert set(choices) >= {"combo_point", "focus", "ki", "holy_power"}


def test_the_ki_budget_counts_only_the_self_heal() -> None:
    breath = LIB.skills["skill_qi_breath"]
    self_points = _consume_points(breath)
    ally = breath.model_copy(
        update={
            "effects": tuple(
                e.model_copy(update={"affects": "allies"}) if e.type == "heal" else e
                for e in breath.effects
            )
        }
    )
    assert _consume_points(ally) == Fraction(0) < self_points  # 治療別人沒有氣的加成點數


def _consume_points(skill: SkillDef) -> Fraction:
    report = skill_budget(skill, LIB)
    return sum((e.points for e in report.effects if e.type == "consume_stack"), Fraction(0))
