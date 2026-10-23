"""新技能跟主屬性、升級三選一優先同屬性（Phase 3H-3，07 7.2）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute, top_attribute
from trpg.skillgen.candidates import CandidateRequest, generate_candidates
from trpg.skillgen.proposal import (
    ProposalContext,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.scaling import pick_scaling_attr, retarget_scaling
from trpg.skillgen.validate import validate_skill

A = Attribute


def _attrs(**kw: int) -> dict[Attribute, int]:
    return {a: kw.get(a.value, 10) for a in Attribute}


def _allowed(skill: SkillDef) -> frozenset[Attribute]:
    lib = library()
    return frozenset(lib.scaling_range(skill))


def test_top_attribute_tie_breaks_by_fixed_order() -> None:
    """並列時固定取六屬性順序（力量、敏捷、體質、智力、感知、意志）的第一個。"""
    assert top_attribute(_attrs()) is A.STR
    assert top_attribute(_attrs(wis=14, wil=14)) is A.WIS
    assert top_attribute(_attrs(int=14, wil=14, dex=14)) is A.DEX
    assert top_attribute(_attrs(str=14, wil=14), exclude=[A.STR]) is A.WIL


def test_pick_scaling_attr_respects_allowed_and_order() -> None:
    assert pick_scaling_attr({A.INT, A.WIS, A.WIL}, _attrs(wil=16)) is A.WIL
    assert pick_scaling_attr({A.INT, A.WIS}, _attrs(wil=16, wis=12, int=12)) is A.INT  # 同分取順序
    assert pick_scaling_attr({A.WIL}, _attrs(str=18), avoid=A.WIL) is None
    assert pick_scaling_attr(frozenset(), _attrs()) is None


@pytest.mark.parametrize("seed", range(40))
def test_composed_skill_follows_highest_allowed_attribute(seed: int) -> None:
    """組合器：縮放屬性＝允許範圍內主角最高的；同一個種子，亂數串流與其他內容不變。"""
    lib = library()
    base = compose_random_skill(seed, tier=1, library=lib)
    mind = _attrs(wil=16)
    follows = compose_random_skill(seed, tier=1, library=lib, hero_attributes=mind)
    assert follows.model_dump(
        exclude={"scaling_attr", "secondary_scaling_attr"}
    ) == base.model_dump(exclude={"scaling_attr", "secondary_scaling_attr"})
    allowed = _allowed(follows)
    assert follows.scaling_attr in allowed
    assert follows.scaling_attr is pick_scaling_attr(allowed, mind)
    assert follows.secondary_scaling_attr != follows.scaling_attr
    assert not validate_skill(follows, lib)


def test_highest_attribute_change_moves_new_skills() -> None:
    """最高屬性改變後，同一個種子的新技能縮放屬性跟著變（限在允許範圍內）。"""
    lib = library()
    changed = 0
    for seed in range(30):
        by_top = {
            top: compose_random_skill(
                seed, tier=1, library=lib, hero_attributes=_attrs(**{top.value: 18})
            )
            for top in (A.STR, A.DEX, A.INT, A.WIS, A.WIL)
        }
        for top, skill in by_top.items():
            if skill.category == "weapon":  # 武器技看手上武器：固定武器大類主屬性（3H-6）
                assert skill.scaling_attr is lib.skill_scaling.weapon_class_attr(skill.weapon_req)
                continue
            allowed = _allowed(skill)
            assert skill.scaling_attr is (
                top if top in allowed else min(allowed, key=list(A).index)
            )
        changed += len({s.scaling_attr for s in by_top.values()}) > 1
    assert changed > 0


def test_retarget_drops_secondary_equal_to_new_primary() -> None:
    lib = library()
    skill = next(
        compose_random_skill(s, tier=3, library=lib, rarity="epic")
        for s in range(200)
        if compose_random_skill(s, tier=3, library=lib, rarity="epic").secondary_scaling_attr
        is not None
    )
    assert skill.secondary_scaling_attr is not None
    fixed = retarget_scaling(skill, _attrs(**{skill.secondary_scaling_attr.value: 20}), lib)
    assert fixed.secondary_scaling_attr != fixed.scaling_attr


def _request(attrs: dict[Attribute, int], seed: int, held: dict[str, int]) -> CandidateRequest:
    return CandidateRequest(
        keyword_counts=held, weapon_class="focus", seed=seed, tier=1, hero_attributes=attrs
    )


@pytest.mark.parametrize("seed", range(8))
def test_candidates_prefer_same_attribute_with_one_new_direction(seed: int) -> None:
    """加深、橋接優先取最高屬性；新方向盡量取不同屬性（和加深／橋接／新方向的種類並存）。"""
    lib = library()
    held = {"ignite": 2, "marked": 1, "charged": 1}
    attrs = _attrs(int=16)
    top = top_attribute(attrs)
    found = generate_candidates(lib, _request(attrs, seed, held))
    assert [c.kind for c in found] == ["deepen", "bridge", "new"]
    assert found[0].skill.scaling_attr is top, "加深應跟主屬性"
    assert found[2].skill.scaling_attr is not top, "新方向保留給不同屬性"


def test_candidates_are_deterministic_and_unchanged_without_attributes() -> None:
    lib = library()
    held = {"ignite": 2, "marked": 1}
    plain = CandidateRequest(keyword_counts=held, weapon_class="focus", seed=5, tier=1)
    assert generate_candidates(lib, plain) == generate_candidates(lib, plain)
    with_attrs = _request(_attrs(wil=16), 5, held)
    assert generate_candidates(lib, with_attrs) == generate_candidates(lib, with_attrs)
    assert len(generate_candidates(lib, with_attrs)) == 3


@pytest.mark.parametrize("skill_id", ["skill_cleave", "skill_fire_arrow"])
def test_llm_proposal_weapon_skill_scaling_is_the_weapon_class_attribute(skill_id: str) -> None:
    """LLM 提議的武器技：縮放屬性一律是武器大類主屬性，不看主角屬性、也不看提議填的值（3H-6）。"""
    lib = library()
    original = lib.skills[skill_id]
    assert original.category == "weapon"
    _, removed = split_numbers(original.model_dump(mode="json", exclude_defaults=True), lib)
    proposal = proposal_from_skill(original, lib)
    models = build_proposal_models(lib)
    expect = lib.skill_scaling.weapon_class_attr(original.weapon_req)
    ids = set()
    for attrs in (None, _attrs(wil=18), _attrs(dex=18), _attrs(int=18)):
        ctx = ProposalContext(
            tier=original.tier, rarity=original.rarity, rank=original.rank, hero_attributes=attrs
        )
        result = evaluate_proposal(proposal, models, lib, ctx, fill=fixed_filler(removed))
        assert result.skill is not None, result.errors
        assert result.skill.scaling_attr is expect
        assert result.skill.secondary_scaling_attr is None
        assert not validate_skill(result.skill, lib)
        ids.add(result.skill.id)
    assert len(ids) == 1


def test_llm_proposal_scaling_follows_highest_attribute() -> None:
    """LLM 提議（法術技）：縮放屬性由引擎改成主角最高的允許屬性（提議的 scaling_attr 只是提議）。"""
    lib = library()
    # 聖水是組合主題（神聖傷害＋造水）：感知或智力；沒有主角屬性時取感知
    original = lib.skills["skill_holy_water"]
    _, removed = split_numbers(original.model_dump(mode="json", exclude_defaults=True), lib)
    proposal = proposal_from_skill(original, lib)
    models = build_proposal_models(lib)
    tier, rarity, rank = original.tier, original.rarity, original.rank
    plain_ctx = ProposalContext(tier=tier, rarity=rarity, rank=rank)
    plain = evaluate_proposal(proposal, models, lib, plain_ctx, fill=fixed_filler(removed))
    assert plain.skill is not None
    dex_ctx = ProposalContext(tier=tier, rarity=rarity, rank=rank, hero_attributes=_attrs(int=18))
    followed = evaluate_proposal(proposal, models, lib, dex_ctx, fill=fixed_filler(removed))
    assert followed.skill is not None
    assert followed.skill.scaling_attr is A.INT
    assert followed.skill.scaling_attr in _allowed(followed.skill)
    assert followed.skill.id != plain.skill.id  # ID 以取代後的內容雜湊
    skip = {"id", "scaling_attr"}
    assert followed.skill.model_dump(exclude=skip) == plain.skill.model_dump(exclude=skip)
