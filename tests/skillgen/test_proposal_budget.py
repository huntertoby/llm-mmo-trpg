"""4-L5：提議的數值補齊（預算器）與引擎可修的錯誤。"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.content.library import ContentLibrary
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.composer_parts import effect_knobs
from trpg.skillgen.composer_tuning import tuning_bounds
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalError,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_budget import (
    REPAIR_COOLDOWN,
    REPAIRABLE_CODES,
    budget_filler,
    cooldown_repairs,
    evaluate_with_repair,
    is_repairable,
    repairable_codes,
    repairable_errors,
)
from trpg.skillgen.proposal_numbers import split_numbers
from trpg.skillgen.random_composer import default_library

WEAK_ONLY = ("skill_fire_arrow", "skill_cleave", "skill_execute", "skill_bloodlust")
"""最小補值下只剩 ``budget.weak``、預算器補完直接合格的手寫技能（結構）。"""


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


@pytest.fixture(scope="module")
def models(library: ContentLibrary) -> ProposalModels:
    return build_proposal_models(library)


def _proposal(library: ContentLibrary, skill_id: str) -> tuple[dict[str, Any], ProposalContext]:
    skill = library.skills[skill_id]
    return proposal_from_skill(skill, library), ProposalContext(skill.tier, skill.rarity)


@pytest.mark.parametrize("skill_id", WEAK_ONLY)
def test_budget_filler_fixes_weak_and_is_deterministic(
    library: ContentLibrary, models: ProposalModels, skill_id: str
) -> None:
    proposal, ctx = _proposal(library, skill_id)
    minimal = evaluate_proposal(proposal, models, library, ctx)
    assert [e.code for e in minimal.errors] == ["budget.weak"]
    first = evaluate_with_repair(proposal, models, library, ctx, seed=11)
    second = evaluate_with_repair(proposal, models, library, ctx, seed=11)
    assert first.ok and first.repaired == ()
    assert first.result.skill is not None and second.result.skill is not None
    assert first.result.skill.model_dump() == second.result.skill.model_dump()
    low, high = tuning_bounds(library)
    ratio = skill_budget(first.result.skill, library).ratio
    assert low <= ratio <= high
    # 形狀參數（LLM 選的結構）保留不調
    assert first.result.skill.shape.model_dump(mode="json", exclude_none=True) == {
        k: v for k, v in proposal["shape"].items() if v is not None
    }


def test_numbers_come_from_filler_not_proposal(library: ContentLibrary) -> None:
    proposal, _ = _proposal(library, "skill_fire_arrow")
    skill = library.skills["skill_fire_arrow"]
    structure, removed = split_numbers(skill.model_dump(mode="json"), library)
    assert removed  # 手寫技能有數值，提議沒有
    assert (
        "dice" not in proposal["effects"][0] and "multiplier_permille" not in proposal["effects"][0]
    )
    data = {**structure, "id": "x", "kind": "active"}
    a = budget_filler(library, seed=1)(dict(data))
    b = budget_filler(library, seed=1)(dict(data))
    assert a == b
    knobs = effect_knobs(library, a["effects"][0], category=a["category"], weight=1)
    assert knobs and all(a["effects"][0][name] in values for name, values, _ in knobs)


def test_different_seeds_may_differ_but_stay_in_bounds(
    library: ContentLibrary, models: ProposalModels
) -> None:
    proposal, ctx = _proposal(library, "skill_cleave")
    low, high = tuning_bounds(library)
    for seed in range(5):
        evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=seed)
        assert evaluation.ok and evaluation.result.skill is not None
        assert low <= skill_budget(evaluation.result.skill, library).ratio <= high


def test_no_cooldown_big_area_repaired_with_minimal_cooldown(
    library: ContentLibrary, models: ProposalModels
) -> None:
    proposal, ctx = _proposal(library, "skill_blinding_dark")
    plain = evaluate_proposal(proposal, models, library, ctx, fill=budget_filler(library, seed=3))
    assert [e.code for e in plain.errors] == ["exclusion.no_cooldown_big_area"]
    evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=3)
    assert evaluation.ok and evaluation.repaired == ("exclusion.no_cooldown_big_area",)
    assert evaluation.result.skill is not None
    assert evaluation.result.skill.cost.cooldown == REPAIR_COOLDOWN


def test_core_share_repair_only_raises_core(
    library: ContentLibrary, models: ProposalModels
) -> None:
    proposal, ctx = _proposal(library, "skill_hex_bolt")
    evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=3)
    assert evaluation.ok and "skeleton.core_share" in evaluation.repaired


def test_cooldown_part_is_repaired_and_the_rest_is_returned(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """4-L5b：硬控規則要求「形狀 single ＋ 冷卻至少 4」。引擎先把冷卻補到 4，形狀不對的部分
    仍回報。"""
    proposal, ctx = _proposal(library, "skill_deep_freeze")
    proposal = {**proposal, "shape": {"type": "cross", "range": 3}}  # 硬控但不是單體
    evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=3)
    assert not evaluation.ok
    assert "exclusion.stun_single_long_cooldown" in [e.code for e in evaluation.result.errors]
    filled = budget_filler(library, seed=3, repairs=["exclusion.stun_single_long_cooldown"])
    data = filled({**proposal, "tier": ctx.tier, "rarity": ctx.rarity})
    assert data["cost"]["cooldown"] == 4  # 補到規則要求的冷卻（skill_exclusions.yaml）


def test_stun_on_single_target_is_repaired_by_the_engine(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """形狀已經是 single 的硬控提議：缺的只有冷卻，引擎補到 4 後通過，不必回 LLM。"""
    proposal = {
        "form": "standard",
        "name_zh": "冰封",
        "kind": "active",
        "skeleton": "control",
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": "int",
        "shape": {"type": "single", "range": 4},
        "effects": [{"type": "apply_status", "status": "stun"}],
    }
    ctx = ProposalContext(tier=2, rarity="rare")
    plain = evaluate_proposal(proposal, models, library, ctx, fill=budget_filler(library, seed=5))
    assert "exclusion.stun_single_long_cooldown" in [e.code for e in plain.errors]
    evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=5)
    assert "exclusion.stun_single_long_cooldown" in evaluation.repaired
    assert "exclusion.stun_single_long_cooldown" not in [e.code for e in evaluation.result.errors]
    if evaluation.ok:
        assert evaluation.result.skill is not None
        assert evaluation.result.skill.cost.cooldown >= 4


def test_mixed_errors_repair_what_can_be_repaired_first(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """可修與不可修的錯誤混在一起時，引擎仍先修可修的（冷卻），只回報剩下的。"""
    proposal, ctx = _proposal(library, "skill_blinding_dark")
    bad = {**proposal, "skeleton": "strike"}  # 骨架不合（不可修）＋ 沒有冷卻的大範圍（可修）
    plain = evaluate_proposal(bad, models, library, ctx, fill=budget_filler(library, seed=3))
    codes = {e.code for e in plain.errors}
    assert "exclusion.no_cooldown_big_area" in codes
    assert codes - {"exclusion.no_cooldown_big_area"}  # 還有不可修的
    evaluation = evaluate_with_repair(bad, models, library, ctx, seed=3)
    assert not evaluation.ok
    assert "exclusion.no_cooldown_big_area" in evaluation.repaired
    left = {e.code for e in evaluation.result.errors}
    assert "exclusion.no_cooldown_big_area" not in left
    assert left  # 不可修的照樣回報


def test_repairable_codes(library: ContentLibrary) -> None:
    assert REPAIRABLE_CODES == (
        "budget.over",
        "budget.weak",
        "skeleton.core_share",
        "skeleton.secondary_share",
    )
    # 補冷卻即可的互斥規則由 skill_exclusions.yaml 推導
    assert cooldown_repairs(library) == {
        "exclusion.no_cooldown_big_area": REPAIR_COOLDOWN,
        "exclusion.stun_single_long_cooldown": 4,
    }
    assert is_repairable("exclusion.no_cooldown_big_area", library)
    assert is_repairable("exclusion.stun_single_long_cooldown", library)
    assert is_repairable("skeleton.secondary_share", library)
    assert not is_repairable("budget.unavailable", library)
    assert not is_repairable("exclusion.no_push_with_pull", library)
    assert not is_repairable("variant.x.budget.weak", library)
    rules = ProposalError("rules", "", "budget.weak", "過弱")
    shape = ProposalError("proposal", "shape", "budget.weak", "x")
    core = ProposalError("rules", "", "skeleton.core", "x")
    assert repairable_errors([rules], library)
    assert not repairable_errors([], library)
    assert not repairable_errors([rules, shape], library)
    assert not repairable_errors([rules, core], library)
    assert repairable_codes([rules, shape, core, rules], library) == ("budget.weak",)
