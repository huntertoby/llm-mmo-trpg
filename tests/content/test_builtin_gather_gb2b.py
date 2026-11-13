"""GB-2b：灰燼之心的吸氣「4 格內」只放寬內建技能的範圍（19.2.3 R7）。

範圍光環當聚集段（``BUILTIN_GATHER_SHAPES``）與範圍光環半徑 4（``skill_shapes.yaml`` 的
``content_max``）只有內建技能或敵人專用招（``SkillDef.content_only_ok``；閃現等衍生版本沿用
``enemy_only``）能寫；技能生成器、LLM 提議看到的範圍不變。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skills import BUILTIN_GATHER_SHAPES, GATHER_SHAPES, SkillDef
from trpg.content.skills.skill import _int_param_problems
from trpg.narrative.skills import followup_text
from trpg.skillgen.validate import validate_skill

INHALE = "skill_heart_inhale"


def _inhale_data(origin: str, *, enemy_only: bool = False) -> dict[str, Any]:
    data = library().skills[INHALE].model_dump(mode="json")
    data["id"] = "skill_t_gb2b_gather"
    data["provenance"] = {"origin": origin, "created_by": "llm"}
    data["enemy_only"] = enemy_only
    return data


def test_llm_facing_ranges_are_unchanged() -> None:
    assert GATHER_SHAPES == ("cross", "square3", "ring")
    assert BUILTIN_GATHER_SHAPES == ("allies_in_radius",)
    radius = library().ruleset.shape_def("allies_in_radius").params["radius"]
    assert (radius.min, radius.max, radius.content_max) == (1, 3, 4)


def test_builtin_inhale_loads_and_validates() -> None:
    lib = library()
    skill = lib.skills[INHALE]
    assert (skill.shape.type, skill.shape.radius) == ("allies_in_radius", 4)
    assert not [v for v in validate_skill(skill, lib) if v.rule == "skeleton.shape"]


@pytest.mark.parametrize("origin", ["level_up", "drop", "workshop", "crafted"])
def test_only_builtin_skills_may_gather_with_an_aura(origin: str) -> None:
    with pytest.raises(ValidationError, match="聚集段的形狀只能是 cross、square3、ring"):
        SkillDef.model_validate(_inhale_data(origin))


def test_derived_enemy_only_skills_keep_the_aura() -> None:
    """閃現、升階等衍生版本換了來源（``level_up``）但仍是敵人專用招。"""
    skill = SkillDef.model_validate(_inhale_data("level_up", enemy_only=True))
    assert skill.content_only_ok
    assert not SkillDef.model_validate(_inhale_data("builtin")).enemy_only


def test_radius_four_is_builtin_only() -> None:
    shape = library().ruleset.shape_def("allies_in_radius")
    assert _int_param_problems("shape", {"radius": 4}, shape, builtin=True) == []
    assert _int_param_problems("shape", {"radius": 3}, shape) == []
    [problem] = _int_param_problems("shape", {"radius": 4}, shape)
    assert "必須在 1–3" in problem
    [problem] = _int_param_problems("shape", {"radius": 5}, shape, builtin=True)
    assert "必須在 1–4" in problem


def test_lava_splash_card_says_it_lands_on_the_farthest_enemy() -> None:
    lib = library()
    text = followup_text(lib, lib.skills["skill_lava_splash"])
    assert text is not None
    assert "離自己最遠的敵人那一帶" in text
    assert "施放時選的格子" not in text
