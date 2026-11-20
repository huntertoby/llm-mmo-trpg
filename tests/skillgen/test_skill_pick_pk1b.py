"""PK-1b：挑選模式的修正——手上技能不進候選、手寫技能上限、同元素補抽、細分打分、怪條件扣分。

固定種子（不用 hypothesis 跑候選池；PK-1 的教訓）。"""

from __future__ import annotations

from functools import cache

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.content.player_pool import player_skills
from trpg.content.skill_pick import SkillPickRules
from trpg.content.skills import SkillDef, skill_elements
from trpg.content.skills.conditions import ConditionSpec
from trpg.shared.types import Element
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import fallback_skill, fits_request, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.skill_pick import (
    ODD_FIRST_ROUND,
    ODD_INSCRIBE,
    PickCandidate,
    candidate_pool,
    design_key,
    odd_conditions,
    pick_slate,
    score_candidate,
)

KEYWORD = ProposalRequest(1, "rare", keywords=("fury",))
"""帶一般關鍵字的題目（LB 第 2 題）。"""
FAST = ProposalRequest(1, "rare", skeleton="rune")
"""不帶關鍵字、指定骨架的題目（LB 第 5 題）。"""
SEEDS = (0, 5, 12345)


@cache
def _lib() -> ContentLibrary:
    return load_library()


def _ctx(request: ProposalRequest) -> ProposalContext:
    return ProposalContext(request.tier, request.rarity, keywords=request.keywords)


def _with(rules: SkillPickRules, **pool: int) -> SkillPickRules:
    return rules.model_copy(update={"pool": rules.pool.model_copy(update=pool)})


def _fitting_pool_skills(request: ProposalRequest) -> list[SkillDef]:
    lib = _lib()
    kind = wanted_kind(lib, request)
    return [
        s
        for s in sorted(player_skills(lib).values(), key=lambda s: s.id)
        if s.tier == request.tier
        and s.rarity == request.rarity
        and fits_request(s, request, kind, lib)
    ]


def test_defaults_leave_handwritten_skills_out() -> None:
    lib = _lib()
    assert lib.skill_pick.pool.handwritten_max == 0
    for seed in SEEDS:
        pool = candidate_pool(lib, KEYWORD, _ctx(KEYWORD), seed=seed)
        assert all(c.source == "composer" for c in pool.candidates)


@pytest.mark.parametrize("seed", SEEDS)
def test_at_most_one_handwritten_skill_reaches_the_slate(seed: int) -> None:
    lib = _lib()
    rules = _with(lib.skill_pick, handwritten_max=1)
    pool = candidate_pool(lib, KEYWORD, _ctx(KEYWORD), seed=seed, rules=rules)
    assert sum(c.source == "pool" for c in pool.candidates) > 1  # 池裡不只一個，才測得到上限
    boosted = rules.model_copy(
        update={"weights": rules.weights.model_copy(update={"pool_bonus": 100_000})}
    )
    slate = pick_slate(lib, KEYWORD, _ctx(KEYWORD), seed=seed, rules=boosted)
    assert sum(c.source == "pool" for c in slate.ranked) == 1


@pytest.mark.parametrize("seed", SEEDS)
def test_held_skills_never_become_candidates(seed: int) -> None:
    """玩家手上已有的技能（同 ID、同名、同設計）絕對不進候選，手寫技能開到 1 個也一樣。"""
    lib = _lib()
    rules = _with(lib.skill_pick, handwritten_max=1)
    fitting = _fitting_pool_skills(KEYWORD)
    first = candidate_pool(lib, KEYWORD, _ctx(KEYWORD), seed=seed, rules=rules)
    composed = next(c.skill for c in first.candidates if c.source == "composer")
    held = (*fitting, composed)
    player = PickPlayer(held_skills=held)
    pool = candidate_pool(lib, KEYWORD, _ctx(KEYWORD), seed=seed, rules=rules, player=player)
    held_ids = {s.id for s in held}
    held_names = {s.name_zh for s in held}
    held_keys = {design_key(s) for s in held}
    for cand in pool.candidates:
        assert cand.skill.id not in held_ids
        assert cand.skill.name_zh not in held_names
        assert cand.key not in held_keys
    slate = pick_slate(lib, KEYWORD, _ctx(KEYWORD), seed=seed, rules=rules, player=player)
    assert all(c.skill.id not in held_ids for c in slate.ranked)


