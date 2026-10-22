"""關鍵字池的真實利用者與不限武器的 1 階技能（Phase 3-24c，``docs/design/06-技能.md`` 6.27.2）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.skillgen.test_keywords import _skill
from trpg.skillgen.keywords import derive_keywords, is_starter_skill
from trpg.skillgen.validate import validate_skill

NEW_SKILLS = (
    "bone_pursuit",
    "shock_follow",
    "soul_burst",
    "spirit_offering",
    "scorching_slash",
    "flare_shot",
    "kindle_pop",
    "icebreaker",
    "frost_snap",
    "thaw_blast",
    "spark_chain",
    "thunder_clap",
    "splash_flask",
    "frost_touch",
    "mark_prey",
)


def _exclusive_users(keyword: str, *, starter: bool) -> list[str]:
    lib = library()
    return [
        sid
        for sid, skill in sorted(lib.skills.items())
        if skill.kind == "active"
        and (not starter or is_starter_skill(skill))
        and keyword in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    ]


@pytest.mark.parametrize(
    ("keyword", "minimum"),
    [("ignite", 3), ("frozen", 3), ("charged", 3), ("collision", 2), ("summon", 1)],
)
def test_pools_have_enough_active_exploiters_under_exclusive_rules(
    keyword: str, minimum: int
) -> None:
    """專屬規則下，起始等級（1 階普通或稀有）的主動利用者數量。"""
    assert len(_exclusive_users(keyword, starter=True)) >= minimum


@pytest.mark.parametrize("name", NEW_SKILLS)
def test_every_new_skill_passes_validation_and_budget(name: str) -> None:
    lib = library()
    skill = lib.skills[f"skill_{name}"]
    assert validate_skill(skill, lib) == []
    assert skill.tier == 1 and skill.kind == "active" and is_starter_skill(skill)
    assert derive_keywords(skill, lib.keywords, exclusive_only=True).all()  # 專屬規則就有關鍵字


def test_taunting_roar_applies_marked() -> None:
    lib = library()
    roar = lib.skills["skill_taunting_roar"]
    assert any(e.type == "apply_status" and e.status == "marked" for e in roar.effects)
    assert validate_skill(roar, lib) == []
    assert "marked" in derive_keywords(roar, lib.keywords, exclusive_only=True).makes


@pytest.mark.parametrize("keyword", ["wet", "frozen", "marked"])
def test_any_weapon_starter_makes_wet_frozen_and_marked(keyword: str) -> None:
    lib = library()
    found = [
        s.id
        for s in lib.skills.values()
        if is_starter_skill(s)
        and s.weapon_req == "any"
        and keyword in derive_keywords(s, lib.keywords, exclusive_only=True).makes
    ]
    assert found, keyword


def test_sacrifice_belongs_to_the_summon_pool_and_target_collided_to_collision() -> None:
    lib = library()
    kw = derive_keywords(lib.skills["skill_soul_burst"], lib.keywords, exclusive_only=True)
    assert kw.uses == ("summon",)
    kw2 = derive_keywords(lib.skills["skill_bone_pursuit"], lib.keywords, exclusive_only=True)
    assert kw2.uses == ("collision",)


def test_new_keyword_descriptions_follow_the_gameplay_wording() -> None:
    table = {k.id: k.description_zh for k in library().keywords.keywords}
    assert "連鎖" in table["charged"] and "靜電" in table["charged"]
    assert "獻祭" in table["summon"]
    assert "近戰" in table["prone"]


def test_the_keywordless_message_lists_all_ten_keywords() -> None:
    lib = library()
    plain = _skill(
        id="skill_t_plain",
        cost={"mana": 6},
        effects=[{"type": "damage", "dice": "2d6", "element": "physical"}],
    )
    (problem,) = [p for p in validate_skill(plain, lib) if p.rule == "keyword.required"]
    assert "這招還沒有接上任何關鍵字，無法和其他技能協同。" in problem.message
    assert "附加燃燒、對倒地目標加傷" in problem.message
    assert len(lib.keywords.keywords) == 10
    for keyword in lib.keywords.keywords:
        assert keyword.name_zh in problem.message
