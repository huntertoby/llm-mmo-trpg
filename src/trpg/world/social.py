"""和 NPC 說話、在酒館聽傳聞（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16.5、16.6）。

- ``talk``：NPC 依好感度能給的內容（9.6.7 #3 只換資訊；玩法 PM 定：中立給一般傳聞、友善給隱藏任務
  入口、信賴才說祕密）。任務的 ``talk`` 條件看這個動作的 ``talked`` 事件。5B-4b：每天第一次
  說話加好感度、信賴的祕密解鎖事件骨架（改角色狀態）。
- ``tavern``：本週傳聞（9.6.7 #1）由賽季種子與週次決定，同一週所有人相同；不耗角色的亂數串流。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.world_quests import RumorDef
from trpg.shared.rng import Rng, fnv1a64
from trpg.world.actions import (
    EventTriggeredEvent,
    RumorsHeardEvent,
    SkeletonUnlockedEvent,
    TalkAction,
    TalkedEvent,
    WorldEvent,
)
from trpg.world.affinity import (
    affinity_of,
    affinity_rules,
    change_affinity,
    rank_of,
    social_of,
    talk_entries,
)
from trpg.world.clock import day_phase, refresh_day
from trpg.world.common import here
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, EventTrigger, WorldState
from trpg.world.weather import weather_at

__all__ = ["talk", "tavern", "week_of", "week_rumors"]


def talk(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: TalkAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """和所在地點的 NPC 說話；不合法拋 :class:`WorldActionError`。

    5B-4b：每天（6 點刷新）第一次說話好感度 +``daily_talk_delta``（先加再決定能說什麼，18.7.6）；
    說出解鎖骨架的祕密時解鎖該骨架，沒有事件在身上就立刻觸發（18.7.7）。
    """
    table = library.world_event_content.npcs.get(char.region)
    card = None if table is None else table.npc_by_id().get(action.npc)
    if card is None:
        raise WorldActionError(f"這一區沒有 NPC {action.npc}")
    if card.location != char.location:
        raise WorldActionError(f"{card.name_zh}不在這裡")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能聊天")
    events: list[WorldEvent] = []
    today = refresh_day(now)
    if char.talk_days.get(action.npc) != today:
        delta = affinity_rules(library).daily_talk_delta
        if delta:
            char, changed = change_affinity(library, char, action.npc, delta, "talk:daily")
            events.append(changed)
        char = char.model_copy(update={"talk_days": {**char.talk_days, action.npc: today}})
    entries = talk_entries(library, char, action.npc)
    available = tuple(
        sorted(
            e.quest
            for e in entries
            if e.kind == "quest_entry" and e.quest is not None and char.quest_state(e.quest) is None
        )
    )
    events.append(
        TalkedEvent(
            npc=action.npc,
            affinity=affinity_of(char, action.npc),
            rank=rank_of(library, char, action.npc),
            entries=tuple(e.id for e in entries),
            quests_available=available,
        )
    )
    for entry in entries:
        skeleton = entry.unlocks_skeleton
        if skeleton is None or skeleton in char.unlocked_skeletons:
            continue
        char, unlocked = _unlock(library, world, char, skeleton, npc=action.npc, now=now)
        events += unlocked
    return char, tuple(events)


def _unlock(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    skeleton_id: str,
    *,
    npc: str,
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    """解鎖骨架；角色沒有事件在身上、骨架的地點含所在地點時立刻觸發（候選只有它）。"""
    unlocked = tuple(sorted({*char.unlocked_skeletons, skeleton_id}))
    char = char.model_copy(update={"unlocked_skeletons": unlocked})
    events: list[WorldEvent] = [SkeletonUnlockedEvent(skeleton=skeleton_id, npc=npc)]
    events_table = library.world_event_content.events.get(char.region)
    skeleton = None if events_table is None else events_table.skeleton_by_id().get(skeleton_id)
    here_ok = skeleton is not None and char.location in skeleton.locations
    if not here_ok or char.pending_event is not None:
        return char, events
    trigger = EventTrigger(
        region=char.region,
        location=char.location,
        skeleton=skeleton_id,
        candidates=(skeleton_id,),
        weather=weather_at(library, world, char.region, now),
        day_phase=day_phase(now),
        at=now,
    )
    events.append(EventTriggeredEvent(trigger=trigger))
    return char.model_copy(update={"pending_event": trigger, "event_steps": 0}), events


def week_of(library: ContentLibrary, world: WorldState, now: int) -> int:
    """賽季開始以來的第幾週（0 起；早上 6 點刷新的日子）。"""
    days = refresh_day(now) - refresh_day(world.season_start)
    return max(0, days) // affinity_rules(library).week_days


def week_rumors(
    library: ContentLibrary, world: WorldState, region: str, now: int
) -> tuple[int, tuple[RumorDef, ...]]:
    """本週傳聞（週次、依 ID 排序）：傳聞池依 ID 排序後用
    ``{season_seed}:{region}:rumors:{week}`` 的種子洗牌，取前 ``rumors_per_week`` 條。"""
    week = week_of(library, world, now)
    table = social_of(library, region)
    if table is None or not table.rumors:
        return week, ()
    pool = sorted(table.rumors, key=lambda r: r.id)
    rng = Rng(fnv1a64(f"{world.season_seed}:{region}:rumors:{week}".encode()))
    picked: list[RumorDef] = []
    count = min(affinity_rules(library).rumors_per_week, len(pool))
    for _ in range(count):
        picked.append(pool.pop(rng.randint(0, len(pool) - 1)))
    return week, tuple(sorted(picked, key=lambda r: r.id))


def tavern(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[WorldEvent, ...]:
    """在城鎮的酒館聽本週傳聞；不改狀態。"""
    if here(library, char).kind != "town":
        raise WorldActionError("只有城鎮有酒館")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能去酒館")
    week, rumors = week_rumors(library, world, char.region, now)
    return (RumorsHeardEvent(week=week, rumors=tuple(r.id for r in rumors)),)
