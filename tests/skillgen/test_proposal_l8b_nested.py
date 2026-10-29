"""Phase 4-L8b：只能巢狀的效果（``refund_ap``、``refund_cooldown``、``damage_multiplier``、
``self_damage_of_hit``）開放給 LLM 提議。不需要網路與模型。"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import GAMBLE_BRANCH_TYPES, NESTED_PARENTS, ON_KILL_TYPES
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_coverage import round_trip_inventory
from trpg.skillgen.proposal_numbers import fixed_filler, minimal_filler, split_numbers


@cache
def _lib() -> ContentLibrary:
    return library()


@cache
def _models() -> ProposalModels:
    return build_proposal_models(_lib())


def _defs() -> dict[str, Any]:
    return _lib().ruleset.primitives.nested_only_by_id()


def test_parents_match_engine_constants() -> None:
    """YAML 的父結構與引擎常數（SkillDef 驗證器用的清單）一致。"""
    expected = {
        "on_kill": {t for t in ON_KILL_TYPES if t not in _lib().ruleset.primitives.by_id()},
        "win": {t for t in GAMBLE_BRANCH_TYPES if t not in _lib().ruleset.primitives.by_id()},
    }
    expected["lose"] = expected["win"]
    for parent in NESTED_PARENTS:
        declared = {d.id for d in _defs().values() if parent in d.parents}
        assert declared == expected[parent], parent


def test_nested_only_are_not_primitives() -> None:
    primitives = _lib().ruleset.primitives.by_id()
    assert set(_defs()) == {
        "refund_ap",
        "refund_cooldown",
        "damage_multiplier",
        "self_damage_of_hit",
    }
    assert not set(_defs()) & set(primitives)
    for d in _defs().values():
        assert d.llm_hint.strip(), d.id


@pytest.mark.parametrize("skill_id", ["skill_ash_harvest", "skill_blood_sacrifice"])
def test_hand_written_round_trip(skill_id: str) -> None:
    passed = {r.skill_id for r in round_trip_inventory(_lib()).rows if r.ok}
    assert skill_id in passed


def test_numbers_are_split_and_filled() -> None:
    skill = _lib().skills["skill_ash_harvest"]
    data = skill.model_dump(mode="json", exclude_defaults=True)
    structure, removed = split_numbers(data, _lib())
    kill = structure["effects"][0]["on_kill"]
    assert kill == [{"type": "refund_ap"}, {"type": "refund_cooldown"}]
    assert any(path[-1] == "amount" for path, _ in removed)
    filled = minimal_filler(_lib())(structure)
    assert filled["effects"][0]["on_kill"][0]["amount"] == 1


def _round_trip(skill_id: str) -> tuple[dict[str, Any], Any]:
    skill = _lib().skills[skill_id]
    _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), _lib())
    return proposal_from_skill(skill, _lib()), fixed_filler(removed)


def test_schema_places_effects_only_under_their_parents() -> None:
    ctx = ProposalContext(tier=1, rarity="rare", rank=1)
    proposal, fill = _round_trip("skill_ash_harvest")
    assert evaluate_proposal(proposal, _models(), _lib(), ctx, fill=fill).ok
    # damage_multiplier 只能放在賭注的分支，不能放在擊殺時效果
    proposal["effects"][0]["on_kill"] = [{"type": "damage_multiplier"}]
    result = evaluate_proposal(proposal, _models(), _lib(), ctx, fill=fill)
    assert not result.ok
    assert {e.stage for e in result.errors} == {"proposal"}
    # refund_ap 只能放在擊殺時效果，不能放在賭注的分支
    proposal, fill = _round_trip("skill_blood_sacrifice")
    assert evaluate_proposal(proposal, _models(), _lib(), ctx, fill=fill).ok
    proposal["effects"][-1]["win"] = [{"type": "refund_ap"}]
    assert not evaluate_proposal(proposal, _models(), _lib(), ctx, fill=fill).ok


def test_bare_top_level_nested_only_is_rejected() -> None:
    proposal = proposal_from_skill(_lib().skills["skill_ash_harvest"], _lib())
    proposal["effects"].append({"type": "refund_ap"})
    ctx = ProposalContext(tier=1, rarity="rare", rank=1)
    assert not evaluate_proposal(proposal, _models(), _lib(), ctx).ok


def test_budget_filler_fills_nested_only_and_cooldown() -> None:
    proposal = proposal_from_skill(_lib().skills["skill_ash_harvest"], _lib())
    ctx = ProposalContext(tier=1, rarity="rare", rank=1)
    done = evaluate_with_repair(proposal, _models(), _lib(), ctx, seed=0)
    # 補值器補了 amount 與冷卻（refund_cooldown 需要冷卻），不會因缺欄位而失敗
    codes = {e.code for e in done.result.errors}
    assert not {c for c in codes if c in ("missing", "value_error")}, done.result.errors
    if done.result.skill is not None:
        assert done.result.skill.cost.cooldown
