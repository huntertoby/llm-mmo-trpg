"""技能縮放屬性的允許範圍（Phase 3H-1，06 6.10、07 7.2）：規則是資料，內建技能逐招檢查。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skill_scaling import (
    SkillScalingRules,
    scaling_problems,
    weapon_attrs,
)
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute

LIB = library()
RULES = LIB.skill_scaling
BUILTIN = sorted(LIB.skills.values(), key=lambda s: s.id)


@pytest.mark.parametrize("skill", BUILTIN, ids=lambda s: s.id)
def test_every_builtin_skill_scales_with_an_allowed_attribute(skill: SkillDef) -> None:
    allowed = RULES.allowed_attrs(skill, LIB.weapons)
    assert skill.scaling_attr in allowed, (skill.id, skill.scaling_attr, allowed)
    if skill.secondary_scaling_attr is not None:
        assert skill.secondary_scaling_attr in allowed, skill.id


def test_the_library_check_reports_no_problem() -> None:
    assert scaling_problems(RULES, LIB.skills, LIB.weapons) == []


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
    for skill in BUILTIN:
        theme = RULES.spell_theme(skill) if skill.category == "spell" else None
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


def _spell(tags: list[str], effect_type: str = "damage") -> SkillDef:
    effect: dict[str, object] = {"type": effect_type}
    if effect_type == "damage":
        effect |= {"dice": "1d4", "element": "fire"}
    base = LIB.skills["skill_fire_bolt"].model_dump(mode="json")
    base |= {"tags": tags, "effects": [effect], "id": "skill_t_scaling"}
    return SkillDef.model_construct(**{**base, "scaling_attr": Attribute.INT})


def test_the_first_matching_theme_wins() -> None:
    summon_fire = _spell(["fire", "summon"])
    theme = RULES.spell_theme(summon_fire)
    assert theme is not None and theme.attr is Attribute.WIL  # 召喚比元素先比對
    heal = _spell(["holy", "heal"])
    theme = RULES.spell_theme(heal)
    assert theme is not None and theme.attr is Attribute.WIS
    marked_shadow = _spell(["shadow", "mark"])
    theme = RULES.spell_theme(marked_shadow)
    assert theme is not None and theme.attr is Attribute.WIS  # 標記屬於偵測與標記
    assert RULES.spell_theme(_spell(["physical"])) is None  # 身體類


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
        "skill_summon_spirit": LIB.skills["skill_summon_spirit"].model_copy(
            update={"scaling_attr": Attribute.INT}
        ),
    }
    problems = scaling_problems(RULES, moved, LIB.weapons)
    assert (
        len(problems) == 1
        and "skill_summon_spirit" in problems[0]
        and "不在允許範圍" in problems[0]
    )


def test_duplicate_themes_or_overrides_are_rejected() -> None:
    data = RULES.model_dump(mode="json")
    with pytest.raises(ValueError, match="重複"):
        SkillScalingRules.model_validate({**data, "spell_themes": [*data["spell_themes"]] * 2})


def test_the_rules_file_is_a_known_content_file() -> None:
    from trpg.content.registry import KNOWN_CONTENT_FILES  # noqa: PLC0415

    assert any(f.relative_path == "skill_scaling.yaml" for f in KNOWN_CONTENT_FILES)
