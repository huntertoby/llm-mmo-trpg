"""HC-4b3：搬進 content 的閃現計價與規則數值開進工坊（新表 ``flash``）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from trpg.api.tuning.objects import TABLE_NAMES_ZH, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TABLE_KINDS, parse_path

CONTENT = bundled_content_dir()
FLASH = "flash_templates.yaml"
OPENED = (
    "pricing.open.cost",
    "pricing.open.options",
    "pricing.open.min_categories",
    "pricing.focused.cost",
    "pricing.focused.options",
    "rules.max_flashes",
    "rules.major_flash",
    "rules.budget_step_permille",
    "rules.dissolve_refund_permille",
    "rules.usage_min_uses",
    "rules.complete.flashes",
    "rules.complete.budget_permille",
    "rules.complete.cap_permille",
    "rules.modifier_fine_step",
    "rules.modifier_drawback_step",
    "rules.single_hit_cap_permille",
    "rules.converge_targets_permille",
    "rules.converge_usage_score",
)
"""這段新開的欄位（HC-4b3 拿掉程式預設值、工坊改得動的數字）。"""


def _now(path: str) -> object:
    return lookup(read_data(CONTENT / FLASH), parse_path(path))


def test_the_flash_table_is_listed(read_service: TuningService) -> None:
    assert "flash" in TABLE_KINDS
    found = [o for o in read_service.objects() if o.kind == "flash"]
    assert [(o.id, o.file, o.name_zh) for o in found] == [
        ("flash_templates", FLASH, TABLE_NAMES_ZH["flash"])
    ]


def test_flash_numbers_are_open_with_chinese_notes(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "flash", "flash_templates")
    by_path = {f.path: f for f in detail.fields}
    assert sorted(by_path) == sorted(OPENED)
    for path in OPENED:
        field = by_path[path]
        assert field.value == _now(path), path
        assert field.label_zh and not field.label_zh.isascii(), path
        assert field.group_zh, path
        assert "調高" in field.note_zh and "調低" in field.note_zh, path


def test_a_flash_draft_validates(read_service: TuningService) -> None:
    path = "pricing.focused.cost"
    now = _now(path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=FLASH, path=path, old=now, new=now + 1)
    result = read_service.check("hc4b3-price", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_major_flash_after_the_last_flash_is_refused(read_service: TuningService) -> None:
    path = "rules.major_flash"
    now = _now(path)
    top = _now("rules.max_flashes")
    assert isinstance(now, int) and isinstance(top, int)
    item = TuningChangeIn(file=FLASH, path=path, old=now, new=top + 1)
    result = read_service.check("hc4b3-major", [item])
    assert not result.ok
    messages = [e.message_zh for e in result.field_errors] + list(result.page_errors)
    assert any("major_flash" in m for m in messages), result
