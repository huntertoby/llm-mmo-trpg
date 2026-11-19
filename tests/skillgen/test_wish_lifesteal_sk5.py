"""SK-5 第 2 項：許願「傷害＋治療」補做吸血版本（玩法交接 4.1.34 第 10 點 SK-4 後補；07 7.6 第 2 點
「照標籤專門做候選」）。只許「治療」時不做。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.shared.rng import Rng
from trpg.skillgen import wish_pick
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.composer_lifesteal import add_lifesteal, lifesteal_ready
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.skill_pick import design_key
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.wish_pick import tag_hits, wish_pool

DAMAGE_HEAL = WishTags(effects=("damage", "heal"))


def _request(seed: int, weapon: str = "melee", tier: int = 1) -> CandidateRequest:
    return CandidateRequest(keyword_counts={}, weapon_class=weapon, seed=seed, tier=tier)


def _has_lifesteal(skill: object) -> bool:
    return any(e.lifesteal_permille for e in skill.effects)  # type: ignore[attr-defined]


def test_add_lifesteal_keeps_the_structure_and_validates() -> None:
    lib = library()
    amount = lib.composer.structure.lifesteal_amount_permille
    done = skipped = 0
    for seed in range(80):
        try:
            skill = compose_random_skill(seed, tier=2, library=lib, kinds=("active",))
        except ComposeError:
            continue
        made = add_lifesteal(lib, skill, Rng(seed))
        if not lifesteal_ready(lib, skill):
            assert made is None
            skipped += 1
            continue
        if made is None:  # 重調後進不了預算窗
            continue
        done += 1
        assert not validate_skill(made, lib)
        assert made.skeleton in lib.composer.structure.lifesteal_skeletons
        assert [e.type for e in made.effects] == [e.type for e in skill.effects]
        assert [e.lifesteal_permille for e in made.effects if e.lifesteal_permille] == [amount]
        assert not tag_hits(lib, made, DAMAGE_HEAL)[1]
    assert done > 5
    assert skipped > 5


def test_damage_heal_wish_gets_lifesteal_candidates() -> None:
    lib = library()
    for weapon in ("melee", "focus"):
        for seed in range(3):
            slate = wish_pool(lib, _request(seed, weapon), DAMAGE_HEAL, PickPlayer())
            full = [c for c in slate.ranked if not tag_hits(lib, c.skill, DAMAGE_HEAL)[1]]
            assert any(_has_lifesteal(c.skill) for c in full), (weapon, seed)


def test_the_pool_is_deterministic() -> None:
    lib = library()
    first = wish_pool(lib, _request(4), DAMAGE_HEAL, PickPlayer())
    again = wish_pool(lib, _request(4), DAMAGE_HEAL, PickPlayer())
    assert [design_key(c.skill) for c in first.ranked] == [
        design_key(c.skill) for c in again.ranked
    ]


@pytest.mark.parametrize(
    "tags",
    [
        WishTags(effects=("heal",)),
        WishTags(effects=("damage",)),
        WishTags(effects=("damage", "heal"), kinds=("passive",)),
    ],
)
def test_no_lifesteal_versions_without_both_tags(
    tags: WishTags, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def spy(*args: object, **kwargs: object) -> None:
        calls.append("called")

    monkeypatch.setattr(wish_pick, "add_lifesteal", spy)
    wish_pool(library(), _request(2), tags, PickPlayer())
    assert calls == []
