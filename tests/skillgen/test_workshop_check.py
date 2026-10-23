"""技能工坊的檢查、隨機與匯出（Phase 3F-1 驗收 2–4）：``trpg.skillgen.draft_check``。"""

from __future__ import annotations

import io
import re
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import DISPLACE, MODIFIER, STRIKE, Walk
from trpg.cli.budget import print_skill_budget
from trpg.skillgen.draft import build_skill, draft_id
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.skill_yaml import skill_from_yaml, skill_to_yaml

_RATIO = re.compile(r"比例 ＝ total ÷ 可用預算 ＝ ([0-9.]+%)")


def _draft(walk: Walk) -> dict[str, Any]:
    draft: dict[str, Any] = {}
    for _step_id, picks in walk:
        draft.update(picks)
    return draft


def _cli_ratio(skill_data: dict[str, Any]) -> str:
    out = io.StringIO()
    print_skill_budget(library(), build_skill(skill_data), out)
    match = _RATIO.search(out.getvalue())
    assert match is not None, out.getvalue()
    return match.group(1)


@pytest.mark.parametrize(
    "walk", [STRIKE, DISPLACE, MODIFIER], ids=["strike", "displace", "modifier"]
)
def test_budget_percent_matches_trpg_skills_budget(walk: Walk) -> None:
    draft = _draft(walk)
    result = check_draft(draft, library())
    assert result.legal and result.budget is not None
    assert result.budget.ratio_text == _cli_ratio(draft)
    assert 0.7 <= result.budget.ratio <= 1.0
    assert result.budget.lines and result.budget.usable > 0


@pytest.mark.parametrize(
    "skill_id", ["skill_bull_rush", "skill_fire_bolt", "skill_war_avatar", "skill_fleet_foot"]
)
def test_shipped_skills_check_like_the_cli(skill_id: str) -> None:
    lib = library()
    data = lib.skills[skill_id].model_dump(mode="json", exclude_none=True)
    result = check_draft(data, lib)
    assert result.legal, result.problems
    assert result.budget is not None and result.budget.ratio_text == _cli_ratio(data)
    assert result.skill is not None and result.skill["id"] == skill_id


def _rules(draft: dict[str, Any]) -> dict[str, str]:
    result = check_draft(draft, library())
    assert result.complete and not result.legal
    return {p.rule: p.message_zh for p in result.problems}


def test_skeleton_violation_names_the_skeleton_rule() -> None:
    draft = _draft(STRIKE) | {"shape": {"type": "cone", "size": 3}}
    rules = _rules(draft)
    assert "skeleton.shape" in rules
    assert rules["skeleton.shape"].startswith("骨架 打擊：形狀只能是 單體、單位與落點")


def test_exclusion_violation_names_the_exclusion_rule() -> None:
    draft = _draft(DISPLACE) | {
        "effects": [
            {"type": "push", "distance": 1},
            {"type": "pull", "distance": 1},
            {"type": "damage", "multiplier_permille": 600},
        ]
    }
    rules = _rules(draft)
    assert rules["exclusion.no_push_with_pull"].startswith(
        "互斥規則「推拉不並存」：同一技能不得同時有 推擊 與 拉扯"
    )


def test_minimum_rarity_violation_and_reasons() -> None:
    draft = _draft(STRIKE) | {"rarity": "common"}
    rules = _rules(draft)
    assert rules["rarity.primitive"] == "稀有度 普通 不能使用原語 擊倒（至少需要 稀有）"
    result = check_draft(draft, library())
    assert result.minimum_rarity == "rare"
    assert result.rarity_reasons == ("原語 擊倒：至少稀有",)


def test_partial_skill_reports_the_missing_steps() -> None:
    result = check_draft(_draft(STRIKE[:3]), library())
    assert not result.complete and not result.legal
    assert result.missing_steps == ("effects", "condition", "cost", "rarity")
    assert result.budget is None and result.skill is None


def test_schema_errors_are_reported_in_chinese() -> None:
    draft = _draft(STRIKE) | {
        "effects": [{"type": "damage", "dice": "2d6"}, {"type": "knock_prone"}]
    }
    result = check_draft(draft, library())
    assert not result.legal
    messages = [p.message_zh for p in result.problems if p.rule == "schema"]
    assert any("武器技的傷害骰來自武器，不可指定 dice" in m for m in messages), messages


def test_draft_id_is_stable_and_ignores_the_given_id() -> None:
    draft = _draft(STRIKE)
    assert draft_id(draft) == draft_id(dict(draft)) == draft_id({**draft, "id": "skill_x"})
    assert draft_id(draft).startswith("skill_ws_")
    assert build_skill(draft).id == draft_id(draft)


def test_random_is_deterministic_and_legal() -> None:
    lib = library()
    for seed in range(8):
        first = compose_random_skill(seed, tier=2, library=lib)
        assert first == compose_random_skill(seed, tier=2, library=lib)
        result = check_draft(first.model_dump(mode="json", exclude_none=True), lib)
        assert result.legal, (seed, result.problems)


def test_export_yaml_round_trips() -> None:
    for draft in (_draft(STRIKE), _draft(DISPLACE), _draft(MODIFIER)):
        skill = build_skill(draft)
        assert skill_from_yaml(skill_to_yaml(skill)) == skill
