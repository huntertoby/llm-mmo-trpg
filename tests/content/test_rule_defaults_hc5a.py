"""HC-5a：閃現生成常數（原本寫死在 ``skillgen/flash_*.py``）搬進 content 之後的規則對照。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.flash_templates import (
    USAGE_SCORE_OPS,
    ExtraMajorTemplate,
    FlashTable,
    TransformTemplate,
)

FLASH = "flash_templates.yaml"


def _read() -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / FLASH).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.parametrize(
    "path",
    [
        ("rules", "charge_cooldown_step"),
        ("rules", "max_charge_cooldown"),
        ("rules", "charge_duration_cap"),
        ("rules", "max_triggers_per_round"),
        ("rules", "hp_relax_step_permille"),
        ("rules", "hp_relax_max_permille"),
        ("rules", "hp_tighten_step_permille"),
        ("rules", "hp_tighten_min_permille"),
        ("rules", "added_hp_condition_permille"),
        ("rules", "max_empty_slots_cap"),
        ("rules", "blood_bonus_permille"),
        ("rules", "summon_hp_steps"),
        ("rules", "new_damage_multiplier_permille"),
        ("rules", "followup_potency_tries"),
        ("rules", "followup_ease_steps"),
        ("rules", "followup_fine_top_permille"),
        ("rules", "usage_scores"),
        ("rules", "usage_multi_targets_permille"),
        ("rules", "usage_frequent_uses"),
        ("rules", "second_keyword_cap"),
        ("rules", "transform_carry_max"),
        ("rules", "beside_power_step_permille"),
        ("rules", "search"),
        ("rules", "search", "tune_attempts"),
        ("rules", "search", "strict_margin_millipoints"),
        ("rules", "search", "cap_shrink_steps"),
        ("rules", "search", "cap_shrink_permille"),
        ("rules", "search", "max_cost_cuts"),
    ],
    ids="/".join,
)
def test_numbers_have_no_program_default(path: tuple[str, ...]) -> None:
    """程式不再有模組常數：內容檔少寫一格就驗證失敗。"""
    data = _read()
    node = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    with pytest.raises(ValidationError, match=path[-1]):
        FlashTable.model_validate(data)


@pytest.mark.parametrize("op", USAGE_SCORE_OPS)
def test_every_usage_score_is_written(op: str) -> None:
    data = _read()
    del data["rules"]["usage_scores"][op]
    with pytest.raises(ValidationError, match=f"usage_scores 缺少：{op}"):
        FlashTable.model_validate(data)


def test_usage_scores_reject_unknown_ops() -> None:
    data = _read()
    data["rules"]["usage_scores"]["converge_single"] = 3  # 收束另看 converge_usage_score
    with pytest.raises(ValidationError, match="usage_scores"):
        FlashTable.model_validate(data)


def test_summon_hp_steps_must_rise() -> None:
    data = _read()
    data["rules"]["summon_hp_steps"] = [200, 100]
    with pytest.raises(ValidationError, match="summon_hp_steps"):
        FlashTable.model_validate(data)


def test_strict_margin_is_a_hundredth_of_a_point() -> None:
    """``strict_margin_millipoints`` 換回原本的 ``Fraction(1, 100)``。"""
    table = FlashTable.model_validate(_read())
    assert table.rules.search.strict_margin * 1000 == table.rules.search.strict_margin_millipoints


def _transform(template_id: str) -> dict[str, Any]:
    found = [t for t in _read()["transforms"] if t["id"] == template_id]
    assert len(found) == 1
    return dict(found[0])


@pytest.mark.parametrize(
    ("template_id", "field"),
    [
        ("to_passive_on_hit", "draft_costs"),
        ("to_reaction_melee", "draft_costs"),
        ("to_reaction_melee", "draft_range"),
        ("to_summon", "draft_costs"),
        ("to_summon", "draft_range"),
        ("to_summon", "draft_ap_cost"),
        ("to_trap", "draft_costs"),
        ("to_trap", "draft_range"),
        ("to_trap", "draft_ap_cost"),
        ("to_trap", "max_trap_effects"),
        ("to_stance", "stance_upkeeps"),
        ("to_passive_companion", "draft_costs"),
        ("to_reaction_guardian", "draft_costs"),
        ("to_reaction_guardian", "draft_range"),
        ("to_passive_blessing", "draft_costs"),
        ("to_reaction_aid", "draft_costs"),
        ("to_reaction_aid", "draft_range"),
    ],
)
def test_transform_drafts_are_required_where_used(template_id: str, field: str) -> None:
    """「有某欄才用到」：轉型用到的草稿欄位必填。"""
    data = _transform(template_id)
    TransformTemplate.model_validate(data)
    del data[field]
    with pytest.raises(ValidationError, match=f"必須填 {field}"):
        TransformTemplate.model_validate(data)


@pytest.mark.parametrize(
    ("template_id", "field", "value"),
    [
        ("to_stance", "draft_costs", [{"mana": 2}]),
        ("to_modifier", "draft_range", 2),
        ("to_passive_on_hit", "draft_range", 2),
        ("to_reaction_melee", "draft_ap_cost", 1),
        ("to_summon", "max_trap_effects", 3),
        ("to_trap", "stance_upkeeps", [1]),
    ],
)
def test_transform_drafts_are_left_out_where_unused(
    template_id: str, field: str, value: object
) -> None:
    data = {**_transform(template_id), field: value}
    with pytest.raises(ValidationError, match=f"不用填 {field}"):
        TransformTemplate.model_validate(data)


def test_draft_costs_only_take_cost_fields() -> None:
    data = {**_transform("to_passive_on_hit"), "draft_costs": [{"hp_percent": 10}]}
    with pytest.raises(ValidationError, match="draft_costs 只能寫"):
        TransformTemplate.model_validate(data)


def test_borrow_needs_amount_and_uses() -> None:
    borrow = next(t for t in _read()["extra_major"] if t["only"] == "borrow")
    ExtraMajorTemplate.model_validate(borrow)
    for field in ("amount", "uses"):
        data = {k: v for k, v in borrow.items() if k != field}
        with pytest.raises(ValidationError, match="必須填 amount 與 uses"):
            ExtraMajorTemplate.model_validate(data)
