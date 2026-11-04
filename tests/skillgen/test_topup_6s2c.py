"""6S-2c：結構補強的附帶效果不再固定先試 ``damage``。

- :func:`filler_order` 依骨架偏好排序、依「題目種子＋提議內容」的雜湊輪替起點，確定性。
- 50 題升級候選（``upgrade_items(seed=0)``）的單一核心提議：新順序下補上的附帶效果不再幾乎全是
  傷害；每個補強結果照樣通過驗證、在預算窗內；合格數不少於舊的固定順序；重跑結果相同。

舊順序（``damage → heal → shield``，沒有有害狀態）用 monkeypatch 還原 :func:`filler_order` 與
:data:`FILLER_EFFECTS` 來對照，數字寫進 ``docs/phases/Phase6S-2c報告.md``。
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Any

import pytest

from trpg.content.library import ContentLibrary
from trpg.content.skills.constants import SkillRarity
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.skill_eval import upgrade_items
from trpg.skillgen import proposal_topic, proposal_topup
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.proposal import ProposalContext, ProposalModels, build_proposal_models
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_layouts import layout_of_effects
from trpg.skillgen.proposal_subset import SubsetError, select_subset
from trpg.skillgen.proposal_topup import (
    FILLER_EFFECTS,
    FILLER_PREFERENCE,
    TOPUP_CODES,
    filler_order,
    topup_candidates,
)
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.validate import validate_skill

LEGACY_ORDER = ("damage", "heal", "shield")
"""6S-2 的固定順序（對照用）。"""


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


def _proposal(skeleton: str, core: str, affects: str, shape: dict[str, Any]) -> dict[str, Any]:
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
    data = _proposal(skeleton, core, affects, {"type": "single", "range": 3})
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
        filler_order(_proposal("aura", "cleanse", "allies", {"type": "single", "range": r}))[0]
        for r in range(1, 9)
    }
    assert firsts == {"heal", "shield"}
    assert set(FILLER_PREFERENCE) <= set(library.skeletons)


def test_candidates_are_deterministic_and_menu_only(library: ContentLibrary) -> None:
    data = _proposal("displace", "pull", "enemies", {"type": "single", "range": 2})
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
    data = _proposal("displace", "pull", "enemies", {"type": "single", "range": 2})
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
    data = _proposal(skeleton, core, affects, {"type": "single", "range": 3})
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
