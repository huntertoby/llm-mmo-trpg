"""代表性 build、標準隊友與分階標準敵人（Phase 2C-3 5.3、5.5、5.6-4、5.6-7）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.engine.helpers import library
from trpg.content.library import load_library
from trpg.content.sim_builds import BuildDef, BuildTable
from trpg.shared.errors import ContentError
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

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
)


def test_builds_file_loads_with_twenty_two_builds_and_two_companions() -> None:
    lib = library()
    assert tuple(b.id for b in lib.builds.builds) == BUILD_IDS
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
        assert validate_skill(skill, lib) == []
        assert skill_budget(skill, lib).ok
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
            "skill_blink, skill_parting_slash", "skill_grapple_arrow, skill_parting_slash", 1
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
    budget = lib.ruleset.core.tier_budget
    bandit = lib.unit("bandit")
    for tier in range(1, 6):
        enemy = lib.unit(f"std_enemy_t{tier}")
        expected = (30 * budget[tier] * 2 + budget[1]) // (2 * budget[1])  # 四捨五入
        assert enemy.max_hp == expected, tier
        assert enemy.skills == () and enemy.ai_profile == "brute" and "sim" in enemy.tags
        assert enemy.attributes == bandit.attributes
        assert (enemy.armor_bonus, enemy.weapon, enemy.resist) == (
            bandit.armor_bonus,
            bandit.weapon,
            bandit.resist,
        )
    assert [lib.unit(f"std_enemy_t{t}").max_hp for t in range(1, 6)] == [30, 39, 49, 62, 77]
