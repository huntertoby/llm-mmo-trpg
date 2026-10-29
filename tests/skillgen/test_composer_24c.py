"""隨機組合器的新原語與新條件（Phase 3-24c）：獻祭召喚物與 ``target_collided`` 都是低權重。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill


def _conditions(skill: object) -> list[str]:
    from trpg.content.skills import SkillDef  # noqa: PLC0415

    assert isinstance(skill, SkillDef)
    found = [skill.condition] if skill.condition is not None else []
    found += [e.condition for e in skill.effects if e.condition is not None]
    return [c.type for c in found]


def test_composer_produces_sacrifice_with_low_weight() -> None:
    lib = library()
    found = []
    for seed in range(500):
        skill = compose_random_skill(seed, library=lib)
        if any(e.type == "sacrifice_summon" for e in skill.effects):
            found.append(skill)
            assert skill.skeleton == "sacrifice" and skill.category == "spell"
            assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
            assert "summon" in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    assert 1 <= len(found) <= 500 * 5 // 100


def test_explicit_sacrifice_skeleton_composes_valid_skills() -> None:
    lib = library()
    modes = set()
    for seed in range(40):
        # 獻祭召喚物要角色 2 階（3W-9）
        skill = compose_random_skill(seed, library=lib, skeleton="sacrifice", tier=2 + seed % 2)
        assert skill.skeleton == "sacrifice" and validate_skill(skill, lib) == [], seed
        modes.add(skill.effects[0].element is None)
    assert modes == {True, False}  # 爆炸與治療兩種都做得出來


def test_composer_can_roll_the_collided_condition_with_low_weight() -> None:
    lib = library()
    hits = []
    conditioned = 0
    for seed in range(600):
        skill = compose_random_skill(seed, library=lib)
        kinds = _conditions(skill)
        conditioned += bool(kinds)
        if "target_collided" in kinds:
            hits.append(skill)
            assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
            assert "collision" in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    assert hits and len(hits) * 5 < conditioned  # 出現過，但遠少於全部有條件的技能
