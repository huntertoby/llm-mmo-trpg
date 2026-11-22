"""KD-1（#176，05 5.13 第 8 點）：倒地改版的數字開進數值工坊。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path

CONTENT = bundled_content_dir()
CORE = "rules/core.yaml"
SURFACES = "surfaces.yaml"
RULES = (
    "prone_ap_loss",
    "prone_stand_up_move_permille",
    "help_up_ap_cost",
    "steady_rounds",
    "prone_contest_bonus",
    "topple_damage_dice",
)


def _now(file: str, path: str) -> Any:
    return lookup(read_data(CONTENT / file), parse_path(path))


def _ice_dc_path(read_service: TuningService) -> str:
    detail = object_detail(CONTENT, read_service.table, "surface", "surfaces")
    (field,) = [f for f in detail.fields if f.path.endswith("on_enter.check.dc")]
    return field.path


def test_prone_rules_are_open_with_chinese_notes(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "rules", "core")
    by_path = {f.path: f for f in detail.fields}
    for path in RULES:
        field = by_path[path]
        assert field.value == _now(CORE, path), path
        assert field.label_zh and not field.label_zh.isascii(), path
        assert "調高" in field.note_zh and "調低" in field.note_zh, path
        assert field.group_zh == "倒地", path


def test_ice_dc_is_open_on_the_surface_table(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "surface", "surfaces")
    (field,) = [f for f in detail.fields if f.path.endswith("on_enter.check.dc")]
    assert field.value == _now(SURFACES, field.path)
    assert "冰" in field.label_zh
    assert "調高" in field.note_zh and "調低" in field.note_zh


@pytest.mark.parametrize("path", [p for p in RULES if p != "topple_damage_dice"])
def test_prone_rule_changes_validate(read_service: TuningService, path: str) -> None:
    now = _now(CORE, path)
    item = TuningChangeIn(file=CORE, path=path, old=now, new=now + 1)
    result = read_service.check(f"kd1-{path.replace('_', '-')}", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_ice_dc_change_validates(read_service: TuningService) -> None:
    path = _ice_dc_path(read_service)
    now = _now(SURFACES, path)
    item = TuningChangeIn(file=SURFACES, path=path, old=now, new=now + 1)
    result = read_service.check("kd1-ice-dc", [item])
    assert result.ok, (result.field_errors, result.page_errors)
