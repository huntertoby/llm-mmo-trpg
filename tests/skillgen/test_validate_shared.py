"""Phase 3E-1 #1：技能驗證器與內容庫載入共用同一份引用檢查（``skill_reference_problems``）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.skillgen.helpers import lib, violations
from trpg.content.library import _check_skills, skill_reference_problems
from trpg.content.skills import SkillDef
from trpg.shared.errors import ContentError

_GRANTER_BASE: dict[str, Any] = {
    "id": "skill_t_granter",
    "name_zh": "測試給技能",
    "tier": 1,
    "rarity": "rare",
    "skeleton": "aura",
    "category": "spell",
    "weapon_req": "any",
    "ap_cost": 1,
    "scaling_attr": "wis",
    "shape": {"type": "self"},
    "cost": {"mana": 0},
}


def granter(granted: str) -> SkillDef:
    effect = {"type": "grant_skill", "skill": granted, "duration": 3, "affects": "self"}
    return SkillDef.model_validate({**_GRANTER_BASE, "effects": [effect]})


def wrong_ap_legend() -> SkillDef:
    data = lib().skills["skill_afterimage_vow"].model_dump(mode="json")
    activation = lib().ruleset.core.legendary_activation_ap
    data["ap_cost"] = activation + 1
    return SkillDef.model_validate(data)


def bad_skills() -> dict[str, SkillDef]:
    return {
        "grant_legendary": granter("skill_time_surge"),
        "grant_rewrite": granter("skill_undying_oath"),
        "grant_missing": granter("skill_nope"),
        "grant_passive": granter("skill_steady_breath"),
        "rule_change_ap": wrong_ap_legend(),
    }


@pytest.mark.parametrize("name", sorted(bad_skills()))
def test_validate_skill_rejects_bad_references(name: str) -> None:
    found = [v for v in violations(bad_skills()[name]) if v.rule == "reference"]
    assert found, name


def test_the_rule_change_legend_ap_cost_is_checked() -> None:
    found = violations(wrong_ap_legend())
    assert any("legendary_activation_ap" in v.message for v in found)


@pytest.mark.parametrize("name", sorted(bad_skills()))
def test_validator_and_content_library_agree_on_bad_skills(name: str, tmp_path: Path) -> None:
    skill = bad_skills()[name]
    library = lib()
    expected = skill_reference_problems(skill, library.ruleset, library.skills)
    assert expected
    from_validator = [v.message for v in violations(skill) if v.rule == "reference"]
    assert from_validator == expected
    with pytest.raises(ContentError) as raised:
        _check_skills(tmp_path, {**library.skills, skill.id: skill}, library.ruleset)
    assert "；".join(expected) in str(raised.value)


def test_every_shipped_skill_passes_the_shared_check() -> None:
    library = lib()
    for skill in library.skills.values():
        assert skill_reference_problems(skill, library.ruleset, library.skills) == [], skill.id
