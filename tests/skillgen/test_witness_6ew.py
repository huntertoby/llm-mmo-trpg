"""Phase 6E-W：出題的可行解檢查（``proposal_witness``）與它在 ``make_topic`` 的套用。

題目取自 roguelite 完整技能三選一的實際出題路徑（``generate_candidates`` 的 LLM 來源；兩個關鍵字、
指定武器大類），見 ``docs/archive/phases/Phase6E-W報告.md``。
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from trpg.content.library import ContentLibrary
from trpg.skillgen import proposal_topic
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_subset import ProposalRequest, build_subset_models, select_subset
from trpg.skillgen.proposal_topic import TopicRequest, make_topic
from trpg.skillgen.proposal_witness import has_witness, witness_proposals
from trpg.skillgen.random_composer import default_library


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


def _ctx(request: ProposalRequest) -> ProposalContext:
    return ProposalContext(request.tier, request.rarity, weapon_class=request.weapon_class)


# 12B 實測退回、而且靜態上找不到合法寫法的題目（實際出題路徑抽出的原題）。
IMPOSSIBLE = [
    # 控場骨架：揭露沒有數值，附帶效果只能 1 個傷害（占比 ≤ 40%），還要帶點燃＋帶電兩種元素（1 階）
    ProposalRequest(
        1, "epic", keywords=("ignite", "charged"), core_primitive="reveal",
        menu_seed=1723973993, weapon_class="focus",
    ),
    # 普通稀有度：冰凍＋隱蔽只能靠冰霜、暗影兩種傷害元素，1 階不能帶兩種元素
    ProposalRequest(
        1, "common", keywords=("frozen", "concealed"), core_primitive="damage",
        menu_seed=4066102471, weapon_class="melee",
    ),
    # 下陷地形：限大地元素、影響格數受階級限制，再帶標記補不到預算
    ProposalRequest(
        1, "epic", keywords=("marked",), core_primitive="lower_terrain",
        menu_seed=942835368, weapon_class="melee",
    ),
]  # fmt: skip

POSSIBLE = [
    ProposalRequest(
        1, "rare", kind="reaction", keywords=("ignite", "charged"), core_primitive="damage",
        menu_seed=2213074107, weapon_class="focus",
    ),
    ProposalRequest(1, "rare", keywords=("ignite",), core_primitive="damage", weapon_class="focus"),
]  # fmt: skip


@pytest.mark.parametrize("request_", IMPOSSIBLE)
def test_impossible_topics_have_no_witness(
    library: ContentLibrary, request_: ProposalRequest
) -> None:
    assert not has_witness(library, request_, _ctx(request_), seed=0)


@pytest.mark.parametrize("request_", POSSIBLE)
def test_witness_is_a_real_legal_skill(library: ContentLibrary, request_: ProposalRequest) -> None:
    """找到的寫法照樣走完整驗證（含題目關鍵字、核心、武器相容）——不放寬任何規則。"""
    assert has_witness(library, request_, _ctx(request_), seed=0)
    subset = select_subset(library, request_)
    models = build_subset_models(library, subset)
    defs = models.json_schema()["$defs"]
    ctx = replace(
        _ctx(request_), keywords=request_.keywords, core_primitive=request_.core_primitive
    )
    found = None
    for data in witness_proposals(library, request_, subset, defs):
        evaluation = evaluate_with_repair(data, models, library, ctx, seed=0)
        if evaluation.ok:
            found = evaluation.result.skill
            break
    assert found is not None
    assert any(e.type == request_.core_primitive for e in found.effects)


def test_witness_proposals_are_deterministic(library: ContentLibrary) -> None:
    request = POSSIBLE[0]
    subset = select_subset(library, request)
    defs = build_subset_models(library, subset).json_schema()["$defs"]
    first = [
        json.dumps(d, sort_keys=True) for d in witness_proposals(library, request, subset, defs)
    ]
    again = [
        json.dumps(d, sort_keys=True) for d in witness_proposals(library, request, subset, defs)
    ]
    assert first == again
    assert first


@pytest.mark.parametrize(
    ("keywords", "weapon_class"),
    [
        (("frozen", "concealed"), "melee"),
        (("ignite", "charged"), "focus"),
        (("marked", "high_ground"), "ranged"),
        (("prone", "collision"), "melee"),
    ],
)
def test_make_topic_only_poses_topics_with_a_witness(
    library: ContentLibrary, keywords: tuple[str, ...], weapon_class: str
) -> None:
    """roguelite 橋接題（兩個關鍵字＋武器大類）：出得出的題目都有合法寫法；同輸入同結果。"""
    for seed in range(4):
        for tier in (1, 2):
            topic = TopicRequest(tier, keywords, seed, {}, weapon_class=weapon_class)
            made = make_topic(library, topic)
            assert made == make_topic(library, topic)
            if made is None:
                continue
            request, ctx, _ = made
            assert has_witness(library, request, ctx, seed=0)


def test_passing_topics_are_unchanged(
    library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    """可行解檢查不消耗出題的亂數：第一次抽到的題目通過檢查時，結果和不檢查時完全相同。"""
    topic = TopicRequest(2, ("ignite",), 5, {}, weapon_class="focus")
    checked = make_topic(library, topic)
    monkeypatch.setattr(proposal_topic, "has_witness", lambda *_a, **_k: True)
    unchecked = make_topic(library, topic)
    assert checked is not None
    assert checked == unchecked
