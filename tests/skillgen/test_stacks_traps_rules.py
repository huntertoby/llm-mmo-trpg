"""Phase 2E-3：層數與陷阱的內容規則、骨架規則與預算。"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.skillgen.helpers import lib, rules_of
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import skill_budget


def variant(base_id: str, **overrides: Any) -> SkillDef:
    data = lib().skills[base_id].model_dump(mode="json")
    data.update(overrides)
    return SkillDef.model_validate(data)


def test_the_stack_table_has_the_two_initial_stacks() -> None:
    stacks = {s.id: s for s in lib().ruleset.stacks.stacks}
    assert (stacks["static_charge"].owner, stacks["static_charge"].max) == ("self", 5)
    assert stacks["static_charge"].expires_after_rounds is None
    assert (stacks["sunder"].owner, stacks["sunder"].max) == ("target", 3)
    assert stacks["sunder"].expires_after_rounds == 3


def test_the_six_handwritten_skills_are_valid_and_in_the_budget_window() -> None:
    for skill_id in (
        "skill_static_palm",
        "skill_thunder_finisher",
        "skill_sunder_strike",
        "skill_armor_breaker",
        "skill_cinder_mine",
        "skill_bear_trap",
    ):
        skill = lib().skills[skill_id]
        assert not rules_of(skill), skill_id
        assert skill_budget(skill, lib()).ok, skill_id


def test_place_trap_and_the_trap_field_must_come_together() -> None:
    data = lib().skills["skill_bear_trap"].model_dump(mode="json")
    del data["trap"]
    with pytest.raises(ValidationError, match="必須成對"):
        SkillDef.model_validate(data)
    data = lib().skills["skill_bear_trap"].model_dump(mode="json")
    data["effects"] = data["effects"][1:]
    with pytest.raises(ValidationError, match="必須成對"):
        SkillDef.model_validate(data)


def test_a_trap_skill_must_be_an_active_ground_tile_skill_without_stacks() -> None:
    with pytest.raises(ValidationError, match="ground_tile"):
        variant("skill_bear_trap", shape={"type": "single", "range": 3})
    effects = lib().skills["skill_bear_trap"].model_dump(mode="json")["effects"]
    extra = {"type": "add_stack", "stack": "static_charge", "amount": 1, "affects": "self"}
    with pytest.raises(ValidationError, match="add_stack"):
        variant("skill_bear_trap", effects=[*effects, extra])


def test_cost_stacks_needs_a_consume_stack_effect_and_the_limit() -> None:
    with pytest.raises(ValidationError, match="consume_stack"):
        variant("skill_static_palm", cost={"mana": 3, "stacks": 1})
    over = variant("skill_thunder_finisher", cost={"mana": 8, "cooldown": 3, "stacks": 6})
    assert any("cost.stacks" in p for p in lib_problems(over))
    target_owned = variant("skill_armor_breaker", cost={"mana": 4, "cooldown": 2, "stacks": 1})
    assert any("cost.stacks" in p for p in lib_problems(target_owned))  # sunder 是 owner: target


def lib_problems(skill: SkillDef) -> list[str]:
    from trpg.content.skills import skill_problems  # noqa: PLC0415

    rules = lib().ruleset
    return skill_problems(
        skill,
        shapes=rules.shapes.by_id(),
        primitives=rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
        stacks={s.id: s for s in rules.stacks.stacks},
    )


def test_the_stack_owner_decides_who_the_effect_may_target() -> None:
    effects = lib().skills["skill_static_palm"].model_dump(mode="json")["effects"]
    effects[1]["affects"] = "enemies"  # static_charge 是 owner: self
    problems = lib_problems(variant("skill_static_palm", effects=effects))
    assert any("只能是 affects: self" in p for p in problems)
    effects = lib().skills["skill_sunder_strike"].model_dump(mode="json")["effects"]
    effects[1]["affects"] = "self"  # sunder 是 owner: target
    assert any(
        "只能是 affects: enemies" in p
        for p in lib_problems(variant("skill_sunder_strike", effects=effects))
    )
    effects[1].update(affects="enemies", amount=4)
    assert any("上限" in p for p in lib_problems(variant("skill_sunder_strike", effects=effects)))


def test_unknown_stack_ids_are_rejected() -> None:
    effects = lib().skills["skill_sunder_strike"].model_dump(mode="json")["effects"]
    effects[1]["stack"] = "nope"
    assert any(
        "未知的層數" in p for p in lib_problems(variant("skill_sunder_strike", effects=effects))
    )


def test_the_enabled_skeletons_require_their_structural_primitive_and_rarity() -> None:
    plain = [{"type": "damage", "dice": "1d8", "element": "lightning"}]
    assert "skeleton.required_primitive" in rules_of(variant("skill_static_palm", effects=plain))
    assert any(
        r.startswith("rarity") for r in rules_of(variant("skill_cinder_mine", rarity="common"))
    )


def test_consume_stack_adds_expected_bonus_points() -> None:
    skill = lib().skills["skill_thunder_finisher"]
    report = skill_budget(skill, lib())
    damage, consume = report.effects
    # 2d10 平均 11；期望消耗 5 × 500‰ ＝ 2.5 層；每層 250‰ → 11 × 2.5 × 0.25
    reach = report.range_coefficient  # 射程係數（3-49）
    assert damage.points == 11 * reach
    assert consume.points == Fraction(11) * reach * Fraction(5, 2) * Fraction(1, 4)


def test_a_trap_uses_the_trap_shape_and_the_trap_coefficient() -> None:
    mine = skill_budget(lib().skills["skill_cinder_mine"], lib())
    assert mine.coefficient_label == "AP 係數 × 陷阱係數"
    assert mine.ap_coefficient == Fraction(1000, 1000) * Fraction(800, 1000)
    by_type = {e.type: e for e in mine.effects}
    assert by_type["damage"].shape == Fraction(1800, 1000)  # cross
    assert by_type["place_trap"].shape == 1 and by_type["place_trap"].points == 2
    bear = skill_budget(lib().skills["skill_bear_trap"], lib())
    assert {e.type: e for e in bear.effects}["damage"].shape == 1  # single
