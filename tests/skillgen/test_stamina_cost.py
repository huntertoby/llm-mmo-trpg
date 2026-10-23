"""武器技花耐力的預算（Phase 3H-2，06 6.10）：耐力與法力預算點數等價，217 招重算後比例不變且在
合格區間；產生器依類別花對的資源。"""

from __future__ import annotations

import pytest

from tests.skillgen.helpers import lib, skill
from trpg.content.skills import SkillCost, SkillDef
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

SKILLS = sorted(lib().skills)


def _as_mana(s: SkillDef) -> SkillDef:
    """把耐力代價換回等價的法力（3H-2 之前的寫法）。"""
    ratio = lib().budget.allowance.stamina_per_mana
    assert s.cost.stamina % ratio == 0
    cost = s.cost.model_copy(update={"mana": s.cost.stamina // ratio, "stamina": 0})
    return s.model_copy(update={"cost": cost})


@pytest.mark.parametrize("skill_id", SKILLS, ids=lambda sid: sid.removeprefix("skill_"))
def test_every_skill_spends_its_category_resource_and_stays_in_the_window(skill_id: str) -> None:
    s = lib().skills[skill_id]
    budget = lib().budget
    assert budget.cost_problem(s.category, s.cost) is None
    if s.category == "weapon":
        assert s.cost.mana == 0
    else:
        assert s.cost.stamina == 0
    assert not validate_skill(s, lib())  # 含預算區間（重算後仍合格）
    report = skill_budget(s, lib())
    if s.cost.stamina:
        old = skill_budget(_as_mana(s), lib())
        assert (report.allowance_permille, report.ratio) == (old.allowance_permille, old.ratio)


def test_weapon_skills_in_the_library_cost_stamina() -> None:
    skills = lib().skills.values()
    assert len(skills) >= 217  # 3H-2 重算時 217 招
    weapon = [s for s in skills if s.category == "weapon" and s.kind == "active"]
    assert sum(1 for s in weapon if s.cost.stamina) >= 60


@pytest.mark.parametrize("mana", [1, 3, 4, 5, 6, 30, 40])
def test_stamina_allowance_equals_the_mana_allowance(mana: int) -> None:
    budget = lib().budget
    stamina = budget.stamina_for_mana(mana)
    a = skill_budget(skill(cost={"stamina": stamina, "cooldown": 2}), lib())
    b = skill_budget(
        skill(cost={"stamina": 0, "cooldown": 2}).model_copy(
            update={"cost": SkillCost(mana=mana, cooldown=2)}
        ),
        lib(),
    )
    assert a.allowance_raw_permille == b.allowance_raw_permille


def test_a_weapon_skill_that_spends_mana_is_a_violation() -> None:
    bad = skill(cost={"mana": 4, "cooldown": 2})
    rules = [v.rule for v in validate_skill(bad, lib())]
    assert "cap.resource" in rules
    spell = skill(
        category="spell",
        weapon_req="focus",
        scaling_attr="int",
        effects=[{"type": "damage", "dice": "2d6", "element": "fire"}],
        cost={"stamina": 8, "cooldown": 2},
    )
    assert "cap.resource" in [v.rule for v in validate_skill(spell, lib())]


def test_resource_cost_converts_only_for_stamina_categories() -> None:
    budget = lib().budget
    assert budget.resource_cost({"mana": 5, "cooldown": 2}, "weapon") == {
        "cooldown": 2,
        "stamina": 10,
    }
    assert budget.resource_cost({"mana": 5}, "spell") == {"mana": 5}
    assert budget.resource_cost({"mana": 0, "cooldown": 1}, "weapon") == {"mana": 0, "cooldown": 1}


@pytest.mark.parametrize("category", ["weapon", "spell"])
def test_the_random_composer_spends_the_category_resource(category: str) -> None:
    paid = 0
    for seed in range(16):
        s = compose_random_skill(seed, category=category)
        assert lib().budget.cost_problem(s.category, s.cost) is None
        assert not validate_skill(s, lib())
        paid += s.cost.stamina if s.category == "weapon" else s.cost.mana
    assert paid > 0
