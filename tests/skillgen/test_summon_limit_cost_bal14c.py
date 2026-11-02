"""BAL-14c：「召喚物同時上限 −1」（約抵 3500 點）不得當一般代價折抵預算。

只有手寫的召喚專精被動（內建，例如 ``skill_summon_elite``）和由它衍生的技能可以帶；
組合器、閃現（小變化 ``mod_cost``、收回、大變化）、進化的代價折抵、升階重配、LLM 提議、工坊白板
都不能新做出這個代價。每條路徑一個測試：會的擋掉（驗證器 ``modifier.summon_limit_cost``），
不會的鎖住現狀。
"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from trpg.content.skills import MODIFIER_CHANGES, SkillDef
from trpg.skillgen import composer_special, flash_major, flash_ops
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.evolution import cost_attempts
from trpg.skillgen.flash_derive import at_role_tier
from trpg.skillgen.flash_ops import FLASH_OPS
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.proposal import CLOSED_SKELETONS, build_proposal_models
from trpg.skillgen.validate import validate_skill

ELITE = "skill_summon_elite"
RULE = "modifier.summon_limit_cost"


def _drawbacks(skill: SkillDef | dict[str, Any]) -> int:
    data: dict[str, Any] = skill.model_dump(mode="json") if isinstance(skill, SkillDef) else skill
    return sum(
        (rule["change"].get("summon_limit_delta") or 0) < 0 for rule in data.get("modifiers", [])
    )


def _modifier_skill(
    delta: int, *, origin: str = "level_up", parents: tuple[str, ...] = ()
) -> SkillDef:
    base = library().skills[ELITE].model_dump(mode="json")
    base["id"] = "skill_bal14c_probe"
    base["modifiers"] = [
        {"applies_to": {"skill_tags": ["summon"]}, "change": {"summon_limit_delta": delta}},
        {"applies_to": {"skill_tags": ["summon"]}, "change": {"summon_hp_permille": 600}},
    ]
    base["provenance"] = {"origin": origin, "parents": list(parents)}
    return SkillDef.model_validate(base)


# ---------------------------------------------------------------------------
# 擋掉的路徑：驗證器（新做出來的技能一律走這裡）
# ---------------------------------------------------------------------------


def test_builtin_elite_mastery_still_carries_the_drawback_and_passes_the_rule() -> None:
    lib = library()
    elite = lib.skills[ELITE]
    assert elite.provenance.origin == "builtin"
    assert _drawbacks(elite) == 1
    assert RULE not in {v.rule for v in validate_skill(elite, lib)}


def test_new_modifier_skill_cannot_use_summon_limit_minus_one_as_a_cost() -> None:
    """組合器、白板、LLM 等新做出來的技能（來源不是內建、沒有 parents）帶 −1 會被擋。"""
    lib = library()
    for origin in ("level_up", "workshop", "starter", "drop", "crafted"):
        found = validate_skill(_modifier_skill(-1, origin=origin), lib)
        assert RULE in {v.rule for v in found}, origin


def test_plus_one_and_derived_skills_are_not_blocked() -> None:
    lib = library()
    assert RULE not in {v.rule for v in validate_skill(_modifier_skill(1), lib)}
    derived = _modifier_skill(-1, parents=(ELITE,))
    assert RULE not in {v.rule for v in validate_skill(derived, lib)}


# ---------------------------------------------------------------------------
# 組合器
# ---------------------------------------------------------------------------


def test_composer_modifier_ladders_never_offer_summon_changes() -> None:
    assert not any(name.startswith("summon_") for name in composer_special._CHANGE_KINDS)
    assert "summon_limit_delta" not in composer_special._LADDERS


def test_composed_modifier_and_legendary_skills_never_carry_the_drawback() -> None:
    lib = library()
    for seed in range(60):
        for found in (
            composer_special.compose_modifier(seed, lib),
            composer_special.compose_legendary(seed, lib, cores=("modifier",)),
        ):
            if found is not None:
                assert _drawbacks(found) == 0, (seed, found.id)


# ---------------------------------------------------------------------------
# 閃現（小變化、收回、大變化）
# ---------------------------------------------------------------------------


def test_flash_modifier_knobs_do_not_include_summon_limit() -> None:
    assert "summon_limit_delta" not in library().flash.rules.modifier_knobs


def test_flash_ops_never_add_the_drawback_to_modifier_skills() -> None:
    """每個閃現模板（含 ``mod_cost``、收回的 ``focus_mod_*``）對每個修正型被動：草稿的
    召喚上限 −1 不會比原技能多。"""
    lib = library()
    modifiers = [s for s in lib.skills.values() if s.kind == "modifier"]
    assert modifiers
    checked = 0
    for skill in modifiers:
        for template in lib.flash.minor:
            op = FLASH_OPS.get(template.op)
            if op is None:
                continue
            variation = Variation(source="minor", template=template.id, category=template.category)
            for base, _effects in op(skill, template, variation, lib):
                assert _drawbacks(base) <= _drawbacks(skill), (skill.id, template.id)
                checked += 1
    assert checked > 0


def test_mod_cost_never_touches_summon_limit() -> None:
    lib = library()
    template = lib.flash.minor_template("mod_cost")
    assert template is not None
    variation = Variation(source="minor", template="mod_cost", category=template.category)
    assert FLASH_OPS[template.op](lib.skills[ELITE], template, variation, lib) == []


def test_reclaim_gain_knobs_never_move_summon_limit() -> None:
    lib = library()
    base = lib.skills[ELITE].model_dump(mode="json")
    for op in ("mod_potency", "mod_duration", "mod_cost", "mod_stack", "mod_cooldown"):
        _targets, knobs = flash_ops.tuning_extras(op, base, lib)
        assert "summon_limit_delta" not in {k.field for k in knobs}, op


def test_major_transform_to_modifier_only_builds_damage_or_status_rules() -> None:
    lib = library()
    for template in lib.flash.transforms:
        for skill in lib.skills.values():
            for base, _effects in flash_major._to_modifier(skill, template, lib):
                assert _drawbacks(base) == 0, (skill.id, template.id)
                for rule in base["modifiers"]:
                    assert set(rule["change"]) <= {"damage_permille", "on_hit_effects"}


# ---------------------------------------------------------------------------
# 大變化的代價折抵（cost_attempts）、升階重配
# ---------------------------------------------------------------------------


def test_cost_attempts_only_change_the_cooldown() -> None:
    """進化／召喚進化的代價折抵只動技能 ``cost`` 的冷卻，不會碰修正規則。"""
    lib = library()
    for skill in lib.skills.values():
        base = skill.cost.model_dump(mode="json")
        for attempt in cost_attempts(skill):
            changed = {k for k in attempt if attempt.get(k) != base.get(k)}
            assert changed <= {"cooldown"}, (skill.id, changed)


def test_retier_keeps_the_drawback_count_of_the_parent() -> None:
    lib = library()
    for skill in lib.skills.values():
        if skill.kind == "modifier":
            for tier in (1, 2, 3):
                assert _drawbacks(at_role_tier(lib, skill, tier)) <= _drawbacks(skill), skill.id


# ---------------------------------------------------------------------------
# LLM 提議、工坊白板
# ---------------------------------------------------------------------------


def test_llm_proposal_has_no_modifier_rules_and_modifier_skeleton_is_closed() -> None:
    lib = library()
    assert "modifier" in CLOSED_SKELETONS
    models = build_proposal_models(lib)
    assert "modifiers" not in str(models.json_schema())


def test_workshop_option_list_still_offers_the_change_but_validation_blocks_it() -> None:
    """白板（玩家工坊）的修正規則選單列出所有 ``MODIFIER_CHANGES``；擋在驗證器，不改選單。"""
    assert "summon_limit_delta" in MODIFIER_CHANGES


def test_workshop_draft_without_provenance_is_checked_as_workshop_made() -> None:
    """白板／工坊的草稿沒有 ``provenance`` 時 schema 預設是內建；``check_draft`` 當成工坊做的，
    所以 −1 一樣被擋（不能靠省略來源繞過）。"""
    lib = library()
    draft = _modifier_skill(-1).model_dump(mode="json", exclude_none=True)
    draft.pop("provenance")
    result = check_draft(draft, lib)
    assert RULE in {p.rule for p in result.problems}
