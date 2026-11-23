"""QF-6（佇列 (r)，06 6.3「預算」2026-11-23 玩法 PM 定）：只有一個效果、預算 0 的技能不合法，只有
預支基本款例外：唯一效果是預支（``borrow_ap``）、主動技、0 AP、形狀自身，四項都要符合。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import borrow_basic, skill_budget
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

BASIC = "skill_borrowed_beat"  # 內容裡的預支基本款：0 AP、冷卻 2、自身、預支 1
BORROW_SEEDS = (238, 336, 435, 606, 873, 998)  # 組合器（預設參數）組出預支基本款的種子


def _variant(**changes: Any) -> SkillDef:
    data = library().skills[BASIC].model_dump(mode="json")
    return SkillDef.model_validate({**data, **changes})


def test_all_four_conditions_pass() -> None:
    lib = library()
    skill = _variant()
    assert borrow_basic(skill)
    report = skill_budget(skill, lib)
    assert report.total == 0 and report.min_ratio == 0
    assert validate_skill(skill, lib) == []


def test_not_self_shape_is_rejected() -> None:
    lib = library()
    skill = _variant(shape={"type": "ring", "radius": 1})
    assert not borrow_basic(skill)
    report = skill_budget(skill, lib)
    assert report.total == 0 and report.min_ratio > 0  # 不再豁免過弱下限
    assert report.too_weak
    assert validate_skill(skill, lib) != []


def test_other_single_zero_budget_effect_is_rejected() -> None:
    lib = library()
    skill = _variant(ap_cost=1, effects=[{"type": "leave_form"}])
    assert not borrow_basic(skill)
    report = skill_budget(skill, lib)
    assert report.total == 0 and report.too_weak
    assert "budget.weak" in {v.rule for v in validate_skill(skill, lib)}


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "passive", "ap_cost": None, "trigger": {"event": "on_turn_start"}},
        {"kind": "reaction", "ap_cost": None, "reaction": {"event": "hit_by_attack"}},
    ],
    ids=["passive", "reaction"],
)
def test_not_active_is_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="borrow_ap 只能用在主動技能"):
        _variant(**changes)


def test_not_zero_ap_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ap_cost 必須是 0"):
        _variant(ap_cost=1)


def test_borrow_with_other_effects_is_rejected_by_the_schema() -> None:
    with pytest.raises(ValidationError, match="borrow_ap 必須是技能唯一的效果"):
        _variant(effects=[{"type": "borrow_ap", "amount": 1}, {"type": "cleanse"}])


@pytest.mark.parametrize("seed", BORROW_SEEDS)
def test_composer_borrow_seeds_are_the_basic_skill(seed: int) -> None:
    lib = library()
    skill = compose_random_skill(seed, library=lib)
    assert borrow_basic(skill)
    assert validate_skill(skill, lib) == []
