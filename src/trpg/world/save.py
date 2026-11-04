"""大世界的存檔格式（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.5）。

| 資料 | 格式 |
|---|---|
| 世界快照 | ``trpg-world/3``（一個 JSON 物件，:class:`~trpg.world.state.WorldState`） |
| 角色 | ``trpg-char/6``（一角色一個 JSON 物件，:class:`~trpg.world.state.CharacterState`） |
| 世界動作日誌 | ``trpg-wlog/7``（JSON Lines：第一行 ``{"format": "trpg-wlog/7"}``，之後一行一筆
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

**Phase 6C-2**：``trpg-char/3`` 照讀（只多了遭遇接觸的選填欄位 ``enemy_at``），讀進來就是
``trpg-char/4``。``trpg-wlog/4`` 也是舊規則寫的（6C-2 起碰到地圖上的敵人就地切 12×12 戰場，``fight``
的步驟是照模板地圖記的），處理同上：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/5``。
**Phase 6C-6**：同一版 ``trpg-char/4`` 也多了選填欄位 ``visited_locations``（和 6C-2
一起合進來，沒有另升版號）。去過的地點只是另外記下來，不改任何規則。

**Phase 6C-5**：``trpg-char/4`` 照讀（只多了選填欄位 ``field_event``、``sneaking``、
``object_uses``），讀進來就是 ``trpg-char/5``。``trpg-wlog/5`` 也是舊規則寫的（6C-5 起有實地地圖的
地點改成走到隱藏入口 3 格內才感知、事件放在地圖上碰到才開），處理同上：照讀、規則已變、不能重播，
寫回時標頭改成 ``trpg-wlog/6``。

**Phase 6C-R2**：``trpg-world/2`` 照讀（只多了 ``defeated_spawns`` 的選填欄位 ``wins``），讀進來就是
``trpg-world/3``。``trpg-wlog/6`` 也是舊規則寫的（6C-R2 起地圖上每隊的陣容改由世界種子＋(區域, 地點,
隊伍)＋重生世代衍生；6C-5b 起營火點的清空條件、新手固定戰照步驟消失、走路抵達格也感知；21.10 第 20
條起走過渡口算一步），處理同上：照讀、規則已變、不能重播，寫回時標頭改成 ``trpg-wlog/7``。

**Phase 6C-R3**：``trpg-wlog/7`` 的標頭另記 ``rules_key``（:func:`log_rules_key`：
``戰鬥紀錄版號|規則包雜湊|內容 digest``，比照 :func:`trpg.server.league.rules_key`）。讀檔的一方
（:class:`trpg.api.world.WorldStore`）拿它和目前的規則鍵比，不一樣（或沒記）就把 ``stale_through``
設成最後一筆，處理同上：規則已變、不能重播。之後內容或規則改了不必再手動升版號（版號只留給格式
變更）。日誌改成只 append：每個動作附加一行（:func:`append_log_line`）；標頭只在 ``stale_through``
或 ``rules_key`` 改變、格式升版時整份重寫（:func:`write_atomic`）。

**Phase 6D-R1**：規則鍵多一段 :data:`WORLD_RULES_VERSION`（``戰鬥紀錄版號|w世界規則版號|規則包雜湊|
內容 digest``）：內容 digest 只看資料，世界規則的**程式**改了（例如走路、遇敵、感知的判法）資料
不會變，所以改了這類程式要手動把它加一（``docs/開發PM交接.md`` 6.6）。讀檔時截掉寫到一半的最後
一行（沒有換行結尾）由 :func:`read_log`／:func:`log_lines` 統一處理，所有讀者共用
（:attr:`WorldLog.torn`）。

**Phase 6D-R2**：``trpg-char/5`` 照讀（只多了 ``field_visit`` 的選填欄位 ``generations``：進圖時
每隊的重生世代，這一趟的陣容固定用它），讀進來就是 ``trpg-char/6``。陣容種子的判法改了，
:data:`WORLD_RULES_VERSION` 升成 2（舊日誌標成規則已變、不能重播）。
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ValidationError

from trpg.content.library import ContentLibrary
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.engine.runner import LOG_FORMAT
from trpg.roguelite.save import ruleset_hash
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
    "WORLD_RULES_VERSION",
    "WorldLog",
    "append_log_line",
    "content_digest",
    "dumps_char",
    "dumps_log",
    "dumps_log_entry",
    "dumps_log_header",
    "dumps_world",
    "loads_char",
    "loads_log",
    "loads_world",
    "log_lines",
    "log_rules_key",
    "read_log",
    "write_atomic",
]

WLOG_FORMAT: Final = "trpg-wlog/7"
LEGACY_WLOG_FORMATS: Final = frozenset(
    {"trpg-wlog/1", "trpg-wlog/2", "trpg-wlog/3", "trpg-wlog/4", "trpg-wlog/5", "trpg-wlog/6"}
)
"""照讀、但標成「規則已變、不能重播」的舊日誌格式。"""
STALE_LOG_ZH: Final = "規則已變、不能重播"
WORLD_RULES_VERSION: Final = 2
"""世界規則程式的版號（6D-R1）：改了世界規則的程式（``trpg.world`` 裡會讓同樣的日誌重播出不同結果
的改動）時手動加一；記在日誌的規則鍵裡（:func:`log_rules_key`），舊日誌就標成規則已變、不能重播。
只改內容資料不用加（內容 digest 會變）。"""


@dataclass(frozen=True)
class WorldLog:
    """讀進來的世界動作日誌。"""

    entries: tuple[WorldLogEntry, ...]
    stale_through: int | None = None
    """這個序號（含）以前的紀錄是舊規則寫的：規則已變、不能重播。``None``＝全部能重播。"""
    rules_key: str | None = None
    """標頭記的規則鍵（6C-R3，:func:`log_rules_key`）；``None``＝沒記（6C-R3 以前寫的、舊格式）。"""
    header: str = field(default="", compare=False)
    """標頭那一行的原文（判斷要不要重寫標頭用）。"""
    torn: bool = field(default=False, compare=False)
    """最後一行沒有換行結尾（append 寫到一半中斷），已略過那一行（6D-R1）。"""

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


def dumps_log_header(*, stale_through: int | None = None, rules_key: str | None = None) -> str:
    """日誌的標頭（一行，不含換行）。鍵的順序固定：``format``、``rules_key``、``stale_through``、
    ``stale_zh``。"""
    header: dict[str, object] = {"format": WLOG_FORMAT}
    if rules_key is not None:
        header["rules_key"] = rules_key
    if stale_through is not None:
        header |= {"stale_through": stale_through, "stale_zh": STALE_LOG_ZH}
    return json.dumps(header, ensure_ascii=False)


def dumps_log(
    entries: Iterable[WorldLogEntry],
    *,
    stale_through: int | None = None,
    rules_key: str | None = None,
) -> str:
    """整份日誌（標頭＋每筆一行，結尾換行）。``stale_through`` 有值時，標頭記下舊規則的紀錄
    到哪一筆；``rules_key`` 有值時記下寫入時的規則鍵（6C-R3）。"""
    header = dumps_log_header(stale_through=stale_through, rules_key=rules_key)
    lines = [header, *(dumps_log_entry(e) for e in entries)]
    return "\n".join(lines) + "\n"


def append_log_line(path: Path, entry: WorldLogEntry) -> None:
    """在已存在、以換行結尾的日誌檔尾端附加一筆（6C-R3）；結果和 :func:`dumps_log` 整份重寫的
    內容逐字相同。"""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(dumps_log_entry(entry) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def content_digest(library: ContentLibrary) -> str:
    """內容的確定性 digest（6C-R3）：全部內容檔（:func:`~trpg.roguelite.save.ruleset_hash`，依相對
    路徑排序、排序鍵 JSON）再加上內容庫裡的實地地圖（依地圖 ID）與大世界規則（測試用
    ``dataclasses.replace`` 換掉、沒進 ``files`` 的也算到）。不用內建 ``hash()``。"""
    maps = library.field_maps
    fields = [[k, maps[k].model_dump(mode="json")] for k in sorted(maps)]
    rules = None if library.world_rules is None else library.world_rules.model_dump(mode="json")
    text = json.dumps(
        [ruleset_hash(library), fields, rules],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def log_rules_key(library: ContentLibrary) -> str:
    """世界日誌的規則鍵（6C-R3）：``戰鬥紀錄版號|w世界規則版號|規則包雜湊|內容 digest``（比照
    :func:`trpg.server.league.rules_key`；世界規則版號 :data:`WORLD_RULES_VERSION` 是 6D-R1 加的）。
    和日誌標頭記的不同＝規則或內容改了，舊紀錄不能重播。"""
    ruleset = hash_ruleset(library.ruleset)
    return f"{LOG_FORMAT}|w{WORLD_RULES_VERSION}|{ruleset}|{content_digest(library)[:16]}"


def _log_header(line: str) -> tuple[int | None, str | None]:
    """讀標頭，回傳 ``(stale_through, rules_key)``（舊格式的 ``stale_through``＝``-1``，表示
    「全部」，由 :func:`read_log` 換成最後一筆的序號）。"""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise WorldSaveFormatError(f"不是合法的 JSON：{exc}") from exc
    if isinstance(raw, dict) and raw.get("format") in LEGACY_WLOG_FORMATS:
        return -1, None
    header = _parse_object(line, WLOG_FORMAT)
    key = header.get("rules_key")
    if key is not None and not isinstance(key, str):
        raise WorldSaveFormatError(f"日誌標頭的 rules_key 不合法：{key!r}")
    stale = header.get("stale_through")
    if stale is None:
        return None, key
    if not isinstance(stale, int) or isinstance(stale, bool) or stale < 0:
        raise WorldSaveFormatError(f"日誌標頭的 stale_through 不合法：{stale!r}")
    return stale, key


def log_lines(text: str) -> tuple[list[str], bool]:
    """日誌的完整行（略過空行）與「最後一行有沒有被丟掉」（6D-R1）：最後一行沒有換行結尾＝append
    寫到一半中斷（那個動作的角色存檔也還沒寫），丟掉那一行。所有讀日誌的地方都經過這裡。"""
    torn = bool(text) and not text.endswith("\n")
    if torn:
        text = text[: text.rfind("\n") + 1]
    return [line for line in text.splitlines() if line.strip()], torn


def read_log(text: str) -> WorldLog:
    """讀整份日誌（含舊格式；見模組說明）。寫到一半的最後一行略過（:func:`log_lines`）；連標頭都
    沒寫完＝空的日誌（``torn`` 為真）。"""
    lines, torn = log_lines(text)
    if not lines:
        if torn:
            return WorldLog(entries=(), torn=True)
        raise WorldSaveFormatError("日誌是空的（缺少標頭）")
    stale, key = _log_header(lines[0])
    entries = _log_entries(lines)
    if stale == -1:
        stale = entries[-1].seq if entries else None
    return WorldLog(entries=entries, stale_through=stale, rules_key=key, header=lines[0], torn=torn)


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
