"""改動單的差異（NW-1a A5）：「對象／欄位中文名／舊值／新值」表＋``git diff`` 風格的文字。"""

from __future__ import annotations

import difflib
from collections.abc import Iterable
from pathlib import Path

from trpg.api.tuning.check import Prepared
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.objects import concrete_fields, read_data
from trpg.api.tuning.schemas import TuningChangeView, TuningDiff, TuningDiffRow
from trpg.content.tuning_fields import TuningFields

__all__ = ["change_views", "diff_rows", "diff_text", "make_diff"]


def _labels(content_dir: Path, table: TuningFields, rel: str) -> tuple[str, dict[str, str]]:
    """(對象中文名, 具體路徑 → 欄位中文名)；檔不在白名單內時回空表。"""
    path = content_dir / rel
    for target in table.targets:
        if path.is_file() and path.match(target.glob):
            data = read_data(path)
            labels = {p: label for _f, p, label in concrete_fields(data, target)}
            return str(data.get("name_zh") or path.stem), labels
    return Path(rel).stem, {}


def change_views(
    content_dir: Path, table: TuningFields, changes: Iterable[Change]
) -> list[TuningChangeView]:
    cache: dict[str, tuple[str, dict[str, str]]] = {}
    out: list[TuningChangeView] = []
    for c in changes:
        if c.file not in cache:
            cache[c.file] = _labels(content_dir, table, c.file)
        _name, labels = cache[c.file]
        out.append(
            TuningChangeView(
                file=c.file,
                path=c.path,
                old=c.old,
                new=c.new,
                object_id=Path(c.file).stem,
                label_zh=labels.get(c.path, c.path),
            )
        )
    return out


def diff_rows(
    content_dir: Path, table: TuningFields, changes: Iterable[Change]
) -> list[TuningDiffRow]:
    rows: list[TuningDiffRow] = []
    names: dict[str, str] = {}
    for view in change_views(content_dir, table, changes):
        if view.file not in names:
            names[view.file] = _labels(content_dir, table, view.file)[0]
        rows.append(
            TuningDiffRow(
                object_id=view.object_id,
                object_name_zh=names[view.file],
                file=view.file,
                path=view.path,
                label_zh=view.label_zh,
                old=view.old,
                new=view.new,
            )
        )
    return rows


def diff_text(prepared: Prepared) -> str:
    """改到的檔的 unified diff（不帶上下文，只含改到的行；路徑照 ``git diff``）。"""
    out: list[str] = []
    for rel in sorted(prepared.texts):
        old = prepared.originals[rel].splitlines(keepends=True)
        new = prepared.texts[rel].splitlines(keepends=True)
        out += difflib.unified_diff(
            old, new, fromfile=f"a/content/{rel}", tofile=f"b/content/{rel}", n=0
        )
    return "".join(line if line.endswith("\n") else line + "\n" for line in out)


def make_diff(content_dir: Path, table: TuningFields, prepared: Prepared) -> TuningDiff:
    return TuningDiff(
        rows=diff_rows(content_dir, table, prepared.changes),
        text="" if prepared.errors else diff_text(prepared),
        errors=prepared.errors,
    )
