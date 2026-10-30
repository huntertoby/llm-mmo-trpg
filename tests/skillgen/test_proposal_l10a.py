"""Phase 4-L10a：4-L9 真模型評估後的 schema、錯誤路徑修正。不需要網路與模型。"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, SkillRuleError, error_path_of
from trpg.skillgen.proposal import _proposal_path, _rule_error, _skill_path


@cache
def _lib() -> ContentLibrary:
    return library()


def _data(skill_id: str) -> dict[str, Any]:
    return _lib().skills[skill_id].model_dump(mode="json", exclude_defaults=True)


def _skill_error(data: dict[str, Any]) -> tuple[str, str]:
    """``SkillDef`` 驗證失敗 → （提議的錯誤路徑、訊息）。"""
    with pytest.raises(ValidationError) as info:
        SkillDef.model_validate(data)
    error = info.value.errors(include_url=False)[0]
    message = str(error["msg"]).removeprefix("Value error, ")
    return _skill_path(error, "", message), message


# -- A1：巢狀效果的錯誤帶完整路徑 ------------------------------------------------


def test_error_path_of_finds_nested_paths() -> None:
    assert error_path_of("effects[0]（damage）：x") == "effects[0]"
    assert error_path_of("cost.on_miss[1]（damage）：x") == "cost.on_miss[1]"
    assert error_path_of("effects[0].then[1]（damage）：x") == "effects[0].then[1]"
    assert error_path_of("effects[2]（gamble）.win[0]（damage）：x") == "effects[2].win[0]"
    assert error_path_of("cost.on_miss[1].status：反噬") == "cost.on_miss[1].status"
    assert error_path_of("followup.effects[0]（push）：x") == "followup.effects[0]"
    assert error_path_of("沒有路徑") == ""


def test_backlash_flag_error_points_at_cost_on_miss() -> None:
    data = _data("skill_fire_arrow")
    data["cost"] = {
        **data["cost"],
        "on_miss": [{"type": "damage", "dice": "1d4", "element": "fire", "explode": True}],
    }
    path, message = _skill_error(data)
    assert path == "cost_on_miss[0]"
    assert message.startswith("cost.on_miss[0]（damage）")


def test_then_flag_error_points_at_then() -> None:
    data = _data("skill_detonate_burning")
    data["effects"][0]["then"][0]["explode"] = True
    path, message = _skill_error(data)
    assert path == "effects[0].then[0]"
    assert "只能用在技能自己的傷害效果" in message


def test_gamble_branch_error_points_at_branch() -> None:
    data = _data("skill_fire_arrow")
    data["category"], data["weapon_req"] = "spell", "focus"
    data["cost"] = {"mana": 4}
    data["effects"] = [
        {"type": "damage", "dice": "1d6", "element": "fire"},
        {
            "type": "gamble",
            "chance_permille": 500,
            "win": [
                {
                    "type": "damage",
                    "dice": "1d4",
                    "element": "fire",
                    "scaling": {"by": "missing_hp_10pct", "per_step_permille": 50, "cap_permille": 200},
                }
            ],
        },
    ]
    path, _ = _skill_error(data)
    assert path == "effects[1].win[0]"


def test_variant_effect_error_points_at_variant() -> None:
    data = _data("skill_tidal_spear")
    data["variants"] = [
        {
            "id": "v1",
            "name_zh": "測試",
            "when": {"caster_high_ground": True},
            "add_effect": {"type": "damage", "element": "ice"},
        }
    ]
    path, message = _skill_error(data)
    assert path == "variants[0].add_effect"
    assert message.startswith("變奏「測試」")


def test_variant_replace_main_damage_points_at_index() -> None:
    data = _data("skill_tidal_spear")
    data["variants"] = [
        {
            "id": "v1",
            "name_zh": "測試",
            "when": {"caster_high_ground": True},
            "replace_effect": {
                "index": 0,
                "effect": {"type": "damage", "dice": "1d4", "element": "ice"},
            },
        }
    ]
    path, _ = _skill_error(data)
    assert path == "variants[0].replace_effect.index"


def test_rule_paths_are_translated_to_proposal_paths() -> None:
    skill = _lib().skills["skill_tidal_spear"]
    assert _proposal_path("cost.on_miss[1].status") == "cost_on_miss[1].status"
    assert _proposal_path("variants.high_tide.when", skill) == "variants[1].when"
    assert _proposal_path("variants.tide_pierce.shape.type", skill) == "variants[0].shape.type"
    error = _rule_error("reference", "variants.high_tide.cost.on_miss[0].status：反噬…", skill)
    assert error.path == "cost_on_miss[0].status"
    error = _rule_error(
        "variant.tide_pierce.skeleton.secondary_count", "水中貫穿：骨架 combo：附帶效果最多", skill
    )
    assert error.path == "variants[0]"


def test_skill_rule_error_is_value_error() -> None:
    assert issubclass(SkillRuleError, ValueError)
