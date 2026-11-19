"""WC-2 第 4 項：吸血（``lifesteal_permille``）、聖光雙效（``split_heal``）算命中「治療」願望（#167
第 4 題；06 6.18 A、B；07 7.6 第 2 點「命中判定」）。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.skillgen.wish_pick import skill_tag_ids, tag_hits, wish_miss_zh

HEAL = WishTags(effects=("damage", "heal"))


def test_lifesteal_and_split_heal_count_as_heal() -> None:
    lib = library()
    for skill_id in ("skill_life_drain", "skill_holy_burst"):
        skill = lib.skills[skill_id]
        assert "heal" in skill_tag_ids(lib, skill).effects, skill_id
        assert tag_hits(lib, skill, HEAL) == (("傷害", "治療"), ()), skill_id
        assert wish_miss_zh(lib, skill, HEAL) is None


def test_plain_damage_is_still_not_heal() -> None:
    lib = library()
    plain = lib.skills["skill_life_drain"]
    data = plain.model_dump(mode="json")
    for effect in data["effects"]:
        effect.pop("lifesteal_permille", None)
    stripped = type(plain).model_validate(data)
    assert "heal" not in skill_tag_ids(lib, stripped).effects
    assert tag_hits(lib, stripped, HEAL)[1] == ("治療",)
