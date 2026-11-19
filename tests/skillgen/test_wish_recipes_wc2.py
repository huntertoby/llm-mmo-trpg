"""WC-2 第 5 項：補配方（#167 第 5 題）。

1. 層數關鍵字不再只有蓄力骨架（附帶配方：一般主動技＋累積／消耗層數）。
2. 召喚：效果標籤有召喚時補抽召喚骨架；召喚物關鍵字有「號令」的附帶配方（利用召喚物的主動技）。
3. 形態：許願池的候選另外放進同關鍵字的手寫形態技（07 7.6 第 2 點「形態例外」）。
4. 元素配方：換主題元素（冰霜＋範圍 0% 的原因是抽樣，見 ``composer_retheme`` 說明）。
"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.composer_retheme import retheme
from trpg.skillgen.composer_rider import COMMANDING, add_rider, rider_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.random_composer import (
    ComposeError,
    compose_random_skill,
    compose_with_stats,
)
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.wish_pick import (
    handwritten_keywords,
    handwritten_pool,
    skill_tag_ids,
    tag_hits,
    wish_pool,
)

STACKS = ("combo_point", "fury", "focus", "ki")


def _request(tier: int, seed: int) -> CandidateRequest:
    return CandidateRequest(keyword_counts={}, weapon_class="melee", seed=seed, tier=tier)


def test_rider_keywords_are_the_stacks_and_summon() -> None:
    assert rider_keywords(library()) == frozenset({*STACKS, "summon"})


def test_stack_keywords_come_out_of_other_skeletons() -> None:
    lib = library()
    for keyword in STACKS:
        skeletons: set[str] = set()
        for seed in range(30):
            try:
                skill = compose_with_stats(
                    seed, tier=2, rarity="rare", library=lib, keyword=keyword,
                    keyword_tries=30, kinds=("active", "stance"),
                ).skill  # fmt: skip
            except ComposeError:
                continue
            assert not validate_skill(skill, lib)
            assert keyword in skill_tag_ids(lib, skill).keywords
            skeletons.add(skill.skeleton)
        assert "builder_finisher" in skeletons, keyword  # 蓄力骨架照舊會出
        assert skeletons - {"builder_finisher"}, keyword  # 也有別的骨架


def test_summon_rider_is_a_commanding_active() -> None:
    lib = library()
    made = None
    for seed in range(100):
        try:
            base = compose_random_skill(seed, tier=2, rarity="rare", library=lib, kinds=("active",))
        except ComposeError:
            continue
        made = add_rider(lib, base, "summon", Rng(seed))
        if made is not None:
            break
    assert made is not None
    assert not validate_skill(made, lib)
    assert any(e.status == COMMANDING and e.affects == "self" for e in made.effects)
    assert "summon" in skill_tag_ids(lib, made).keywords


def test_summon_effect_wish_gets_summon_candidates() -> None:
    lib = library()
    tags = WishTags(effects=("summon",))
    hits = 0
    for seed in range(3):
        slate = wish_pool(lib, _request(2, seed), tags, PickPlayer())
        hits += sum(1 for c in slate.ranked if not tag_hits(lib, c.skill, tags)[1])
    assert hits > 0


def test_form_wish_takes_handwritten_form_skills() -> None:
    lib = library()
    assert handwritten_keywords(lib) == frozenset({"form"})
    pool = handwritten_pool(lib, "form", 1)
    assert pool and all("form" in skill_tag_ids(lib, s).keywords for s in pool)
    slate = wish_pool(lib, _request(1, 5), WishTags(keywords=("form",)), PickPlayer())
    assert slate.ranked
    assert all("form" in skill_tag_ids(lib, c.skill).keywords for c in slate.ranked)
    assert {c.skill.id for c in slate.ranked} <= {s.id for s in pool}


def test_retheme_keeps_the_structure() -> None:
    lib = library()
    done = 0
    for seed in range(60):
        try:
            skill = compose_random_skill(seed, tier=2, rarity="rare", library=lib)
        except ComposeError:
            continue
        made = retheme(lib, skill, "ice")
        if made is None:
            continue
        done += 1
        assert not validate_skill(made, lib)
        assert skill_tag_ids(lib, made).elements == ("ice",)
        assert made.shape == skill.shape
        assert [e.type for e in made.effects] == [e.type for e in skill.effects]
    assert done > 10


def test_ice_area_wish_finds_ice_area_candidates() -> None:
    """冰霜＋範圍（WC-1 0%）：許願池換主題元素後做得到。"""
    lib = library()
    tags = WishTags(elements=("ice",), shapes=("area",))
    hits = 0
    for seed in range(8):  # 範圍形狀本來就少，多看幾次許願
        request = CandidateRequest(keyword_counts={}, weapon_class="focus", seed=seed, tier=2)
        slate = wish_pool(lib, request, tags, PickPlayer())
        hits += sum(1 for c in slate.ranked if not tag_hits(lib, c.skill, tags)[1])
    assert hits > 0
