"""組合器的被動與反應技候選原語來自骨架資料（Phase 2F-2 4.1）。"""

from __future__ import annotations

import pytest

from tests.skillgen.helpers import lib
from trpg.content.skill_rules import SecondaryRules, SkeletonCore, SkeletonDef
from trpg.content.skills import SKILL_REACTION_EVENTS
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.composer_parts import (
    NON_INTERCEPT_EVENTS,
    Ctx,
    Retry,
    build_passive_effects,
    build_reaction_effects,
)


def _ctx(skeleton: SkeletonDef, seed: int, rarity: str = "legendary") -> Ctx:
    library = lib()
    return Ctx(library, Rng(seed), skeleton, rarity, 3, "spell", 1, Element.FIRE)  # type: ignore[arg-type]


def _with(skeleton_id: str, **core_and_secondary: object) -> SkeletonDef:
    base = lib().skeletons[skeleton_id]
    update: dict[str, object] = {}
    if "core" in core_and_secondary:
        update["core"] = SkeletonCore(primitives=core_and_secondary["core"])  # type: ignore[arg-type]
    if "secondary" in core_and_secondary:
        update["secondary"] = SecondaryRules(
            primitives=core_and_secondary["secondary"],  # type: ignore[arg-type]
            max_count=1,
        )
    return base.model_copy(update=update)


@pytest.mark.parametrize("seed", range(20))
def test_passive_core_candidates_follow_the_skeleton(seed: int) -> None:
    only_heal = _with("passive", core=("heal",), secondary=("heal",))
    ctx = _ctx(only_heal, seed)
    build_passive_effects(ctx, "self")
    assert [e["type"] for e in ctx.effects] == ["heal"]


def test_passive_without_any_allowed_candidate_retries() -> None:
    skeleton = _with("passive", core=("damage",))  # target self 沒有 damage 可用
    with pytest.raises(Retry):
        build_passive_effects(_ctx(skeleton, 1), "self")


@pytest.mark.parametrize("seed", range(20))
def test_reaction_candidates_follow_the_skeleton(seed: int) -> None:
    only_push = _with("reaction", core=("push", "intercept"))
    ctx = _ctx(only_push, seed)
    build_reaction_effects(ctx, "hit_by_melee")
    assert ctx.effects[0]["type"] == "push"


def test_reaction_self_branch_only_uses_skeleton_primitives() -> None:
    # 預設反應技骨架的核心沒有 heal／shield：自身增益分支不可能出現 heal／shield。
    default = lib().skeletons["reaction"]
    for seed in range(200):
        ctx = _ctx(default, seed)
        try:
            build_reaction_effects(ctx, "hit_by_attack")
        except Retry:
            continue
        assert not {"heal", "shield"} & {e["type"] for e in ctx.effects[:1]}


def test_intercept_needs_the_skeleton_to_allow_it() -> None:
    skeleton = _with("reaction", core=("damage",))
    with pytest.raises(Retry):
        build_reaction_effects(_ctx(skeleton, 1), "ally_hit_adjacent")


def test_reaction_events_have_a_single_source() -> None:
    assert set(NON_INTERCEPT_EVENTS) | {"ally_hit_adjacent"} == set(SKILL_REACTION_EVENTS)
