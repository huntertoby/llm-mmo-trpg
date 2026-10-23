"""技能縮放屬性的允許範圍（Phase 3H-1，06 6.10、07 7.2）：規則是資料，內建技能逐招檢查。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from tests.engine.helpers import library
from trpg.content.skill_scaling import (
    ScalingFacts,
    SkillScalingRules,
    scaling_problems,
    weapon_attrs,
    weapon_class_mismatches,
)
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute

LIB = library()
RULES = LIB.skill_scaling
BUILTIN = sorted(LIB.skills.values(), key=lambda s: s.id)


@pytest.mark.parametrize("skill", BUILTIN, ids=lambda s: s.id)
def test_every_builtin_skill_scales_with_an_allowed_attribute(skill: SkillDef) -> None:
    """表格測試（3H-7）：主題改由效果推導後，內建 217 招推導出的允許範圍仍包含現值。"""
    allowed = LIB.scaling_range(skill)
    assert skill.scaling_attr in allowed, (skill.id, skill.scaling_attr, allowed)
    if skill.secondary_scaling_attr is not None:
        assert skill.secondary_scaling_attr in allowed, skill.id
        assert skill.category == "spell", skill.id  # 武器技不帶第二屬性


def test_the_builtin_table_covers_every_skill() -> None:
    assert len(BUILTIN) == 217
    sources = {LIB.scaling_basis(s).source for s in BUILTIN if s.category == "spell"}
    assert sources == {"effect", "tags", "override", "body"}


def test_the_library_check_reports_no_problem() -> None:
    assert scaling_problems(RULES, LIB.skills, LIB.weapons, LIB.summon_elements()) == []


def test_builtin_weapon_skill_hints_match_their_weapon_class() -> None:
    """3H-7（3H-6 待決 #3）：7 招近戰武器技的提示屬性改成武器大類主屬性，不再有不一致的招。"""
    assert weapon_class_mismatches(RULES, LIB.skills) == []


def test_weapon_skills_follow_the_weapons_of_their_class() -> None:
    melee = weapon_attrs("melee", LIB.weapons)
    assert {Attribute.STR, Attribute.DEX, Attribute.CON} <= melee  # 劍、匕首、錘
    assert weapon_attrs("ranged", LIB.weapons) == {Attribute.DEX}
    assert Attribute.WIL not in melee  # 召喚物專用武器不算
    weapon_skills = [s for s in BUILTIN if s.category == "weapon"]
    assert weapon_skills
    for skill in weapon_skills:
        assert skill.scaling_attr in weapon_attrs(skill.weapon_req, LIB.weapons), skill.id


def test_spell_themes_split_into_the_three_mind_attributes() -> None:
    by_attr: dict[Attribute, list[str]] = {}
    summons = LIB.summon_elements()
    for skill in BUILTIN:
        theme = RULES.spell_theme(skill, summons) if skill.category == "spell" else None
        if theme is not None and theme.attr == skill.scaling_attr:
            by_attr.setdefault(skill.scaling_attr, []).append(skill.id)
    assert set(by_attr) == {Attribute.INT, Attribute.WIS, Attribute.WIL}
    wil = set(by_attr[Attribute.WIL])
    # 召喚、獻祭、暗影都在意志底下
    for sid in (
        "skill_summon_spirit",
        "skill_raise_skeleton",
        "skill_summon_golem",
        "skill_soul_burst",
        "skill_dread_gaze",
        "skill_hush",
        "skill_life_drain",
    ):
        assert sid in wil, sid
    assert len(wil) >= 30  # 玩法 PM 粗算約 31 招


def _facts(effects: Sequence[Mapping[str, object]], tags: tuple[str, ...] = ()) -> ScalingFacts:
    return ScalingFacts(
        skill_id="skill_t_scaling",
        category="spell",
        weapon_req="focus",
        tags=frozenset(tags),
        effects=tuple(effects),
    )


def _range(
    effects: Sequence[Mapping[str, object]], tags: tuple[str, ...] = ()
) -> tuple[Attribute, ...]:
    return LIB.scaling_range(_facts(effects, tags))


FIRE = {"type": "damage", "dice": "1d6", "element": "fire"}
SHADOW = {"type": "damage", "dice": "1d6", "element": "shadow"}
PHYSICAL = {"type": "damage", "dice": "1d6", "element": "physical"}
HEAL = {"type": "heal", "dice": "1d6"}
MARK = {"type": "apply_status", "status": "marked", "duration": 2}


def test_the_theme_comes_from_the_main_effect_not_the_tags() -> None:
    """玩法 PM 2026-10-24：主題由效果推導（元素、原語、狀態），依主要效果；標籤不能改主題。"""
    assert _range([FIRE]) == (Attribute.INT,)  # 工坊草稿沒有標籤也能判斷（盤點 #3）
    assert _range([FIRE], ("heal", "summon")) == (Attribute.INT,)  # 標籤改不了主題
    assert _range([HEAL], ("fire",)) == (Attribute.WIS,)
    assert _range([SHADOW]) == (Attribute.WIL,)
    # 主要效果在前，附帶效果不算
    assert _range([MARK, SHADOW]) == (Attribute.WIS,)
    assert _range([SHADOW, MARK]) == (Attribute.WIL,)
    # 沒有主題訊號的效果（拉扯、物理傷害、減速）跳過，看下一個
    assert _range([{"type": "pull", "distance": 1}, FIRE]) == (Attribute.INT,)
    assert _range([{"type": "apply_status", "status": "burning", "duration": 1}]) == (
        Attribute.INT,
    )
    consume = {"type": "consume_status", "status": "frozen", "then": [FIRE]}
    assert _range([consume]) == (Attribute.INT,)


