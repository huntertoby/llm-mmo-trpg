"""Phase 3-54d：LLM 提議有「技能元素」欄位，大地限制與驗證器同源（不需要網路與模型）。"""

from __future__ import annotations

import copy
import json
from typing import Any

from tests.engine.helpers import library
from trpg.skillgen.proposal import (
    ProposalContext,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)

LIB = library()


def _quake(**changes: Any) -> dict[str, Any]:
    skill = LIB.skills["skill_quake_wave"]
    data = copy.deepcopy(proposal_from_skill(skill, LIB))
    data.update(changes)
    return data


def _problems(data: dict[str, Any]) -> list[str]:
    skill = LIB.skills["skill_quake_wave"]
    models = build_proposal_models(LIB)
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity)
    result = evaluate_proposal(data, models, LIB, ctx)
    return [f"{e.stage}:{e.code}:{e.message}" for e in result.errors]


def test_the_proposal_schema_has_an_optional_element() -> None:
    schema = json.dumps(build_proposal_models(LIB).json_schema(), ensure_ascii=False)
    assert '"element"' in schema
    assert _quake()["element"] == "earth"


def test_an_earth_proposal_with_a_shockwave_passes_the_earth_rule() -> None:
    assert not [p for p in _problems(_quake()) if "terrain_needs_earth" in p]


def test_the_same_proposal_without_the_earth_element_is_rejected() -> None:
    variants: list[dict[str, Any]] = [
        {"element": "fire", "tags": ["spell", "area"]},
        {"element": None, "tags": []},
    ]
    for changes in variants:
        data = _quake(**changes)
        if data.get("element") is None:
            data.pop("element")
        found = _problems(data)
        assert [p for p in found if "terrain_needs_earth" in p or "大地" in p], found
