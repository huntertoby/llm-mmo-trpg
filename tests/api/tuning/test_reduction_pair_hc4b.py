"""HC-4b（HC-W2 裁定 2）：裝備的總減傷上限和核心規則的元素修正下限一起開進工坊，兩格一起驗證。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.content.loader import bundled_content_dir

CONTENT = bundled_content_dir()
CORE = "rules/core.yaml"
EQUIPMENT = "rules/equipment.yaml"
FLOOR = "element_mod_floor_permille"
CAP = "caps.damage_reduction_permille"


def _now() -> tuple[int, int]:
    floor = read_data(CONTENT / CORE)[FLOOR]
    cap = read_data(CONTENT / EQUIPMENT)["caps"]["damage_reduction_permille"]
    assert cap == 1000 - floor
    return floor, cap


def test_both_cells_are_open_and_say_they_change_together(read_service: TuningService) -> None:
    core = object_detail(CONTENT, read_service.table, "rules", "core")
    equipment = object_detail(CONTENT, read_service.table, "equipment", "equipment")
    floor_field = next(f for f in core.fields if f.path == FLOOR)
    cap_field = next(f for f in equipment.fields if f.path == CAP)
    floor, cap = _now()
    assert (floor_field.value, cap_field.value) == (floor, cap)
    for field in (floor_field, cap_field):
        assert "兩格要一起改" in field.note_zh, field.path
        assert "越" in field.note_zh, field.path


def test_changing_only_one_cell_is_refused_on_that_cell(read_service: TuningService) -> None:
    floor, cap = _now()
    for file, path, old, new in ((CORE, FLOOR, floor, floor + 50), (EQUIPMENT, CAP, cap, cap - 50)):
        item = TuningChangeIn(file=file, path=path, old=old, new=new)
        result = read_service.check("hc4b-one", [item])
        assert not result.ok
        assert [(e.file, e.path) for e in result.field_errors] == [(file, path)], result
        assert "兩格要一起改" in result.field_errors[0].message_zh


def test_changing_both_cells_together_passes(read_service: TuningService) -> None:
    floor, cap = _now()
    items = [
        TuningChangeIn(file=CORE, path=FLOOR, old=floor, new=floor + 50),
        TuningChangeIn(file=EQUIPMENT, path=CAP, old=cap, new=cap - 50),
    ]
    result = read_service.check("hc4b-both", items)
    assert result.ok, (result.field_errors, result.page_errors)


def test_both_cells_changed_inconsistently_mark_both(read_service: TuningService) -> None:
    floor, cap = _now()
    items = [
        TuningChangeIn(file=CORE, path=FLOOR, old=floor, new=floor + 50),
        TuningChangeIn(file=EQUIPMENT, path=CAP, old=cap, new=cap - 100),
    ]
    result = read_service.check("hc4b-both-bad", items)
    assert not result.ok
    assert sorted((e.file, e.path) for e in result.field_errors) == [
        (CORE, FLOOR),
        (EQUIPMENT, CAP),
    ]
