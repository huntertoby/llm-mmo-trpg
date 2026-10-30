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
from trpg.content.skills import FOLLOWUP_WHEN_VALUES
from trpg.llm import MockLLMClient
from trpg.llm.propose import propose_skill
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
    reaction_events,
)
from trpg.skillgen.proposal_budget import budget_filler, is_repairable, segment_code
from trpg.skillgen.proposal_costs import hp_cost_permille
from trpg.skillgen.proposal_coverage import round_trip_inventory
from trpg.skillgen.proposal_followup import FOLLOWUP_WHEN_HINTS
from trpg.skillgen.proposal_numbers import minimal_filler
from trpg.skillgen.proposal_subset import ProposalRequest, available_payload, select_subset
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


# ---------------------------------------------------------------------------
# 反應
# ---------------------------------------------------------------------------

REACTIONS = (
    "skill_ambush_stab",
    "skill_counterspell",
    "skill_covering_fire",
    "skill_grief_rage",
    "skill_parting_slash",
    "skill_reflex_ward",
    "skill_riposte",
    "skill_stand_firm",
)


@pytest.mark.parametrize("skill_id", REACTIONS)
def test_reaction_skills_round_trip(skill_id: str) -> None:
    assert _lib().skills[skill_id].reaction is not None
    assert skill_id in _passed()


def test_reaction_field_only_with_reaction_skeleton() -> None:
    assert '"Reaction"' not in _schema_text(build_proposal_models(_lib(), skeletons=["strike"]))
    text = _schema_text(build_proposal_models(_lib(), skeletons=["reaction"]))
    assert "Reaction" in text
    for event_id, hint in reaction_events(_lib()):
        assert event_id in text and hint


def test_reaction_kind_without_event_is_locatable() -> None:
    data = _proposal("skill_riposte", reaction=None)
    result = evaluate_proposal(data, _models(), _lib(), ProposalContext(1, "rare"))
    assert result.skill is None
    # 4-L10a：反應技分支的 reaction 必填，缺了在提議格式階段就指到 reaction
    assert [(e.stage, e.path, e.code) for e in result.errors] == [
        ("proposal", "reaction", "missing")
    ], result.errors


def test_mock_reaction_proposal_gets_budgeted_numbers() -> None:
    text = json.dumps(_proposal("skill_riposte"), ensure_ascii=False)
    request = ProposalRequest(1, "rare", skeleton="reaction")
    outcome = propose_skill(
        MockLLMClient([text]), _lib(), request, ProposalContext(1, "rare"), seed=4
    )
    assert outcome.source == "llm", outcome.reason
    assert outcome.skill.kind == "reaction"
    assert outcome.skill.reaction is not None
    assert outcome.skill.reaction.event == "hit_by_melee"
    assert outcome.skill.effects[0].multiplier_permille is not None  # 數值由預算器補
    assert validate_skill(outcome.skill, _lib()) == []


def test_reaction_topic_subset_lists_events() -> None:
    subset = select_subset(_lib(), ProposalRequest(1, "rare", skeleton="reaction"))
    assert subset.kind == "reaction"
    payload = available_payload(_lib(), subset)
    assert [e["id"] for e in payload["reactions"]] == [e for e, _ in reaction_events(_lib())]


# ---------------------------------------------------------------------------
# 複合技能
# ---------------------------------------------------------------------------

FOLLOWUPS = (
    "skill_armor_break_combo",
    "skill_charged_cleave",
    "skill_death_spiral",
    "skill_gravity_burst",
    "skill_leap_slam",
    "skill_parry_riposte",
    "skill_retreating_slash",
    "skill_shadow_whirl",
)


@pytest.mark.parametrize("skill_id", FOLLOWUPS)
def test_followup_skills_round_trip(skill_id: str) -> None:
    assert _lib().skills[skill_id].followup is not None
    assert skill_id in _passed()


