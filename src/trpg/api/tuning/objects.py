"""數值工坊的對象與欄位（NW-1a）：白名單 × 磁碟上的單位檔 → 畫面用的清單與表單資料。

值一律讀**磁碟上**的 ``content/``（寫回後不重開伺服器也看到新值）；唯讀提示（遭遇護甲調整）讀
伺服器啟動時載入的內容庫。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from trpg.api.tuning.schemas import TuningFieldView, TuningObjectDetail, TuningObjectSummary
from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup
from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.loader import parse_yaml
from trpg.content.tuning_fields import (
    PathPart,
    TuningField,
    TuningFields,
    TuningTarget,
    format_path,
    parse_path,
    target_files,
)

__all__ = [
    "ObjectNotFoundError",
    "concrete_fields",
    "list_objects",
    "object_detail",
    "object_file",
    "read_data",
]

_DEFAULTS_ZH = {
    "speed": "沒寫＝5",
    "armor_bonus": "沒寫＝0",
    "level": "沒寫＝1",
    "max_mana": "沒寫＝依武器大類",
    "stamina": "沒寫＝依武器大類",
}


class ObjectNotFoundError(LookupError):
    """沒有這個對象（或不在白名單內）。"""


def read_data(path: Path) -> Any:
    return parse_yaml(path.read_bytes().decode("utf-8").removeprefix("﻿"))


def object_file(content_dir: Path, target: TuningTarget, object_id: str) -> Path:
    for path in target_files(content_dir, target):
        if path.stem == object_id:
            return path
    raise ObjectNotFoundError(f"數值工坊沒有這個對象：{target.kind}/{object_id}")


def _category(data: Any) -> Literal["boss", "enemy"]:
    tags = data.get("tags") or ()
    return "boss" if "boss" in tags else "enemy"


def list_objects(content_dir: Path, table: TuningFields) -> list[TuningObjectSummary]:
    out: list[TuningObjectSummary] = []
    for target in table.targets:
        for path in target_files(content_dir, target):
            data = read_data(path)
            out.append(
                TuningObjectSummary(
                    kind=target.kind,
                    id=path.stem,
                    name_zh=str(data.get("name_zh") or path.stem),
                    category=_category(data),
                    file=path.relative_to(content_dir).as_posix(),
                )
            )
    return out


def _phase_label(data: Any, index: int) -> str:
    phase = (data.get("phases") or [])[index]
    return f"第 {index + 1} 階段「{phase.get('name_zh') or phase.get('id')}」"


def _phase_skipped(field: TuningField, phase: Any) -> bool:
    """``phases[*]`` 的欄位不展開到這個階段：開場階段（沒有 ``trigger``；schema 規定開場階段不能有
    改動，NW-1b 起 ``mana_restore`` 也照這條）；``phases[*].trigger.*`` 另外只展開 ``hp_below``。"""
    trigger = (phase or {}).get("trigger") if isinstance(phase, dict) else None
    if not trigger:
        return True
    return field.path.startswith("phases[*].trigger.") and trigger.get("kind") != "hp_below"


def concrete_fields(data: Any, target: TuningTarget) -> list[tuple[TuningField, str, str]]:
    """這個對象實際可改的欄位：``(白名單欄位, 具體路徑, 中文標籤)``。``phases[*]`` 不展開開場階段；
    ``phases[*].trigger.*`` 只展開有 HP 門檻（``hp_below``）的階段（:func:`_phase_skipped`）。"""
    out: list[tuple[TuningField, str, str]] = []
    for field in target.fields:
        parts = parse_path(field.path)
        if "*" not in parts:
            out.append((field, field.path, field.label_zh))
            continue
        star = parts.index("*")
        items = lookup(data, parts[:star])
        for i in range(len(items) if isinstance(items, list) else 0):
            concrete: tuple[PathPart, ...] = (*parts[:star], i, *parts[star + 1 :])
            if parts[:star] == ("phases",) and _phase_skipped(field, items[i]):
                continue
            label = field.label_zh
            if parts[:star] == ("phases",):
                label = f"{_phase_label(data, i)}{field.label_zh}"
            out.append((field, format_path(concrete), label))
    return out


def _value(data: Any, path: str) -> int | None:
    try:
        found = lookup(data, parse_path(path))
    except PatchError:
        return None
    return None if found is MISSING or not isinstance(found, int) else found


def _armor_notes(library: ContentLibrary | None, unit_id: str) -> list[str]:
    if library is None:
        return []
    notes: list[str] = []
    for region in sorted(library.world_encounters):
        for loc in library.world_encounters[region].locations:
            mods = loc.armor_mods
            if mods is not None and mods.unit == unit_id:
                notes.append(
                    f"實戰時另有遭遇護甲調整（{region}／{loc.location}，"
                    f"{mods.min_total:+d}～{mods.max_total:+d}，依劇情旗標；數值工坊 NW-3 才開）"
                )
    return notes


def object_detail(
    content_dir: Path,
    table: TuningFields,
    kind: str,
    object_id: str,
    library: ContentLibrary | None = None,
) -> TuningObjectDetail:
    target = table.target(kind)
    if target is None:
        raise ObjectNotFoundError(f"數值工坊沒有這類對象：{kind}")
    path = object_file(content_dir, target, object_id)
    data = read_data(path)
    template = UnitTemplate.model_validate(data)
    fields = [
        TuningFieldView(
            path=concrete,
            pattern=field.path,
            label_zh=label,
            kind=field.kind,
            value=_value(data, concrete),
            default_zh=_DEFAULTS_ZH.get(field.path) if _value(data, concrete) is None else None,
            hint_min=field.hint_min,
            hint_max=field.hint_max,
            note_zh=field.note_zh,
        )
        for field, concrete, label in concrete_fields(data, target)
    ]
    notes = ["大世界的敵人另依遭遇等級成長（grow_enemy），這裡改的是單位檔的基礎值。"]
    notes += _armor_notes(library, template.id)
    return TuningObjectDetail(
        kind=kind,
        id=object_id,
        name_zh=template.name_zh,
        category=_category(data),
        file=path.relative_to(content_dir).as_posix(),
        fields=fields,
        notes_zh=notes,
    )
