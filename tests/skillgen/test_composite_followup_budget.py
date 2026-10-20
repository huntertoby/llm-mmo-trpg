"""Phase 3F-4a：四種即時第二段的預算與元素連鎖規則（``docs/phases/Phase3F計畫.md`` 4.1、4.3）。

- ``after_action``、``after_gather``：（第一段 ＋ 第二段）× 1.15（同基本型）；
- ``on_kill``、``on_hit``：（第一段 ＋ 第二段 × 觸發機率）× 1.15，觸發機率沿用既有係數
  （``on_kill_expected_permille``、``modifier.hit_rate_permille``）；
- 兩段之間有元素／表面連鎖時再 ×（1000 ＋ ``composite_self_combo_permille``）÷ 1000（初值 1000‰）。
"""

from __future__ import annotations

import io
from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.engine.test_composite_followups import CONE, HIT, SINGLE, kind_data
from trpg.cli.budget import print_skill_budget
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import BudgetReport, skill_budget
from trpg.skillgen.combo import self_combo_reasons
from trpg.skillgen.draft_check import check_draft

LABELS = {
    "skill_retreating_slash": ("動作段", "位移段", 1000),
    "skill_gravity_burst": ("聚集段", "打擊段", 1000),
    "skill_death_spiral": ("第一段", "擊殺後的第二段", 300),
    "skill_armor_break_combo": ("第一段", "命中後的第二段", 600),
}


def _parts(skill: SkillDef) -> tuple[BudgetReport, BudgetReport, BudgetReport]:
    lib = library()
    follow = skill.followup_skill()
    assert follow is not None
    return (
        skill_budget(skill, lib),
        skill_budget(skill.move_segment(), lib),
        skill_budget(follow, lib),
    )


@pytest.mark.parametrize("skill_id", sorted(LABELS))
def test_the_total_is_first_plus_second_times_the_chance_plus_15_percent(skill_id: str) -> None:
    first_label, second_label, chance = LABELS[skill_id]
    report, first, second = _parts(library().skills[skill_id])
    expected = (first.total + second.total * Fraction(chance, 1000)) * Fraction(115, 100)
    assert report.total == expected
    assert [s.label for s in report.segments] == [first_label, second_label]
    assert [s.chance_permille for s in report.segments] == [1000, chance]
    assert report.self_combo_permille == 0 and report.self_combo_reasons == ()
    assert report.usable == first.usable


def test_the_chances_come_from_the_existing_coefficients() -> None:
    budget = library().budget
    assert budget.on_kill_expected_permille == LABELS["skill_death_spiral"][2]
    assert budget.modifier.hit_rate_permille == LABELS["skill_armor_break_combo"][2]
    assert budget.composite_self_combo_permille == 1000


def _oil_then(element: str, *, status: str | None = None) -> SkillDef:
    """命中 → 加碼段：第一段打一下並在腳下造油（或施加狀態），第二段是 ``element`` 元素的錐形。"""
    extra: dict[str, Any] = (
        {"type": "create_surface", "surface": "oil", "duration": 2}
        if status is None
        else {"type": "apply_status", "status": status, "duration": 1}
    )
    second = {"type": "damage", "multiplier_permille": 1000, "element": element}
    return SkillDef.model_validate(
        kind_data("on_hit", [HIT, extra], SINGLE, ("area", CONE, [second]), skeleton="strike")
    )


def test_oil_then_fire_doubles_the_points() -> None:
    skill = _oil_then("fire")
    reasons = self_combo_reasons(skill, library())
    assert reasons and "oil" in reasons[0] and "fire_ignites_oil" in reasons[0]
    report, first, second = _parts(skill)
    plain = (first.total + second.total * Fraction(600, 1000)) * Fraction(115, 100)
    assert report.self_combo_permille == 1000
    assert report.total == plain * 2
    assert report.self_combo_reasons == reasons


def test_a_status_the_second_element_removes_is_a_combo() -> None:
    reasons = self_combo_reasons(_oil_then("fire", status="frozen"), library())
    assert reasons == ("第一段施加的狀態 frozen 會被第二段的 fire 元素解除",)


def test_no_combo_without_an_interaction() -> None:
    assert self_combo_reasons(_oil_then("ice"), library()) == ()
    assert self_combo_reasons(_oil_then("fire", status="slow"), library()) == ()
    for skill_id in (*LABELS, "skill_shadow_whirl", "skill_leap_slam"):
        assert self_combo_reasons(library().skills[skill_id], library()) == ()


def test_the_cli_budget_shows_the_chance_and_the_combo() -> None:
    lib = library()
    out = io.StringIO()
    assert print_skill_budget(lib, lib.skills["skill_death_spiral"], out) == 0
    text = out.getvalue()
    assert "【第一段】骨架 strike  形狀 single" in text
    assert "【擊殺後的第二段】骨架 strike  形狀 single" in text
    assert "× 觸發機率 300‰" in text and "→ 合格" in text
    out = io.StringIO()
    print_skill_budget(lib, _oil_then("fire"), out)
    text = out.getvalue()
    assert "× 觸發機率 600‰" in text and "連鎖加價 1000" in text
    assert "連鎖：第一段產生的表面 oil" in text


def test_the_workshop_check_lists_the_chance_and_the_combo() -> None:
    lib = library()
    data = lib.skills["skill_armor_break_combo"].model_dump(mode="json", exclude_none=True)
    result = check_draft(data, lib)
    assert result.legal, result.problems
    assert result.budget is not None
    assert [s.chance_permille for s in result.budget.segments] == [1000, 600]
    assert result.minimum_rarity == "rare"
    combo = check_draft(_oil_then("fire").model_dump(mode="json", exclude_none=True), lib)
    assert combo.budget is not None and combo.budget.self_combo_permille == 1000
    assert combo.budget.self_combo_reasons
