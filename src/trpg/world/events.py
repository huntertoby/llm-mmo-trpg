"""事件出現擲骰（Phase 5B-1；``docs/phases/Phase5計畫.md`` 8.6）。

``docs/design/09-世界與敘事.md`` 9.6.7 #6：「事件出現頻率由引擎依移動步數與種子決定，LLM 不能自己
多生事件」。每次移動抵達後擲一次（``event`` 串流，亂數消耗固定）：機率依距離上次事件的步數線性
增加；遇敵的那一步不出事件（戰鬥優先）。觸發時只產生 :class:`~trpg.world.state.EventTrigger`
（哪個骨架、候選清單）；解法、結果與線頭在 5B-2～5B-4，LLM 包裝在 5B-3。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventFrequency, EventSkeletonDef
from trpg.world.actions import (
    EventCheckEvent,
    EventLeftEvent,
    EventResolvedEvent,
    EventTriggeredEvent,
    WorldEvent,
)
from trpg.world.calendar import day_of, season_day
from trpg.world.clock import day_phase
from trpg.world.opening_limits import in_starter_period
from trpg.world.rng import STREAM_EVENT, draw
from trpg.world.state import CharacterState, EventTrigger, WorldState
from trpg.world.threads import active_threads
from trpg.world.weather import weather_at

__all__ = [
    "EventRoll",
    "event_candidates",
    "event_chance",
    "guaranteed_opportunity",
    "is_opportunity",
    "mark_finished",
    "mark_met_opportunities",
    "roll_event",
    "season_day",
]


def event_chance(frequency: EventFrequency, steps: int) -> int:
    """距離上次事件 ``steps`` 步時的事件機率（‰）。"""
    return min(frequency.max_permille, frequency.per_step_permille * max(0, steps))


def event_candidates(
    library: ContentLibrary,
    world: WorldState,
    region: str,
    location: str,
    now: int,
    *,
    unlocked: Collection[str] = (),
    finished: Collection[str] = (),
    failed: Mapping[str, int] | None = None,
) -> tuple[EventSkeletonDef, ...]:
    """``region`` 的 ``location`` 在 ``now`` 合格的事件骨架（地點、時段、天氣），依 ID 排序。
    ``unlock_only`` 的骨架只有在 ``unlocked``（角色解鎖的骨架）裡才算（5B-4b）；``once`` 的骨架在
    ``finished``（角色解決過的）裡就不算（5B-4c），在 ``failed``（骨架 → 判定失敗那天）裡、而且
    今天還是失敗那天時也不算（5B-4d：隔天 6 點刷新後可再試）。"""
    table = library.world_event_content.events.get(region)
    if table is None:
        return ()
    phase = day_phase(now)
    weather: str | None = None
    out: list[EventSkeletonDef] = []
    for skeleton in sorted(table.skeletons, key=lambda s: s.id):
        if location not in skeleton.locations:
            continue
        if skeleton.unlock_only and skeleton.id not in unlocked:
            continue
        if skeleton.once and skeleton.id in finished:
            continue
        if skeleton.once and _failed_today(failed, skeleton.id, day_of(library, now)):
            continue
        if skeleton.day_phase is not None and skeleton.day_phase != phase:
            continue
        if skeleton.weather:
            if weather is None:
                weather = weather_at(library, world, region, now)
            if weather not in skeleton.weather:
                continue
        out.append(skeleton)
    return tuple(out)


def _failed_today(failed: Mapping[str, int] | None, skeleton: str, today: int) -> bool:
    day = None if failed is None else failed.get(skeleton)
    return day is not None and today <= day


def is_opportunity(skeleton: EventSkeletonDef) -> bool:
    """骨架有機遇解法（07 7.6；18.4 #12）。"""
    return any(s.kind == "opportunity" for s in skeleton.solutions)


