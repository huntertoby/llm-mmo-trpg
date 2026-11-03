"""全服首殺紀錄（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.5）。

- 現有資料能給的首殺：**全服第一個打倒某種精英的角色**
  （``InsightGainedEvent(source="elite:<種類>")``，06 6.34.2；代決 5E3-1）。
  賽季 Boss 首殺（#101）是 5F，用同一個格式（``kind`` 欄位）。
- :class:`~trpg.api.world.WorldStore` 每個成功的世界動作之後（世界的寫入鎖內、日誌寫完後）呼叫
  :meth:`FirstKillRegistry.record`；同一種只記第一筆。
- 存檔 ``<世界資料夾>/first_kills.json``（``trpg-firstkills/1``）。這是由世界日誌決定的衍生資料
  （日誌序號 ``seq``＋時間戳可查證），不進 ``trpg-world/1``、不影響重播。Bot 只讀這個檔（31.6）。
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.content.library import ContentLibrary
from trpg.shared.errors import TrpgError
from trpg.world.actions import InsightGainedEvent, WorldEvent
from trpg.world.save import write_atomic
from trpg.world.season import FIRST_SEASON_ID
from trpg.world.state import CharacterState

__all__ = [
    "FIRST_KILLS_FILE",
    "FIRST_KILLS_FORMAT",
    "FirstKill",
    "FirstKillError",
    "FirstKillRegistry",
    "elite_kind_name",
    "load_first_kills",
]

FIRST_KILLS_FORMAT: Final = "trpg-firstkills/1"
FIRST_KILLS_FILE: Final = "first_kills.json"
ELITE_SOURCE: Final = "elite:"


class FirstKillError(TrpgError):
    """首殺紀錄檔壞了或格式不認得。"""


class FirstKill(BaseModel):
    """一筆全服首殺。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["elite", "season_boss"]
    target: str
    """精英種類（``<單位>`` 或 ``<單位>+<詞綴>``）；賽季 Boss 的 ID（5F）。"""
    target_name_zh: str
    character_id: str
    name: str
    """當下的角色名（玩家文字；放進公告前要中和，31.6）。"""
    region: str
    location: str
    seq: int = Field(ge=0)
    """世界日誌的序號（查證用）。"""
    at: int = Field(ge=0)
    """UTC 秒。"""
    season_id: str = FIRST_SEASON_ID
    """首殺的賽季（Phase 5D-R2；紀念類，季末保留）。舊檔沒有這個欄位＝第一季
    （:data:`~trpg.world.season.FIRST_SEASON_ID`；欄位加上之前還沒有任何季末重置）。"""


class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["trpg-firstkills/1"] = FIRST_KILLS_FORMAT
    kills: tuple[FirstKill, ...] = ()


def elite_kind_name(library: ContentLibrary, kind: str) -> str:
    """精英種類的中文名（``<單位>+<詞綴>`` → 「單位（詞綴）」；找不到就用 ID）。"""
    unit, _, affix = kind.partition("+")
    catalog = library.enemy_catalog()
    try:
        name = catalog.template(unit).name_zh
    except KeyError:
        name = unit
    if affix:
        try:
            name = f"{name}（{catalog.affix(affix).name_zh}）"
        except KeyError:
            name = f"{name}（{affix}）"
    return name


def load_first_kills(path: Path) -> tuple[FirstKill, ...]:
    """讀首殺紀錄（檔案不存在＝沒有首殺）；依 ``seq`` 排序。"""
    if not path.is_file():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FirstKillError(f"首殺紀錄 {path} 讀不了：{exc}") from exc
    if not isinstance(raw, dict) or raw.get("format") != FIRST_KILLS_FORMAT:
        found = raw.get("format") if isinstance(raw, dict) else None
        raise FirstKillError(f"不認得的首殺紀錄格式：{found!r}（需要 {FIRST_KILLS_FORMAT}）")
    try:
        data = _File.model_validate(raw)
    except ValidationError as exc:
        raise FirstKillError(f"首殺紀錄 {path} 的內容不合法：{exc}") from exc
    return tuple(sorted(data.kills, key=lambda k: k.seq))


class FirstKillRegistry:
    """``<世界資料夾>/first_kills.json`` 的讀寫（只有遊戲伺服器寫；呼叫者持有世界的寫入鎖）。"""

    def __init__(self, library: ContentLibrary, root: Path) -> None:
        self.library = library
        self.path = root / FIRST_KILLS_FILE

    def all(self) -> tuple[FirstKill, ...]:
        return load_first_kills(self.path)

    def record(
        self,
        char: CharacterState,
        events: Iterable[WorldEvent],
        *,
        seq: int,
        now: int,
        season_id: str = FIRST_SEASON_ID,
    ) -> tuple[FirstKill, ...]:
        """把這次動作的精英首殺裡、這一季全服還沒人打過的記下來；回傳新記的。

        首殺按賽季算（5D-R2）：上一季打過的種類，這一季的第一個仍然是首殺。"""
        kinds = [
            e.source.removeprefix(ELITE_SOURCE)
            for e in events
            if isinstance(e, InsightGainedEvent) and e.source.startswith(ELITE_SOURCE)
        ]
        if not kinds:
            return ()
        existing = self.all()
        taken = {(k.kind, k.target) for k in existing if k.season_id == season_id}
        location = char.last_battle.location if char.last_battle is not None else char.location
        added = tuple(
            FirstKill(
                kind="elite",
                target=kind,
                target_name_zh=elite_kind_name(self.library, kind),
                character_id=char.character_id,
                name=char.hero.name_zh,
                region=char.region,
                location=location,
                seq=seq,
                at=now,
                season_id=season_id,
            )
            for kind in sorted(set(kinds))
            if ("elite", kind) not in taken
        )
        if added:
            data = _File(kills=(*existing, *added))
            text = json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2)
            write_atomic(self.path, text + "\n")
        return added
