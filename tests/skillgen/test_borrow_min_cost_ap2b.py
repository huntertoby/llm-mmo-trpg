"""AP-2b：帶預支（``borrow_ap``）的技能不受最低花費限制（06 6.10 例外、6.3「預支」）——0 法力、
0 耐力可以通過；不帶預支的主動技照舊至少 1 法力／1 耐力。驗證器、LLM 提議補值、往返覆蓋都照同一條。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.proposal_numbers import _fill_cost
from trpg.skillgen.validate import validate_skill

BORROW = "skill_borrowed_beat"


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return library()


def _variant(lib: ContentLibrary, skill_id: str, **update: Any) -> SkillDef:
    data = lib.skills[skill_id].model_dump(mode="json")
    return SkillDef.model_validate({**data, **update})


def _rules(lib: ContentLibrary, skill: SkillDef) -> set[str]:
    return {v.rule for v in validate_skill(skill, lib)}


@pytest.mark.parametrize(("category", "weapon_req"), [("spell", "any"), ("weapon", "melee")])
def test_borrow_skill_with_no_mana_or_stamina_passes(
    lib: ContentLibrary, category: str, weapon_req: str
) -> None:
    skill = _variant(lib, BORROW, category=category, weapon_req=weapon_req, cost={"cooldown": 2})
    assert skill.cost.mana == 0 and skill.cost.stamina == 0
    assert skill.borrows_ap
    assert "cap.min_cost" not in _rules(lib, skill)
    assert lib.budget.min_cost_problem(skill.kind, skill.category, skill.cost, borrows=True) is None


def _plain_active(lib: ContentLibrary, category: str) -> SkillDef:
    for skill_id in sorted(lib.skills):
        skill = lib.skills[skill_id]
        resource = lib.budget.resource_of(skill.category)
        if (
            skill.kind == "active"
            and skill.category == category
            and not skill.borrows_ap
            and skill.cost.source is None
            and "gear" not in skill.tags
            and getattr(skill.cost, resource) >= 1
        ):
            return skill
    raise AssertionError(category)


@pytest.mark.parametrize("category", ["spell", "weapon"])
def test_skill_without_borrow_still_needs_one(lib: ContentLibrary, category: str) -> None:
    base = _plain_active(lib, category)
    assert "cap.min_cost" not in _rules(lib, base)
    data = base.model_dump(mode="json")
    cost = {k: v for k, v in data["cost"].items() if k not in ("mana", "stamina")}
    skill = SkillDef.model_validate({**data, "cost": cost})
    assert "cap.min_cost" in _rules(lib, skill)
    assert lib.budget.min_cost_problem(skill.kind, skill.category, skill.cost) is not None


def test_proposal_filler_leaves_borrow_cost_alone(lib: ContentLibrary) -> None:
    out: dict[str, Any] = {
        "kind": "active",
        "effects": [{"type": "borrow_ap", "amount": 1}],
        "cost": {"cooldown": 2},
    }
    _fill_cost(out, lib, "spell")
    assert out["ap_cost"] == 0
    assert out["cost"] == {"cooldown": 2}


def test_proposal_filler_still_tops_up_other_skills(lib: ContentLibrary) -> None:
    out: dict[str, Any] = {"kind": "active", "effects": [{"type": "damage"}], "cost": {}}
    _fill_cost(out, lib, "spell")
    assert out["cost"]["mana"] == 10  # X10-2b：最低費用 1 × quantity_scale
