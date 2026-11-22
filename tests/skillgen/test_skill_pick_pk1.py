"""PK-1：挑選模式的候選池與打分（提案第 7.1、7.2、7.5、7.8 節）。"""

from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.player_pool import player_skills
from trpg.content.skill_pick import PickPoolRules, PickWeights, WishTagRules
from trpg.shared.types import Attribute
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import fits_request, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.skill_pick import (
    PickCandidate,
    candidate_pool,
    design_key,
    design_label,
    pick_slate,
    rank_candidates,
    score_candidate,
)
from trpg.skillgen.validate import validate_skill

FAST = ProposalRequest(1, "rare", skeleton="rune")
"""不帶關鍵字、指定骨架的題目（LB 第 5 題）：組合器很快。"""
KEYWORD = ProposalRequest(1, "rare", keywords=("fury",))
"""帶一般關鍵字的題目（LB 第 2 題）。"""


@cache
def _lib() -> ContentLibrary:
    return load_library()


def _ctx(request: ProposalRequest) -> ProposalContext:
    return ProposalContext(request.tier, request.rarity, keywords=request.keywords)


def test_the_table_loads_and_every_number_is_written() -> None:
    rules = _lib().skill_pick
    # HC-4b2：程式不再有預設值，每個數字都寫在 skill_pick.yaml（少一欄就載入失敗）
    for model, data in (
        (PickPoolRules, rules.pool.model_dump()),
        (PickWeights, rules.weights.model_dump()),
        (WishTagRules, rules.wish_tags.model_dump()),
    ):
        for name in sorted(n for n, v in data.items() if isinstance(v, int)):
            with pytest.raises(ValidationError, match=name):
                model.model_validate({k: v for k, v in data.items() if k != name})
    assert rules.wish_tags.elements and rules.wish_tags.effects
    assert 4 <= rules.pool.top_k <= 6  # 提案第 6 節第 2 題 A：每格 4～6 個
    assert rules.pool.min_for_llm == 2  # 提案 7.6：少於 2 個就不呼叫 LLM


def test_design_key_matches_the_census_definition() -> None:
    lib = _lib()
    skill = next(iter(player_skills(lib).values()))
    key = design_key(skill)
    assert key[:3] == (skill.skeleton, skill.kind, skill.shape.type)
    assert design_label(key).split("|")[:3] == [skill.skeleton, skill.kind, skill.shape.type]


def test_pool_candidates_are_legal_distinct_and_fit_the_request() -> None:
    lib = _lib()
    for request in (FAST, KEYWORD):
        pool = candidate_pool(lib, request, _ctx(request), seed=7)
        assert pool.candidates
        kind = wanted_kind(lib, request)
        keys = [c.key for c in pool.candidates]
        assert len(keys) == len(set(keys))  # 依設計去重
        for cand in pool.candidates:
            assert not validate_skill(cand.skill, lib)
            assert fits_request(cand.skill, request, kind, lib)
            assert cand.key == design_key(cand.skill)
            assert (cand.seed is None) == (cand.source == "pool")


def test_pool_stops_at_the_design_cap() -> None:
    lib = _lib()
    base = lib.skill_pick
    rules = base.model_copy(
        update={"pool": base.pool.model_copy(update={"designs": 4, "top_k": 4})}
    )
    pool = candidate_pool(lib, FAST, _ctx(FAST), seed=3, rules=rules)
    composer = [c for c in pool.candidates if c.source == "composer"]
    assert len(composer) == 4


@pytest.mark.parametrize("seed", [0, 12345, 2**31])
def test_the_slate_is_deterministic(seed: int) -> None:
    lib = _lib()
    first = pick_slate(lib, FAST, _ctx(FAST), seed=seed)
    second = pick_slate(lib, FAST, _ctx(FAST), seed=seed)
    assert first == second
    assert [c.skill.id for c in first.ranked] == [c.skill.id for c in second.ranked]
    assert len(first.ranked) == min(lib.skill_pick.pool.top_k, first.pool_size)


def _maker_and_user() -> tuple[str, PickCandidate, PickCandidate]:
    """手寫技能裡一招製造 K、一招利用 K（同一個關鍵字）。"""
    lib = _lib()
    skills = sorted(player_skills(lib).values(), key=lambda s: s.id)
    derived = {s.id: derive_keywords(s, lib.keywords, exclusive_only=True) for s in skills}
    for maker in skills:
        for keyword in derived[maker.id].makes:
            user = next(
                (
                    s
                    for s in skills
                    if keyword in derived[s.id].uses and keyword not in derived[s.id].makes
                ),
                None,
            )
            if user is not None and keyword not in derived[maker.id].uses:
                return (
                    keyword,
                    PickCandidate(maker, "pool", None, design_key(maker)),
                    PickCandidate(user, "pool", None, design_key(user)),
                )
    raise AssertionError("找不到製造／利用同一個關鍵字的兩招")


