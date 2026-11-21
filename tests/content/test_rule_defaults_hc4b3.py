"""HC-4b3：閃現模板的預設值搬進 content 之後的規則對照。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.flash_templates import FlashTable, TransformTemplate
from trpg.content.library import load_library
from trpg.shared.errors import ContentError

FLASH = "flash_templates.yaml"


def _read() -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / FLASH).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    return root


@pytest.mark.parametrize(
    "path",
    [
        ("rules",),
        ("pricing",),
        ("rules", "max_flashes"),
        ("rules", "major_flash"),
        ("rules", "budget_step_permille"),
        ("rules", "dissolve_refund_permille"),
        ("rules", "usage_min_uses"),
        ("rules", "stance_magnitudes"),
        ("rules", "modifier_fine_step"),
        ("rules", "modifier_drawback_step"),
        ("rules", "single_hit_cap_permille"),
        ("rules", "converge_targets_permille"),
        ("rules", "converge_usage_score"),
        ("rules", "complete"),
        ("rules", "complete", "flashes"),
        ("rules", "complete", "budget_permille"),
        ("rules", "complete", "cap_permille"),
        ("rules", "complete", "summon_power_steps"),
        ("rules", "complete", "stance_magnitude_steps"),
        ("rules", "complete", "status_magnitude_steps"),
        ("pricing", "open"),
        ("pricing", "focused"),
    ],
    ids="/".join,
)
def test_numbers_have_no_program_default(path: tuple[str, ...]) -> None:
    """程式不再有預設值：內容檔少寫一格就驗證失敗。"""
    data = _read()
    node = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    with pytest.raises(ValidationError, match=path[-1]):
        FlashTable.model_validate(data)


def _transform(template_id: str) -> dict[str, Any]:
    found = [t for t in _read()["transforms"] if t["id"] == template_id]
    assert len(found) == 1
    return dict(found[0])


@pytest.mark.parametrize(
    ("template_id", "field"),
    [
        ("to_passive_on_hit", "scale_permille"),
        ("to_reaction_melee", "scale_permille"),
        ("to_summon", "summon_duration"),
    ],
)
def test_transform_numbers_are_required_where_used(template_id: str, field: str) -> None:
    """「有某欄才用到」：敵對原招轉被動／反應才用縮小起點、轉召喚才用召喚輪數；用到時必填。"""
    data = _transform(template_id)
    TransformTemplate.model_validate(data)
    del data[field]
    with pytest.raises(ValidationError, match=f"必須填 {field}"):
        TransformTemplate.model_validate(data)


@pytest.mark.parametrize("template_id", ["to_passive_companion", "to_reaction_aid", "to_trap"])
def test_transform_numbers_may_be_omitted_where_unused(template_id: str) -> None:
    """其他轉型可以不寫（召喚技、輔助技的被動與反應另由技能預算表的 ``flash_transform`` 定）。"""
    data = _transform(template_id)
    assert "scale_permille" not in data and "summon_duration" not in data
    template = TransformTemplate.model_validate(data)
    assert (template.scale_permille, template.summon_duration) == (None, None)


def test_the_flash_file_is_required(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / FLASH).unlink()
    with pytest.raises(ContentError, match=r"flash_templates\.yaml"):
        load_library(root)


def test_form_magnitudes_follow_the_enter_form_cap(tmp_path: Path) -> None:
    """HC-4b 裁定 3 的做法：形態幅度階梯的上限對照 ``enter_form.magnitude_permille`` 的上限
    （原本寫死在 schema 的 2000‰）。"""
    lib = library()
    top = lib.ruleset.primitives.by_id()["enter_form"].params["magnitude_permille"].max
    assert top == lib.flash.rules.form_magnitudes[-1]
    root = _copy(tmp_path)
    path = root / FLASH
    text = path.read_text(encoding="utf-8")
    old = f", {top - 50}, {top}]"
    assert text.count(old) == 1
    path.write_text(text.replace(old, f", {top - 50}, {top}, {top + 50}]"), encoding="utf-8")
    with pytest.raises(ContentError, match=f"form_magnitudes 最多 {top}‰.*兩格要一起改"):
        load_library(root)