def test_tags_only_help_when_no_effect_has_a_theme() -> None:
    assert _range([PHYSICAL], ("arcane",)) == (Attribute.INT,)
    assert _range([PHYSICAL], ("physical", "heal")) == (Attribute.STR, Attribute.DEX, Attribute.CON)
    assert _range([PHYSICAL]) == (Attribute.STR, Attribute.DEX, Attribute.CON)  # 身體類
    assert _range([], ("shadow", "mark")) == (Attribute.WIS,)  # 只看標籤時標記仍歸感知
    basis = LIB.scaling_basis(_facts([PHYSICAL], ("arcane",)))
    assert basis.source == "tags"


def test_element_combined_with_another_theme_allows_either_attribute() -> None:
    """組合主題（玩法 PM 2026-10-23，06 6.10）：主要效果同時是元素與意志／感知主題時可看其一，
    主題的屬性在前；純元素仍只看智力。"""
    sacrifice = {"type": "sacrifice_summon", "dice": "2d8", "radius": 1, "element": "fire"}
    assert _range([sacrifice]) == (Attribute.WIL, Attribute.INT)
    spirit = {"type": "summon", "unit": "summon_fire_spirit", "duration": 2}
    assert _range([spirit]) == (Attribute.WIL, Attribute.INT)  # 召喚看召喚物武器的元素
    skeleton = {"type": "summon", "unit": "summon_skeleton_warrior", "duration": 2}
    assert _range([skeleton], ("fire",)) == (Attribute.WIL,)  # 標籤不能放寬
    assert _range([FIRE, HEAL]) == (Attribute.INT,)  # 附帶的治療不算
    assert _range([], ("fire", "curse")) == (Attribute.WIL, Attribute.INT)
    assert _range([], ("water", "heal")) == (Attribute.WIS, Attribute.INT)


def test_overrides_also_apply_to_evolved_skills() -> None:
    bloodlust = LIB.skills["skill_bloodlust"]
    body = (Attribute.STR, Attribute.DEX, Attribute.CON)
    assert LIB.scaling_range(bloodlust) == body
    evolved = ScalingFacts.of_skill(bloodlust)
    for skill_id, parents in (
        ("skill_bloodlust_evo_extend", ()),
        ("skill_other", ("skill_bloodlust",)),
    ):
        facts = ScalingFacts(
            skill_id, "spell", "any", evolved.tags, evolved.effects, parents=parents
        )
        assert LIB.scaling_range(facts) == body
        assert LIB.scaling_basis(facts).source == "override"


def test_a_weapon_skill_with_a_second_attribute_is_a_problem() -> None:
    sword = next(s for s in BUILTIN if s.category == "weapon" and s.weapon_req == "melee")
    moved = {
        sword.id: sword.model_copy(
            update={"scaling_attr": Attribute.STR, "secondary_scaling_attr": Attribute.INT}
        )
    }
    problems = scaling_problems(RULES, moved, LIB.weapons, LIB.summon_elements())
    assert any("不帶第二縮放屬性" in p for p in problems), problems


def test_a_combo_with_an_unknown_theme_is_rejected() -> None:
    data = RULES.model_dump(mode="json")
    data["combos"] = [{"themes": ["elemental", "nope"], "reason_zh": "測試"}]
    with pytest.raises(ValueError, match="未知的主題"):
        SkillScalingRules.model_validate(data)


def test_an_unknown_override_skill_is_a_problem() -> None:
    bad = SkillScalingRules.model_validate(
        {
            **RULES.model_dump(mode="json"),
            "overrides": [{"skill": "skill_nope", "attrs": ["str"], "reason_zh": "x"}],
        }
    )
    assert any("skill_nope" in p for p in scaling_problems(bad, LIB.skills, LIB.weapons))


def test_a_wrong_attribute_is_reported_in_chinese() -> None:
    moved = {
        **LIB.skills,
        # 純召喚（沒有元素）不能看智力；元素之靈這類「元素＋召喚」照組合主題可以看智力
        "skill_raise_skeleton": LIB.skills["skill_raise_skeleton"].model_copy(
            update={"scaling_attr": Attribute.INT}
        ),
    }
    problems = scaling_problems(RULES, moved, LIB.weapons, LIB.summon_elements())
    assert (
        len(problems) == 1
        and "skill_raise_skeleton" in problems[0]
        and "不在允許範圍" in problems[0]
    )


def test_duplicate_themes_or_overrides_are_rejected() -> None:
    data = RULES.model_dump(mode="json")
    with pytest.raises(ValueError, match="重複"):
        SkillScalingRules.model_validate({**data, "spell_themes": [*data["spell_themes"]] * 2})


def test_the_rules_file_is_a_known_content_file() -> None:
    from trpg.content.registry import KNOWN_CONTENT_FILES  # noqa: PLC0415

    assert any(f.relative_path == "skill_scaling.yaml" for f in KNOWN_CONTENT_FILES)
