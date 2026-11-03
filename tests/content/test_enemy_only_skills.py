"""只給敵人的技能（``SkillDef.enemy_only``）的入口（Phase 5F-R1）：``grant_skill`` 不能給、玩家
這一邊的範本（build 英雄＝主角／影子／傭兵／劇情夥伴的底稿、開發用起始包）不能裝、
劇情技能不能標。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trpg.content.library import (
    ContentLibrary,
    _story_skill_problems,
    load_library,
    player_template_enemy_only_problems,
    skill_reference_problems,
)
from trpg.content.skills.problems import granted_skill_problems
from trpg.shared.errors import ContentError
from trpg.skillgen.validate import validate_skill

CONTENT = Path(__file__).resolve().parents[2] / "content"
ENEMY_SKILL = "skill_mist_shift"


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _copy_content(tmp_path: Path) -> Path:
    dest = tmp_path / "content"
    shutil.copytree(CONTENT, dest)
    return dest


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, path
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_fixture_skill_is_enemy_only(library: ContentLibrary) -> None:
    skill = library.skills[ENEMY_SKILL]
    assert skill.enemy_only and skill.kind == "active" and skill.rarity != "legendary"


def test_grant_skill_cannot_give_an_enemy_only_skill(library: ContentLibrary) -> None:
    gift = library.skills["skill_wing_gift"]
    effects = tuple(
        e.model_copy(update={"skill": ENEMY_SKILL}) if e.type == "grant_skill" else e
        for e in gift.effects
    )
    bad = gift.model_copy(update={"effects": effects})
    primitives = library.ruleset.primitives.by_id()
    assert not granted_skill_problems(gift, library.skills, primitives)
    problems = granted_skill_problems(bad, library.skills, primitives)
    assert any("enemy_only" in p and ENEMY_SKILL in p for p in problems)
    references = skill_reference_problems(bad, library.ruleset, library.skills)
    assert any("enemy_only" in p for p in references)
    # 技能驗證器（LLM／生成器的提議）同樣擋下
    violations = validate_skill(bad, library)
    assert any("enemy_only" in v.message for v in violations)


@pytest.mark.parametrize(
    ("relative", "old", "new", "message"),
    [
        (
            "sim/builds.yaml",
            "skills: [skill_fire_bolt,",
            f"skills: [{ENEMY_SKILL}, skill_fire_bolt,",
            f"技能 {ENEMY_SKILL} 只給敵人",
        ),
        (
            "dev_starters.yaml",
            "skills: [skill_summon_spirit, skill_fire_bolt]",
            f"skills: [{ENEMY_SKILL}, skill_fire_bolt]",
            f"技能 {ENEMY_SKILL} 只給敵人",
        ),
    ],
)
def test_loader_rejects_enemy_only_skill_on_player_side(
    tmp_path: Path, relative: str, old: str, new: str, message: str
) -> None:
    root = _copy_content(tmp_path)
    _edit(root / relative, old, new)
    with pytest.raises(ContentError, match=message):
        load_library(root)


def test_player_template_check_covers_reactions(library: ContentLibrary) -> None:
    hero = library.builds.builds[0].hero
    rules = library.ruleset.reactions.default_rules
    assert rules
    bad = hero.model_copy(
        update={"reactions": (rules[0].model_copy(update={"reaction": ENEMY_SKILL}),)}
    )
    problems = player_template_enemy_only_problems("h", bad, library.skills, library.ruleset)
    assert problems and ENEMY_SKILL in problems[0]


def test_story_skill_cannot_be_enemy_only(library: ContentLibrary) -> None:
    quests = library.world_quests.quests
    story = next(s for region in sorted(quests) for s in quests[region].story_skills)
    budget = library.budget
    assert not _story_skill_problems(story, library.ruleset, library.skills, budget)
    bad = story.model_copy(update={"enemy_only": True})
    problems = _story_skill_problems(bad, library.ruleset, library.skills, budget)
    assert any("enemy_only" in p for p in problems)
