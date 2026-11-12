"""LLM 生成、白板配方、工坊草稿不帶 ``icon_prop``（IP-1，06 6.36）：有就丟掉、不算錯。"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from tests.engine.helpers import library
from trpg.content.skills import SkillDef, drop_icon_prop
from trpg.skillgen.draft import build_skill
from trpg.skillgen.proposal import (
    ProposalContext,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers
from trpg.skillgen.whiteboard import compose_whiteboard


def _round_trip(proposal: dict[str, Any] | str, skill: SkillDef) -> SkillDef | None:
    lib = library()
    _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), lib)
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
    result = evaluate_proposal(
        proposal, build_proposal_models(lib), lib, ctx, fill=fixed_filler(removed)
    )
    assert result.errors == (), result.errors
    return result.skill


def test_drop_icon_prop_removes_only_that_key() -> None:
    data = {"id": "x", "icon_prop": "w:sword", "tags": ["a"]}
    assert drop_icon_prop(data) == {"id": "x", "tags": ["a"]}
    assert data["icon_prop"] == "w:sword"  # 不改原本的 dict


def test_llm_proposal_with_icon_prop_is_accepted_and_dropped() -> None:
    """LLM 的提議多帶 ``icon_prop``：不算錯（提議模型 extra=forbid 也不報），結果和沒帶時相同。"""
    skill = library().skills["skill_cleave"]
    proposal = proposal_from_skill(skill, library())
    plain = _round_trip(proposal, skill)
    for raw in ({**proposal, "icon_prop": "w:hammer"}, json.dumps({**proposal, "icon_prop": 7})):
        tainted = _round_trip(raw, skill)
        assert tainted is not None and plain is not None
        assert tainted.icon_prop is None
        assert tainted == plain


def test_few_shot_examples_never_carry_icon_prop() -> None:
    """有填 ``icon_prop`` 的手寫技能轉成提議範例時不帶它（也不因此丟 ``ValueError``）。"""
    lib = library()
    skill = lib.skills["skill_armor_breaker"]
    assert skill.icon_prop == "w:hammer"
    assert "icon_prop" not in proposal_from_skill(skill, lib)


def test_whiteboard_recipe_icon_prop_is_dropped() -> None:
    """白板配方（``skill`` 欄位是自由的 dict）帶了 ``icon_prop``：組出來的白板照樣成立、不帶它。"""
    lib = library()
    rules = lib.composer.whiteboard
    recipe = next(r for r in rules.active if r.id == "summon_skeleton")
    tainted = recipe.model_copy(update={"skill": {**recipe.skill, "icon_prop": "w:sword"}})
    active = tuple(tainted if r.id == recipe.id else r for r in rules.active)
    composer = lib.composer.model_copy(
        update={"whiteboard": rules.model_copy(update={"active": active})}
    )
    patched = dataclasses.replace(lib, composer=composer)
    board = compose_whiteboard(
        3, kind="active", tier=2, library=patched, recipe_id="summon_skeleton"
    )
    original = compose_whiteboard(
        3, kind="active", tier=2, library=lib, recipe_id="summon_skeleton"
    )
    assert board.icon_prop is None
    assert board == original


def test_workshop_draft_icon_prop_is_dropped() -> None:
    lib = library()
    draft = lib.skills["skill_cleave"].model_dump(mode="json", exclude={"id"})
    plain = build_skill(draft)
    tainted = build_skill({**draft, "icon_prop": "w:hammer"})
    assert tainted.icon_prop is None
    assert tainted == plain
    assert build_skill(draft, {"icon_prop": "w:hammer"}).icon_prop is None
