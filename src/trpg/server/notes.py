"""地點留言與足跡（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.7；09 9.6.10 #105）。

- 只有地點留言與足跡、留言上限 50 字；不過濾、不檢舉、不封鎖、不限次數；使用者（管理者）手動刪。
- 存檔 ``<世界資料夾>/notes.json``（``trpg-notes/1``）。**不進世界日誌**（代決 5E3-3）：留言是
  玩家文字、不影響規則、要能手動刪；照 5E1-2（帳號不進日誌）的慣例放在伺服器服務層，
  ``trpg-wlog/1`` 與重播不變。
- 每次操作都重讀檔案（管理者腳本 ``scripts/location_notes.py`` 可以從另一個程序刪）；呼叫者持有
  世界的寫入鎖。
- 留言只當資料顯示，**不送進 LLM**（守則 7）。
- 足跡從世界日誌算（唯讀）：其他角色走到這個地點的最近一次時間＋這個地點的首殺紀錄。
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.server.first_kills import FirstKill
from trpg.shared.errors import TrpgError
from trpg.world.actions import TravelAction
from trpg.world.layout import NOTES_FILE
from trpg.world.replay import WorldLogEntry
from trpg.world.save import write_atomic
from trpg.world.state import CharacterState

__all__ = [
    "BOARD_NOTES",
    "FOOTPRINT_MAX",
    "NOTES_FILE",
    "NOTES_FORMAT",
    "NOTE_MAX_LEN",
    "Footprint",
    "LocationNote",
    "LocationNoteStore",
    "NoteError",
    "NoteNotFoundError",
    "clean_note_text",
    "footprints",
]

NOTES_FORMAT: Final = "trpg-notes/1"
NOTE_MAX_LEN: Final = 50
"""留言上限（#105）。"""
BOARD_NOTES: Final = 20
"""畫面顯示最新幾則（代決 5E3-5）。"""
FOOTPRINT_MAX: Final = 10
NOTE_ID_PREFIX: Final = "n"


class NoteError(TrpgError):
    """留言不合法（422）。"""


class NoteNotFoundError(TrpgError):
    """沒有這則留言（404）。"""


class LocationNote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    note_id: str = Field(pattern=r"^n[0-9a-f]{8}$")
    region: str
    location: str
    character_id: str
    name: str
    """留言當下的角色名。"""
    text: str = Field(min_length=1, max_length=NOTE_MAX_LEN)
    at: int = Field(ge=0)


class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["trpg-notes/1"] = NOTES_FORMAT
    notes: tuple[LocationNote, ...] = ()


def clean_note_text(text: str) -> str:
    """去頭尾空白後 1～50 字、不能有控制字元（換行也不行）；不合法拋 :class:`NoteError`。"""
    cleaned = text.strip()
    if not cleaned:
        raise NoteError("留言不能是空的")
    if len(cleaned) > NOTE_MAX_LEN:
        raise NoteError(f"留言最多 {NOTE_MAX_LEN} 字（現在 {len(cleaned)} 字）")
    if any(not ch.isprintable() for ch in cleaned):
        raise NoteError("留言不能有換行或控制字元")
    return cleaned


def _new_id() -> str:
    return NOTE_ID_PREFIX + secrets.token_hex(4)


