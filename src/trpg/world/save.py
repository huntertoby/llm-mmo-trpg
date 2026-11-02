"""大世界的存檔格式（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.5）。

| 資料 | 格式 |
|---|---|
| 世界快照 | ``trpg-world/1``（一個 JSON 物件，:class:`~trpg.world.state.WorldState`） |
| 角色 | ``trpg-char/1``（一角色一個 JSON 物件，:class:`~trpg.world.state.CharacterState`） |
| 世界動作日誌 | ``trpg-wlog/1``（JSON Lines：第一行 ``{"format": "trpg-wlog/1"}``，之後一行一筆
  :class:`~trpg.world.replay.WorldLogEntry`） |

JSON 一律排序鍵、UTF-8 不跳脫，同樣的狀態得到逐字相同的檔案。讀檔時 ``format`` 不認得就拒絕
（:class:`~trpg.world.errors.WorldSaveFormatError`）。寫檔走暫存檔＋原子改名（:func:`write_atomic`）。
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ValidationError

from trpg.world.errors import WorldSaveFormatError
from trpg.world.replay import WorldLogEntry
from trpg.world.state import CHAR_FORMAT, WORLD_FORMAT, CharacterState, WorldState

__all__ = [
    "WLOG_FORMAT",
    "dumps_char",
    "dumps_log",
    "dumps_log_entry",
    "dumps_world",
    "loads_char",
    "loads_log",
    "loads_world",
    "write_atomic",
]

WLOG_FORMAT: Final = "trpg-wlog/1"


def _dumps(model: BaseModel, *, indent: int | None) -> str:
    separators = None if indent is not None else (",", ":")
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
        separators=separators,
    )


def _parse_object(text: str, expected: str) -> dict[str, Any]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorldSaveFormatError(f"不是合法的 JSON：{exc}") from exc
    if not isinstance(raw, dict):
        raise WorldSaveFormatError("存檔必須是 JSON 物件")
    found = raw.get("format")
    if found != expected:
        raise WorldSaveFormatError(f"不認得的存檔格式：{found!r}（需要 {expected}）")
    return raw


def _validate[M: BaseModel](model: type[M], raw: object) -> M:
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise WorldSaveFormatError(f"{model.__name__} 的內容不合法：{exc}") from exc


def dumps_world(world: WorldState) -> str:
    return _dumps(world, indent=2) + "\n"


def loads_world(text: str) -> WorldState:
    return _validate(WorldState, _parse_object(text, WORLD_FORMAT))


def dumps_char(char: CharacterState) -> str:
    return _dumps(char, indent=2) + "\n"


def loads_char(text: str) -> CharacterState:
    return _validate(CharacterState, _parse_object(text, CHAR_FORMAT))


def dumps_log_entry(entry: WorldLogEntry) -> str:
    """日誌的一行（不含換行）。"""
    return _dumps(entry, indent=None)


def dumps_log(entries: Iterable[WorldLogEntry]) -> str:
    """整份日誌（標頭＋每筆一行，結尾換行）。"""
    lines = [json.dumps({"format": WLOG_FORMAT}), *(dumps_log_entry(e) for e in entries)]
    return "\n".join(lines) + "\n"


def loads_log(text: str) -> tuple[WorldLogEntry, ...]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise WorldSaveFormatError("日誌是空的（缺少標頭）")
    _parse_object(lines[0], WLOG_FORMAT)
    entries: list[WorldLogEntry] = []
    for number, line in enumerate(lines[1:], start=2):
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorldSaveFormatError(f"日誌第 {number} 行不是合法的 JSON：{exc}") from exc
        entries.append(_validate(WorldLogEntry, raw))
    return tuple(entries)


def write_atomic(path: Path, text: str) -> None:
    """寫入 ``path``：先寫同資料夾的暫存檔再原子改名（中斷時舊檔不會壞掉）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