def test_synergy_counts_makes_uses_links() -> None:
    lib = _lib()
    _, maker, user = _maker_and_user()
    weights = lib.skill_pick.weights
    alone = score_candidate(lib, maker, PickPlayer(), weights)
    linked = score_candidate(lib, maker, PickPlayer(held_skills=(user.skill,)), weights)
    assert dict(alone.parts)["synergy"] == 0
    assert dict(linked.parts)["synergy"] >= weights.synergy_per_link
    assert linked.score > alone.score
    capped = weights.model_copy(update={"synergy_max_links": 0})
    none = score_candidate(lib, maker, PickPlayer(held_skills=(user.skill,)), capped)
    assert dict(none.parts)["synergy"] == 0


def test_behavior_and_route_add_points_but_not_power() -> None:
    lib = _lib()
    keyword_def = next(k for k in lib.keywords.keywords if k.actions)
    skill = next(
        s
        for s in sorted(player_skills(lib).values(), key=lambda s: s.id)
        if keyword_def.id in derive_keywords(s, lib.keywords, exclusive_only=True).all()
    )
    cand = PickCandidate(skill, "pool", None, design_key(skill))
    action = keyword_def.actions[0]
    scored = score_candidate(lib, cand, PickPlayer(behavior={action: 3}), lib.skill_pick.weights)
    assert dict(scored.parts)["behavior"] == min(400, 3 * 20)
    attrs = {a: 18 if a == skill.scaling_attr else 10 for a in Attribute}
    routed = score_candidate(lib, cand, PickPlayer(hero_attributes=attrs), lib.skill_pick.weights)
    assert dict(routed.parts)["route"] == lib.skill_pick.weights.route_main
    assert "budget" not in dict(routed.parts)  # 不比強弱


def test_rank_prefers_diverse_designs_and_breaks_ties_by_order() -> None:
    lib = _lib()
    pool = candidate_pool(lib, FAST, _ctx(FAST), seed=11).candidates
    base = pool[0]
    clone = replace(base, skill=base.skill.model_copy(update={"id": "clone"}))
    other = next(c for c in pool if c.key[3] != base.key[3])
    ranked = rank_candidates([base, clone, other], lib.skill_pick.weights, 3)
    assert [c.skill.id for c in ranked] == [base.skill.id, other.skill.id, "clone"]
    assert dict(ranked[2].parts)["diversity"] < 0
    no_penalty = lib.skill_pick.weights.model_copy(
        update={
            "same_skeleton_penalty": 0,
            "same_shape_penalty": 0,
            "same_effects_penalty": 0,
            "same_element_penalty": 0,
        }
    )
    plain = rank_candidates([base, clone, other], no_penalty, 3)
    assert [c.skill.id for c in plain] == [base.skill.id, "clone", other.skill.id]


def test_workshop_weights_change_the_order() -> None:
    """數值工坊改權重後排序跟著變：手寫技能加分很大時，手寫技能排第一。PK-1b 起預設不放手寫技能
    （``pool.handwritten_max`` 0），這裡開到 1 再比。"""
    lib = _lib()
    allowed = lib.skill_pick.model_copy(
        update={"pool": lib.skill_pick.pool.model_copy(update={"handwritten_max": 1})}
    )
    default = pick_slate(lib, KEYWORD, _ctx(KEYWORD), seed=5, rules=allowed)
    assert any(
        c.source == "pool"
        for c in candidate_pool(lib, KEYWORD, _ctx(KEYWORD), seed=5, rules=allowed).candidates
    )
    boosted = allowed.model_copy(
        update={"weights": allowed.weights.model_copy(update={"pool_bonus": 100_000})}
    )
    changed = pick_slate(lib, KEYWORD, _ctx(KEYWORD), seed=5, rules=boosted)
    assert changed.ranked[0].source == "pool"
    assert [c.skill.id for c in changed.ranked] != [c.skill.id for c in default.ranked]


def test_default_ranking_snapshot() -> None:
    """預設權重下的排序快照（LB 第 5 題、種子 0）：改了組合器、打分或權重要更新這裡。"""
    lib = _lib()
    slate = pick_slate(lib, FAST, _ctx(FAST), seed=0)
    assert len(slate.ranked) == lib.skill_pick.pool.top_k
    labels = slate.designs
    assert len(set(labels)) == len(labels)
    assert all(label.startswith("rune|active|") for label in labels)
