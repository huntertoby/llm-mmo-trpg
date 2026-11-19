"""WC-2 第 1 項：願望的元素上限 2 階起 2 個，組合器做得出雙元素的完整技能（#167；07 7.6 第 1 點、
06 6.34.9 第二元素 2 階開放）。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.content.skills import SkillDef, card_elements, damage_elements
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.composer_dual import add_second_element, second_element_tier
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import minimum_tier, validate_skill
from trpg.skillgen.wish_pick import (
    clean_wish_tags,
    dual_elements,
    skill_tag_ids,
    tag_hits,
    tag_limits,
    wish_pool,
    wish_tags_problem,
)

MENU = ("ignite", "frozen", "summon")
TWO = WishTags(elements=("fire", "ice"))


def _fire_skill(tier: int) -> SkillDef:
    """組合器組出的第一個火焰主動技（種子由小到大找）。"""
    lib = library()
    for seed in range(400):
        try:
            skill = compose_random_skill(seed, tier=tier, library=lib, kinds=("active",))
        except ComposeError:
            continue
        fire = {e.value for e in damage_elements(skill)} == {"fire"}
        if fire and skill.followup is None and skill.trap is None:
            return skill
    raise AssertionError("找不到火焰主動技")


def test_limit_is_one_below_the_second_element_tier() -> None:
    lib = library()
    assert second_element_tier(lib) == 2
    assert not dual_elements(lib, 1)
    assert dual_elements(lib, 2)
    assert tag_limits(lib, 1)["elements"] == 1
    assert tag_limits(lib, 2)["elements"] == 2
    assert tag_limits(lib, 3)["elements"] == 2
    assert tag_limits(lib, 2)["keywords"] == 2  # 其他類照舊


def test_problem_and_clean_follow_the_tier() -> None:
    lib = library()
    assert wish_tags_problem(lib, TWO, MENU) == "元素最多選 1 個"
    assert wish_tags_problem(lib, TWO, MENU, tier=1) == "元素最多選 1 個"
    assert wish_tags_problem(lib, TWO, MENU, tier=2) is None
    raw = {"elements": ["fire", "ice"]}
    tags, codes = clean_wish_tags(lib, raw, MENU)
    assert tags.elements == ("fire",)
    assert codes == ("wish.dropped.elements",)
    tags, codes = clean_wish_tags(lib, raw, MENU, tier=2)
    assert tags.elements == ("fire", "ice")
    assert codes == ()


def test_composer_adds_a_second_element() -> None:
    lib = library()
    skill = _fire_skill(2)
    made = add_second_element(lib, skill, "ice", Rng(7))
    assert made is not None
    assert not validate_skill(made, lib)
    assert {e.value for e in damage_elements(made)} == {"fire", "ice"}
    assert minimum_tier(made, lib) >= 2  # 第二元素要 2 階（驗證器的門檻）
    assert len(made.effects) == len(skill.effects) + 1
    assert [e.display_name for e in card_elements(made)] == ["火焰", "冰霜"]
    mine = skill_tag_ids(lib, made)
    assert set(mine.elements) == {"fire", "ice"}
    assert tag_hits(lib, made, TWO) == (("火焰", "冰霜"), ())
    # 確定性：同樣的 rng 同樣的結果
    assert add_second_element(lib, skill, "ice", Rng(7)) == made


@pytest.mark.parametrize("element", ["fire", "physical"])
def test_composer_refuses_same_or_physical(element: str) -> None:
    lib = library()
    assert add_second_element(lib, _fire_skill(2), element, Rng(1)) is None


def test_composer_refuses_below_the_tier() -> None:
    lib = library()
    assert add_second_element(lib, _fire_skill(1), "ice", Rng(1)) is None


def test_card_elements_only_for_elemental_skills() -> None:
    """技能本身沒有元素（物理）時卡片照舊不寫元素（效果自己的元素不讓它變元素技能，06 6.33）。"""
    lib = library()
    skill = _fire_skill(2)
    assert [e.value for e in card_elements(skill)] == ["fire"]
    physical = lib.skills["skill_marrow_thorn"]
    assert card_elements(physical) == ()
    assert {e.value for e in damage_elements(physical)} == {"poison"}


def _request(tier: int, seed: int) -> CandidateRequest:
    return CandidateRequest(keyword_counts={}, weapon_class="focus", seed=seed, tier=tier)


def test_wish_pool_makes_dual_candidates_from_tier_two() -> None:
    lib = library()
    hits = 0
    for seed in range(3):
        slate = wish_pool(lib, _request(2, seed), TWO, PickPlayer())
        hits += sum(1 for c in slate.ranked if not tag_hits(lib, c.skill, TWO)[1])
    assert hits > 0
    # 1 階：不做雙元素（元素上限 1，引擎也不會給兩個元素的標籤；這裡直接呼叫也不加）
    for seed in range(3):
        slate = wish_pool(lib, _request(1, seed), TWO, PickPlayer())
        assert all(len(damage_elements(c.skill)) <= 1 for c in slate.ranked)
