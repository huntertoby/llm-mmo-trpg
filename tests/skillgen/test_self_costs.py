"""Phase 3-50：代價換強度第一批（06 6.5，玩法決定 #54）的預算、驗證器、工坊、組合器與 LLM 提議。

共通規則 7 條各一組測試（對照表見 ``docs/phases/Phase3-50報告.md``）：

1. 整體上限 50%　2. 一招最多 1 個自身狀態　3. 自付狀態不觸發控制遞減（引擎，見
``tests/engine/test_self_costs.py``）　4. 限骨架由驗證器檢查　5. 卡片代價行　6. AI 使用條件（引擎）
7. LLM 只能挑允許的代價。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.skillgen.helpers import rules_of, skill
from trpg.content.skills import SkillDef
from trpg.llm import MockLLMClient
from trpg.llm.propose import propose_skill
from trpg.narrative.skills import cost_parts, cost_summary
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.option_models import Choice
from trpg.skillgen.options import draft_options
from trpg.skillgen.proposal import (
    ProposalContext,
    build_proposal_models,
    proposal_from_skill,
)
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.self_penalty import OVERDRAFT_CHOICE, penalty_choices
from trpg.skillgen.validate import validate_skill

LIB = library()
DEMO = (
    "skill_frost_armor_seal",
    "skill_all_in_chant",
    "skill_blood_rage_slash",
    "skill_overdraft_strike",
)

SPELL: dict[str, Any] = {
    "category": "spell",
    "weapon_req": "focus",
    "scaling_attr": "int",
    "skeleton": "area",
    "tier": 2,
    "ap_cost": 2,
    "shape": {"type": "square3", "range": 4},
    "effects": [{"type": "damage", "dice": "2d10", "element": "fire"}],
}


def _spell(cost: dict[str, Any], **overrides: Any) -> SkillDef:
    return skill(**{**SPELL, "cost": cost, **overrides})


def _rules(s: SkillDef) -> set[str]:
    return rules_of(s)


# ---------------------------------------------------------------------------
# 規則 1：整體上限 50%（各項先套上限，加總後再截斷）
# ---------------------------------------------------------------------------


def test_the_total_allowance_is_capped_at_fifty_percent() -> None:
    heavy = _spell(
        {"mana": 30, "cooldown": 6, "self_status": {"status": "stun", "duration": 2}},
        rarity="rare",
    )
    report = skill_budget(heavy, LIB)
    assert report.allowance_raw_permille > 500  # 320（暈眩）＋ 300（冷卻）＋ 150（法力）
    assert report.allowance_permille == 500 and report.allowance_capped
    assert LIB.budget.allowance.total_cap == 500


def test_the_stun_allowance_is_320_and_limited_by_its_own_40_percent_cap() -> None:
    rule = LIB.budget.allowance.self_status
    assert rule.cap_of("stun") == 400 and rule.cap_of("slow") == 250  # 專屬上限 40%，其他 25%
    stun = _spell({"mana": 10, "self_status": {"status": "stun", "duration": 2}}, rarity="rare")
    parts = dict(skill_budget(stun, LIB).allowance_parts)
    assert parts["自身暈眩 2 回合"] == 320  # 8 點 × 1 個有效回合 × 40‰


@pytest.mark.parametrize(
    ("status", "duration", "expected"),
    [("silenced", 2, 200), ("silenced", 3, 250), ("bleed", 2, 120), ("bleed", 3, 240)],
)
def test_silence_and_bleed_allowances_follow_the_common_formula(
    status: str, duration: int, expected: int
) -> None:
    s = _spell({"mana": 10, "self_status": {"status": status, "duration": duration}}, rarity="rare")
    assert (
        dict(skill_budget(s, LIB).allowance_parts)[f"自身{_name(status)} {duration} 回合"]
        == expected
    )


def _name(status: str) -> str:
    return LIB.ruleset.statuses.by_id()[status].name_zh


def test_overdraft_is_a_flat_twenty_percent() -> None:
    s = _spell({"mana": 10, "overdraft": 1})
    report = skill_budget(s, LIB)
    assert ("透支（下回合少 1 AP）", 200) in report.allowance_parts
    assert LIB.budget.allowance.overdraft_permille == 200


# ---------------------------------------------------------------------------
# 規則 2：一招最多 1 個自身狀態
# ---------------------------------------------------------------------------


def test_a_skill_can_have_only_one_self_status() -> None:
    from trpg.content.skills import SkillCost  # noqa: PLC0415

    assert SkillCost.model_fields["self_status"].annotation is not list  # 單一欄位，不是列表
    with pytest.raises(ValueError, match=r"self_status"):
        SkillCost.model_validate(
            {"self_status": [{"status": "stun", "duration": 2}, {"status": "slow", "duration": 2}]}
        )


def test_self_status_and_overdraft_cannot_be_combined() -> None:
    both = _spell(
        {
            "mana": 10,
            "self_status": {"status": "bleed", "duration": 2},
            "overdraft": 1,
        }
    )
    assert "cap.self_penalty_single" in _rules(both)
    only_status = _spell({"mana": 10, "self_status": {"status": "bleed", "duration": 2}})
    only_overdraft = _spell({"mana": 10, "overdraft": 1})
    assert "cap.self_penalty_single" not in _rules(only_status) | _rules(only_overdraft)


def test_only_active_skills_can_pay_self_costs() -> None:
    for cost in ({"overdraft": 1}, {"self_status": {"status": "slow", "duration": 2}}):
        with pytest.raises(ValueError, match="只有主動技能"):
            skill(
                kind="passive",
                skeleton="passive",
                ap_cost=None,
                trigger={"event": "on_cast_tag", "tag": "fire", "target": "self"},
                cost={"mana": 2, **cost},
            )


# ---------------------------------------------------------------------------
# 規則 4：會白拿折扣的代價限骨架／類別（驗證器檢查）
# ---------------------------------------------------------------------------


def test_self_silence_is_only_allowed_on_spells() -> None:
    cost = {"self_status": {"status": "silenced", "duration": 2}}
    assert "cap.self_status_category" not in _rules(_spell({"mana": 10, **cost}, rarity="rare"))
    weapon = skill(cost={"stamina": 8, "cooldown": 2, **cost}, rarity="rare")
    assert "cap.self_status_category" in _rules(weapon)


def test_stun_duration_is_fixed_at_two() -> None:
    assert "cap.self_status_duration" in _rules(
        _spell({"mana": 10, "self_status": {"status": "stun", "duration": 3}}, rarity="rare")
    )
    assert "cap.self_status_duration" not in _rules(
        _spell({"mana": 10, "self_status": {"status": "stun", "duration": 2}}, rarity="rare")
    )


def test_unlisted_self_statuses_are_still_rejected() -> None:
    assert "cap.self_status" in _rules(
        _spell({"mana": 10, "self_status": {"status": "frozen", "duration": 2}}, rarity="rare")
    )


def test_every_demo_skill_passes_the_validator_inside_the_budget_window() -> None:
    for skill_id in DEMO:
        demo = LIB.skills[skill_id]
        assert validate_skill(demo, LIB) == [], skill_id
        report = skill_budget(demo, LIB)
        ratio = report.ratio
        assert LIB.budget.min_ratio_permille / 1000 <= ratio <= 1, (skill_id, float(ratio))


# ---------------------------------------------------------------------------
# 規則 5：卡片代價行；工坊即時顯示折扣
# ---------------------------------------------------------------------------


def test_the_card_shows_the_cost_line_with_the_discount() -> None:
    seal = LIB.skills["skill_frost_armor_seal"]
    assert "代價：施放後自己暈眩 1 回合（換 32% 預算）" in cost_parts(LIB, seal)
    chant = LIB.skills["skill_all_in_chant"]
    assert "代價：施放後自己沉默 1 回合（換 20% 預算）" in cost_parts(LIB, chant)
    slash = LIB.skills["skill_blood_rage_slash"]
    assert "代價：施放後自己流血 1 回合（換 12% 預算）" in cost_parts(LIB, slash)
    overdraft = LIB.skills["skill_overdraft_strike"]
    assert "代價：施放後自己下一個回合少 1 AP（換 20% 預算）" in cost_parts(LIB, overdraft)
    assert "換 32% 預算" in cost_summary(LIB, seal)


def _cost_fields(draft: dict[str, Any]) -> dict[str, Any]:
    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "cost")
    return {f.field: f for f in step.fields}


def _draft_of(skill_id: str, **cost: Any) -> dict[str, Any]:
    data = LIB.skills[skill_id].model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    data["cost"] = cost
    data["kind"] = "active"
    for key in ("id", "provenance", "narrative"):
        data.pop(key, None)
    return data


def test_the_workshop_cost_step_offers_the_new_penalties() -> None:
    fields = _cost_fields(_draft_of("skill_frost_armor_seal", mana=6, cooldown=4))
    status = next(f for f in fields["cost.self_status"].fields if f.field == "status")
    assert {c.value for c in status.choices} >= {"stun", "silenced", "bleed"}
    assert fields["cost.overdraft"].max == 1
    assert "20%" in fields["cost.overdraft"].description_zh


def test_the_workshop_locks_the_stun_duration_and_disables_silence_on_weapon_skills() -> None:
    fields = _cost_fields(_draft_of("skill_blood_rage_slash", stamina=8, cooldown=2))
    status = next(f for f in fields["cost.self_status"].fields if f.field == "status")
    by_value: dict[str, Choice] = {str(c.value): c for c in status.choices}
    stun_duration = next(p for p in by_value["stun"].params if p.field == "duration")
    assert (stun_duration.min, stun_duration.max) == (2, 2)  # 暈眩固定 2
    bleed_duration = next(p for p in by_value["bleed"].params if p.field == "duration")
    assert (bleed_duration.min, bleed_duration.max) == (2, 3)
    reason = by_value["silenced"].info.get("unavailable_zh")
    assert isinstance(reason, str) and "法術技" in reason  # 武器技：沉默事前停用並附原因
    assert "unavailable_zh" not in by_value["stun"].info


def test_the_workshop_does_not_disable_silence_on_spells() -> None:
    fields = _cost_fields(_draft_of("skill_all_in_chant", mana=10, cooldown=4))
    status = next(f for f in fields["cost.self_status"].fields if f.field == "status")
    silenced = next(c for c in status.choices if c.value == "silenced")
    assert "unavailable_zh" not in silenced.info


def test_the_workshop_hides_the_other_penalty_once_one_is_chosen() -> None:
    chosen_status = _cost_fields(
        _draft_of(
            "skill_blood_rage_slash", stamina=8, self_status={"status": "bleed", "duration": 2}
        )
    )
    assert "cost.self_status" in chosen_status and "cost.overdraft" not in chosen_status
    chosen_overdraft = _cost_fields(_draft_of("skill_overdraft_strike", stamina=6, overdraft=1))
    assert "cost.overdraft" in chosen_overdraft and "cost.self_status" not in chosen_overdraft


def test_workshop_options_and_the_validator_agree_on_silence() -> None:
    """選項與驗證器同源（3-48h）：選項說可以的，驗證器不報；選項停用的，驗證器真的會報。"""
    for skill_id, allowed in (("skill_blood_rage_slash", False), ("skill_all_in_chant", True)):
        fields = _cost_fields(_draft_of(skill_id, stamina=8, mana=10, cooldown=3))
        status = next(f for f in fields["cost.self_status"].fields if f.field == "status")
        silenced = next(c for c in status.choices if c.value == "silenced")
        offered = "unavailable_zh" not in silenced.info
        base = LIB.skills[skill_id].model_dump(mode="json", exclude_none=True)
        base["cost"] = {
            **base["cost"],
            "self_status": {"status": "silenced", "duration": 2},
        }
        violated = "cap.self_status_category" in {
            v.rule for v in validate_skill(SkillDef.model_validate(base), LIB)
        }
        assert offered == allowed == (not violated), skill_id


# ---------------------------------------------------------------------------
# 規則 7：LLM 只能從允許的代價中挑一個
# ---------------------------------------------------------------------------


def test_the_proposal_schema_lists_exactly_the_allowed_penalties() -> None:
    models = build_proposal_models(LIB, rarity="rare")
    schema = models.json_schema()
    text = json.dumps(schema, ensure_ascii=False)
    assert "cost_penalty" in text
    expected = set(penalty_choices(LIB, "rare"))
    assert expected == {
        "vulnerable",
        "weaken",
        "slow",
        "root",
        "stun",
        "silenced",
        "bleed",
        OVERDRAFT_CHOICE,
    }
    enum_values: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            prop = node.get("properties", {}).get("cost_penalty")
            if isinstance(prop, dict):
                for option in prop.get("anyOf", [prop]):
                    enum_values.update(option.get("enum", []))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(schema)
    assert enum_values == expected


def test_a_common_proposal_cannot_pick_rare_only_penalties() -> None:
    common = set(penalty_choices(LIB, "common"))
    assert {"stun", "silenced"}.isdisjoint(common)
    assert {"slow", "weaken", "vulnerable", "bleed", OVERDRAFT_CHOICE} <= common


def _proposal(skill_id: str, penalty: object) -> str:
    data = proposal_from_skill(LIB.skills[skill_id], LIB)
    data.pop("cost_penalty", None)
    if penalty is not None:
        data["cost_penalty"] = penalty
    return json.dumps(data, ensure_ascii=False)


def test_a_proposal_with_an_allowed_penalty_becomes_a_valid_skill() -> None:
    request = ProposalRequest(2, "rare", skeleton="area")
    text = _proposal("skill_all_in_chant", "silenced")
    outcome = propose_skill(MockLLMClient([text]), LIB, request, ProposalContext(2, "rare"), seed=3)
    assert outcome.source == "llm", outcome.reason
    assert outcome.skill.cost.self_status is not None
    assert outcome.skill.cost.self_status.status == "silenced"
    assert validate_skill(outcome.skill, LIB) == []


def test_an_overdraft_proposal_becomes_cost_overdraft() -> None:
    request = ProposalRequest(2, "common", skeleton="strike")
    outcome = propose_skill(
        MockLLMClient([_proposal("skill_overdraft_strike", OVERDRAFT_CHOICE)]),
        LIB,
        request,
        ProposalContext(2, "common"),
        seed=3,
    )
    assert outcome.source == "llm", outcome.reason
    assert outcome.skill.cost.overdraft == 1 and outcome.skill.cost.self_status is None


@pytest.mark.parametrize("bad", ["frozen", "stun_forever", ["stun", "slow"], 3])
def test_a_proposal_with_an_unknown_or_multiple_penalty_is_rejected(bad: object) -> None:
    request = ProposalRequest(2, "rare", skeleton="area")
    text = _proposal("skill_all_in_chant", bad)
    outcome = propose_skill(
        MockLLMClient([text, text, text]), LIB, request, ProposalContext(2, "rare"), seed=3
    )
    assert outcome.source != "llm"  # 三次都不合格 → 退回組合器
    assert outcome.records and all(r.codes for r in outcome.records)


def test_a_rare_only_penalty_in_a_common_proposal_is_rejected() -> None:
    request = ProposalRequest(2, "common", skeleton="strike")
    text = _proposal("skill_overdraft_strike", "stun")
    outcome = propose_skill(
        MockLLMClient([text, text, text]), LIB, request, ProposalContext(2, "common"), seed=3
    )
    assert outcome.source != "llm"


def test_the_engine_validator_still_checks_a_legal_looking_penalty() -> None:
    """LLM 挑的是允許清單裡的值，但沉默放在武器技仍由驗證器擋下（規則 4）。"""
    request = ProposalRequest(2, "rare", skeleton="strike")
    text = _proposal("skill_blood_rage_slash", "silenced")
    outcome = propose_skill(
        MockLLMClient([text, text, text]), LIB, request, ProposalContext(2, "rare"), seed=3
    )
    assert outcome.source != "llm"
    assert any("cap.self_status_category" in r.codes for r in outcome.records)


# ---------------------------------------------------------------------------
# 隨機組合器
# ---------------------------------------------------------------------------


def test_the_composer_only_produces_valid_penalties() -> None:
    seen: set[str] = set()
    for seed in range(400):
        s = compose_random_skill(seed, tier=2, library=LIB)
        assert validate_skill(s, LIB) == [], (seed, s.cost)
        if s.cost.self_status is not None:
            status = s.cost.self_status
            seen.add(status.status)
            if status.status == "stun":
                assert status.duration == 2 and s.rarity != "common"
            if status.status == "silenced":
                assert s.category == "spell"
        assert s.cost.overdraft is None or s.cost.self_status is None
        if s.cost.overdraft is not None:
            seen.add(OVERDRAFT_CHOICE)
    assert OVERDRAFT_CHOICE in seen and seen & {"stun", "silenced", "bleed"}
