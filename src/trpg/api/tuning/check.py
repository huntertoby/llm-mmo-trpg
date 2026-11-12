"""改動單 → 改後的檔案文字 → 驗證（NW-1a A4／A5，規格 5.5）。

順序（任何一步有錯就不往下）：

1. 轉型（:func:`to_changes`）：使用者打的文字轉整數，轉不了是欄位錯誤。
2. 對到白名單（檔在對象清單內、路徑對到欄位；階段門檻只開有 ``hp_below`` 的階段）、``old`` 等於
   磁碟現值（不同就「這個值已經被改過（現在是 X）」）、YAML 字面替換（:func:`prepare`）。
3. 單檔 schema（``UnitTemplate``）：pydantic 錯誤轉中文、依 ``loc`` 對到欄位
   （:func:`schema_errors`）。
4. 整包：草稿複本 ``load_checked_library`` ＋ ``library_violations``（＝``trpg content check``
   同一套；:func:`library_errors`）。``ContentError`` 指到改過的檔時掛在那個檔的欄位上，其他放頁首。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from trpg.api.primitive_coverage import load_checked_library
from trpg.api.tuning.drafts import Change, normalize
from trpg.api.tuning.objects import concrete_fields, read_data
from trpg.api.tuning.schemas import TuningChangeIn, TuningFieldError
from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup, patch_text
from trpg.content.battle import UnitTemplate
from trpg.content.loader import parse_yaml
from trpg.content.tuning_fields import (
    PathPart,
    TuningFields,
    TuningTarget,
    format_path,
    parse_path,
    target_files,
)
from trpg.shared.errors import ContentError
from trpg.skillgen.library_check import library_violations

__all__ = [
    "Prepared",
    "library_errors",
    "prepare",
    "schema_errors",
    "to_changes",
]

_TRIGGER_KINDS = frozenset({"hp_below", "tag_down", "round_at"})
"""``trigger`` 判別欄位的值：pydantic 的 ``loc`` 會多一段，對欄位時拿掉。"""


@dataclass
class Prepared:
    """套用改動單的結果：``texts`` 是改到的檔（相對路徑 → 改後全文），``originals`` 是改前全文。"""

    changes: tuple[Change, ...]
    texts: dict[str, str] = field(default_factory=dict)
    originals: dict[str, str] = field(default_factory=dict)
    errors: list[TuningFieldError] = field(default_factory=list)


def _to_int(value: int | str | None) -> int | None:
    if value is None or isinstance(value, int):
        return value
    text = value.strip().replace("，", "").replace(",", "")
    if text in ("", "沒寫"):
        return None
    return int(text)  # 轉不了丟 ValueError


def to_changes(
    items: Iterable[TuningChangeIn],
) -> tuple[list[Change], list[TuningFieldError]]:
    """請求的改動 → :class:`Change`；新值不是整數的回欄位錯誤。"""
    changes: list[Change] = []
    errors: list[TuningFieldError] = []
    for item in items:
        try:
            new = _to_int(item.new)
        except ValueError:
            errors.append(
                TuningFieldError(file=item.file, path=item.path, message_zh="要填整數（例：120）")
            )
            continue
        try:
            changes.append(Change(file=item.file, path=item.path, old=item.old, new=new))
        except ValidationError:
            errors.append(
                TuningFieldError(
                    file=item.file, path=item.path, message_zh="檔名或欄位路徑格式不對"
                )
            )
    return changes, errors


def _target_of(content_dir: Path, table: TuningFields, rel: str) -> TuningTarget | None:
    for target in table.targets:
        if any(
            p.relative_to(content_dir).as_posix() == rel for p in target_files(content_dir, target)
        ):
            return target
    return None


def _check_file(
    content_dir: Path, target: TuningTarget, rel: str, changes: Sequence[Change]
) -> tuple[str | None, str, list[TuningFieldError]]:
    """一個檔：白名單、``old`` 比對、字面替換。回傳 (改後全文或 None, 原文, 錯誤)。"""
    raw = (content_dir / rel).read_bytes().decode("utf-8")
    data = read_data(content_dir / rel)
    allowed = {path for _f, path, _label in concrete_fields(data, target)}
    errors: list[TuningFieldError] = []
    edits: list[tuple[Sequence[PathPart], int | None]] = []
    for change in changes:

        def fail(message: str, change: Change = change) -> None:
            errors.append(TuningFieldError(file=rel, path=change.path, message_zh=message))

        if change.path not in allowed:
            fail("這個欄位數值工坊不開放")
            continue
        parts = parse_path(change.path)
        current = lookup(data, parts)
        now = None if current is MISSING else current
        if now != change.old:
            shown = "沒寫" if now is None else now
            fail(f"這個值已經被改過（現在是 {shown}），請重新載入")
            continue
        edits.append((parts, change.new))
    if errors:
        return None, raw, errors
    try:
        return patch_text(raw, edits), raw, []
    except PatchError as exc:
        path = str(exc).split("：", 1)[0]
        return None, raw, [TuningFieldError(file=rel, path=path, message_zh=str(exc))]


def prepare(content_dir: Path, table: TuningFields, changes: Iterable[Change]) -> Prepared:
    """對到白名單、比對 ``old``、字面替換（第 2 步）。"""
    out = Prepared(changes=normalize(changes))
    by_file: dict[str, list[Change]] = defaultdict(list)
    for change in out.changes:
        by_file[change.file].append(change)
    for rel in sorted(by_file):
        target = _target_of(content_dir, table, rel)
        if target is None:
            out.errors += [
                TuningFieldError(file=rel, path=c.path, message_zh="這個檔不在數值工坊可改的範圍")
                for c in by_file[rel]
            ]
            continue
        text, raw, errors = _check_file(content_dir, target, rel, by_file[rel])
        out.errors += errors
        out.originals[rel] = raw
        if text is not None and text != raw:
            out.texts[rel] = text
    return out


def _message_zh(error: Any) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    known = {
        "greater_than_equal": f"不能小於 {ctx.get('ge')}",
        "less_than_equal": f"不能大於 {ctx.get('le')}",
        "greater_than": f"要大於 {ctx.get('gt')}",
        "less_than": f"要小於 {ctx.get('lt')}",
        "int_parsing": "要填整數",
        "int_type": "要填整數",
        "int_from_float": "要填整數（不能有小數）",
        "missing": "必填",
    }
    if kind in known:
        return known[kind]
    return str(error.get("msg", "")).removeprefix("Value error, ")


def _field_path(loc: Sequence[Any]) -> str:
    parts: list[PathPart] = []
    for i, part in enumerate(loc):
        if isinstance(part, str) and part in _TRIGGER_KINDS and i and loc[i - 1] == "trigger":
            continue
        parts.append(part)
    return format_path(parts) if parts else ""


def schema_errors(prepared: Prepared) -> tuple[list[TuningFieldError], list[str]]:
    """改後的單檔 schema 檢查（第 3 步）：(欄位錯誤, 頁首錯誤)。"""
    fields: list[TuningFieldError] = []
    page: list[str] = []
    changed = {(c.file, c.path) for c in prepared.changes}
    for rel, text in sorted(prepared.texts.items()):
        try:
            UnitTemplate.model_validate(parse_yaml(text.removeprefix("﻿")))
        except ValidationError as exc:
            for error in exc.errors(include_url=False):
                path = _field_path(error["loc"])
                message = _message_zh(error)
                if (rel, path) in changed:
                    fields.append(TuningFieldError(file=rel, path=path, message_zh=message))
                else:
                    page.append(f"{rel}：{message}")
    return fields, page


def library_errors(draft_dir: Path, prepared: Prepared) -> tuple[list[TuningFieldError], list[str]]:
    """草稿複本的整包檢查（第 4 步）：(欄位錯誤, 頁首錯誤)。"""
    try:
        library = load_checked_library(draft_dir)
    except ContentError as exc:
        try:
            rel = exc.path.resolve().relative_to(draft_dir.resolve()).as_posix()
        except ValueError:
            rel = exc.path.as_posix()
        mine = [c for c in prepared.changes if c.file == rel]
        if mine:
            return [
                TuningFieldError(file=rel, path=c.path, message_zh=exc.reason) for c in mine
            ], []
        return [], [f"{rel}：{exc.reason}"]
    violations = library_violations(library)
    return [], [f"技能違規：{v}" for v in violations]
