"""6S-2：升級候選退回率——結構補強、過弱補強的占比重試、出題的關鍵字可達性、prompt 說明。

表格中的提議是依 27B 評估（commit 6af12836，升級候選 50 題）``skills_errors.csv`` 的真實失敗重建的：
``topup=False`` 時得到 **一字不差** 的原始錯誤訊息（同樣的 total ÷ 可用預算），證明是同一種提議；
``topup=True``（正式流程）時合格，而且預算比例仍在驗證器的窗內。驗證規則與預算數值都沒有改。
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest

from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skills.constants import SkillRarity
from trpg.llm import MockLLMClient
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.propose import propose_skill
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
)
from trpg.skillgen.proposal_budget import WEAK_ADVICE, evaluate_with_repair
from trpg.skillgen.proposal_layouts import layout_of_effects
from trpg.skillgen.proposal_subset import ProposalRequest, available_payload, select_subset
from trpg.skillgen.proposal_topic import TopicRequest, make_topic
from trpg.skillgen.proposal_topup import (
    TOPUP_MAX,
    keyword_way_texts,
    keywords_reachable,
    topup_candidates,
)
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.validate import validate_skill

SEED = 7


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


@pytest.fixture(scope="module")
def models(library: ContentLibrary) -> ProposalModels:
    return build_proposal_models(library)


def _proposal(
    library: ContentLibrary, skeleton: str, shape: dict[str, Any], effects: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "layout": layout_of_effects(library, [e["type"] for e in effects]),
        "kind": "active",
        "skeleton": skeleton,
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "shape": shape,
        "effects": effects,
    }


def _single(r: int) -> dict[str, Any]:
    return {"type": "single", "range": r}


def _ctx(tier: int, rarity: SkillRarity, keywords: tuple[str, ...] = ()) -> ProposalContext:
    return ProposalContext(tier, rarity, keywords=keywords)


type WeakCase = tuple[int, SkillRarity, str, dict[str, Any], list[dict[str, Any]], str]
WEAK_CASES: dict[str, WeakCase] = {
    # 27B 題號：(角色階級, 稀有度, 骨架, 形狀, 效果, skills_errors.csv 的原始訊息)
    "9_pull": (
        1,
        "rare",
        "displace",
        _single(2),
        [{"type": "pull", "affects": "enemies"}],
        "過弱：total 3.60 ÷ 可用預算 14.07 ＝ 25.6%（下限 70.0%，階級 1）",
    ),
    "45_push": (
        1,
        "rare",
        "displace",
        _single(3),
        [{"type": "push", "affects": "enemies"}],
        "過弱：total 3.80 ÷ 可用預算 14.07 ＝ 27.0%（下限 70.0%，階級 1）",
    ),
    "8_topple": (
        3,
        "epic",
        "displace",
        _single(3),
        [{"type": "topple", "affects": "enemies"}],
        "過弱：total 5.70 ÷ 可用預算 23.11 ＝ 24.7%（下限 70.0%，階級 3）",
    ),
    "26_cleanse": (
        3,
        "common",
        "aura",
        _single(4),
        [{"type": "cleanse", "affects": "allies"}],
        "過弱：total 3.00 ÷ 可用預算 23.11 ＝ 13.0%（下限 70.0%，階級 3）",
    ),
    "48_cleanse": (
        1,
        "rare",
        "aura",
        _single(3),
        [{"type": "cleanse", "affects": "allies"}],
        "過弱：total 2.85 ÷ 可用預算 14.07 ＝ 20.3%（下限 70.0%，階級 1）",
    ),
    "49_cleanse_radius": (
        2,
        "common",
        "aura",
        {"type": "allies_in_radius", "radius": 1},
        [{"type": "cleanse", "affects": "allies"}],
        "過弱：total 4.20 ÷ 可用預算 18.99 ＝ 22.1%（下限 70.0%，階級 2）",
    ),
}


@pytest.mark.parametrize("name", sorted(WEAK_CASES))
def test_real_weak_failures_are_topped_up(
    library: ContentLibrary, models: ProposalModels, name: str
) -> None:
    tier, rarity, skeleton, shape, effects, message = WEAK_CASES[name]
    raw = json.dumps(_proposal(library, skeleton, shape, effects))
    ctx = _ctx(tier, rarity)

    before = evaluate_with_repair(raw, models, library, ctx, seed=SEED, topup=False)
    assert [e.code for e in before.result.errors] == ["budget.weak"]
    assert before.result.errors[0].message == message  # 與 27B 的真實失敗相同

    after = evaluate_with_repair(raw, models, library, ctx, seed=SEED)
    assert after.ok, [e.message for e in after.result.errors]
    assert "topup.budget.weak" in after.repaired
    skill = after.result.skill
    assert skill is not None
    assert validate_skill(skill, library) == []
    report = skill_budget(skill, library)
    assert report.min_ratio <= report.ratio <= report.max_ratio  # 仍在預算窗內
    # LLM 選的核心與形狀原樣保留，只多一個附帶效果
    assert [e.type for e in skill.effects][: len(effects)] == [e["type"] for e in effects]
    assert len(skill.effects) == len(effects) + 1
    assert skill.shape.type == shape["type"]
    # 補的效果語意合理：傷害與有害狀態打敵方、治療／護盾給友方（6S-2c 起也可能補有害狀態）
    added = skill.effects[-1]
    if added.type == "damage":
        assert added.affects == "enemies"
    elif added.type == "apply_status":
        assert added.affects == "enemies"
        assert added.status is not None
        assert not library.ruleset.statuses.by_id()[added.status].beneficial
    else:
        assert added.type in ("heal", "shield")
        assert added.affects in ("allies", "self")


def test_secondary_share_then_weak_is_repaired(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """位移＋傷害：第一次調值把傷害調過占比上限，修占比（傷害降回最低）後又變過弱——兩者一起修
    （27B 題 35、39、46、47 的 ``skeleton.secondary_share|budget.weak``）。"""
    raw = _proposal(
        library,
        "displace",
        _single(4),
        [
            {"type": "push", "affects": "enemies"},
            {"type": "damage", "affects": "enemies", "element": "physical"},
        ],
    )
    ctx = _ctx(1, "rare")
    before = evaluate_with_repair(raw, models, library, ctx, seed=SEED, topup=False)
    after = evaluate_with_repair(raw, models, library, ctx, seed=SEED)
    for evaluation in (before, after):  # 這一步是數值修補，不需要結構補強
        assert evaluation.ok, [e.message for e in evaluation.result.errors]
        assert {"skeleton.secondary_share", "budget.weak"} <= set(evaluation.repaired)
    assert before.result.skill == after.result.skill
    assert after.result.skill is not None
    assert [e.type for e in after.result.skill.effects] == ["push", "damage"]


type KeywordCase = tuple[int, SkillRarity, str, list[dict[str, Any]], str, str, str]
KEYWORD_CASES: dict[str, KeywordCase] = {
    # (階級, 稀有度, 骨架, 效果, 題目關鍵字, 補的原語, 補的對象)
    "18_topple_marked": (
        1,
        "rare",
        "displace",
        [{"type": "topple", "affects": "enemies"}],
        "marked",
        "apply_status",
        "enemies",
    ),
    "12_knock_prone_summon": (
        1,
        "rare",
        "displace",
        [{"type": "knock_prone", "affects": "enemies"}],
        "summon",
        "apply_status",
        "allies",
    ),
}


@pytest.mark.parametrize("name", sorted(KEYWORD_CASES))
def test_missing_keyword_is_topped_up(
    library: ContentLibrary, models: ProposalModels, name: str
) -> None:
    tier, rarity, skeleton, effects, keyword, primitive, affects = KEYWORD_CASES[name]
    raw = _proposal(library, skeleton, _single(4), effects)
    ctx = _ctx(tier, rarity, (keyword,))
    before = evaluate_with_repair(raw, models, library, ctx, seed=SEED, topup=False)
    assert not before.ok
    after = evaluate_with_repair(raw, models, library, ctx, seed=SEED)
    assert after.ok, [e.message for e in after.result.errors]
    skill = after.result.skill
    assert skill is not None
    assert keyword in derive_keywords(skill, library.keywords, exclusive_only=True).all()
    added = skill.effects[-1]
    assert (added.type, added.affects) == (primitive, affects)
    report = skill_budget(skill, library)
    assert report.min_ratio <= report.ratio <= report.max_ratio


def test_topup_is_deterministic_and_pure(library: ContentLibrary, models: ProposalModels) -> None:
    tier, rarity, skeleton, shape, effects, _ = WEAK_CASES["9_pull"]
    data = _proposal(library, skeleton, shape, effects)
    frozen = deepcopy(data)
    ctx = _ctx(tier, rarity, ("marked",))
    first = evaluate_with_repair(data, models, library, ctx, seed=SEED)
    second = evaluate_with_repair(deepcopy(data), models, library, ctx, seed=SEED)
    assert first == second
    assert data == frozen  # 輸入不被修改
    candidates = topup_candidates(library, data, keywords=("marked",), weak=True)
    assert candidates == topup_candidates(library, data, keywords=("marked",), weak=True)
    assert 0 < len(candidates) <= TOPUP_MAX
    assert data == frozen


def test_topup_only_adds_menu_primitives(library: ContentLibrary) -> None:
    data = _proposal(library, "displace", _single(4), [{"type": "pull", "affects": "enemies"}])
    found = topup_candidates(library, data, weak=True, primitives=("pull", "heal"))
    assert found  # heal 不合骨架，但候選只看選單；驗證會擋
    assert all(c["effects"][-1]["type"] == "heal" for c in found)
    assert topup_candidates(library, data, weak=True, primitives=("pull",)) == []


def test_unfixable_weak_gets_actionable_feedback(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """控制骨架的淨地（傷害最多占 40%）補什麼都不夠：照舊回報 ``budget.weak``，訊息附建議。

    6S-2c 起附帶效果也會試有害狀態（``apply_status`` 是控制骨架的核心原語，淨地＋定身就合格），
    所以這裡用不開放 ``apply_status`` 的選單，維持「補強救不回」的情境。"""
    no_status = build_proposal_models(
        library,
        primitives=[p.id for p in library.ruleset.primitives.primitives if p.id != "apply_status"],
    )
    raw = _proposal(
        library, "control", _single(3), [{"type": "clear_surface", "affects": "enemies"}]
    )
    fixed = evaluate_with_repair(raw, models, library, _ctx(2, "rare"), seed=SEED)
    assert fixed.ok and "topup.budget.weak" in fixed.repaired
    after = evaluate_with_repair(raw, no_status, library, _ctx(2, "rare"), seed=SEED)
    assert [e.code for e in after.result.errors] == ["budget.weak"]
    assert after.result.errors[0].message.endswith(WEAK_ADVICE)


# ---------------------------------------------------------------------------
# 出題：選單帶不到關鍵字的題目不出
# ---------------------------------------------------------------------------


def test_unreachable_keyword_topic_is_detected(library: ContentLibrary) -> None:
    """27B 題 0：普通稀有度的淨化光環配「召喚物」——號令（commanding）要稀有，光環不能對敵，
    選單裡沒有任何寫法帶得到，三次都 ``keyword.required``。"""
    request = ProposalRequest(1, "common", keywords=("summon",), core_primitive="cleanse")
    subset = select_subset(library, request)
    assert not keywords_reachable(library, subset, core="cleanse")
    rare = select_subset(library, replace(request, rarity="rare"))
    assert keywords_reachable(library, rare, core="cleanse")


@pytest.mark.slow
def test_make_topic_only_poses_reachable_keyword_topics(library: ContentLibrary) -> None:
    keywords = ("summon", "poisoned", "collision", "prone", "wet", "marked")
    made = 0
    for keyword in keywords:
        for seed in range(8):
            topic = make_topic(
                library, TopicRequest(tier=1 + seed % 3, keywords=(keyword,), seed=seed, uses={})
            )
            if topic is None:
                continue
            request, _, _ = topic
            made += 1
            subset = select_subset(library, request)
            assert keywords_reachable(library, subset, core=request.core_primitive)
    assert made > 0


def test_topics_without_keywords_are_unchanged(library: ContentLibrary) -> None:
    """沒有關鍵字的題目不受可達性檢查影響（同種子同題目；核心第一次仍用 ``core`` 串流）。"""
    for seed in range(6):
        topic = make_topic(library, TopicRequest(tier=2, keywords=(), seed=seed, uses={}))
        assert topic is not None
        again = make_topic(library, TopicRequest(tier=2, keywords=(), seed=seed, uses={}))
        assert topic == again
        assert topic[0].core_primitive is not None


# ---------------------------------------------------------------------------
# prompt：預算與關鍵字說明
# ---------------------------------------------------------------------------


def test_available_keywords_list_ways(library: ContentLibrary) -> None:
    request = ProposalRequest(1, "rare", keywords=("summon",), core_primitive="knock_prone")
    payload = available_payload(library, select_subset(library, request))
    (entry,) = payload["keywords"]
    assert "apply_status（status＝commanding）" in entry["ways"]
    assert keyword_way_texts(library, "summon", primitives=()) == []


def test_request_payload_has_budget_and_keyword_notes(library: ContentLibrary) -> None:
    request = ProposalRequest(1, "rare", keywords=("summon",), core_primitive="knock_prone")
    prompt = build_proposal_prompt(library, request)
    user = prompt.messages[1]["content"]
    assert "budget_note_zh" in user
    assert "不一定是傷害" in user
    assert "cleanse＋shield" in user
    assert "keyword_note_zh" in user
    plain = build_proposal_prompt(library, ProposalRequest(1, "rare", core_primitive="pull"))
    assert "keyword_note_zh" not in plain.messages[1]["content"]
    assert plain.tokens < 3_500  # 不大幅增加（context 8192）


def test_propose_skill_accepts_weak_proposal_first_try(library: ContentLibrary) -> None:
    """Mock LLM 回 27B 題 26 的單一淨化：第一次就由引擎補成合格技能，不退回。"""
    tier, rarity, skeleton, shape, effects, _ = WEAK_CASES["26_cleanse"]
    text = json.dumps(_proposal(library, skeleton, shape, effects))
    request = ProposalRequest(tier, rarity, core_primitive="cleanse", skeleton=skeleton)
    outcome = propose_skill(
        MockLLMClient([text] * 3), library, request, _ctx(tier, rarity), seed=SEED
    )
    assert outcome.source == "llm"
    assert outcome.attempts == 1
    assert "topup.budget.weak" in outcome.records[0].repaired
