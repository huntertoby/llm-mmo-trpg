"""驗證器擋一定成立（或一定不成立）的距離條件（SK-2b，玩法交接 4.1.29 第 1 點）：貼身要最大射程
≥ 2，遠距要最大射程 ≥ ``core.far_distance``（工坊值）。"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from trpg.content.skills import SkillDef
from trpg.skillgen.validate import skill_reach, validate_skill

RULE = "cap.distance_condition"
DAMAGE: dict[str, Any] = {"type": "damage", "dice": "1d6", "element": "fire"}


def _skill(shape: dict[str, Any], condition: str | None, *, effect_level: bool = False) -> SkillDef:
    effect = dict(DAMAGE)
    if condition is not None and effect_level:
        effect["condition"] = {"type": condition}
    data = make_skill("skill_t", shape, [effect]).model_dump(mode="json", exclude_none=True)
    if condition is not None and not effect_level:
        data["condition"] = {"type": condition}
    return SkillDef.model_validate(data)


def _rules(shape: dict[str, Any], condition: str, *, effect_level: bool = False) -> set[str]:
    skill = _skill(shape, condition, effect_level=effect_level)
    return {v.rule for v in validate_skill(skill, library())}


@pytest.mark.parametrize("effect_level", [False, True])
@pytest.mark.parametrize(
    ("shape", "condition", "blocked"),
    [
        ({"type": "single", "range": 1}, "point_blank", True),
        ({"type": "single", "range": 2}, "point_blank", False),
        ({"type": "single", "range": 4}, "long_range", True),
        ({"type": "single", "range": 5}, "long_range", False),
        ({"type": "line", "size": 4}, "long_range", True),
        ({"type": "line", "size": 3}, "point_blank", False),
    ],
)
def test_reach_gate(
    shape: dict[str, Any], condition: str, blocked: bool, effect_level: bool
) -> None:
    assert (RULE in _rules(shape, condition, effect_level=effect_level)) is blocked


def test_gate_reads_the_workshop_threshold() -> None:
    lib = library()
    far = lib.ruleset.core.far_distance
    skill = _skill({"type": "single", "range": far}, "long_range")
    assert RULE not in {v.rule for v in validate_skill(skill, lib)}
    core = lib.ruleset.core.model_copy(update={"far_distance": far + 1})
    raised = dataclasses.replace(lib, ruleset=lib.ruleset.model_copy(update={"core": core}))
    assert RULE in {v.rule for v in validate_skill(skill, raised)}


def test_reach_of_shapes() -> None:
    def reach(shape: dict[str, Any]) -> int | None:
        return skill_reach(_skill(shape, None))

    assert reach({"type": "single", "range": 3}) == 3
    assert reach({"type": "cone", "size": 2}) == 2
    assert reach({"type": "self"}) is None
