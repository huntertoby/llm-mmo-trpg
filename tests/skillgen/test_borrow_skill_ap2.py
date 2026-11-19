"""基本款預支技能（AP-2 第 2 項，06 6.3「預支」）：0 AP、冷卻 2、自身、只給自己；通用池（沒有
關鍵字）、稀有、1 階、不限武器；閃現大變化 +2／−2 每場 1 次；許願「增益＋自身」出得來；
只有精英、頭目能帶。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.library.ruleset import skill_reference_problems
from trpg.content.library.unit_checks import borrow_carrier_problems
from trpg.content.skill_pick import WishTags
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.flash_major import apply_extra, extra_variations
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.wish_pick import tag_hits, wish_pool

BORROW = "skill_borrowed_beat"


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return library()


def test_the_basic_borrow_skill(lib: ContentLibrary) -> None:
    skill = lib.skills[BORROW]
    assert skill.kind == "active" and skill.ap_cost == 0
    assert skill.cost.cooldown == 2
    assert skill.cost.mana == 0 and skill.cost.stamina == 0  # AP-2b：預支不受最低花費限制
    assert skill.shape.type == "self"
    assert [(e.type, e.amount) for e in skill.effects] == [("borrow_ap", 1)]
    assert skill.rarity == "rare" and skill.tier == 1
    assert skill.weapon_req == "any"
    assert not derive_keywords(skill, lib.keywords).all()  # 通用池：沒有關鍵字
    assert validate_skill(skill, lib) == []
    report = skill_budget(skill, lib)
    assert report.total == 0 and report.ok


def test_the_flash_major_borrows_two_once_per_battle(lib: ContentLibrary) -> None:
    skill = lib.skills[BORROW]
    found = [
        v
        for v in extra_variations(lib, skill, "deepen", support=False)
        if v.template == "borrow_deep"
    ]
    assert len(found) == 1
    done = apply_extra(lib, skill, found[0], Rng(1))
    assert done is not None
    assert [(e.type, e.amount) for e in done.effects] == [("borrow_ap", 2)]
    assert done.cost.uses_per_battle == 1
    assert done.ap_cost == 0


def test_other_skills_do_not_get_the_borrow_major(lib: ContentLibrary) -> None:
    other = lib.skills["skill_vigil_call"]
    assert all(
        v.template != "borrow_deep" for v in extra_variations(lib, other, "deepen", support=True)
    )


def test_only_elites_and_bosses_may_carry_borrow(lib: ContentLibrary) -> None:
    plain = lib.units["bandit"].model_copy(update={"skills": (BORROW,)})
    assert borrow_carrier_problems("bandit", plain, lib.skills)
    elite = lib.units["bandit_captain"].model_copy(update={"skills": (BORROW,)})
    assert borrow_carrier_problems("bandit_captain", elite, lib.skills) == []


def test_a_buff_self_wish_offers_the_borrow_skill(lib: ContentLibrary) -> None:
    request = CandidateRequest(keyword_counts={}, weapon_class="melee", seed=3, tier=1)
    tags = WishTags(effects=("buff",), shapes=("around",))
    slate = wish_pool(lib, request, tags, PickPlayer())
    picked = [c for c in slate.ranked if c.skill.id == BORROW]
    assert picked
    hits, _ = tag_hits(lib, picked[0].skill, tags)
    assert set(hits) >= {"增益", "自身周圍"}


def test_other_wishes_do_not_add_the_borrow_skill(lib: ContentLibrary) -> None:
    request = CandidateRequest(keyword_counts={}, weapon_class="melee", seed=3, tier=1)
    slate = wish_pool(lib, request, WishTags(effects=("buff",)), PickPlayer())
    assert all(c.skill.id != BORROW for c in slate.ranked)


def test_skills_cannot_apply_the_borrow_penalty_status(lib: ContentLibrary) -> None:
    """``borrowed_ap`` 只由預支施加（mechanic_only）：技能引用它＝引用錯誤。"""
    base = lib.skills["skill_vigil_call"].model_dump(mode="json", exclude_none=True)
    base["effects"] = [{"type": "apply_status", "status": "borrowed_ap", "affects": "allies"}]
    skill = SkillDef.model_validate(base)
    problems = skill_reference_problems(skill, lib.ruleset, lib.skills)
    assert any("mechanic_only" in p for p in problems)
