"""「你不在的時候」摘要（Phase 5F-1b；09 9.6.10 #103 的 5F-1 代決：玩家下次上線時跳一則摘要）。

內容：世界事件的成敗、懸賞被誰搶下、新開放的區域；範圍是角色上次看過（``news_seen_at``）到現在。
看過之後前端送 ``news_seen`` 世界動作（``until``＝這份摘要的 ``as_of``），寫進角色狀態，下次就不再跳
（走世界動作日誌，可重播）。用「換日後」的世界算（同公告板；只算不寫檔）。地點名照看的人套隱藏
地點的提示語（5C-3f）；自己搶下的懸賞不列。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from trpg.content.library import ContentLibrary
from trpg.content.world_season import WorldEventDef
from trpg.server.announce import region_name
from trpg.world.calendar import day_of, day_start
from trpg.world.narration import location_name_for
from trpg.world.state import CharacterState, WorldEventState, WorldState

__all__ = ["AbsenceItemView", "AbsenceView", "absence_summary"]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AbsenceItemView(_ApiModel):
    """摘要的一行。"""

    kind: str
    """``world_event``（世界事件成敗）、``bounty``（懸賞被搶下）、``opened``（新開放的區域）。"""
    at: int
    """發生的 UTC 秒數（排序用）。"""
    text_zh: str


class AbsenceView(_ApiModel):
    """``GET /api/world/characters/{id}/absence``：沒有新消息時 ``items`` 為空（前端不跳）。"""

    since: int
    """從這個時刻之後（角色上次看過的時刻；舊存檔＝開賽）。"""
    as_of: int
    """算到的時刻；看過時把它當 ``news_seen`` 動作的 ``until`` 送回。"""
    items: tuple[AbsenceItemView, ...] = ()


@dataclass(frozen=True)
class _Resolved:
    event: WorldEventDef
    state: WorldEventState
    at: int


def _resolved_at(library: ContentLibrary, state: WorldEventState) -> int | None:
    if state.resolved_at is not None:
        return state.resolved_at
    return None if state.resolved_day is None else day_start(library, state.resolved_day)


def _resolved(library: ContentLibrary, world: WorldState, since: int, now: int) -> list[_Resolved]:
    season = library.world_season
    if season is None:
        return []
    found: list[_Resolved] = []
    for event in season.world_events:
        state = world.world_event(event.id)
        if state is None or state.status == "active":
            continue
        at = _resolved_at(library, state)
        if at is not None and since < at <= now:
            found.append(_Resolved(event=event, state=state, at=at))
    return found


def _event_line(library: ContentLibrary, row: _Resolved) -> str:
    succeeded = row.state.status == "succeeded"
    effect = row.event.on_success if succeeded else row.event.on_failure
    text = f"世界事件「{row.event.name_zh}」{'成功' if succeeded else '失敗'}"
    text += f"（{row.state.progress}／{row.state.target}）"
    bonus = [f"{region_name(library, b.region)}建議等級 +{b.amount}" for b in effect.level_bonus]
    return text + ("，" + "、".join(bonus) if bonus else "") + "。"


def _opened_lines(
    library: ContentLibrary, char: CharacterState, row: _Resolved
) -> list[AbsenceItemView]:
    succeeded = row.state.status == "succeeded"
    flags = set((row.event.on_success if succeeded else row.event.on_failure).flags)
    items: list[AbsenceItemView] = []
    for region in sorted(library.world_maps):
        for place in library.world_maps[region].locations:
            if place.unlock_flag is None or place.unlock_flag not in flags:
                continue
            name = location_name_for(library, char, region, place.id)
            text = f"「{name}」開放了"
            if place.gate_to is not None:
                text += f"，可以前往{region_name(library, place.gate_to)}"
            items.append(AbsenceItemView(kind="opened", at=row.at, text_zh=text + "。"))
    return items


def _bounty_lines(
    library: ContentLibrary, world: WorldState, char: CharacterState, since: int, now: int
) -> list[AbsenceItemView]:
    season = library.world_season
    if season is None:
        return []
    bounties = season.bounty_by_id()
    start = day_of(library, world.season_start)
    items: list[AbsenceItemView] = []
    for claim in world.bounty_claims:
        if not since < claim.at <= now or claim.character_id == char.character_id:
            continue
        bounty = bounties.get(claim.bounty)
        if bounty is None:
            continue
        where = location_name_for(library, char, bounty.region, bounty.location)
        day = claim.day - start + 1
        text = f"第 {day} 天的懸賞「{bounty.name_zh}」（{where}）被 {claim.name} 搶下。"
        items.append(AbsenceItemView(kind="bounty", at=claim.at, text_zh=text))
    return items


def absence_summary(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> AbsenceView:
    """``char`` 上次看過之後的世界消息（``world`` 是換日後的世界）。"""
    since = world.season_start if char.news_seen_at is None else char.news_seen_at
    items: list[AbsenceItemView] = []
    for row in _resolved(library, world, since, now):
        items.append(
            AbsenceItemView(kind="world_event", at=row.at, text_zh=_event_line(library, row))
        )
        items += _opened_lines(library, char, row)
    items += _bounty_lines(library, world, char, since, now)
    order = {"world_event": 0, "opened": 1, "bounty": 2}
    items.sort(key=lambda i: (i.at, order.get(i.kind, 9), i.text_zh))
    return AbsenceView(since=since, as_of=now, items=tuple(items))