def test_empty_slate_fallback_skips_held_skills() -> None:
    lib = _lib()
    fitting = _fitting_pool_skills(KEYWORD)
    assert fitting
    ids = [s.id for s in fitting]
    skill, origin = fallback_skill(
        lib, KEYWORD, _ctx(KEYWORD), seed=1, skip_composer=True, exclude_ids=ids
    )
    assert skill.id not in ids
    assert origin == "workshop"
    plain, plain_origin = fallback_skill(lib, KEYWORD, _ctx(KEYWORD), seed=1, skip_composer=True)
    assert plain_origin == "pool" and plain.id in ids  # 預設照舊


def _elemental_player(element: Element) -> PickPlayer:
    skill = next(
        s
        for s in sorted(player_skills(_lib()).values(), key=lambda s: s.id)
        if skill_elements(s) == {element} and s.tier == 1
    )
    return PickPlayer(held_skills=(skill,))


@pytest.mark.parametrize("seed", SEEDS)
def test_element_top_up_is_deterministic_and_independent(seed: int) -> None:
    lib = _lib()
    player = _elemental_player(Element.ICE)
    rules = _with(lib.skill_pick, element_designs=6, element_seeds=60)
    off = _with(rules, element_seeds=0)
    base = candidate_pool(lib, FAST, _ctx(FAST), seed=seed, rules=off, player=player)
    first = candidate_pool(lib, FAST, _ctx(FAST), seed=seed, rules=rules, player=player)
    again = candidate_pool(lib, FAST, _ctx(FAST), seed=seed, rules=rules, player=player)
    assert first == again
    # 補抽用獨立的亂數串流：主要的候選照舊，補上的接在後面、而且都是冰霜
    assert first.candidates[: len(base.candidates)] == base.candidates
    added = first.candidates[len(base.candidates) :]
    assert all(Element.ICE in skill_elements(c.skill) for c in added)
    ice = sum(1 for c in first.candidates if Element.ICE in skill_elements(c.skill))
    assert ice >= rules.pool.element_designs or first.element_seeds == rules.pool.element_seeds
    assert first.element_seeds > 0 or ice >= rules.pool.element_designs


def test_no_top_up_without_player_elements() -> None:
    lib = _lib()
    pool = candidate_pool(lib, FAST, _ctx(FAST), seed=3, player=PickPlayer())
    assert pool.element_seeds == 0


def _find(lib: ContentLibrary, request: ProposalRequest, test: object) -> PickCandidate:
    assert callable(test)
    for seed in range(40):
        for cand in candidate_pool(lib, request, _ctx(request), seed=seed).candidates:
            if test(cand.skill):
                return cand
    raise AssertionError("找不到符合的候選")


def test_element_match_counts_held_skills_of_the_same_element() -> None:
    lib = _lib()
    w = _lib().skill_pick.weights
    cand = _find(lib, FAST, lambda s: Element.ICE in skill_elements(s))
    alone = dict(score_candidate(lib, cand, PickPlayer(), w).parts)
    assert alone["element"] == w.element_any
    ice = _elemental_player(Element.ICE)
    one = dict(score_candidate(lib, cand, ice, w).parts)
    assert one["element"] == w.element_any + w.element_match
    fire = _elemental_player(Element.FIRE)
    other = dict(score_candidate(lib, cand, fire, w).parts)
    assert other["element"] == w.element_any


def test_keyword_fit_tells_makers_from_users() -> None:
    lib = _lib()
    w = _lib().skill_pick.weights
    seen: dict[tuple[bool, bool], int] = {}
    for seed in SEEDS:
        for cand in candidate_pool(lib, KEYWORD, _ctx(KEYWORD), seed=seed).candidates:
            found = derive_keywords(cand.skill, lib.keywords, exclusive_only=True)
            role = ("fury" in found.makes, "fury" in found.uses)
            extra = sum(1 for k in found.all() if k != "fury")
            parts = dict(score_candidate(lib, cand, PickPlayer(), w, KEYWORD).parts)
            expected = (
                w.keyword_make * role[0] + w.keyword_use * role[1] - w.keyword_extra_penalty * extra
            )
            assert parts["keyword"] == expected
            seen[role] = parts["keyword"]
    assert len(seen) >= 2  # 製造、利用兩種都抽得到，分數不同


