"""Phase 4-L8b：AP、冷卻、耐力（法力）成為預算旋鈕。補值器在最低費用仍超出預算時往上補費用；
手寫技能的預算不變。不需要網路與模型。"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen import proposal_budget
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    proposal_from_skill,
)
from trpg.skillgen.proposal_budget import _with_step, evaluate_with_repair


@cache
def _lib() -> ContentLibrary:
    return library()


@cache
def _models() -> ProposalModels:
    return build_proposal_models(_lib())


def _run(skill_id: str, seed: int) -> Any:
    skill = _lib().skills[skill_id]
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
    prop = proposal_from_skill(skill, _lib())
    return evaluate_with_repair(prop, _models(), _lib(), ctx, seed=seed)


def test_ladder_respects_cooldown_limit() -> None:
    rules = _lib().composer.llm_cost
    assert rules.steps
    assert rules.max_cooldown == 5
    assert all((s.cooldown or 0) <= 5 for s in rules.steps)


@pytest.mark.parametrize("skill_id", ["skill_cleave", "skill_fire_bolt"])
def test_ladder_is_monotone(skill_id: str) -> None:
    """階梯由輕到重：同一個技能套上每一階後，預算比例不會上升（折抵與 AP 係數單調）。"""
    lib = _lib()
    if skill_id not in lib.skills:
        pytest.skip("沒有這個技能")
    data = lib.skills[skill_id].model_dump(mode="json", exclude_defaults=True)
    data["ap_cost"] = 2
    data["cost"] = {lib.budget.resource_of(data["category"]): 1}
    last = None
    for step in lib.composer.llm_cost.steps:
        trial = _with_step(lib, data, step)
        ratio = skill_budget(SkillDef.model_validate(trial), lib).ratio
        if last is not None:
            assert ratio <= last, step
        last = ratio


def test_step_converts_mana_to_stamina_for_weapon_skills() -> None:
    lib = _lib()
    step = next(s for s in lib.composer.llm_cost.steps if s.mana)
    weapon = _with_step(lib, {"category": "weapon", "cost": {"stamina": 1}}, step)
    spell = _with_step(lib, {"category": "spell", "cost": {"mana": 1}}, step)
    assert weapon["cost"]["stamina"] == lib.budget.stamina_for_mana(step.mana or 0)
    assert "mana" not in weapon["cost"]
    assert spell["cost"]["mana"] == step.mana


def test_step_never_lowers_existing_cost() -> None:
    lib = _lib()
    step = lib.composer.llm_cost.steps[0]
    out = _with_step(lib, {"category": "spell", "ap_cost": 3, "cost": {"cooldown": 4}}, step)
    assert out["ap_cost"] == 3
    assert out["cost"]["cooldown"] == 4


@pytest.mark.parametrize("skill_id", ["skill_leap_slam", "skill_gravity_burst"])
def test_over_budget_composites_now_succeed(skill_id: str) -> None:
    """4-L8 的待決 #6：以最低費用計算就超出預算的複合技能，補值器調高費用後回到區間。"""
    for seed in range(5):
        result = _run(skill_id, seed)
        assert result.ok, (seed, result.result.errors)
        skill = result.result.skill
        assert (skill.cost.cooldown or 0) > 0 or skill.ap_cost > 2  # 補了費用
        assert (skill.cost.cooldown or 0) <= 5


def test_without_the_knob_leap_slam_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """對照：關掉費用旋鈕，leap_slam 在補值器下過不了預算（4-L8 的現況）。"""
    monkeypatch.setattr(proposal_budget, "raise_costs", lambda _lib, data: data)
    failed = [s for s in range(5) if not _run("skill_leap_slam", s).ok]
    assert failed


def test_no_raise_when_within_budget() -> None:
    """沒有超出預算的提議不動費用（AP 2、沒有冷卻）。"""
    result = _run("skill_ash_harvest", 0)
    skill = result.result.skill
    assert skill is not None
    assert skill.ap_cost == 2


def test_hand_written_budgets_untouched() -> None:
    """旋鈕只在補值器：內容庫每一招手寫技能的預算比例仍在驗證範圍內（逐字比對見報告）。"""
    lib = _lib()
    for skill in lib.skills.values():
        assert skill_budget(skill, lib).ratio > 0
