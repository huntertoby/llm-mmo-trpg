"""射程係數（Phase 3-49，玩法決定 #53）：預算器、工坊顯示、CLI 用同一個係數。"""

from __future__ import annotations

import io
from fractions import Fraction
from typing import Any

import pytest

from tests.skillgen.helpers import lib, skill
from trpg.cli.budget import print_skill_budget
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.draft_check import check_draft

CASES: list[tuple[str, dict[str, Any], Fraction, str]] = [
    ("range1", {"type": "single", "range": 1}, Fraction(85, 100), "射程 1：×0.85"),
    ("range4", {"type": "single", "range": 4}, Fraction(1), "射程 4：×1"),
    ("range10", {"type": "single", "range": 10}, Fraction(130, 100), "射程 10：×1.3"),
    ("weapon", {"type": "single", "range": "weapon"}, Fraction(1), ""),
    ("self", {"type": "self"}, Fraction(1), ""),
]


def _expected_total(shape: dict[str, Any]) -> Fraction:
    """射程 4 的同一招（係數 1.0）的 total，用來確認係數乘在 shaped 點數上。"""
    return skill_budget(skill(shape={**shape, "range": 4}), lib()).total


@pytest.mark.parametrize(("name", "shape", "coefficient", "text"), CASES, ids=[c[0] for c in CASES])
def test_budget_workshop_and_cli_use_the_same_coefficient(
    name: str, shape: dict[str, Any], coefficient: Fraction, text: str
) -> None:
    library = lib()
    s = skill(shape=shape)
    report = skill_budget(s, library)
    assert report.range_coefficient == coefficient, name
    # 工坊顯示的係數 ＝ 預算器實際用的係數
    result = check_draft(s.model_dump(mode="json", exclude_none=True), library)
    assert result.budget is not None
    assert result.budget.range_coefficient == pytest.approx(float(report.range_coefficient))
    assert result.budget.range_text == text
    # 每個作用在單位的效果都乘上它
    for line, effect in zip(result.budget.lines, report.effects, strict=True):
        assert line.range == pytest.approx(float(effect.range))
        assert effect.range == report.range_coefficient or shape["type"] == "self"
    # CLI 輸出
    out = io.StringIO()
    print_skill_budget(library, s, out)
    assert (f"  {text}（" in out.getvalue()) == (text != "")


def test_the_coefficient_multiplies_the_shaped_points() -> None:
    near = skill_budget(skill(shape={"type": "single", "range": 1}), lib())
    base = skill_budget(skill(shape={"type": "single", "range": 4}), lib())
    far = skill_budget(skill(shape={"type": "single", "range": 10}), lib())
    assert near.total == base.total * Fraction(85, 100)
    assert far.total == base.total * Fraction(130, 100)
    assert _expected_total({"type": "single"}) == base.total


def test_zero_range_and_trap_shapes_have_no_coefficient() -> None:
    cross = skill_budget(skill(shape={"type": "cross", "range": 0}), lib())
    assert cross.range_value is None and cross.range_coefficient == 1
    ranged = skill_budget(skill(shape={"type": "cross", "range": 6}), lib())
    assert ranged.range_coefficient == Fraction(110, 100)


def test_a_variant_range_delta_is_priced_on_the_form() -> None:
    library = lib()
    spear = library.skills["skill_tidal_spear"]
    report = skill_budget(spear, library)
    form = next(f for f in report.variants if f.id == "high_tide").report
    assert report.range_value is not None and form.range_value == report.range_value + 2
    assert form.range_coefficient - report.range_coefficient == Fraction(10, 100)


def test_known_budget_exceptions_are_real_and_exactly_the_out_of_range_skills() -> None:
    """已知例外清單 ＝ 內建技能中預算範圍違規的那幾個（調整技能後要從清單移除）。"""
    library = lib()
    out_of_range = {
        s.id
        for s in library.skills.values()
        if not s.id.startswith("skill_gear_") and not skill_budget(s, library).ok
    }
    assert out_of_range == set(library.budget.known_budget_exceptions)
