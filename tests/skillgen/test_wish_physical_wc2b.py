"""WC-2b 第 2 件：物理＋元素做得到（#167 補，使用者：「可以，1 階就行」；07 7.6 第 1 點）。物理
不佔元素名額，1 階也可以；一招有一段物理（武器）傷害、又有一段該元素的傷害，就算命中「物理＋該
元素」。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.composer_dual import add_second_element
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import minimum_tier, validate_skill
from trpg.skillgen.wish_pick import (
    clean_wish_tags,
    menu_limits,
    skill_tag_ids,
    tag_hits,
    wish_pool,
    wish_tags_problem,
)

FIRE_SWORD = WishTags(elements=("physical", "fire"))


def _physical_skill(tier: int) -> SkillDef:
    """組合器組出的第一個物理武器主動技（傷害沒有元素）。"""
    lib = library()
    for seed in range(400):
        try:
            skill = compose_random_skill(seed, tier=tier, library=lib, kinds=("active",))
        except ComposeError:
            continue
        mine = skill_tag_ids(lib, skill)
        plain = skill.trap is None and skill.followup is None
        if plain and mine.elements == ("physical",) and "damage" in mine.effects:
            return skill
    raise AssertionError("找不到物理主動技")


def test_physical_does_not_take_an_element_slot() -> None:
    lib = library()
    assert wish_tags_problem(lib, FIRE_SWORD, ()) is None  # 1 階
    three = WishTags(elements=("physical", "fire", "ice"))
    assert wish_tags_problem(lib, three, (), tier=1) == "元素最多選 1 個（物理另外算）"
    assert wish_tags_problem(lib, three, (), tier=2) is None
    tags, codes = clean_wish_tags(lib, {"elements": ["fire", "physical", "ice"]}, ())
    assert tags.elements == ("fire", "physical")
    assert codes == ("wish.dropped.elements",)
    assert menu_limits(lib, 1)["elements"] == 2
    assert menu_limits(lib, 2)["elements"] == 3


def test_composer_makes_a_fire_sword_at_tier_one() -> None:
    lib = library()
    skill = _physical_skill(1)
    made = add_second_element(lib, skill, "fire", Rng(3))
    assert made is not None
    assert not validate_skill(made, lib)
    assert minimum_tier(made, lib) == minimum_tier(skill, lib)  # 物理＋元素不是第二元素
    assert set(skill_tag_ids(lib, made).elements) == {"physical", "fire"}
    assert tag_hits(lib, made, FIRE_SWORD) == (("物理", "火焰"), ())


def test_elemental_skill_is_not_physical() -> None:
    """全部傷害都帶元素的技能不算物理；完全沒有傷害、也沒有元素的照舊算物理。"""
    lib = library()
    for seed in range(200):
        try:
            skill = compose_random_skill(seed, tier=1, library=lib, category="spell")
        except ComposeError:
            continue
        if any(e.type == "damage" for e in skill.effects):
            assert "physical" not in skill_tag_ids(lib, skill).elements
            break


def test_wish_pool_finds_fire_swords_at_tier_one() -> None:
    lib = library()
    hits = 0
    for seed in range(3):
        request = CandidateRequest(keyword_counts={}, weapon_class="melee", seed=seed, tier=1)
        slate = wish_pool(lib, request, FIRE_SWORD, PickPlayer())
        hits += sum(1 for c in slate.ranked if not tag_hits(lib, c.skill, FIRE_SWORD)[1])
    assert hits > 0
