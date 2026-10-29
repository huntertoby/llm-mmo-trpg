"""Phase 4-L8：開放更多結構給 LLM 提議（代價類欄位、反應、複合技能、只能巢狀的效果）。

每個新開放的結構：schema 有這個欄位、手寫技能往返成功、預算器補數值、Mock 提議走完整流程。全部
用 ``MockLLMClient``，不需要網路與模型。
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.llm import MockLLMClient
from trpg.llm.propose import propose_skill
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_budget import budget_filler
from trpg.skillgen.proposal_costs import hp_cost_permille
from trpg.skillgen.proposal_coverage import round_trip_inventory
from trpg.skillgen.proposal_numbers import minimal_filler
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.validate import validate_skill


@cache
def _lib() -> ContentLibrary:
    return library()


@cache
def _models() -> ProposalModels:
    return build_proposal_models(_lib())


@cache
def _passed() -> frozenset[str]:
    return frozenset(r.skill_id for r in round_trip_inventory(_lib()).rows if r.ok)


def _proposal(skill_id: str, **changes: Any) -> dict[str, Any]:
    data = proposal_from_skill(_lib().skills[skill_id], _lib())
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


def _schema_text(models: ProposalModels) -> str:
    return json.dumps(models.json_schema(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# 代價類欄位
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("skill_id", "field"),
    [
        ("skill_mirror_cast", "source"),
        ("skill_undying_oath", "source"),
        ("skill_resurrection", "uses_per_battle"),
        ("skill_thunder_finisher", "stacks"),
        ("skill_all_in", "on_miss"),
    ],
)
def test_cost_skills_round_trip(skill_id: str, field: str) -> None:
    original = _lib().skills[skill_id]
    assert getattr(original.cost, field)
    assert skill_id in _passed()
    proposal = proposal_from_skill(original, _lib())
    assert "cost" not in proposal  # 代價只用結構欄位表達，數值由引擎補


def test_cost_fields_are_structural_choices() -> None:
    proposal = proposal_from_skill(_lib().skills["skill_resurrection"], _lib())
    assert proposal["cost_once_per_battle"] is True
    backlash = proposal_from_skill(_lib().skills["skill_all_in"], _lib())
    assert backlash["cost_on_miss"] == [{"type": "apply_status", "status": "prone"}]
    text = _schema_text(_models())
    for field in ("cost_once_per_battle", "cost_hp", "cost_on_miss", "BacklashEffect"):
        assert field in text


def test_on_miss_is_hidden_below_its_rarity() -> None:
    assert "cost_on_miss" not in _schema_text(build_proposal_models(_lib(), rarity="common"))
    assert "cost_on_miss" in _schema_text(build_proposal_models(_lib(), rarity="rare"))


def test_backlash_effects_cannot_target_others() -> None:
    data = _proposal(
        "skill_all_in",
        cost_on_miss=[{"type": "apply_status", "status": "prone", "affects": "enemies"}],
    )
    result = evaluate_proposal(data, _models(), _lib(), ProposalContext(1, "rare"))
    assert any(
        e.code == "extra_forbidden" and e.path.startswith("cost_on_miss[0]") for e in result.errors
    ), result.errors


def test_hp_cost_takes_the_full_allowance() -> None:
    allowance = _lib().budget.allowance
    assert hp_cost_permille(_lib()) * allowance.hp_per_permille == allowance.hp_cap
    data = _proposal("skill_cleave", cost_hp=True)
    result = evaluate_proposal(
        data, _models(), _lib(), ProposalContext(1, "rare"), fill=budget_filler(_lib(), seed=1)
    )
    assert result.skill is not None, result.errors
    assert result.skill.cost.hp_percent == hp_cost_permille(_lib())


def test_legendary_proposals_get_source_from_the_filler() -> None:
    """傳說技能必須花源力：提議沒有這個欄位，補值器補最小值 1（往返時由固定數值放回原值）。"""
    data = {"kind": "active", "rarity": "legendary", "category": "spell", "effects": []}
    assert minimal_filler(_lib())(data)["cost"]["source"] == 1
    assert "cost" not in minimal_filler(_lib())({**data, "rarity": "epic", "kind": "passive"})
    oath = _lib().skills["skill_undying_oath"]
    assert oath.cost.source == 2 and "skill_undying_oath" in _passed()


def test_mock_proposal_with_once_per_battle() -> None:
    text = json.dumps(_proposal("skill_resurrection"), ensure_ascii=False)
    request = ProposalRequest(1, "rare", skeleton="aura")
    outcome = propose_skill(
        MockLLMClient([text]), _lib(), request, ProposalContext(1, "rare"), seed=3
    )
    assert outcome.source == "llm", outcome.reason
    assert outcome.skill.cost.uses_per_battle == 1
    assert validate_skill(outcome.skill, _lib()) == []


def test_mock_proposal_with_backlash() -> None:
    text = json.dumps(_proposal("skill_all_in"), ensure_ascii=False)
    request = ProposalRequest(1, "rare", skeleton="strike")
    outcome = propose_skill(
        MockLLMClient([text]), _lib(), request, ProposalContext(1, "rare"), seed=3
    )
    assert outcome.source == "llm", outcome.reason
    assert [e.type for e in outcome.skill.cost.on_miss] == ["apply_status"]
    assert validate_skill(outcome.skill, _lib()) == []
