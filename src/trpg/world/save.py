"""大世界的存檔格式（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.5）。

| 資料 | 格式 |
|---|---|
| 世界快照 | ``trpg-world/2``（一個 JSON 物件，:class:`~trpg.world.state.WorldState`） |
| 角色 | ``trpg-char/3``（一角色一個 JSON 物件，:class:`~trpg.world.state.CharacterState`） |
| 世界動作日誌 | ``trpg-wlog/4``（JSON Lines：第一行 ``{"format": "trpg-wlog/4"}``，之後一行一筆
  :class:`~trpg.world.replay.WorldLogEntry`） |

JSON 一律排序鍵、UTF-8 不跳脫，同樣的狀態得到逐字相同的檔案。讀檔時 ``format`` 不認得就拒絕
（:class:`~trpg.world.errors.WorldSaveFormatError`）。寫檔走暫存檔＋原子改名（:func:`write_atomic`）。

**舊格式（Phase 6B-2）**：

- ``trpg-char/1`` 照讀，讀進來就是 ``trpg-char/2``（只多了選填欄位）。
- ``trpg-wlog/1`` 照讀，但那些紀錄是舊規則寫的（6B-2 起，有實地地圖的地點不能 ``travel``），
  **規則已變、不能重播**（同 ``LOG_FORMAT`` 遞增時的處理）。下一次寫回時標頭改成 ``trpg-wlog/2``，
  另記 ``stale_through``（最後一筆舊紀錄的序號）與 ``stale_zh``；重播只能從那之後開始
  （:attr:`WorldLog.stale_through`）。

**Phase 6C-1**：``trpg-char/2`` 照讀（只多了選填欄位 ``field_visit``、遭遇的 ``contact``），讀進來
就是 ``trpg-char/3``。``trpg-wlog/2`` 也是舊規則寫的（6C-1 起有實地地圖的地點不再擲遇敵，改成
看得見的敵人），處理同 ``trpg-wlog/1``：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/3``。

**Phase 6C-1b**：``trpg-world/1`` 照讀（只多了選填欄位 ``defeated_spawns``），讀進來就是
``trpg-world/2``。``trpg-wlog/3`` 也是舊規則寫的（6C-1b 起進圖寬限、每隊清空、``personal``、
``day_phase``），處理同上：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/4``。
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ValidationError

from trpg.world.errors import WorldSaveFormatError
from trpg.world.replay import WorldLogEntry
from trpg.world.state import (
    CHAR_FORMAT,
    LEGACY_CHAR_FORMATS,
    LEGACY_WORLD_FORMATS,
    WORLD_FORMAT,
    CharacterState,
    WorldState,
)

__all__ = [
    "LEGACY_WLOG_FORMATS",
    "STALE_LOG_ZH",
    "WLOG_FORMAT",
    "WorldLog",
    "dumps_char",
    "dumps_log",
    "dumps_log_entry",
    "dumps_world",
    "loads_char",
    "loads_log",
    "loads_world",
    "read_log",
    "write_atomic",
]

WLOG_FORMAT: Final = "trpg-wlog/4"
LEGACY_WLOG_FORMATS: Final = frozenset({"trpg-wlog/1", "trpg-wlog/2", "trpg-wlog/3"})
"""照讀、但標成「規則已變、不能重播」的舊日誌格式。"""
STALE_LOG_ZH: Final = "規則已變、不能重播"


@dataclass(frozen=True)
class WorldLog:
    """讀進來的世界動作日誌。"""

    entries: tuple[WorldLogEntry, ...]
    stale_through: int | None = None
    """這個序號（含）以前的紀錄是舊規則寫的：規則已變、不能重播。``None``＝全部能重播。"""

    @property
    def stale_zh(self) -> str | None:
        return None if self.stale_through is None else STALE_LOG_ZH


def _dumps(model: BaseModel, *, indent: int | None) -> str:
    separators = None if indent is not None else (",", ":")
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
        separators=separators,
    )


def _parse_object(text: str, expected: str, legacy: frozenset[str] = frozenset()) -> dict[str, Any]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorldSaveFormatError(f"不是合法的 JSON：{exc}") from exc
    if not isinstance(raw, dict):
        raise WorldSaveFormatError("存檔必須是 JSON 物件")
    found = raw.get("format")
    if found != expected and found not in legacy:
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
    return _validate(WorldState, _parse_object(text, WORLD_FORMAT, LEGACY_WORLD_FORMATS))


def dumps_char(char: CharacterState) -> str:
    return _dumps(char, indent=2) + "\n"


def loads_char(text: str) -> CharacterState:
    return _validate(CharacterState, _parse_object(text, CHAR_FORMAT, LEGACY_CHAR_FORMATS))


def dumps_log_entry(entry: WorldLogEntry) -> str:
    """日誌的一行（不含換行）。"""
    return _dumps(entry, indent=None)


def dumps_log(entries: Iterable[WorldLogEntry], *, stale_through: int | None = None) -> str:
    """整份日誌（標頭＋每筆一行，結尾換行）。``stale_through`` 有值時，標頭記下舊規則的紀錄
    到哪一筆。"""
    header: dict[str, object] = {"format": WLOG_FORMAT}
    if stale_through is not None:
        header |= {"stale_through": stale_through, "stale_zh": STALE_LOG_ZH}
    lines = [json.dumps(header, ensure_ascii=False), *(dumps_log_entry(e) for e in entries)]
    return "\n".join(lines) + "\n"


def _log_header(line: str) -> int | None:
    """讀標頭，回傳 ``stale_through``（舊格式＝``-1``，表示「全部」，由 :func:`read_log` 換成
    最後一筆的序號）。"""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise WorldSaveFormatError(f"不是合法的 JSON：{exc}") from exc
    if isinstance(raw, dict) and raw.get("format") in LEGACY_WLOG_FORMATS:
        return -1
    header = _parse_object(line, WLOG_FORMAT)
    stale = header.get("stale_through")
    if stale is None:
        return None
    if not isinstance(stale, int) or isinstance(stale, bool) or stale < 0:
        raise WorldSaveFormatError(f"日誌標頭的 stale_through 不合法：{stale!r}")
    return stale


def read_log(text: str) -> WorldLog:
    """讀整份日誌（含舊格式；見模組說明）。"""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise WorldSaveFormatError("日誌是空的（缺少標頭）")
    stale = _log_header(lines[0])
    entries = _log_entries(lines)
    if stale == -1:
        stale = entries[-1].seq if entries else None
    return WorldLog(entries=entries, stale_through=stale)


def loads_log(text: str) -> tuple[WorldLogEntry, ...]:
    """整份日誌的紀錄（含舊格式的；要知道能不能重播用 :func:`read_log`）。"""
    return read_log(text).entries


def _log_entries(lines: list[str]) -> tuple[WorldLogEntry, ...]:
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
