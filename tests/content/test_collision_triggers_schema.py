"""Phase 3C-3a：新觸發時機的參數（``tag``、``status``）、撞擊骰與預算、演示技能。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

DEMOS = {
    "skill_fracture_mark": "on_collision",
    "skill_creeping_blight": "on_status_applied",
    "skill_ember_ward": "on_cast_tag",
}


def test_trigger_params_must_match_the_event() -> None:
    assert TriggerSpec(event="on_cast_tag", tag="fire").tag == "fire"
    assert TriggerSpec(event="on_status_applied").status is None
    assert TriggerSpec(event="on_status_applied", status="burning").status == "burning"
    assert TriggerSpec(event="on_collision").tag is None
    with pytest.raises(ValidationError, match="on_cast_tag 必須填 tag"):
        TriggerSpec(event="on_cast_tag")
    with pytest.raises(ValidationError, match="只有 on_cast_tag 使用 tag"):
        TriggerSpec(event="on_hit", tag="fire")
    with pytest.raises(ValidationError, match="只有 on_status_applied 使用 status"):
        TriggerSpec(event="on_collision", status="burning")
    with pytest.raises(ValidationError):
        TriggerSpec(event="on_cast_tag", tag="Fire Tag")


def _demo(skill_id: str, **trigger: Any) -> SkillDef:
    skill = library().skills[skill_id]
    assert skill.trigger is not None
    return skill.model_copy(
        update={"trigger": TriggerSpec.model_validate({**skill.trigger.model_dump(), **trigger})}
    )


def test_unknown_status_in_trigger_is_reported() -> None:
    lib = library()
    bad = _demo("skill_creeping_blight", status="no_such_status")
    assert any("trigger.status" in v.message for v in validate_skill(bad, lib))
    good = _demo("skill_creeping_blight", status="burning")
    assert validate_skill(good, lib) == []


def test_target_other_needs_a_party_for_on_cast_tag() -> None:
    bad = _demo("skill_ember_ward", target="other")
    assert any("target" in v.message for v in validate_skill(bad, library()))


def test_demo_skills_use_the_new_triggers_and_pass_validation_and_budget() -> None:
    lib = library()
    for skill_id, event in DEMOS.items():
        skill = lib.skills[skill_id]
        assert skill.trigger is not None and skill.trigger.event == event
        assert skill.rarity == "epic" and validate_skill(skill, lib) == []
        assert 0.7 <= float(skill_budget(skill, lib).ratio) <= 1.0
    assert library().skills["skill_ember_ward"].trigger.tag == "fire"  # type: ignore[union-attr]


def test_new_triggers_need_epic_and_are_not_picked_by_the_random_composer() -> None:
    rules = library().ruleset
    for event in DEMOS.values():
        definition = rules.trigger_def(event)
        assert definition.min_rarity == "epic" and definition.random_composer is False
    seen = {
        s.trigger.event
        for seed in range(60)
        if (s := compose_random_skill(seed, tier=1, rarity="epic", skeleton="passive")).trigger
    }
    assert seen and seen.isdisjoint(DEMOS.values())


def test_collision_dice_is_a_push_pull_parameter_and_costs_budget_points() -> None:
    lib = library()
    ram = lib.skills["skill_battering_ram"]
    push = next(e for e in ram.effects if e.type == "push")
    assert str(push.collision_dice) == "2d6"
    assert validate_skill(ram, lib) == []
    plain = ram.model_copy(
        update={
            "effects": tuple(
                e.model_copy(update={"collision_dice": None}) if e.type == "push" else e
                for e in ram.effects
            )
        }
    )
    extra = skill_budget(ram, lib).total - skill_budget(plain, lib).total
    assert extra == 2 * lib.budget.collision_die_points  # 2 顆骰
    damage = next(e for e in ram.effects if e.type == "damage")
    bad = ram.model_copy(
        update={"effects": (damage.model_copy(update={"collision_dice": push.collision_dice}),)}
    )
    assert any("collision_dice" in v.message for v in validate_skill(bad, lib))
