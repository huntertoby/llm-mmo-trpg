"""Phase 3C-6b：組合器能產生 3C／3D 的新條件、新原語、新觸發時機、賭博型、修正技能與傳說。"""

from __future__ import annotations

import pytest

from tests.skillgen.helpers import lib
from trpg.content.skills import SkillDef
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.skill_yaml import skill_to_yaml
from trpg.skillgen.validate import validate_skill


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
