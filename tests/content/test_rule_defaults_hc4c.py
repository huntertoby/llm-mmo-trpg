"""HC-4c：閃現模板收尾、AI 與環境的預設值搬進 content 之後的規則對照。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.flash_templates import FlashTable, TransformTemplate


def _read(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _drop(data: dict[str, Any], path: tuple[str | int, ...]) -> None:
    node: Any = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]


@pytest.mark.parametrize(
    "path",
    [
        ("rules", "insight_per_win"),
        ("rules", "form_magnitudes"),
        ("rules", "tighten_permille"),
        ("rules", "complete", "cost_cuts"),
        ("rules", "complete", "cost_cuts", 0, "step"),
        ("pricing", "open", "min_categories"),
        ("pricing", "focused", "min_categories"),
    ],
    ids=lambda p: "/".join(map(str, p)),
)
def test_flash_numbers_have_no_program_default(path: tuple[str | int, ...]) -> None:
    """HC-4b3 裁定 4：閃現表剩下的幾格也必填，內容檔少寫一格就驗證失敗。"""
    data = _read("flash_templates.yaml")
    _drop(data, path)
    field = next(p for p in reversed(path) if isinstance(p, str))
    with pytest.raises(ValidationError, match=field):
        FlashTable.model_validate(data)


def test_flash_values_follow_the_content_file() -> None:
    """值以內容檔為準：``insight_per_win`` 是 2（原本程式寫 1）、法力與耐力的步距 10。"""
    table = FlashTable.model_validate(_read("flash_templates.yaml"))
    assert table.rules.insight_per_win == 2
    assert [(c.field, c.step) for c in table.rules.complete.cost_cuts] == [
        ("stance_upkeep", 1),
        ("cooldown", 1),
        ("mana", 10),
        ("stamina", 10),
        ("ap_cost", 1),
    ]
    assert table.pricing.focused.min_categories == 1


def test_transform_scale_permille_is_gone() -> None:
    """HC-4b3 裁定 3：沒有程式讀的 ``scale_permille`` 刪掉，寫了就驗證失敗。"""
    assert "scale_permille" not in TransformTemplate.model_fields
    transforms = _read("flash_templates.yaml")["transforms"]
    found = [t for t in transforms if t["id"] == "to_passive_on_hit"]
    data = {**found[0], "scale_permille": 500}
    with pytest.raises(ValidationError, match="scale_permille"):
        TransformTemplate.model_validate(data)
