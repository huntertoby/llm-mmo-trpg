"""Phase 2E-1 3.9：被動技能的驗證（trigger 欄位、時機、稀有度、預算）。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from pydantic import ValidationError

from tests.skillgen.helpers import lib, rules_of, violations
from trpg.content.skills import SkillDef
from trpg.skillgen.validate import structural_rarity


def passive(**overrides: Any) -> SkillDef:
    data: dict[str, Any] = lib().skills["skill_ember_brand"].model_dump(mode="json")
    data.update(overrides)
    return SkillDef.model_validate(data)


def _trigger(**updates: Any) -> dict[str, Any]:
    trigger = lib().skills["skill_ember_brand"].model_dump(mode="json")["trigger"]
    return {**trigger, **updates}


def test_the_shipped_passives_validate() -> None:
    for skill_id in ("skill_ember_brand", "skill_second_wind", "skill_thorn_skin"):
        assert violations(lib().skills[skill_id]) == []


def test_a_passive_without_trigger_and_an_active_with_one_are_schema_errors() -> None:
    with pytest.raises(ValidationError, match="必須有 trigger"):
        passive(trigger=None)
    with pytest.raises(ValidationError, match="只有被動技能可以有 trigger"):
        SkillDef.model_validate(
            {
                **lib().skills["skill_cleave"].model_dump(mode="json"),
                "trigger": _trigger(),
            }
        )


def test_an_unknown_event_is_rejected() -> None:
    found = violations(passive(trigger=_trigger(event="on_birthday")))
    assert any(v.rule == "reference" and "未知的觸發時機" in v.message for v in found)


def test_target_other_needs_a_trigger_with_another_party() -> None:
    found = violations(passive(trigger=_trigger(event="on_turn_start")))
    assert any(v.rule == "reference" and "沒有另一方" in v.message for v in found)


def test_every_n_hits_needs_n_two_or_three() -> None:
    ok = passive(trigger=_trigger(event="every_n_hits", n=2))
    assert not any("trigger" in v.message for v in violations(ok))
    with pytest.raises(ValidationError):
        passive(trigger=_trigger(event="every_n_hits", n=5))
    with pytest.raises(ValidationError):
        passive(trigger=_trigger(event="every_n_hits"))


def test_max_per_round_is_between_one_and_three() -> None:
    for bad in (0, 4):
        with pytest.raises(ValidationError):
            passive(trigger=_trigger(max_per_round=bad))


def test_a_passive_below_epic_is_only_a_marker() -> None:
    # 3W-9：稀有度只是「長得多複雜」的標記，不再擋（6.34.9）；被動的結構算出來是史詩
    assert not any(r.startswith("rarity") for r in rules_of(passive(rarity="rare")))
    assert structural_rarity(passive(rarity="rare"), lib()) == "epic"


def test_a_passive_must_be_a_spell_with_any_weapon() -> None:
    assert "passive.category" in rules_of(passive(category="weapon", weapon_req="melee"))


def test_a_self_target_passive_cannot_hurt_enemies() -> None:
    effects = [{"type": "damage", "dice": "1d6", "element": "fire", "affects": "enemies"}]
    skill = passive(effects=effects, trigger=_trigger(target="self"))
    assert "passive.affects" in rules_of(skill)


def test_an_over_budget_passive_is_rejected() -> None:
    effects = [{"type": "damage", "dice": "8d12", "element": "fire", "affects": "enemies"}]
    assert any(r.startswith("budget") for r in rules_of(passive(effects=effects)))


def test_the_passive_category_rule_is_read_from_the_skeleton_data() -> None:
    assert lib().skeletons["passive"].required_category == "spell"
    assert lib().skeletons["passive"].required_weapon_req == "any"
    weapon_passive = passive(category="weapon", weapon_req="melee")
    relaxed_skeleton = (
        lib()
        .skeletons["passive"]
        .model_copy(update={"required_category": None, "required_weapon_req": None})
    )
    relaxed = replace(lib(), skeletons={**lib().skeletons, "passive": relaxed_skeleton})
    assert "passive.category" in rules_of(weapon_passive)
    assert "passive.category" not in rules_of(weapon_passive, relaxed)
