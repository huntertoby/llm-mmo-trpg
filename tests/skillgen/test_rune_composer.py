"""隨機組合器與刻印（Phase 3-23）：低權重地產生 ``inscribe`` 技能，種子 0–49 仍然合法。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill


def test_seeds_0_to_49_stay_valid() -> None:
    lib = library()
    for seed in range(50):
        skill = compose_random_skill(seed, library=lib)
        assert validate_skill(skill, lib) == [], seed
        assert skill_budget(skill, lib).ok, seed


def test_composer_produces_inscribe_with_low_weight() -> None:
    lib = library()
    found = []
    for seed in range(400):
        skill = compose_random_skill(seed, library=lib)
        if any(e.type == "inscribe" for e in skill.effects):
            found.append(skill)
            assert skill.skeleton == "rune" and skill.kind == "active"
            assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
            (rune,) = [e for e in skill.effects if e.type == "inscribe"]
            assert (rune.element is None) != (rune.tag is None)
    assert 1 <= len(found) <= 400 * 5 // 100  # 低權重：400 個種子裡至少出現一次、不超過 5%


def test_explicit_rune_skeleton_composes_valid_skills() -> None:
    lib = library()
    for seed in range(20):
        skill = compose_random_skill(seed, library=lib, skeleton="rune")
        assert skill.skeleton == "rune"
        assert validate_skill(skill, lib) == [], seed
        assert not any(e.type == "detonate_runes" for e in skill.effects)  # 消耗型只給手寫技能
