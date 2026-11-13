"""數值工坊的改動單與草稿（NW-1a A2，規格 5.1）。

- **改動單**＝一串 :class:`Change`（``file`` 相對 ``content/`` 的路徑、``path`` 欄位路徑、``old``
  改前的值、``new`` 新值；``None``＝「沒寫」），依 ``(file, path)`` 排序、同一欄位只留一筆
  （:func:`normalize`）。
- 草稿存 ``<save_dir>/tuning/drafts/<名稱>.json``（不在 ``content/``、不進 git）；不是存檔，
  格式可隨段改、不寫轉換（0.0）。預設一份 :data:`DEFAULT_DRAFT`。
- 反向改動單（還原）：:func:`reverse`。
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DEFAULT_DRAFT",
    "DRAFT_NAME_PATTERN",
    "Change",
    "Draft",
    "DraftStore",
    "merge",
    "normalize",
    "reverse",
]

DEFAULT_DRAFT: Final = "current"
DRAFT_NAME_PATTERN: Final = r"^[a-z0-9][a-z0-9_-]{0,39}$"
_FORMAT: Final = "trpg-tuning-draft/1"


class Change(BaseModel):
    """一筆改動（``old``／``new`` 為 ``None``＝那個欄位沒寫、用預設值）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str = Field(pattern=r"^[a-z0-9_]+(/[a-z0-9_]+)*\.yaml$")
    path: str = Field(min_length=1, max_length=120)
    old: int | str | tuple[str, ...] | None
    new: int | str | tuple[str, ...] | None
    """整數、骰子字串（``2d6``）、技能 ID 清單（NW-2a）；``None``＝沒寫。"""

    @property
    def key(self) -> tuple[str, str]:
        return (self.file, self.path)


class Draft(BaseModel):
    """一份草稿。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format: str = _FORMAT
    name: str = Field(pattern=DRAFT_NAME_PATTERN)
    changes: tuple[Change, ...] = ()


def normalize(changes: Iterable[Change]) -> tuple[Change, ...]:
    """同一欄位只留一筆（後到的 ``new`` 取代、``old`` 保留最早的），去掉改回原值的，依
    ``(file, path)`` 排序。"""
    merged: dict[tuple[str, str], Change] = {}
    for change in changes:
        first = merged.get(change.key)
        keep = change if first is None else change.model_copy(update={"old": first.old})
        merged[change.key] = keep
    return tuple(merged[k] for k in sorted(merged) if merged[k].old != merged[k].new)


def merge(base: Iterable[Change], more: Iterable[Change]) -> tuple[Change, ...]:
    """把 ``more`` 併進 ``base``（同欄位以 ``more`` 的新值為準）。"""
    return normalize([*base, *more])


def reverse(changes: Iterable[Change]) -> tuple[Change, ...]:
    """反向改動單（新 → 舊）。"""
    return normalize(c.model_copy(update={"old": c.new, "new": c.old}) for c in changes)


class DraftStore:
    """``<save_dir>/tuning/drafts/`` 下的草稿檔。"""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, name: str) -> Path:
        Draft(name=name)  # 名稱格式不對丟 ValidationError
        return self.root / f"{name}.json"

    def names(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.stem for p in self.root.glob("*.json"))

    def get(self, name: str) -> Draft:
        """讀草稿；沒有這份時回空草稿。"""
        path = self._path(name)
        if not path.is_file():
            return Draft(name=name)
        return Draft.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def put(self, draft: Draft) -> Draft:
        draft = draft.model_copy(update={"changes": normalize(draft.changes)})
        path = self._path(draft.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(draft.model_dump_json(indent=1) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
        return draft

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if not path.is_file():
            return False
        path.unlink()
        return True