def test_theme_counts_keywords_shared_with_held_skills() -> None:
    lib = _lib()
    w = _lib().skill_pick.weights
    cand = _find(lib, KEYWORD, lambda s: len(derive_keywords(s, lib.keywords).all()) >= 2)
    other = next(
        k
        for k in derive_keywords(cand.skill, lib.keywords, exclusive_only=True).all()
        if k != "fury"
    )
    holder = next(
        s
        for s in sorted(player_skills(lib).values(), key=lambda s: s.id)
        if other in derive_keywords(s, lib.keywords, exclusive_only=True).all()
    )
    parts = dict(score_candidate(lib, cand, PickPlayer(held_skills=(holder,)), w, KEYWORD).parts)
    assert parts["theme"] >= w.theme_per_keyword


_DAMAGE = ("damage", "delayed_damage")


def _gate(skill: SkillDef, effect_type: str, condition: str) -> SkillDef:
    """把 ``effect_type`` 的效果都加上條件（只給偵測用，不驗證）。"""
    effects = [
        e.model_copy(update={"condition": ConditionSpec(type=condition)})
        if e.type == effect_type
        else e
        for e in skill.effects
    ]
    return skill.model_copy(update={"effects": effects, "condition": None})


def _has(skill: SkillDef, *types: str) -> bool:
    return any(e.type in types for e in skill.effects)


def test_odd_conditions_are_detected() -> None:
    lib = _lib()
    rune_only = _find(lib, FAST, lambda s: _has(s, "inscribe") and not _has(s, *_DAMAGE)).skill
    rune_hit = _find(lib, FAST, lambda s: _has(s, "inscribe") and _has(s, *_DAMAGE)).skill
    status = _find(lib, KEYWORD, lambda s: _has(s, "apply_status") and _has(s, *_DAMAGE)).skill
    plain = rune_only.model_copy(update={"condition": None})
    assert odd_conditions(_gate(plain, "none", "first_round")) == ()
    # 刻紋自己帶條件 → 怪；技能層級條件只在沒有傷害時才算
    assert odd_conditions(_gate(rune_hit, "inscribe", "adjacent_ally")) == (ODD_INSCRIBE,)
    top = ConditionSpec(type="adjacent_ally")
    assert odd_conditions(rune_only.model_copy(update={"condition": top})) == (ODD_INSCRIBE,)
    assert odd_conditions(rune_hit.model_copy(update={"condition": top})) == ()
    # 非傷害效果只在第一輪生效 → 怪；傷害效果在第一輪生效不算
    assert odd_conditions(_gate(status, "apply_status", "first_round")) == (ODD_FIRST_ROUND,)
    assert ODD_FIRST_ROUND not in odd_conditions(_gate(status, "damage", "first_round"))
    first = ConditionSpec(type="first_round")
    no_damage = status.model_copy(
        update={"effects": [e for e in status.effects if e.type not in _DAMAGE], "condition": first}
    )
    assert odd_conditions(no_damage) == (ODD_FIRST_ROUND,)
    assert odd_conditions(status.model_copy(update={"condition": first})) == ()


def test_odd_conditions_cost_points() -> None:
    lib = _lib()
    w = _lib().skill_pick.weights
    rune = _find(lib, FAST, lambda s: _has(s, "inscribe")).skill
    clean = _gate(rune, "none", "first_round")
    gated = _gate(rune, "inscribe", "adjacent_ally")
    a = score_candidate(
        lib, PickCandidate(clean, "composer", 1, design_key(clean)), PickPlayer(), w
    )
    b = score_candidate(
        lib, PickCandidate(gated, "composer", 1, design_key(gated)), PickPlayer(), w
    )
    assert dict(a.parts)["odd"] == 0
    assert dict(b.parts)["odd"] == -w.odd_condition_penalty
    assert b.score == a.score - w.odd_condition_penalty


def test_scores_spread_out_for_a_real_player() -> None:
    """細分打分後，前 5 名的基本分不再只有一兩種值（PK-1：幾乎只有 300 或 0）。"""
    lib = _lib()
    player = PickPlayer(
        held_skills=tuple(_fitting_pool_skills(KEYWORD)[:1])
        + _elemental_player(Element.ICE).held_skills,
        behavior={"trip": 4, "aim": 2},
    )
    slate = pick_slate(lib, KEYWORD, _ctx(KEYWORD), seed=0, player=player)
    base = {c.score - dict(c.parts)["diversity"] for c in slate.ranked}
    assert len(base) >= 3
