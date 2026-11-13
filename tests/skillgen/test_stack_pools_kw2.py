"""KW-2（#161，06 6.27.2、6.32.1）：連擊、怒氣、專注、氣的技能池與周邊系統。

- 池子門檻：每個新關鍵字至少 3 招 1 階起始技能（手寫）、3 招主動的專屬利用者、3 個 1 階白板配方。
- 白板：每種武器大類都組得出製造者與利用者白板，而且符合白板定義。
- 隨機組合器：指定關鍵字時做得出這四種層數的累積與消耗。
- 閃現（加第二個關鍵字）：製造方＝多累積 1 層；利用方＝層數達 N 時多一段傷害。
- 開局：四個關鍵字都能選，兩招之間標出觸發關係；許願池選單出現。
- 確定性：同種子組兩次一樣（hypothesis）。
"""

from __future__ import annotations

from functools import cache

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.roguelite.start import links_between, new_keyword_run, starter_pools
from trpg.skillgen.evolution import EvolutionRequest, evolution_options
from trpg.skillgen.keywords import derive_keywords, is_starter_skill
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard, is_whiteboard
from trpg.world.wish import wish_menu

NEW = ("combo_point", "fury", "focus", "ki")
DEMOS = {
    "combo_point": ("skill_swift_stab", "skill_shadow_glide", "skill_throat_cut"),
    "fury": ("skill_blood_fury", "skill_war_cry", "skill_rage_unleashed", "skill_grit_teeth"),
    "focus": ("skill_centering", "skill_eagle_eye", "skill_heart_piercer"),
    "ki": ("skill_inch_force", "skill_breathing_qi", "skill_qigong_wave", "skill_qi_breath"),
}
"""06 6.32.1 的 14 招示範（狂暴劈砍併進怒氣爆發、內觀併進沉息癒傷：效果相同就合併，玩法 PM）。"""


@cache
def lib() -> ContentLibrary:
    return library()


def _kw(skill_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    found = derive_keywords(lib().skills[skill_id], lib().keywords, exclusive_only=True)
    return found.makes, found.uses


@pytest.mark.parametrize("keyword", NEW)
def test_each_demo_carries_its_keyword(keyword: str) -> None:
    for skill_id in DEMOS[keyword]:
        makes, uses = _kw(skill_id)
        assert keyword in makes + uses, skill_id
        assert validate_skill(lib().skills[skill_id], lib()) == [], skill_id


@pytest.mark.parametrize("keyword", NEW)
def test_each_pool_meets_the_threshold(keyword: str) -> None:
    pool = starter_pools(lib())[keyword]
    assert len(pool) >= 3, pool
    assert all(is_starter_skill(lib().skills[s]) for s in pool)
    users = [
        sid
        for sid, s in sorted(lib().skills.items())
        if s.kind == "active" and not s.enemy_only and keyword in _kw(sid)[1]
    ]
    assert len(users) >= 3, users
    recipes = [r for r in lib().composer.whiteboard.recipes("active", 1) if r.keyword == keyword]
    assert len(recipes) >= 3


@pytest.mark.parametrize("keyword", NEW)
@pytest.mark.parametrize("weapon_class", ["melee", "ranged", "focus"])
def test_whiteboards_make_and_use_the_keyword_for_every_weapon_class(
    keyword: str, weapon_class: str
) -> None:
    roles: set[str] = set()
    for seed in range(12):
        skill = compose_whiteboard(
            seed, keyword=keyword, tier=1, weapon_class=weapon_class, library=lib()
        )
        assert is_whiteboard(skill, lib(), 1), skill.id
        found = derive_keywords(skill, lib().keywords, exclusive_only=True)
        assert found.all() == (keyword,)
        roles |= {"makes"} if found.makes else {"uses"}
    assert roles == {"makes", "uses"}


@pytest.mark.parametrize("keyword", NEW)
def test_the_composer_builds_and_spends_each_stack(keyword: str) -> None:
    effects: set[str] = set()
    for seed in range(40):
        skill = compose_random_skill(seed, library=lib(), keyword=keyword)
        assert validate_skill(skill, lib()) == []
        effects |= {e.type for e in skill.effects if e.stack == keyword}
        if effects == {"add_stack", "consume_stack"}:
            return
    pytest.fail(f"{keyword}：只做出 {sorted(effects)}")


@pytest.mark.parametrize("keyword", NEW)
@pytest.mark.parametrize("side", ["makes", "uses"])
def test_flash_bridge_grafts_the_keyword(keyword: str, side: str) -> None:
    extra = (
        {"target_keywords": {keyword: 3}, "partner_makes": {keyword: 3}}
        if side == "uses"
        else {"partner_uses": {keyword: 3}}
    )
    usage = SkillUsage.model_validate({"uses": 4, "targets": 4, "distance": 8, **extra})
    request = EvolutionRequest(lib().skills["skill_cleave"], usage, {}, 7)
    bridge = evolution_options(lib(), request)[-1]
    assert bridge.keyword == keyword and not bridge.fallback
    found = derive_keywords(bridge.skill, lib().keywords, exclusive_only=True)
    assert keyword in (found.makes if side == "makes" else found.uses)


@pytest.mark.parametrize(
    ("first", "second", "weapon"),
    [
        ("combo_point", "concealed", "dagger"),
        ("fury", "prone", "one_handed_sword"),
        ("focus", "high_ground", "bow"),
        ("ki", "collision", "fire_staff"),
        ("combo_point", "ki", "one_handed_sword"),
    ],
)
def test_the_new_keywords_can_start_a_run(first: str, second: str, weapon: str) -> None:
    run = new_keyword_run(lib(), weapon, (first, second), 11)
    assert run.start is not None and run.start.keywords == (first, second)
    by_id = {s.id: s for s in run.generated_skills} | dict(lib().skills)
    a, b = (by_id[s] for s in run.hero.skills)
    assert first in derive_keywords(a, lib().keywords, exclusive_only=True).all()
    assert second in derive_keywords(b, lib().keywords, exclusive_only=True).all()
    links_between(lib(), a, b)  # 觸發關係照常算得出來（有沒有關係看抽到的招）


def test_the_wish_menu_lists_all_sixteen_keywords() -> None:
    assert wish_menu(lib()) == lib().keywords.ids()
    assert set(NEW) <= set(wish_menu(lib()))


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(min_value=0, max_value=10_000), keyword=st.sampled_from(NEW))
def test_whiteboards_are_deterministic(seed: int, keyword: str) -> None:
    one = compose_whiteboard(seed, keyword=keyword, tier=1, library=lib())
    two = compose_whiteboard(seed, keyword=keyword, tier=1, library=lib())
    assert one == two
