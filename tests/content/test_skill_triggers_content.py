"""Phase 2E-1：``content/skill_triggers.yaml``、被動骨架與四個手寫被動的內容檢查。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skill_triggers import REQUIRED_TRIGGERS, SkillTriggerDef, SkillTriggerTable

COEFFICIENTS = {
    "on_hit": 400,
    "on_crit": 250,
    "on_natural_20": 150,
    "on_kill": 300,
    "on_damaged": 400,
    "on_turn_start": 500,
    "on_turn_end": 500,
    "on_move": 300,
}
PASSIVES = ("skill_ember_brand", "skill_second_wind", "skill_thorn_skin", "skill_mark_detonation")


def test_the_nine_triggers_are_defined_with_the_spec_coefficients() -> None:
    rules = library().ruleset
    assert sorted(t.id for t in rules.skill_triggers.triggers) == sorted(REQUIRED_TRIGGERS)
    for trigger_id, permille in COEFFICIENTS.items():
        assert rules.trigger_def(trigger_id).coefficient_permille(None) == permille
    every = rules.trigger_def("every_n_hits")
    assert (every.coefficient_permille(2), every.coefficient_permille(3)) == (500, 600)
    assert all(t.min_rarity == "epic" for t in rules.skill_triggers.triggers)
    assert rules.core.max_trigger_depth == 3


def test_only_triggers_with_another_party_allow_target_other() -> None:
    rules = library().ruleset
    no_other = {"on_turn_start", "on_turn_end", "on_move"}
    for trigger in rules.skill_triggers.triggers:
        assert trigger.has_other is (trigger.id not in no_other)


def test_the_four_handwritten_passives_exist_and_are_not_on_existing_builds() -> None:
    lib = library()
    for skill_id in PASSIVES:
        skill = lib.skills[skill_id]
        assert skill.kind == "passive" and skill.skeleton == "passive" and skill.ap_cost is None
        assert skill.trigger is not None and skill.rarity in ("epic", "legendary")
    in_builds = {s for unit in lib.units.values() for s in unit.skills}
    assert not in_builds & set(PASSIVES)


def test_the_passive_skeleton_is_enabled_for_epic_and_above() -> None:
    skeleton = library().skeletons["passive"]
    assert skeleton.enabled and skeleton.min_rarity == "epic" and skeleton.kinds == ("passive",)


def test_the_trigger_table_rejects_missing_unknown_and_malformed_entries() -> None:
    table = library().ruleset.skill_triggers
    with pytest.raises(ValidationError, match="缺少"):
        SkillTriggerTable(triggers=table.triggers[1:])
    extra = SkillTriggerDef(
        id="on_party", name_zh="x", description_zh="x", has_other=False,
        budget_coefficient_permille=100,
    )  # fmt: skip
    with pytest.raises(ValidationError, match="on_party"):
        SkillTriggerTable(triggers=(*table.triggers, extra))
    with pytest.raises(ValidationError, match="budget_by_n_permille"):
        SkillTriggerDef(id="every_n_hits", name_zh="x", description_zh="x", has_other=True)
    with pytest.raises(ValidationError, match="budget_coefficient_permille"):
        SkillTriggerDef(id="on_hit", name_zh="x", description_zh="x", has_other=True)
