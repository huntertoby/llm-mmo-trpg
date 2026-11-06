"""主題合併（R2）。

原 ``test_topup_6s2.py``：

6S-2：升級候選退回率——結構補強、過弱補強的占比重試、出題的關鍵字可達性、prompt 說明。

表格中的提議是依 27B 評估（commit 6af12836，升級候選 50 題）``skills_errors.csv`` 的真實失敗重建的：
``topup=False`` 時得到 **一字不差** 的原始錯誤訊息（同樣的 total ÷ 可用預算），證明是同一種提議；
``topup=True``（正式流程）時合格，而且預算比例仍在驗證器的窗內。驗證規則與預算數值都沒有改。

原 ``test_topup_6s2c.py``：

6S-2c：結構補強的附帶效果不再固定先試 ``damage``。

- :func:`filler_order` 依骨架偏好排序、依「題目種子＋提議內容」的雜湊輪替起點，確定性。
- 50 題升級候選（``upgrade_items(seed=0)``）的單一核心提議：新順序下補上的附帶效果不再幾乎全是
  傷害；每個補強結果照樣通過驗證、在預算窗內；合格數不少於舊的固定順序；重跑結果相同。

舊順序（``damage → heal → shield``，沒有有害狀態）用 monkeypatch 還原 :func:`filler_order` 與
:data:`FILLER_EFFECTS` 來對照，數字寫進 ``docs/archive/phases/Phase6S-2c報告.md``。

原 ``test_fallback_6s2b.py``：

6S-2b：升級候選退回路徑的缺口——任何合法出題都至少產生一個保底技能。

退回（:func:`~trpg.skillgen.proposal_fallback.fallback_skill`）只看題目的階級、稀有度、種類、
骨架、關鍵字與種子（核心原語、輪替選單種子、主題不影響退回），所以「階級 × 出題稀有度 × 種類 ×
關鍵字」窮舉、種子抽樣，就涵蓋升級候選出題（:func:`~trpg.skillgen.proposal_topic.make_topic`）的
所有退回情況。合法出題＝ :func:`select_subset` 得出選單，且選單帶得到題目關鍵字（與 ``make_topic``
相同的條件）。
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

import pytest

from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillRarity
from trpg.llm import MockLLMClient
from trpg.llm.prompts.proposal import LOCAL_CONTEXT_TOKENS, build_proposal_prompt
from trpg.llm.propose import propose_skill
from trpg.llm.skill_eval import upgrade_items
from trpg.skillgen import proposal_topic, proposal_topup
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
)
from trpg.skillgen.proposal_budget import WEAK_ADVICE, evaluate_with_repair
from trpg.skillgen.proposal_fallback import fallback_skill
from trpg.skillgen.proposal_layouts import layout_of_effects
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    SubsetError,
    available_payload,
    select_subset,
)
from trpg.skillgen.proposal_topic import TOPIC_RARITIES, TopicRequest, make_topic
from trpg.skillgen.proposal_topup import (
    FILLER_EFFECTS,
    FILLER_PREFERENCE,
    TOPUP_CODES,
    TOPUP_MAX,
    filler_order,
    keyword_way_texts,
    keywords_reachable,
    topup_candidates,
)
from trpg.skillgen.validate import validate_skill

# --- 原 test_topup_6s2.py ---

SEED = 7


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
    # LLM-1：固定說明搬到每題相同的 <guide>（沒關鍵字的題目也帶，才能共用前綴）；題目區只有 keywords
    plain = build_proposal_prompt(library, ProposalRequest(1, "rare", core_primitive="pull"))
    plain_user = plain.messages[1]["content"]
    assert "keyword_note_zh" in plain_user.split("<guide>")[1].split("</guide>")[0]
    assert "keyword_note_zh" not in plain_user.split("<request>")[1]
    assert plain.tokens + 1024 <= LOCAL_CONTEXT_TOKENS  # 固定全目錄要放得進本機 16k 上下文


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


# --- 原 test_topup_6s2c.py ---

LEGACY_ORDER = ("damage", "heal", "shield")
"""6S-2 的固定順序（對照用）。"""


def _6s2c_proposal(skeleton: str, core: str, affects: str, shape: dict[str, Any]) -> dict[str, Any]:
    return {
        "layout": "standard",
        "kind": "active",
        "skeleton": skeleton,
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "shape": shape,
        "effects": [{"type": core, "affects": affects}],
    }


# ---------------------------------------------------------------------------
# 順序：偏好與輪替
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("skeleton", "core", "affects", "first"),
    [
        ("strike", "damage", "enemies", {"damage"}),
        ("area", "damage", "enemies", {"damage"}),
        ("aura", "cleanse", "allies", {"heal", "shield"}),
        ("control", "reveal", "enemies", {"apply_status"}),
        ("displace", "pull", "enemies", {"damage", "apply_status"}),
        ("reaction", "intercept", "self", {"heal", "shield"}),  # 表外：核心對自己 → 治療／護盾
        ("reaction", "pull", "enemies", {"damage", "apply_status"}),  # 表外：核心對敵
    ],
)
def test_filler_order_prefers_skeleton_theme(
    skeleton: str, core: str, affects: str, first: set[str]
) -> None:
    data = _6s2c_proposal(skeleton, core, affects, {"type": "single", "range": 3})
    seen_first: set[str] = set()
    for seed in range(40):
        order = filler_order(data, seed=seed)
        assert sorted(order) == sorted(FILLER_EFFECTS)  # 每種都會試到，只是先後不同
        assert set(order[: len(first)]) == first  # 偏好的一組在前
        assert order == filler_order(data, seed=seed)  # 確定性
        seen_first.add(order[0])
    assert seen_first == first  # 偏好組內輪替起點


def test_filler_order_rotates_by_content(library: ContentLibrary) -> None:
    """同一個種子、不同提議內容（射程）也會輪替；沒有偏好時不固定先試傷害。"""
    firsts = {
        filler_order(_6s2c_proposal("aura", "cleanse", "allies", {"type": "single", "range": r}))[0]
        for r in range(1, 9)
    }
    assert firsts == {"heal", "shield"}
    assert set(FILLER_PREFERENCE) <= set(library.skeletons)


def test_candidates_are_deterministic_and_menu_only(library: ContentLibrary) -> None:
    data = _6s2c_proposal("displace", "pull", "enemies", {"type": "single", "range": 2})
    first = topup_candidates(library, data, weak=True, seed=5, rarity="rare")
    assert first == topup_candidates(library, data, weak=True, seed=5, rarity="rare")
    added = {c["effects"][-1]["type"] for c in first}
    assert added == set(FILLER_EFFECTS)
    statuses = library.ruleset.statuses.by_id()
    for candidate in first:
        effect = candidate["effects"][-1]
        if effect["type"] == "apply_status":
            assert effect["affects"] == "enemies"
            assert not statuses[effect["status"]].beneficial
    only = topup_candidates(library, data, weak=True, seed=5, primitives=("pull", "shield"))
    assert {c["effects"][-1]["type"] for c in only} == {"shield"}


def test_common_rarity_only_offers_common_statuses(library: ContentLibrary) -> None:
    data = _6s2c_proposal("displace", "pull", "enemies", {"type": "single", "range": 2})
    table = library.ruleset.statuses.by_id()
    for seed in range(20):
        for candidate in topup_candidates(library, data, weak=True, seed=seed, rarity="common"):
            effect = candidate["effects"][-1]
            if effect["type"] == "apply_status":
                assert table[effect["status"]].min_rarity == "common"


# ---------------------------------------------------------------------------
# 手寫題：支援骨架輪替治療與護盾，位移骨架輪替傷害與有害狀態
# ---------------------------------------------------------------------------


type SeedCase = tuple[int, SkillRarity, str, str, str, set[str]]
SEED_CASES: dict[str, SeedCase] = {
    # (階級, 稀有度, 骨架, 核心, 對象, 補上的附帶效果種類)
    "aura_cleanse": (3, "common", "aura", "cleanse", "allies", {"heal", "shield"}),
    "displace_pull": (1, "rare", "displace", "pull", "enemies", {"damage", "apply_status"}),
}


@pytest.mark.parametrize("name", sorted(SEED_CASES))
def test_weak_topup_varies_with_seed(library: ContentLibrary, name: str) -> None:
    tier, rarity, skeleton, core, affects, expect = SEED_CASES[name]
    models = build_proposal_models(library)
    data = _6s2c_proposal(skeleton, core, affects, {"type": "single", "range": 3})
    data["layout"] = layout_of_effects(library, [core])
    ctx = ProposalContext(tier, rarity)
    added: Counter[str] = Counter()
    for seed in range(12):
        after = evaluate_with_repair(data, models, library, ctx, seed=seed)
        assert after.ok, [e.message for e in after.result.errors]
        assert "topup.budget.weak" in after.repaired
        skill = after.result.skill
        assert skill is not None
        assert validate_skill(skill, library) == []
        report = skill_budget(skill, library)
        assert report.min_ratio <= report.ratio <= report.max_ratio
        added[skill.effects[-1].type] += 1
    assert set(added) == expect, added


# ---------------------------------------------------------------------------
# 50 題升級候選：補強分布（新順序 vs 6S-2 的固定順序）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    index: int
    data: dict[str, Any]
    models: ProposalModels
    ctx: ProposalContext
    seed: int


_CATEGORIES = (("spell", "focus", "int"), ("weapon", "melee", "str"))
_AFFECTS = ("enemies", "allies", "self")
_SHAPES_PER_SKELETON = 2


def _shape(library: ContentLibrary, shape_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {"type": shape_id}
    for name, spec in sorted(library.ruleset.shapes.by_id()[shape_id].params.items()):
        out[name] = max(spec.min, min(spec.max, 3))
    return out


def _variants(library: ContentLibrary, request: Any, skeleton: str) -> Iterator[dict[str, Any]]:
    subset = select_subset(library, request)
    shapes = [s for s in subset.shapes if s in library.skeletons[skeleton].shapes]
    for shape_id in shapes[:_SHAPES_PER_SKELETON]:
        for affects in _AFFECTS:
            for category, weapon_req, attr in _CATEGORIES:
                yield {
                    "layout": layout_of_effects(library, [request.core_primitive]),
                    "kind": subset.kind or "active",
                    "skeleton": skeleton,
                    "category": category,
                    "weapon_req": weapon_req,
                    "scaling_attr": attr,
                    "shape": _shape(library, shape_id),
                    "effects": [{"type": request.core_primitive, "affects": affects}],
                }


def _only_topup_errors(evaluation: Any) -> bool:
    errors = evaluation.result.errors
    return bool(errors) and all(e.stage == "rules" and e.code in TOPUP_CODES for e in errors)


def _build_cases(library: ContentLibrary) -> list[Case]:
    """每題、每個骨架、前兩個形狀 × 對象：取第一個「只剩補強處理的錯誤」的單一核心提議
    （最常見的失敗型態；與 6S-2 報告 3.2 的掃描同一種建構）。"""
    cases: list[Case] = []
    for item in upgrade_items(library, 50, seed=0):
        request = item.request
        if request.core_primitive is None:
            continue
        try:
            models = build_proposal_prompt(library, request).models
            skeletons = select_subset(library, request).skeletons
        except (SubsetError, ValueError):
            continue
        ctx = replace(item.ctx, keywords=request.keywords, core_primitive=request.core_primitive)
        for skeleton in skeletons:
            picked: dict[tuple[str, str], dict[str, Any]] = {}
            for data in _variants(library, request, skeleton):
                key = (json.dumps(data["shape"], sort_keys=True), data["effects"][0]["affects"])
                if key in picked:
                    continue
                before = evaluate_with_repair(
                    data, models, library, ctx, seed=item.seed, topup=False
                )
                if _only_topup_errors(before):
                    picked[key] = data
            cases += [Case(item.index, d, models, ctx, item.seed) for d in picked.values()]
    return cases


@pytest.fixture(scope="module")
def cases(library: ContentLibrary) -> list[Case]:
    # 6E-W 起出題會跳過找不到合法寫法的題目；這組表格驗的是補強的附帶效果順序，沿用 6S-2c 的同一批
    # 題目（關掉可行解檢查），讓前後對照的樣本不變。
    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(proposal_topic, "has_witness", lambda *_a, **_k: True)
        return _build_cases(library)


type Outcome = tuple[str, ...]
"""每個提議的補強結果：``("fail",)``，或 ``(路徑, 補上的效果…)``。"""


def _outcomes(library: ContentLibrary, cases: list[Case]) -> list[Outcome]:
    out: list[Outcome] = []
    for case in cases:
        after = evaluate_with_repair(case.data, case.models, library, case.ctx, seed=case.seed)
        skill = after.result.skill
        if not after.ok or skill is None:
            out.append(("fail",))
            continue
        assert validate_skill(skill, library) == []
        report = skill_budget(skill, library)
        assert report.min_ratio <= report.ratio <= report.max_ratio
        filler = not case.ctx.keywords and "topup.budget.weak" in after.repaired
        added = tuple(e.type for e in skill.effects[1:])
        out.append(("filler" if filler else "other", *added))
    return out


def _filler_counts(outcomes: list[Outcome]) -> Counter[str]:
    return Counter(o[-1] for o in outcomes if o[0] == "filler" and len(o) > 1)


def test_upgrade_topup_distribution(
    library: ContentLibrary, cases: list[Case], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert len(cases) >= 30  # 可建構的提議夠多才有意義
    new = _outcomes(library, cases)
    assert new == _outcomes(library, cases)  # 確定性：重跑相同

    with monkeypatch.context() as patched:
        patched.setattr(proposal_topup, "FILLER_EFFECTS", LEGACY_ORDER)
        patched.setattr(proposal_topup, "filler_order", lambda data, *, seed=0: LEGACY_ORDER)
        legacy = _outcomes(library, cases)

    new_counts = _filler_counts(new)
    legacy_counts = _filler_counts(legacy)
    print("legacy", sorted(legacy_counts.items()), "new", sorted(new_counts.items()))
    # 合格數不減少（驗證與預算沒放寬，只換試的先後）
    assert sum(o[0] != "fail" for o in new) >= sum(o[0] != "fail" for o in legacy)
    # 舊順序：只要傷害合格就一定是傷害
    assert legacy_counts["damage"] > sum(legacy_counts.values()) // 2
    # 新順序：不再集中在傷害，至少三種附帶效果
    assert new_counts["damage"] < legacy_counts["damage"]
    assert new_counts["damage"] <= sum(new_counts.values()) // 2
    assert len(new_counts) >= 3, new_counts


# --- 原 test_fallback_6s2b.py ---

TIERS = (1, 2, 3)
KINDS = (None, "reaction")


def _composable(library: ContentLibrary) -> list[str]:
    table = library.keywords.by_id()
    return [k for k in library.keywords.ids() if table[k].composable]


def _legal(library: ContentLibrary, request: ProposalRequest) -> bool:
    try:
        subset = select_subset(library, request)
    except SubsetError:
        return False
    return keywords_reachable(library, subset)


def _check(library: ContentLibrary, request: ProposalRequest, seed: int) -> str:
    ctx = ProposalContext(request.tier, request.rarity)
    skill, source = fallback_skill(library, request, ctx, seed=seed)
    assert validate_skill(skill, library) == []
    assert skill.tier == request.tier and skill.rarity == request.rarity
    assert skill.kind == (request.kind or "active")
    return source


# ---------------------------------------------------------------------------
# 回歸：6S-2 報告待決 6 的那一題（mock 升級候選第 43 題）
# ---------------------------------------------------------------------------

REGRESSION = ProposalRequest(
    2,
    "rare",
    kind="reaction",
    keywords=("high_ground",),
    core_primitive="heal",
    menu_seed=457164577,
)
REGRESSION_SEED = 3514268949


def test_reaction_heal_high_ground_rare_tier2_falls_back(library: ContentLibrary) -> None:
    """反應技＋高地（階級 2 稀有）：組合器做不出帶高地的反應技、技能池沒有階級 2 的反應技，
    原本工坊也沒填反應時機而丟 FallbackError；現在由工坊做出反應技。"""
    ctx = ProposalContext(2, "rare")
    skill, source = fallback_skill(library, REGRESSION, ctx, seed=REGRESSION_SEED)
    assert source == "workshop"
    assert skill.kind == "reaction" and skill.skeleton == "reaction"
    assert skill.reaction is not None
    assert validate_skill(skill, library) == []
    again, _ = fallback_skill(library, REGRESSION, ctx, seed=REGRESSION_SEED)
    assert again == skill  # 確定性


@pytest.mark.parametrize("keyword", ["wet", "high_ground", "summon"])
def test_reaction_keywords_the_composer_cannot_carry(library: ContentLibrary, keyword: str) -> None:
    """修補前所有階級的稀有／史詩反應技配這三個關鍵字都會丟 FallbackError（掃描 18 組）。"""
    request = ProposalRequest(3, "epic", kind="reaction", keywords=(keyword,))
    assert _legal(library, request)
    assert _check(library, request, seed=0) == "workshop"


# ---------------------------------------------------------------------------
# 窮舉（slow）
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("rarity", TOPIC_RARITIES)
@pytest.mark.parametrize("tier", TIERS)
def test_every_legal_topic_has_a_fallback(
    library: ContentLibrary, tier: int, rarity: SkillRarity, kind: str | None
) -> None:
    """每個合法的（階級, 稀有度, 種類, 無關鍵字或一個可交給 LLM 的關鍵字）× 種子 0、1 都有保底。"""
    checked = 0
    for keywords in [(), *((k,) for k in _composable(library))]:
        request = ProposalRequest(tier, rarity, kind=kind, keywords=keywords)
        if not _legal(library, request):
            continue
        for seed in (0, 1):
            _check(library, request, seed)
            checked += 1
    if kind is None or rarity != "common":  # 反應技最低稀有；其餘每組都至少有沒關鍵字的題
        assert checked > 0


@pytest.mark.slow
def test_sampled_make_topic_outputs_have_a_fallback(library: ContentLibrary) -> None:
    """照升級候選的出題方式依種子抽樣（含反應技題與帶關鍵字的題），每題都有保底。"""
    keywords = _composable(library)
    made = 0
    for seed in range(60):
        picked = (keywords[seed % len(keywords)],) if seed % 2 else ()
        topic = make_topic(
            library,
            TopicRequest(
                tier=TIERS[seed % 3],
                keywords=picked,
                seed=seed,
                uses={},
                reaction_permille=500,
            ),
        )
        if topic is None:
            continue
        request, ctx, item_seed = topic
        skill, _ = fallback_skill(library, request, ctx, seed=item_seed)
        assert validate_skill(skill, library) == []
        made += 1
    assert made >= 40
