"""世界動作日誌（``trpg-wlog/1``）與重播（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.4、6.4）。

世界與角色的變化一律由 append-only 的世界動作日誌重播得到，快照只是快取。所有世界動作經 API 層的
單一寫入佇列依序套用，每筆帶伺服器序號 ``seq``；重播照序號。

本段的重播從「初始世界快照＋初始角色快照」開始（代決 5A2-8：角色建立在 5E-1 才進日誌）。

6L-2：每筆另記這個動作用到的生成內容（``generated``，:mod:`trpg.world.generated`：閃現提議、劇情
技能的元素與文字、機遇的三選一，連同來源）。重播只讀這些紀錄，**完全不呼叫 LLM**。

6T-1a：交易那一筆同時改兩個角色（寄信、拒收、取回過期的信）：另記 ``counterpart``（另一個角色）與
``counterpart_actor``（他的帳號）；重播時兩個角色一起從那一筆的結果更新（``trpg-wlog/9`` 起）。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.content.library import ContentLibrary
from trpg.world.actions import WorldAction, WorldEvent
from trpg.world.errors import WorldReplayError
from trpg.world.generated import Generated, recorded, using_generated
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import world_step

__all__ = ["ReplayResult", "WorldLogEntry", "replay"]


class WorldLogEntry(BaseModel):
    """日誌的一筆：伺服器序號、時間（UTC 秒）、角色、動作。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seq: int = Field(ge=0)
    now: int = Field(ge=0)
    character_id: str = Field(pattern=ID_PATTERN)
    action: WorldAction
    actor: str | None = None
    """做這個動作的帳號 ID（Phase 5F-1：世界事件門檻的上線人數）；``None``＝用角色 ID（開發模式、
    舊日誌）。"""
    generated: tuple[Generated, ...] = ()
    """這個動作最後給出的生成內容與來源（6L-2，依發生順序）；舊日誌沒有＝全部用組合器、模板與
    內容版。"""
    counterpart: str | None = Field(default=None, pattern=ID_PATTERN)
    """同時改的另一個角色（6T-1a 交易）；``None``＝只改 ``character_id``。"""
    counterpart_actor: str | None = None
    """另一個角色的帳號 ID（6T-1a）；``None``＝用他的角色 ID。"""


@dataclass(frozen=True)
class ReplayResult:
    world: WorldState
    characters: dict[str, CharacterState]
    """角色 ID → 狀態（依 ID 排序）。"""
    events: tuple[tuple[int, WorldEvent], ...]
    """``(seq, 事件)``，依套用順序。"""


def replay(
    library: ContentLibrary,
    world: WorldState,
    characters: Mapping[str, CharacterState],
    entries: Iterable[WorldLogEntry],
) -> ReplayResult:
    """從初始快照依序套用日誌。``seq`` 必須嚴格遞增、``now`` 不可倒退，否則拋
    :class:`WorldReplayError`；動作不合法時照樣拋 :class:`~trpg.world.errors.WorldActionError`
    （正常的日誌只會有通過檢查的動作）。"""
    chars = dict(characters)
    events: list[tuple[int, WorldEvent]] = []
    last_seq: int | None = None
    last_now: int | None = None
    for entry in entries:
        if last_seq is not None and entry.seq <= last_seq:
            raise WorldReplayError(f"序號必須遞增：{entry.seq} 在 {last_seq} 之後")
        if last_now is not None and entry.now < last_now:
            raise WorldReplayError(f"第 {entry.seq} 筆的時間倒退：{entry.now} < {last_now}")
        char = chars.get(entry.character_id)
        if char is None:
            raise WorldReplayError(f"第 {entry.seq} 筆：找不到角色 {entry.character_id}")
        other = None if entry.counterpart is None else chars.get(entry.counterpart)
        if entry.counterpart is not None and other is None:
            raise WorldReplayError(f"第 {entry.seq} 筆：找不到角色 {entry.counterpart}")
        with using_generated(recorded(entry.generated)):  # 6L-2：只讀日誌，不呼叫 LLM
            result = world_step(
                library,
                world,
                char,
                entry.action,
                entry.now,
                actor=entry.actor,
                other=other,
                other_actor=entry.counterpart_actor,
            )
        world = result.world
        chars[entry.character_id] = result.char
        if entry.counterpart is not None and result.other is not None:  # 6T-1a：交易的另一方
            chars[entry.counterpart] = result.other
        events += [(entry.seq, event) for event in result.events]
        last_seq, last_now = entry.seq, entry.now
    return ReplayResult(world=world, characters=dict(sorted(chars.items())), events=tuple(events))