class LocationNoteStore:
    """``<世界資料夾>/notes.json`` 的讀寫。"""

    def __init__(self, root: Path, *, new_id: Callable[[], str] = _new_id) -> None:
        self.path = root / NOTES_FILE
        self._new_id = new_id
        self._cache: tuple[tuple[int, int] | None, tuple[LocationNote, ...]] | None = None
        """記憶體快取（6C-R3）：（檔案的修改時間與大小, 留言）。讀過一次或寫入後就有；檔案被別的
        程式改過（管理腳本 ``scripts/notes.py``）時重讀；:meth:`forget` 清掉。"""

    def forget(self) -> None:
        """丟掉記憶體快取，下次重讀留言檔。"""
        self._cache = None

    def _stamp(self) -> tuple[int, int] | None:
        try:
            info = self.path.stat()
        except OSError:
            return None
        return info.st_mtime_ns, info.st_size

    def all(self) -> tuple[LocationNote, ...]:
        stamp = self._stamp()
        if self._cache is not None and self._cache[0] == stamp:
            return self._cache[1]
        notes = self._read()
        self._cache = (stamp, notes)
        return notes

    def _read(self) -> tuple[LocationNote, ...]:
        if not self.path.is_file():
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise NoteError(f"留言檔 {self.path} 讀不了：{exc}") from exc
        if not isinstance(raw, dict) or raw.get("format") != NOTES_FORMAT:
            found = raw.get("format") if isinstance(raw, dict) else None
            raise NoteError(f"不認得的留言檔格式：{found!r}（需要 {NOTES_FORMAT}）")
        try:
            return _File.model_validate(raw).notes
        except ValidationError as exc:
            raise NoteError(f"留言檔 {self.path} 的內容不合法：{exc}") from exc

    def _write(self, notes: Iterable[LocationNote]) -> None:
        data = _File(notes=tuple(notes))
        text = json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2)
        write_atomic(self.path, text + "\n")
        self._cache = (self._stamp(), data.notes)

    def at(self, region: str, location: str, limit: int = BOARD_NOTES) -> list[LocationNote]:
        """這個地點的留言，新的在前。"""
        here = [n for n in self.all() if n.region == region and n.location == location]
        here.sort(key=lambda n: (n.at, n.note_id), reverse=True)
        return here[:limit]

    def add(self, char: CharacterState, text: str, now: int) -> LocationNote:
        """在角色**現在所在**的地點留一則（所以不必另外檢查「站在那裡」）。"""
        cleaned = clean_note_text(text)
        notes = self.all()
        taken = {n.note_id for n in notes}
        note_id = self._new_id()
        while note_id in taken:  # pragma: no cover - 機率極低
            note_id = self._new_id()
        note = LocationNote(
            note_id=note_id,
            region=char.region,
            location=char.location,
            character_id=char.character_id,
            name=char.hero.name_zh,
            text=cleaned,
            at=now,
        )
        self._write((*notes, note))
        return note

    def delete(self, note_id: str, *, author: str | None = None) -> LocationNote:
        """刪一則留言。``author``＝角色 ID 時只能刪這個角色留的（5E-3b：作者刪自己的留言；別人的
        一律當作找不到，不洩漏是誰的）；``None``＝管理者，哪則都能刪。"""
        notes = self.all()
        found = next((n for n in notes if n.note_id == note_id), None)
        if found is None or (author is not None and found.character_id != author):
            raise NoteNotFoundError(f"找不到留言 {note_id}")
        self._write(n for n in notes if n.note_id != note_id)
        return found


@dataclass(frozen=True)
class Footprint:
    kind: Literal["visit", "first_kill"]
    character_id: str
    name: str
    at: int
    target_name_zh: str | None = None
    """首殺的精英名（``first_kill``）。"""


def footprints(
    entries: Iterable[WorldLogEntry],
    names: Mapping[str, str],
    kills: Iterable[FirstKill],
    *,
    region: str,
    location: str,
    exclude: str,
    region_of: Callable[[str], str | None],
) -> list[Footprint]:
    """其他角色在這個地點的足跡（新的在前、最多 :data:`FOOTPRINT_MAX` 筆）。

    ``region_of(location)``：地點 ID 屬於哪一區（日誌只記 ``travel`` 的目的地，區域由地點圖查）。"""
    visits: dict[str, int] = {}
    if region_of(location) == region:
        for entry in entries:
            action = entry.action
            if (
                isinstance(action, TravelAction)
                and action.to == location
                and entry.character_id != exclude
            ):
                visits[entry.character_id] = max(visits.get(entry.character_id, 0), entry.now)
    found = [Footprint("visit", cid, names.get(cid, cid), at) for cid, at in sorted(visits.items())]
    found += [
        Footprint("first_kill", k.character_id, k.name, k.at, k.target_name_zh)
        for k in kills
        if k.region == region
        and k.location == location
        and k.character_id != exclude
        and k.kind == "elite"  # 賽季 Boss 首殺在裂界門，不留在出發的城鎮（5F-3）
    ]
    found.sort(key=lambda f: (f.at, f.kind, f.character_id), reverse=True)
    return found[:FOOTPRINT_MAX]