def guaranteed_opportunity(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> EventSkeletonDef | None:
    """機遇保底（Phase 5B-4d，07 7.6「第 7 天前保底 1 次」；代決 5B4d-3、5B4d-4）：賽季第
    ``guarantee_from_day`` 天起，還沒遇過也沒拿過機遇的角色，所在地點的機遇骨架（不看天氣、時段；
    ``unlock_only`` 要已解鎖、``once`` 要沒解決；多個時取 ID 最小者）；不保底時 ``None``。"""
    rules = library.world_rules
    start = 0 if rules is None else rules.opportunity.guarantee_from_day
    if start <= 0 or season_day(library, world, now) < start:
        return None
    if char.met_opportunities or char.opportunities:
        return None
    if in_starter_period(char):  # OB-4（#150）：入門期領不了機遇，保底留到正式選定之後
        return None
    table = library.world_event_content.events.get(char.region)
    if table is None:
        return None
    for skeleton in sorted(table.skeletons, key=lambda s: s.id):
        if char.location not in skeleton.locations or not is_opportunity(skeleton):
            continue
        if skeleton.unlock_only and skeleton.id not in char.unlocked_skeletons:
            continue
        if skeleton.once and (
            skeleton.id in char.finished_skeletons
            or _failed_today(char.failed_skeletons, skeleton.id, day_of(library, now))
        ):
            continue
        return skeleton
    return None


def _followed(
    candidates: tuple[EventSkeletonDef, ...], live: frozenset[str]
) -> tuple[EventSkeletonDef, ...]:
    """能接上有效線頭的候選（9.6.7 #6「產生下一個事件時優先接線頭」）。"""
    return tuple(s for s in candidates if live.intersection(s.follows))


@dataclass(frozen=True)
class EventRoll:
    char: CharacterState
    events: tuple[WorldEvent, ...]


def roll_event(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    *,
    encountered: bool,
    now: int,
) -> EventRoll:
    """角色抵達 ``char.location`` 後的事件擲骰（:func:`trpg.world.step.world_step` 的移動用）。

    沒有 ``event_rules.yaml`` 或該區沒有骨架檔時整段跳過、不耗亂數。
    """
    rules = library.world_event_content.rules
    region = char.region
    if rules is None or region not in library.world_event_content.events:
        return EventRoll(char=char, events=())
    events: list[WorldEvent] = []
    pending = char.pending_event
    if pending is not None:
        events.append(
            EventLeftEvent(
                skeleton=pending.skeleton,
                location=pending.location,
                guaranteed=pending.guaranteed,
            )
        )
        char = char.model_copy(update={"pending_event": None})

    steps = char.event_steps + 1
    chance = event_chance(rules.frequency, steps)
    rng, char = draw(world.season_seed, char, STREAM_EVENT)
    roll = rng.randint(0, 999)
    candidates = event_candidates(
        library,
        world,
        region,
        char.location,
        now,
        unlocked=char.unlocked_skeletons,
        finished=char.finished_skeletons,
        failed=char.failed_skeletons,
    )
    guaranteed = None if encountered else guaranteed_opportunity(library, world, char, now)
    if guaranteed is not None:  # 機遇保底（5B-4d）：不看天氣、時段與機率，候選只有它
        candidates = (guaranteed,)
    triggered = (roll < chance or guaranteed is not None) and not encountered and bool(candidates)
    events.append(
        EventCheckEvent(
            location=char.location,
            steps=steps,
            chance_permille=chance,
            roll=roll,
            triggered=triggered,
        )
    )
    if not triggered:
        return EventRoll(char=char.model_copy(update={"event_steps": steps}), events=tuple(events))

    live = frozenset(t.thread for t in active_threads((*char.threads, *world.threads), now))
    picked = guaranteed or rng.choice(_followed(candidates, live) or candidates)
    hits = sorted(live.intersection(picked.follows))
    trigger = EventTrigger(
        region=region,
        location=char.location,
        skeleton=picked.id,
        candidates=tuple(s.id for s in candidates),
        follows_thread=hits[0] if hits else None,
        weather=weather_at(library, world, region, now),
        day_phase=day_phase(now),
        at=now,
        guaranteed=guaranteed is not None,
    )
    events.append(EventTriggeredEvent(trigger=trigger))
    char = char.model_copy(update={"event_steps": 0, "pending_event": trigger})
    return EventRoll(char=char, events=tuple(events))


def mark_finished(
    library: ContentLibrary, char: CharacterState, events: Collection[WorldEvent], *, now: int
) -> CharacterState:
    """這個動作結束了 ``once`` 的骨架（5B-4c，18.4 補充「骨架 22 每個角色只出現到解決為止」）：

    - 成功、部分成功 → 記進 ``finished_skeletons``（5B-4d，18.7.6「只有成功或部分成功才算解決」）。
    - 失敗 → ``failed_skeletons[骨架] = refresh_day(now)``：當天不再出現，隔天可以再試。
    - 放棄照舊不記。"""
    table = library.world_event_content.events.get(char.region)
    if table is None:
        return char
    defs = table.skeleton_by_id()
    ended = [
        e
        for e in events
        if isinstance(e, EventResolvedEvent)
        and e.outcome != "abandoned"
        and (d := defs.get(e.skeleton)) is not None
        and d.once
    ]
    if not ended:
        return char
    finished = set(char.finished_skeletons)
    failed = dict(char.failed_skeletons)
    for event in ended:
        if event.outcome == "failure":
            failed[event.skeleton] = day_of(library, now)
        else:
            finished.add(event.skeleton)
            failed.pop(event.skeleton, None)
    return char.model_copy(
        update={"finished_skeletons": tuple(sorted(finished)), "failed_skeletons": failed}
    )


def mark_met_opportunities(
    library: ContentLibrary, char: CharacterState, events: Collection[WorldEvent]
) -> CharacterState:
    """這個動作觸發了機遇骨架（移動擲骰、聊天解鎖都算）→ 記進 ``met_opportunities``（5B-4d：
    機遇保底只給還沒遇過的角色；代決 5B4d-4）。"""
    table = library.world_event_content.events.get(char.region)
    if table is None or in_starter_period(char):  # OB-4：入門期領不了機遇，不算遇過（保底還在）
        return char
    defs = table.skeleton_by_id()
    met = {
        e.trigger.skeleton
        for e in events
        if isinstance(e, EventTriggeredEvent)
        and (d := defs.get(e.trigger.skeleton)) is not None
        and is_opportunity(d)
    }
    if met <= set(char.met_opportunities):
        return char
    return char.model_copy(
        update={"met_opportunities": tuple(sorted({*char.met_opportunities, *met}))}
    )
