"""SK-1：距離條件「貼身」「遠距」（``point_blank``、``long_range``；06 6.38 第 1 點，#166）。

判定（距離 1／至少 ``far_distance``）、門檻可調、沒有單位的格子不成立、照一般條件打折預算，
以及組合器只給射程用得上的招。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import library, make_map, make_state, spawn
from tests.engine.skill_helpers import U1, U2
from trpg.content.skills import ConditionSpec, SkillDef, condition_text
from trpg.engine import BattleState
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.shared.types import Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_random_skill

FLAT = "\n".join(["0000000"] * 3)


def world(target_x: int, **core: Any) -> BattleState:
    """施放者在 (0, 1)，目標在 (target_x, 1)。"""
    spawns = [spawn(Team.ALLY, (0, 1)), spawn(Team.ENEMY, (target_x, 1))]
    return make_state(make_map(FLAT, ally=[(0, 1)], enemy=[(target_x, 1)]), spawns, **core)


def holds(state: BattleState, kind: str) -> bool:
    target = state.units[U2]
    return condition_met(
        state, state.units[U1], ConditionSpec(type=kind), Subject(target, target.xy)
    )


@pytest.mark.parametrize(
    ("x", "near", "far"), [(1, True, False), (2, False, False), (4, False, False), (5, False, True)]
)
def test_distance_conditions_by_distance(x: int, near: bool, far: bool) -> None:
    state = world(x)
    assert holds(state, "point_blank") is near
    assert holds(state, "long_range") is far


def test_far_distance_is_a_core_rule() -> None:
    assert library().ruleset.core.far_distance == 5
    assert holds(world(3, far_distance=3), "long_range")
    assert not holds(world(4, far_distance=6), "long_range")


def test_no_unit_on_the_tile_never_holds() -> None:
    state = world(5)
    for kind in ("point_blank", "long_range"):
        spec = ConditionSpec(type=kind)
        assert not condition_met(state, state.units[U1], spec, Subject(None, (1, 1)))
        assert not condition_met(state, state.units[U1], spec, Subject(None, (6, 1)))


def test_condition_text_is_chinese() -> None:
    assert condition_text(ConditionSpec(type="point_blank")) == "貼身（和目標相鄰）"
    assert condition_text(ConditionSpec(type="long_range")) == "遠距（和目標隔得夠遠）"


def _bolt(condition: dict[str, object] | None) -> SkillDef:
    base = library().skills["skill_fire_bolt"]
    spec = None if condition is None else ConditionSpec.model_validate(condition)
    return base.model_copy(update={"condition": spec})


@pytest.mark.parametrize("kind", ["point_blank", "long_range"])
def test_budget_discounts_like_a_common_condition(kind: str) -> None:
    lib = library()
    plain = skill_budget(_bolt(None), lib)
    common = lib.budget.condition_permille["common"]
    assert skill_budget(_bolt({"type": kind}), lib).condition_multiplier == Fraction(common, 1000)
    assert plain.condition_multiplier == 1


def test_composer_only_gives_distance_conditions_to_fitting_ranges() -> None:
    lib = library()
    far = lib.ruleset.core.far_distance
    seen: dict[str, int] = {"point_blank": 0, "long_range": 0}
    for seed in range(3000):
        skill = compose_random_skill(seed, rarity="epic", library=lib)
        found = [skill.condition] if skill.condition is not None else []
        found += [e.condition for e in skill.effects if e.condition is not None]
        for cond in found:
            if cond.type not in seen:
                continue
            seen[cond.type] += 1
            reach = skill.shape.range
            assert isinstance(reach, int)
            assert reach >= (2 if cond.type == "point_blank" else far), skill.id
    assert seen["point_blank"] > 0
    assert seen["long_range"] > 0