def test_every_followup_when_is_used_by_a_round_trip() -> None:
    whens = set()
    for skill_id in FOLLOWUPS:
        follow = _lib().skills[skill_id].followup
        assert follow is not None
        whens.add(follow.when)
    assert whens == set(FOLLOWUP_WHEN_VALUES)
    assert set(FOLLOWUP_WHEN_HINTS) == set(FOLLOWUP_WHEN_VALUES)


def test_followup_effects_exclude_forbidden_primitives() -> None:
    follow = {
        "skeleton": "area",
        "shape": {"type": "cone", "size": 2},
        "effects": [{"type": "summon", "summon": "summon_wolf"}],
    }
    data = _proposal("skill_shadow_whirl", followup=follow)
    result = evaluate_proposal(data, _models(), _lib(), ProposalContext(1, "rare"))
    assert result.skill is None
    assert any(
        e.path.startswith("followup.effects[0]") and e.stage == "proposal" for e in result.errors
    ), result.errors


def test_followup_is_closed_when_disabled() -> None:
    assert '"Followup"' not in _schema_text(build_proposal_models(_lib(), followup=False))
    assert "Followup" in _schema_text(_models())


def test_budget_filler_tunes_the_second_segment() -> None:
    """第一段只有傳送（沒有旋鈕）：預算器調第二段的傷害倍率，把強度調進區間。"""
    data = _proposal("skill_shadow_whirl")
    ctx = ProposalContext(2, "rare")  # 接續段、傳送要角色 2 階（3W-9）
    result = evaluate_proposal(data, _models(), _lib(), ctx, fill=budget_filler(_lib(), seed=5))
    assert result.skill is not None, result.errors
    assert result.skill.followup is not None
    damage = result.skill.followup.effects[0]
    assert damage.multiplier_permille is not None
    assert damage.multiplier_permille > 500
    assert validate_skill(result.skill, _lib()) == []


@pytest.mark.parametrize(
    "skill_id", ["skill_shadow_whirl", "skill_retreating_slash", "skill_charged_cleave"]
)
def test_mock_followup_proposal(skill_id: str) -> None:
    original = _lib().skills[skill_id]
    assert original.followup is not None
    text = json.dumps(_proposal(skill_id), ensure_ascii=False)
    request = ProposalRequest(2, "rare", skeleton=original.skeleton)  # 接續段要 2 階（3W-9）
    outcome = propose_skill(
        MockLLMClient([text]), _lib(), request, ProposalContext(2, "rare"), seed=6
    )
    assert outcome.source == "llm", outcome.reason
    assert outcome.skill.followup is not None
    assert outcome.skill.followup.when == original.followup.when
    assert validate_skill(outcome.skill, _lib()) == []


def test_second_segment_codes_are_repairable() -> None:
    assert segment_code("followup.skeleton.core_share") == "skeleton.core_share"
    assert is_repairable("followup.budget.weak", _lib())
    assert not is_repairable("followup.reference", _lib())


def test_followup_scope_in_subsets() -> None:
    common = select_subset(_lib(), ProposalRequest(1, "common", skeleton="strike"))
    assert common.followup_skeletons == ()
    assert "followup" not in available_payload(_lib(), common)
    first = select_subset(_lib(), ProposalRequest(1, "rare", skeleton="area"))
    assert first.followup_skeletons == ()  # 接續段要角色 2 階（3W-9，6.34.9）
    rare = select_subset(_lib(), ProposalRequest(2, "rare", skeleton="area"))
    assert {"area", "strike", "displace"} <= set(rare.followup_skeletons)
    assert "leap" in rare.followup_moves
    assert "leap" not in rare.primitives
    payload = available_payload(_lib(), rare)
    assert [m["id"] for m in payload["followup"]["moves"]] == [
        m for m in rare.followup_moves if m not in rare.primitives
    ]
    assert [w["id"] for w in payload["followup"]["when"]] == list(FOLLOWUP_WHEN_VALUES)
    assert {c["id"] for c in payload["costs"]} >= {"cost_penalty", "cost_hp", "cost_on_miss"}
    reaction = select_subset(_lib(), ProposalRequest(1, "rare", skeleton="reaction"))
    assert reaction.followup_skeletons == ()
    assert "costs" not in available_payload(_lib(), reaction)
