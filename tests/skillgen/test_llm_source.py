"""Phase 4-L6：候選產生器的 LLM 來源、題目的核心原語／輪替選單／配額、驗證器的題目要求。"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace

import pytest

from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.llm import MockLLMClient
from trpg.llm.candidate_source import make_proposer
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.propose import propose_skill
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import CandidateRequest, CandidateRules, generate_candidates
from trpg.skillgen.proposal import (
    ProposalContext,
    _topic_errors,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    SubsetError,
    available_payload,
    build_subset_models,
    legal_core_primitives,
    select_subset,
)
from trpg.skillgen.proposal_topic import (
    LlmAttempt,
    TopicRequest,
    make_topic,
    pick_core_primitive,
    primitive_uses,
)
from trpg.skillgen.random_composer import compose_random_skill


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _request(seed: int = 1) -> CandidateRequest:
    return CandidateRequest(
        keyword_counts={"ignite": 1},
        weapon_class="focus",
        seed=seed,
        tier=1,
    )


def _composer_proposer(library: ContentLibrary, calls: list[int] | None = None):  # type: ignore[no-untyped-def]
    """假提議器：用組合器做一個帶題目關鍵字的技能（當作「合格的提議」）。"""

    def propose(request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
        if calls is not None:
            calls.append(seed)
        skill = compose_random_skill(
            seed,
            tier=request.tier,
            library=library,
            keyword=request.keywords[0],
            category="spell" if request.weapon_class == "focus" else None,
        )
        return LlmAttempt(skill, 1)

    return propose


def _failing(request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
    return LlmAttempt(None, 3, ("literal_error",), "用盡 3 次")


RULES = CandidateRules(llm_share_permille=1000, llm_theme_permille=100)


# -- 候選產生器 ---------------------------------------------------------------


def test_without_llm_is_identical(library: ContentLibrary) -> None:
    """沒傳提議器、或分享比例 0：候選逐字相同（亂數串流不變）。"""
    for seed in range(1, 8):
        base = generate_candidates(library, _request(seed), CandidateRules())
        assert generate_candidates(library, _request(seed), CandidateRules(), None) == base
        off = CandidateRules(llm_share_permille=0)
        assert generate_candidates(library, _request(seed), off, _failing) == base
        # 提議器失敗：退回後的候選與沒有 LLM 時相同（技能），只多了 llm 紀錄
        failed = generate_candidates(library, _request(seed), RULES, _failing)
        assert [c.skill for c in failed] == [c.skill for c in base]


def test_llm_source_is_used_and_fills_three(library: ContentLibrary) -> None:
    calls: list[int] = []
    found = generate_candidates(library, _request(3), RULES, _composer_proposer(library, calls))
    assert len(found) == 3
    llm = [c for c in found if c.source == "llm"]
    assert llm and len(calls) <= 3  # 每種候選最多請一次
    for c in llm:
        assert c.llm is not None and c.llm.ok and c.llm.attempts == 1
    # 同種子同提議器 → 同結果
    assert generate_candidates(library, _request(3), RULES, _composer_proposer(library)) == found


def test_failure_falls_back_and_keeps_three(library: ContentLibrary) -> None:
    found = generate_candidates(library, _request(5), RULES, _failing)
    assert len(found) == 3
    assert all(c.source != "llm" for c in found)
    assert any(c.llm is not None for c in found)  # 通用池的候選不請 LLM
    assert all(c.llm is None or not c.llm.ok for c in found)


def test_llm_is_not_asked_for_form_keyword(library: ContentLibrary) -> None:
    assert not library.keywords.by_id()["form"].composable
    assert make_topic(library, TopicRequest(1, ("form",), 1, {})) is None
    calls: list[int] = []
    request = CandidateRequest(keyword_counts={"form": 2}, weapon_class="melee", seed=2, tier=1)
    generate_candidates(library, request, RULES, _composer_proposer(library, calls))
    # 加深的題目是 form：不出題；其他兩種可能出題
    assert len(calls) <= 2


# -- 題目 ----------------------------------------------------------------------


def test_topic_is_deterministic_and_excludes_form(library: ContentLibrary) -> None:
    topic = TopicRequest(1, ("ignite",), 77, {})
    assert make_topic(library, topic) == make_topic(library, topic)
    for seed in range(60):
        made = make_topic(library, TopicRequest(1, ("ignite",), seed, {}, theme_permille=200))
        assert made is not None
        request = made[0]
        assert request.core_primitive not in ("enter_form", "leave_form")
        assert request.menu_seed is not None
        select_subset(library, request)  # 一定出得了子集


def test_every_legal_core_primitive_is_drawn(library: ContentLibrary) -> None:
    base = ProposalRequest(1, "epic")
    legal = legal_core_primitives(library, base)
    assert "enter_form" not in legal and legal
    drawn: Counter[str] = Counter()
    for seed in range(1000):
        picked = pick_core_primitive(library, legal, {}, Rng(seed))
        assert picked is not None
        drawn[picked] += 1
    assert set(drawn) == set(legal)
    mean = 1000 / len(legal)
    assert all(count < mean * 3 for count in drawn.values())  # 權重相同：分布不離譜


def test_quota_lowers_probability_of_seen_primitives(library: ContentLibrary) -> None:
    legal = legal_core_primitives(library, ProposalRequest(1, "epic"))
    seen = legal[0]
    fresh: Counter[str] = Counter()
    used: Counter[str] = Counter()
    for seed in range(2000):
        fresh[pick_core_primitive(library, legal, {}, Rng(seed)) or ""] += 1
        used[pick_core_primitive(library, legal, {seen: 1}, Rng(seed)) or ""] += 1
    assert used[seen] < fresh[seen]
    rules = library.composer.llm_topic
    assert rules.weight_of(seen, 1) < rules.weight_of(seen, 0) and rules.weight_of(seen, 9) >= 1


def test_core_primitive_restricts_the_subset(library: ContentLibrary) -> None:
    legal = legal_core_primitives(library, ProposalRequest(1, "rare"))
    core = "apply_status" if "apply_status" in legal else legal[0]
    subset = select_subset(library, ProposalRequest(1, "rare", core_primitive=core))
    assert core in subset.primitives
    with pytest.raises(SubsetError):
        select_subset(library, ProposalRequest(1, "common", core_primitive="enter_form"))


def test_menu_rotation_shrinks_and_shuffle_keeps_membership(library: ContentLibrary) -> None:
    full = select_subset(library, ProposalRequest(1, "epic"))
    rules = library.composer.llm_topic
    rotated = select_subset(library, ProposalRequest(1, "epic", menu_seed=5))
    assert len(rotated.conditions) <= rules.condition_count + 1  # 骨架必要的條件另計
    assert set(rotated.primitives) < set(full.primitives)
    other = select_subset(library, ProposalRequest(1, "epic", menu_seed=6))
    assert rotated != other
    ids = [e["id"] for e in available_payload(library, rotated)["primitives"]]
    assert sorted(ids) == sorted(rotated.primitives)
    assert select_subset(library, ProposalRequest(1, "epic", menu_seed=5)) == rotated


def test_shuffle_does_not_change_evaluation(library: ContentLibrary) -> None:
    skill = library.skills["skill_fire_arrow"]
    text = json.dumps(proposal_from_skill(skill, library))
    results = []
    for seed in (None, 1, 2):
        # 打亂只影響 available 的順序；子集成員相同時 schema 與驗證結果不變
        request = ProposalRequest(skill.tier, skill.rarity)
        subset = select_subset(library, request)
        shuffled = replace(subset, menu_seed=seed)
        models = build_subset_models(library, shuffled)
        results.append(
            evaluate_proposal(text, models, library, ProposalContext(skill.tier, skill.rarity)).ok
        )
    assert len(set(results)) == 1


def test_theme_goes_into_prompt(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, ProposalRequest(1, "common", theme="nature"))
    assert "自然" in prompt.messages[1]["content"]
    with pytest.raises(ValueError, match="未知的主題"):
        build_proposal_prompt(library, ProposalRequest(1, "common", theme="nope"))


def test_primitive_uses_counts_each_skill_once(library: ContentLibrary) -> None:
    skill = library.skills["skill_fire_arrow"]
    uses = primitive_uses([skill, skill])
    assert all(v == 2 for v in uses.values())


# -- 驗證器與提議迴圈 -----------------------------------------------------------


def _good_topic(library: ContentLibrary) -> tuple[SkillDef, ProposalRequest, str]:
    skill = library.skills["skill_fire_arrow"]
    owned = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    assert owned
    request = ProposalRequest(skill.tier, skill.rarity, keywords=owned[:1])
    return skill, request, json.dumps(proposal_from_skill(skill, library), ensure_ascii=False)


def test_good_mock_proposal_is_accepted_with_budget_numbers(library: ContentLibrary) -> None:
    skill, request, good = _good_topic(library)
    ctx = ProposalContext(skill.tier, skill.rarity)
    outcome = propose_skill(MockLLMClient([good]), library, request, ctx, seed=1)
    assert outcome.source == "llm" and outcome.attempts == 1
    assert (
        request.keywords[0]
        in derive_keywords(outcome.skill, library.keywords, exclusive_only=True).all()
    )


def test_missing_keyword_core_bad_json_and_form_fall_back(library: ContentLibrary) -> None:
    skill, request, good = _good_topic(library)
    ctx = ProposalContext(skill.tier, skill.rarity)
    other = next(
        k
        for k in library.keywords.ids()
        if k not in derive_keywords(skill, library.keywords, exclusive_only=True).all()
        and library.keywords.by_id()[k].composable
    )
    no_kw = ProposalRequest(skill.tier, skill.rarity, keywords=(other,))
    outcome = propose_skill(MockLLMClient([good] * 3), library, no_kw, ctx, seed=1)
    assert outcome.source != "llm" and outcome.codes[0] == ("keyword.required",)
    needs = "shield" if all(e.type != "shield" for e in skill.effects) else "damage"
    if all(e.type != needs for e in skill.effects):
        strict = ProposalContext(skill.tier, skill.rarity, core_primitive=needs)
        assert [e.code for e in _topic_errors(skill, strict, library)] == ["core.required"]
    outcome = propose_skill(MockLLMClient(["{not json"] * 3), library, request, ctx, seed=1)
    assert outcome.source != "llm" and outcome.attempts == 3


def test_make_proposer_reports_failure_without_using_fallback_skill(
    library: ContentLibrary,
) -> None:
    skill, request, good = _good_topic(library)
    ctx = ProposalContext(skill.tier, skill.rarity)
    propose = make_proposer(MockLLMClient([good]), library)
    ok = propose(request, ctx, 1)
    assert ok.skill is not None and ok.attempts == 1
    broken = make_proposer(MockLLMClient(["{}"] * 3), library)(request, ctx, 1)
    assert broken.skill is None and broken.attempts == 3 and broken.reason


def test_good_proposer_share_is_high(library: ContentLibrary) -> None:
    """合格的提議器 ＋ 分享比例 1000‰：候選中 LLM 來源占 70% 以上（通用池的新方向除外）。"""
    total = llm = 0
    for seed in range(1, 11):
        for c in generate_candidates(library, _request(seed), RULES, _composer_proposer(library)):
            total += 1
            llm += c.source == "llm"
    assert llm * 100 >= total * 70
