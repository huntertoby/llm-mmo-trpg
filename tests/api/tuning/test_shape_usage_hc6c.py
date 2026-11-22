"""HC-6c（HC-W2 裁定 1）：形狀「沒填參數時」的基礎倍率沒有招用到時，工坊說明多一句「目前沒有招用到，
改了暫時沒效果。」——判斷由資料算（改那格重算全部技能預算）。"""

from __future__ import annotations

from dataclasses import replace

from trpg.api.tuning.objects import object_detail
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.shape_usage import (
    UNUSED_BASE_NOTE_ZH,
    unused_base_note,
    unused_shape_bases,
)
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir

CONTENT = bundled_content_dir()


def _uses_default(library: ContentLibrary, shape_id: str) -> bool:
    """有沒有招用這個形狀卻沒填參數（陷阱的觸發範圍一律不填）。"""
    for skill in library.skills.values():
        if skill.trap is not None and skill.trap.shape == shape_id:
            return True
        if skill.shape.type == shape_id and not skill.shape.param_values():
            return True
    return False


def test_unused_bases_follow_data() -> None:
    library = load_library()
    unused = unused_shape_bases(library)
    tables = sorted(
        sid
        for sid, price in library.budget.shape_budget.items()
        if price.by_value or price.non_power_by_value or price.solid_by_value
    )
    assert unused <= set(tables)
    for sid in tables:
        assert (sid in unused) == (not _uses_default(library, sid)), sid
    # 現在的資料：十字的基礎值給陷阱用；錐形、環形、連鎖沒有招用到（HC-W2 報告）
    assert "cross" not in unused
    assert {"cone", "ring", "chain"} <= unused


def test_note_only_on_unused_base_fields() -> None:
    library = load_library()
    assert unused_base_note("shape_budget.cone.base_permille", library) == UNUSED_BASE_NOTE_ZH
    assert unused_base_note("shape_budget.cross.base_permille", library) is None
    assert unused_base_note("shape_budget.cone.by_value.2", library) is None
    assert unused_base_note("shape_budget.single.base_permille", library) is None
    assert unused_base_note("shape_budget.cone.base_permille", None) is None


def test_note_appears_when_unused_and_goes_away_when_used() -> None:
    """有一招不填錐形長度時，錐形那格就不再加這句（判斷跟著資料走）。"""
    library = load_library()
    sid, skill = next((k, s) for k, s in sorted(library.skills.items()) if s.shape.type == "cone")
    bare = skill.model_copy(update={"shape": skill.shape.model_copy(update={"size": None})})
    changed = replace(library, skills={**library.skills, sid: bare})
    assert "cone" in unused_shape_bases(library)
    assert "cone" not in unused_shape_bases(changed)


def test_object_detail_note(read_service: TuningService) -> None:
    detail = object_detail(
        CONTENT, read_service.table, "budget", "skill_budget", read_service.library
    )
    notes = {f.path: f.note_zh for f in detail.fields}
    for sid in ("cone", "ring", "chain"):
        note = notes[f"shape_budget.{sid}.base_permille"]
        assert note.endswith(UNUSED_BASE_NOTE_ZH)
        assert "通常沒有效果" not in note
    assert not notes["shape_budget.cross.base_permille"].endswith(UNUSED_BASE_NOTE_ZH)
    assert not notes["shape_budget.cone.by_value.2"].endswith(UNUSED_BASE_NOTE_ZH)
