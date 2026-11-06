"""主題合併（R2）。

原 ``test_composer_3c6b.py``：

Phase 3C-6b：組合器能產生 3C／3D 的新條件、新原語、新觸發時機、賭博型、修正技能與傳說。

原 ``test_composer_24c.py``：

隨機組合器的新原語與新條件（Phase 3-24c）：獻祭召喚物與 ``target_collided`` 都是低權重。

原 ``test_composer_traits_3t8.py``：

骨架專屬的組合器設定來自 YAML（Phase 3T-8）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.skillgen.helpers import lib
from trpg.content.skill_rules import ComposerTraits
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.composer_parts import Ctx, choose_core
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.skill_yaml import skill_to_yaml
from trpg.skillgen.validate import validate_skill

# --- 原 test_composer_3c6b.py ---


def _conditions(skill: SkillDef) -> set[str]:
    found = [skill.condition] if skill.condition is not None else []
    found += [e.condition for e in skill.effects if e.condition is not None]
    return {c.type for c in found}


def test_the_composer_uses_the_combo_conditions() -> None:
    seen: set[str] = set()
    for seed in range(300):
        seen |= _conditions(compose_random_skill(seed, rarity="epic"))
    assert {"moved_this_turn", "adjacent_ally", "first_round", "target_isolated"} <= seen


@pytest.mark.slow
def test_the_composer_uses_the_new_structural_primitives() -> None:
    library = lib()
    seen: set[str] = set()
    for seed in range(400):
        for skeleton in ("control", "aura"):
            skill = compose_random_skill(seed, rarity="epic", skeleton=skeleton)
            assert validate_skill(skill, library) == []
            seen |= {e.type for e in skill.effects}
    assert {"restore_resource", "dispel", "reveal", "delayed_damage", "steal_buff"} <= seen


def test_hand_written_only_primitives_are_never_composed() -> None:
    hand_written = {"summon", "zone", "leap", "swap", "swap_any", "teleport_target", "revive"}
    hand_written |= {"hurl_object", "topple", "charge_through", "shadowstep", "grant_skill"}
    hand_written |= {"copy_skill"}
    for seed in range(200):
        skill = compose_random_skill(seed)
        found = {e.type for e in skill.effects}
        assert found.isdisjoint(hand_written)


def test_modifier_skills_cover_many_kinds_of_change() -> None:
    kinds = {
        compose_random_skill(seed, skeleton="modifier", rarity="epic").modifiers[0].change.kind
        for seed in range(80)
    }
    assert len(kinds) >= 7


def test_legendary_composition_is_deterministic() -> None:
    first = skill_to_yaml(compose_random_skill(12, rarity="legendary"))
    assert first == skill_to_yaml(compose_random_skill(12, rarity="legendary"))


# --- 原 test_composer_24c.py ---


def _24c_conditions(skill: object) -> list[str]:
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
        kinds = _24c_conditions(skill)
        conditioned += bool(kinds)
        if "target_collided" in kinds:
            hits.append(skill)
            assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
            assert "collision" in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    assert hits and len(hits) * 5 < conditioned  # 出現過，但遠少於全部有條件的技能


# --- 原 test_composer_traits_3t8.py ---


def test_composer_traits_in_yaml() -> None:
    skeletons = lib().skeletons
    by_trait = {
        "legendary": {"aura", "modifier"},
        "explicit_only_active": {"builder_finisher", "trap", "rune", "sacrifice"},
        "hand_written_only": {"consume_status", "summon"},
    }
    for trait, expected in by_trait.items():
        assert {n for n, s in skeletons.items() if getattr(s.composer, trait)} == expected
    assert skeletons["control"].composer.core_count == "up_to_two"
    assert skeletons["displace"].composer.core_count == "second_by_chance"
    assert skeletons["trap"].composer.setup == "trap"
    assert skeletons["builder_finisher"].composer.setup == "stack"


@pytest.mark.parametrize("seed", range(20))
def test_core_count_follows_the_trait_not_the_id(seed: int) -> None:
    """控場骨架換成預設設定後，核心數量固定 1（不看骨架 ID）。"""
    library = lib()
    plain = library.skeletons["control"].model_copy(update={"composer": ComposerTraits()})
    ctx = Ctx(library, Rng(seed), plain, "legendary", 3, "spell", 1, Element.FIRE)
    assert len(choose_core(ctx)) == 1
