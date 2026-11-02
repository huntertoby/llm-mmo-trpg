"""事件的放棄、交涉、戰鬥解法（Phase 5B-4b；``docs/phases/Phase5計畫.md`` 19.6；09 9.6.7 #6）。

情境判定在 :mod:`trpg.world.situations`；本模組結算其他三種解法（``event_solve`` 動作）：

- **放棄**：清掉事件，沒有獎懲（18.4 補充「離開地點就算放棄，不留懲罰」），結果 ``abandoned``。
- **交涉**：不擲骰、一定成功。付 ``cost_supplies`` 補給；持有 ``waive_thread`` 的個人線頭時可以改用
  它抵（線頭用掉；18.4 補充「用人情代替青竹節」）。成功留下解法的 ``threads``。
- **戰鬥**：在所在地點開一般遭遇（同移動遇敵，``battle`` 串流），事件記下 ``combat_solution``；遭遇
  結束的那個動作（:func:`settle_event_combat`，``world_step`` 後段）結算：打贏＝成功（留線頭），
  輸或撤退＝失敗。經驗只有戰鬥本身。
- **機遇** 本段不結算（拒絕）。

純函式：不讀時間、亂數只用角色的 ``battle`` 串流（戰鬥解法開遭遇時）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventSkeletonDef, SolutionDef
from trpg.content.world_map import LocationDef
from trpg.world.actions import (
    BattleEndedEvent,
    EncounterEvent,
    EventResolvedEvent,
    EventSolveAction,
    EventSolvedEvent,
    ThreadSpentEvent,
    WorldEvent,
)
from trpg.world.clock import day_phase
from trpg.world.common import here
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.rng import STREAM_BATTLE, draw
from trpg.world.situations import grant_threads
from trpg.world.state import CharacterState, EncounterResult, EventTrigger, WorldState
from trpg.world.weather import weather_at

__all__ = ["make_encounter", "settle_event_combat", "solve_event"]


def make_encounter(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    target: LocationDef,
    now: int,
) -> tuple[EncounterResult, CharacterState]:
    """在 ``target`` 產生遭遇（``battle`` 串流：地圖、戰鬥種子）；移動遇敵與戰鬥解法共用。"""
    rng, char = draw(world.season_seed, char, STREAM_BATTLE)
    battle_map = rng.choice(target.battle_maps) if target.battle_maps else None
    seed = rng.next_u32()
    assert target.level_max is not None
    result = EncounterResult(
        region=char.region,
        location=target.id,
        level=target.level_max,
        battle_map=battle_map,
        battle_seed=seed,
        weather=weather_at(library, world, char.region, now),
        day_phase=day_phase(now),
        at=now,
    )
    return result, char


def _skeleton(library: ContentLibrary, trigger: EventTrigger) -> EventSkeletonDef:
    table = library.world_event_content.events.get(trigger.region)
    skeleton = None if table is None else table.skeleton_by_id().get(trigger.skeleton)
    if skeleton is None:
        raise WorldError(f"{trigger.region} 沒有事件骨架 {trigger.skeleton}")
    return skeleton


def _resolved(trigger: EventTrigger, solution: int, outcome: str) -> EventResolvedEvent:
    return EventResolvedEvent.model_validate(
        {
            "skeleton": trigger.skeleton,
            "location": trigger.location,
            "solution": solution,
            "outcome": outcome,
        }
    )


def _check(
    library: ContentLibrary, char: CharacterState, action: EventSolveAction
) -> tuple[EventTrigger, SolutionDef]:
    trigger = char.pending_event
    if trigger is None:
        raise WorldActionError("目前沒有事件")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇")
    skeleton = _skeleton(library, trigger)
    if action.solution >= len(skeleton.solutions):
        raise WorldActionError(f"這個事件沒有第 {action.solution} 個解法")
    solution = skeleton.solutions[action.solution]
    if solution.kind == "situation":
        raise WorldActionError("情境判定請用 situation 動作")
    if solution.kind == "opportunity":
        raise WorldActionError("機遇的結算還沒開放")
    if action.use_thread is not None and solution.kind != "parley":
        raise WorldActionError("只有交涉可以拿線頭抵掉付出")
    return trigger, solution


def solve_event(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: EventSolveAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """``event_solve`` 動作（見模組說明）；不合法拋 :class:`WorldActionError`。"""
    trigger, solution = _check(library, char, action)
    if solution.kind == "abandon":
        solved = EventSolvedEvent(
            skeleton=trigger.skeleton, solution=action.solution, solution_kind="abandon"
        )
        char = char.model_copy(update={"pending_event": None})
        return world, char, (solved, _resolved(trigger, action.solution, "abandoned"))
    if solution.kind == "parley":
        return _parley(library, world, char, action, trigger, solution, now)
    return _combat(library, world, char, action, trigger, now)


def _parley(  # noqa: PLR0917 — 一個解法的完整結算
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: EventSolveAction,
    trigger: EventTrigger,
    solution: SolutionDef,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    events: list[WorldEvent] = []
    spent = 0
    if action.use_thread is not None:
        if action.use_thread != solution.waive_thread:
            raise WorldActionError(f"這次交涉不能用線頭 {action.use_thread} 抵")
        held = [t for t in char.threads if t.thread == action.use_thread and t.expires_at > now]
        if not held:
            raise WorldActionError("沒有持有這條線頭")
        threads = tuple(t for t in char.threads if t.thread != action.use_thread)
        char = char.model_copy(update={"threads": threads})
    else:
        spent = solution.cost_supplies
        if char.supplies < spent:
            raise WorldActionError(f"補給不足，交涉要 {spent} 補給")
        char = char.model_copy(update={"supplies": char.supplies - spent})
    events.append(
        EventSolvedEvent(
            skeleton=trigger.skeleton,
            solution=action.solution,
            solution_kind="parley",
            supplies_spent=spent,
            thread_spent=action.use_thread,
        )
    )
    if action.use_thread is not None:
        events.append(ThreadSpentEvent(thread=action.use_thread))
    world, char, added = grant_threads(
        library, world, char, solution.threads, skeleton=trigger.skeleton, now=now
    )
    events += added
    char = char.model_copy(update={"pending_event": None})
    events.append(_resolved(trigger, action.solution, "success"))
    return world, char, tuple(events)


def _combat(  # noqa: PLR0917 — 一個解法的完整結算
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: EventSolveAction,
    trigger: EventTrigger,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    place = here(library, char)
    table = library.world_encounters.get(char.region)
    listed = table is not None and place.id in table.location_by_id()
    if place.level_max is None or not listed:
        raise WorldActionError(f"{place.name_zh}打不起來（這裡沒有敵人）")
    result, char = make_encounter(library, world, char, place, now)
    result = result.model_copy(update={"from_location": char.location})  # 撤退留在原地
    marked = trigger.model_copy(update={"combat_solution": action.solution})
    char = char.model_copy(update={"pending_encounter": result, "pending_event": marked})
    solved = EventSolvedEvent(
        skeleton=trigger.skeleton, solution=action.solution, solution_kind="combat"
    )
    return world, char, (solved, EncounterEvent(result=result))


def settle_event_combat(
    library: ContentLibrary,
    world: WorldState,
    before: CharacterState,
    char: CharacterState,
    events: Sequence[WorldEvent],
    *,
    now: int,
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    """戰鬥解法的遭遇在這個動作結束了（打完或撤退）→ 結算事件；其他情況不變、不發事件。"""
    trigger = before.pending_event
    if (
        trigger is None
        or trigger.combat_solution is None
        or before.pending_encounter is None
        or char.pending_encounter is not None
    ):
        return world, char, []
    index = trigger.combat_solution
    won = any(isinstance(e, BattleEndedEvent) and e.won for e in events)
    out: list[WorldEvent] = []
    if won:
        solution = _skeleton(library, trigger).solutions[index]
        world, char, added = grant_threads(
            library, world, char, solution.threads, skeleton=trigger.skeleton, now=now
        )
        out += added
    char = char.model_copy(update={"pending_event": None})
    out.append(_resolved(trigger, index, "success" if won else "failure"))
    return world, char, out
