"""WC-2 第 3 項：被動骨架加開「自身周圍」小範圍，反應骨架維持自身、單體；被動作用在觸發的那個人時，
許願池算命中「單體」（#167，06 6.9、07 7.6 第 2 點「命中判定」）。"""

from __future__ import annotations

from typing import Any

from tests.roguelite.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.wish_pick import skill_tag_ids


def _passive(shape: dict[str, Any], target: str, affects: str) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": "skill_t_wc2_passive",
            "name_zh": "測試被動",
            "tier": 1,
            "rarity": "epic",
            "kind": "passive",
            "skeleton": "passive",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "int",
            "shape": shape,
            "effects": [{"type": "damage", "dice": "1d4", "element": "fire", "affects": affects}],
            "condition": None,
            "trigger": {"event": "on_damaged", "target": target, "max_per_round": 1},
            "cost": {"mana": 1},
        }
    )


def _codes(skill: SkillDef) -> set[str]:
    return {v.rule for v in validate_skill(skill, library())}


def test_skeletons_open_ring_for_passive_only() -> None:
    lib = library()
    passive = lib.skeletons["passive"]
    assert passive.shapes == ("self", "ring")
    assert passive.max_radius == 1
    assert lib.skeletons["reaction"].shapes == ("self", "single")  # 反應維持


def test_validator_keeps_the_ring_small_and_centred_on_the_holder() -> None:
    ring1 = _passive({"type": "ring", "radius": 1}, "self", "enemies")
    assert not {"skeleton.shape", "skeleton.radius", "passive.around"} & _codes(ring1)
    ring2 = _passive({"type": "ring", "radius": 2}, "self", "enemies")
    assert "skeleton.radius" in _codes(ring2)
    other = _passive({"type": "ring", "radius": 1}, "other", "enemies")
    assert "passive.around" in _codes(other)
    cone = _passive({"type": "cone", "size": 2}, "self", "enemies")
    assert "skeleton.shape" in _codes(cone)


def test_composer_makes_around_passives() -> None:
    lib = library()
    found: list[SkillDef] = []
    for seed in range(200):
        try:
            skill = compose_random_skill(
                seed, tier=1, rarity="epic", library=lib, kinds=("passive",)
            )
        except ComposeError:
            continue
        if skill.shape.type == "ring":
            found.append(skill)
    assert found
    for skill in found:
        assert not validate_skill(skill, lib)
        assert skill.shape.radius == 1
        assert skill.trigger is not None and skill.trigger.target == "self"
        assert all(e.affects == "enemies" for e in skill.effects)
        assert skill_tag_ids(lib, skill).shapes == ("around",)


def test_passive_on_the_triggering_unit_counts_as_single() -> None:
    lib = library()
    on_other = _passive({"type": "self"}, "other", "enemies")
    assert skill_tag_ids(lib, on_other).shapes == ("single",)
    on_self = SkillDef.model_validate(
        {
            **_passive({"type": "self"}, "self", "self").model_dump(mode="json"),
            "effects": [{"type": "heal", "dice": "1d4", "affects": "self"}],
        }
    )
    assert skill_tag_ids(lib, on_self).shapes == ("around",)
