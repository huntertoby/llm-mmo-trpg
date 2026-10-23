"""代表性 build、標準隊友與分階標準敵人（Phase 2C-3 5.3、5.5、5.6-4、5.6-7）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.engine.helpers import library
from tests.known_budget_exceptions import RANGE_BUDGET_EXCEPTIONS, shipped_violations
from trpg.content.library import load_library
from trpg.content.sim_builds import BuildDef, BuildTable
from trpg.shared.errors import ContentError
from trpg.skillgen.budget import skill_budget

BUILD_IDS = (
    "build_push",
    "build_fire",
    "build_storm",
    "build_tank",
    "build_ranged",
    "build_assassin",
    "build_support",
    "build_healer",
    "build_warlock",
    "build_guardian",
    "build_striker",
    "build_trapper",
    "build_charger",  # Phase 3D-2
    "build_banisher",  # Phase 3D-2b
    "build_summoner",  # Phase 3D-4b
    "build_gambler",  # Phase 3D-7a
    "build_seer",  # Phase 3D-8a
    "build_bomber",  # Phase 3D-8b
    "build_winged",  # Phase 3D-8c
    "build_telekinesis",  # Phase 3C-6b
    "build_wallburn",  # Phase 3C-6b
    "build_detonator",  # Phase 3C-6b
    "build_runeweaver",  # Phase 3-23
)


def test_builds_file_loads_with_twenty_three_builds_and_two_companions() -> None:
    lib = library()
    assert tuple(b.id for b in lib.builds.sim_builds()) == BUILD_IDS
    assert lib.builds.companions == ("sim_companion_fighter", "sim_companion_archer")
    for companion in lib.builds.companions:
        template = lib.unit(companion)
        assert template.skills == () and "sim" in template.tags


@pytest.mark.parametrize("build_id", BUILD_IDS)
def test_every_build_skill_exists_and_passes_budget_validation(build_id: str) -> None:
    lib = library()
    build = lib.builds.by_id()[build_id]
    assert build.hero.id == build_id and build.hero.skills
    for skill_id in build.hero.skills:
        skill = lib.skills[skill_id]
        assert shipped_violations(skill_id, lib) == []
        assert skill_budget(skill, lib).ok or skill_id in RANGE_BUDGET_EXCEPTIONS  # 3-49
    # 武器與技能相容、欄位數量在上限內（載入時已檢查，這裡確認 build 沒有被排除在檢查之外）
    assert build_id not in lib.units


def test_a_build_with_an_incompatible_skill_is_rejected(tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(library().root, content)
    path = content / "sim" / "builds.yaml"
    text = path.read_text(encoding="utf-8")
    # 位移流是近戰武器，換入遠程技能就違反 weapon_req
    path.write_text(
        text.replace(
            "skill_charged_cleave, skill_parting_slash",
            "skill_grapple_arrow, skill_parting_slash",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match=r"grapple|遠程"):
        load_library(content)


def test_a_build_hero_id_must_match_and_ids_must_be_unique() -> None:
    lib = library()
    build = lib.builds.builds[0]
    data = build.model_dump(mode="json")
    data["hero"]["id"] = "build_other"
    with pytest.raises(ValueError, match=r"hero\.id"):
        BuildDef.model_validate(data)
    table = lib.builds.model_dump(mode="json")
    table["builds"].append(table["builds"][0])
    with pytest.raises(ValueError, match="重複"):
        BuildTable.model_validate(table)


def test_standard_enemies_follow_the_tier_budget_hp_formula() -> None:
    lib = library()
    core = lib.ruleset.core
    budget = core.tier_budget
    bandit = lib.unit("bandit")
    for tier in range(1, 6):
        enemy = lib.unit(f"std_enemy_t{tier}")
        expected = (30 * budget[tier] * 2 + budget[1]) // (2 * budget[1])  # 四捨五入
        assert core.template_max_hp(enemy) == expected, tier
        assert enemy.skills == () and enemy.ai_profile == "brute" and "sim" in enemy.tags
        assert enemy.attributes == bandit.attributes
        assert (enemy.armor_bonus, enemy.weapon, enemy.resist) == (
            bandit.armor_bonus,
            bandit.weapon,
            bandit.resist,
        )
    assert [core.template_max_hp(lib.unit(f"std_enemy_t{t}")) for t in range(1, 6)] == [
        30,
        39,
        49,
        62,
        77,
    ]


def test_blank_builds_have_no_skills_and_stay_out_of_simulations() -> None:
    """白板主角（使用者要求，2026-10-20）：戰士拿單手劍、法師拿火焰法杖，沒有任何技能；不列入模擬。"""
    lib = library()
    builds = lib.builds.by_id()
    warrior, mage = builds["build_blank_warrior"], builds["build_blank_mage"]
    assert warrior.blank and mage.blank
    assert warrior.hero.skills == () and mage.hero.skills == ()
    assert (warrior.hero.weapon, mage.hero.weapon) == ("one_handed_sword", "fire_staff")
    assert all(v == 10 for v in warrior.hero.attributes.values())
    sim_ids = {b.id for b in lib.builds.sim_builds()}
    assert "build_blank_warrior" not in sim_ids and "build_blank_mage" not in sim_ids
