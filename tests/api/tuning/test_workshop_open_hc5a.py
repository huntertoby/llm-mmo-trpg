"""HC-5a：從 ``skillgen/flash_*.py`` 搬進 content 的閃現規則數值開進工坊的 ``flash`` 表。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from tests.api.tuning.test_workshop_open_hc4b3 import OPENED as OPENED_HC4B3
from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn, TuningFieldView
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path

CONTENT = bundled_content_dir()
FLASH = "flash_templates.yaml"
OPENED = (
    "rules.charge_cooldown_step",
    "rules.max_charge_cooldown",
    "rules.charge_duration_cap",
    "rules.max_triggers_per_round",
    "rules.hp_relax_step_permille",
    "rules.hp_relax_max_permille",
    "rules.hp_tighten_step_permille",
    "rules.added_hp_condition_permille",
    "rules.blood_bonus_permille",
    "rules.usage_scores.area",
    "rules.usage_scores.kill_refund",
    "rules.usage_scores.keyword_exploit",
    "rules.usage_multi_targets_permille",
    "rules.usage_frequent_uses",
    "rules.transform_carry_max",
    "rules.beside_power_step_permille",
)
"""這段新開的欄位（HC-5a 從程式搬進 ``flash_templates.yaml``、工坊改得動的數字）。"""


def _now(path: str) -> object:
    return lookup(read_data(CONTENT / FLASH), parse_path(path))


def _detail(read_service: TuningService) -> dict[str, TuningFieldView]:
    detail = object_detail(CONTENT, read_service.table, "flash", "flash_templates")
    return {f.path: f for f in detail.fields}


def test_flash_table_has_exactly_the_opened_fields(read_service: TuningService) -> None:
    assert sorted(_detail(read_service)) == sorted({*OPENED_HC4B3, *OPENED})


def test_new_flash_numbers_are_open_with_chinese_notes(read_service: TuningService) -> None:
    by_path = _detail(read_service)
    for path in OPENED:
        field = by_path[path]
        assert field.value == _now(path), path
        label = field.label_zh
        assert label and not label.isascii(), path
        assert field.group_zh, path
        note = field.note_zh
        assert "調高" in note and "調低" in note, path
        low, high = field.hint_min, field.hint_max
        assert isinstance(field.value, int) and low is not None and high is not None, path
        assert low <= field.value <= high, path


def test_new_groups_are_adjacent(read_service: TuningService) -> None:
    """同組相鄰（前端畫成可收合的區塊）。"""
    groups = [f.group_zh for f in _detail(read_service).values()]
    seen: list[str | None] = []
    for group in groups:
        if not seen or seen[-1] != group:
            assert group not in seen, groups
            seen.append(group)


def test_a_new_flash_draft_validates(read_service: TuningService) -> None:
    path = "rules.charge_cooldown_step"
    now = _now(path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=FLASH, path=path, old=now, new=now + 1)
    result = read_service.check("hc5a-charge", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_a_permille_over_1000_is_refused(read_service: TuningService) -> None:
    path = "rules.hp_relax_max_permille"
    now = _now(path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=FLASH, path=path, old=now, new=1001)
    result = read_service.check("hc5a-relax", [item])
    assert not result.ok
