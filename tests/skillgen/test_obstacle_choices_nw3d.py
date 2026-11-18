"""NW-3d（玩法 PM 交接 4.1.16）：LLM 提議與技能工坊的造牆物件，和組合器同一份候選
（:func:`~trpg.skillgen.composer_parts.obstacle_candidates`）。冷卻井、油桶都選不到；
投擲（``hurl_object``）丟場上已有的物件，照舊丟得到油桶。
"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library as shared_library
from tests.engine.test_hurl_object import HURL, O1, arena
from trpg.content.library import ContentLibrary
from trpg.engine import UseSkill, legal_actions
from trpg.skillgen.composer_parts import obstacle_candidates
from trpg.skillgen.options import draft_options
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers

BANNED = ("cooling_well", "oil_barrel")

WALL_DRAFT: dict[str, Any] = {
    "skeleton": "control",
    "name_zh": "石牆",
    "kind": "active",
    "ap_cost": 1,
    "category": "spell",
    "weapon_req": "focus",
    "scaling_attr": "int",
    "tier": 1,
    "shape": {"type": "cross", "range": 3},
    "tags": ["earth", "spell", "obstacle"],
}
"""控場骨架、法術、十字範圍（同手寫「石牆術」）：效果步驟有「產生障礙」。"""


@cache
def _cached_models() -> ProposalModels:
    return build_proposal_models(shared_library())


def _models(library: ContentLibrary) -> ProposalModels:
    assert library is shared_library()
    return _cached_models()


def _object_params(library: ContentLibrary) -> list[tuple[str, str]]:
    return sorted(
        (p.id, name)
        for p in library.ruleset.primitives.primitives
        for name, spec in p.params.items()
        if spec.type == "object"
    )


def test_only_create_obstacle_takes_an_object_param(library: ContentLibrary) -> None:
    """``object`` 型參數只有造牆一處，所以把它換成造牆候選不會波及其他原語（投擲沒有這個參數）。"""
    assert _object_params(library) == [("create_obstacle", "object")]
    hurl = library.ruleset.primitives.by_id()["hurl_object"]
    assert all(spec.type != "object" for spec in hurl.params.values())


def test_candidates_exclude_the_cooling_well_and_the_oil_barrel(library: ContentLibrary) -> None:
    objects = library.ruleset.objects.by_id()
    assert set(BANNED) <= set(objects)  # 兩個都還在內容裡（不是因為刪掉才選不到）
    candidates = obstacle_candidates(library)
    assert not set(BANNED) & set(candidates)
    assert {"earth_wall", "ice_wall", "thorn_wall"} <= set(candidates)


# ---------------------------------------------------------------------------
# LLM 提議
# ---------------------------------------------------------------------------


def _enums(schema: Any) -> list[list[str]]:
    """schema 裡所有 ``create_obstacle`` 效果的 ``object`` 列舉。"""
    found: list[list[str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict) and props.get("type", {}).get("const") == "create_obstacle":
                found.append(list(props["object"]["enum"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return found


def test_llm_schema_lists_only_the_obstacle_candidates(library: ContentLibrary) -> None:
    enums = _enums(_models(library).json_schema())
    assert len(enums) >= 2  # 一般效果與只作用在施放者的效果
    for enum in enums:
        assert enum == list(obstacle_candidates(library))
        assert not set(BANNED) & set(enum)


def _wall_proposal(library: ContentLibrary, obj: str) -> tuple[dict[str, Any], Any]:
    skill = library.skills["skill_stone_wall"]
    proposal = proposal_from_skill(skill, library)
    proposal["effects"][0]["object"] = obj
    _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), library)
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
    result = evaluate_proposal(proposal, _models(library), library, ctx, fill=fixed_filler(removed))
    return proposal, result


@pytest.mark.parametrize("obj", BANNED)
def test_llm_proposal_cannot_build_the_banned_objects(library: ContentLibrary, obj: str) -> None:
    _, result = _wall_proposal(library, obj)
    assert not result.ok
    (error,) = [e for e in result.errors if e.path == "effects[0].object"]
    assert error.stage == "proposal"
    assert obj not in (error.allowed or ())


def test_llm_proposal_still_builds_an_earth_wall(library: ContentLibrary) -> None:
    _, result = _wall_proposal(library, "earth_wall")
    assert result.ok, result.errors


# ---------------------------------------------------------------------------
# 技能工坊（後端給前端的選單＋送出時的檢查）
# ---------------------------------------------------------------------------


def _workshop_objects(library: ContentLibrary) -> list[str]:
    options = draft_options(WALL_DRAFT, library)
    for step in options.steps:
        for field in step.fields:
            for choice in field.choices:
                if choice.value == "create_obstacle":
                    (obj,) = [p for p in choice.params if p.field == "object"]
                    return [str(c.value) for c in obj.choices]
    raise AssertionError("效果步驟沒有「產生障礙」")


def test_workshop_menu_lists_only_the_obstacle_candidates(library: ContentLibrary) -> None:
    menu = _workshop_objects(library)
    assert sorted(menu) == list(obstacle_candidates(library))
    order = [o.id for o in library.ruleset.objects.objects]
    assert menu == sorted(menu, key=order.index)  # 照 objects.yaml 的順序


@pytest.mark.parametrize("obj", BANNED)
def test_workshop_rejects_the_banned_objects(library: ContentLibrary, obj: str) -> None:
    draft = {**WALL_DRAFT, "effects": [{"type": "create_obstacle", "object": obj}]}
    problems = draft_options(draft, library).problems
    assert any("物件不在可選範圍內" in p for p in problems), problems


def test_workshop_accepts_an_earth_wall(library: ContentLibrary) -> None:
    draft = {**WALL_DRAFT, "effects": [{"type": "create_obstacle", "object": "earth_wall"}]}
    assert draft_options(draft, library).problems == ()


# ---------------------------------------------------------------------------
# 投擲照舊
# ---------------------------------------------------------------------------


def test_hurling_a_field_oil_barrel_is_still_legal() -> None:
    state = arena(objects=[(1, 3, "oil_barrel")])
    hurls = [
        a
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.skill_id == HURL.id and a.target_object_id == O1
    ]
    assert hurls
