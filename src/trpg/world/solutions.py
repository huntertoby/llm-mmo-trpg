"""事件的放棄、交涉、戰鬥解法（Phase 5B-4b；``docs/phases/Phase5計畫.md`` 19.6；09 9.6.7 #6）。

情境判定在 :mod:`trpg.world.situations`；本模組結算其他三種解法（``event_solve`` 動作）：

- **放棄**：清掉事件，沒有獎懲（18.4 補充「離開地點就算放棄，不留懲罰」），結果 ``abandoned``。
- **交涉**：不擲骰、一定成功。付 ``cost_supplies`` 補給；持有 ``waive_thread`` 的個人線頭時可以改用
  它抵（線頭用掉；18.4 補充「用人情代替青竹節」）。成功留下解法的 ``threads``。
- **戰鬥**：在所在地點開一般遭遇（同移動遇敵，``battle`` 串流），事件記下 ``combat_solution``；遭遇
  結束的那個動作（:func:`settle_event_combat`，``world_step`` 後段）結算：打贏＝成功（留線頭），
  輸或撤退＝失敗。經驗只有戰鬥本身。
- **機遇**（Phase 5B-4c，07 7.6）：條件（裝備的技能帶 ``requires_keyword``）成立、這個骨架的機遇
  還沒拿過 → 給一組完整技能三選一（``pinned_keyword``＝觸發的關鍵字，三張都帶它；5B-4d）；用
  ``fnv1a64("{技能種子}:opportunity:{骨架}")`` 擲 ``tier_up_permille``，中了而且本季還有次數時高
  1 階。結果一定成功。
- **戰鬥解法的勝利條件**（Phase 5B-4c）：解法的 ``objective``（撤離、守點）記在遭遇上，地圖優先挑
  支援它的（開戰時地圖不支援就全滅，:mod:`trpg.world.battle`）。

純函式：不讀時間、亂數只用角色的 ``battle`` 串流（戰鬥解法開遭遇時）與技能種子衍生的機遇種子。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventSkeletonDef, SolutionDef
from trpg.content.world_map import LocationDef
from trpg.roguelite.offers import make_offer, offer_key
from trpg.roguelite.state import RunState, SkillOffer
from trpg.shared.rng import Rng, fnv1a64
from trpg.skillgen.skill_tier import character_tier
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
from trpg.world.common import here, rules_of
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.generated import OfferGen, supply
from trpg.world.growth import as_run, hero_tier, skill_seed, world_library
from trpg.world.opening_limits import solution_problem
from trpg.world.quests import store_offer
from trpg.world.rng import STREAM_BATTLE, draw
from trpg.world.season_board import open_bounty_at
from trpg.world.situations import grant_threads, opportunity_available
from trpg.world.state import CharacterState, EncounterResult, EventTrigger, WorldState
from trpg.world.story_gen import checked_offer, opportunity_request
from trpg.world.weather import weather_at

__all__ = ["make_encounter", "settle_event_combat", "solve_event"]


def make_encounter(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    target: LocationDef,
    now: int,
    *,
    objective: Literal["escape", "defend"] | None = None,
) -> tuple[EncounterResult, CharacterState]:
    """在 ``target`` 產生遭遇（``battle`` 串流：地圖、戰鬥種子）；移動遇敵與戰鬥解法共用。

    ``objective``（Phase 5B-4c 戰鬥解法的勝利條件）：地點的 ``battle_maps`` 裡有支援它的地圖時只從
    那些挑（亂數消耗相同）。遇敵當下有效的世界旗標記進 ``world_flags``（世界級線頭到期結局）。
    呼叫端沒有指定 ``objective`` 時用遭遇表地點的 ``objective``（Phase 5F-5a：三村落的守點戰）。"""
    if objective is None:
        objective = _location_objective(library, char.region, target.id)
    rng, char = draw(world.season_seed, char, STREAM_BATTLE)
    maps = target.battle_maps
    if objective is not None:
        maps = tuple(m for m in maps if library.map(m).supports_objective(objective)) or maps
    battle_map = rng.choice(maps) if maps else None
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
        objective=objective,
        world_flags=world.active_flags(now),
        level_bonus=world.level_bonus.get(char.region, 0),  # 世界事件失敗的建議等級加成（5F-1）
        bounty=open_bounty_at(library, world, char, target.id, now),  # 懸賞（5F-1b）
    )
    return result, char


def _location_objective(
    library: ContentLibrary, region: str, location: str
) -> Literal["escape", "defend"] | None:
    """遭遇表地點的勝利條件（Phase 5F-5a）；沒有遭遇表或沒寫＝``None``。"""
    table = library.world_encounters.get(region)
    entry = None if table is None else table.location_by_id().get(location)
    return None if entry is None else entry.objective


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
    blocked = solution_problem(char, solution.kind)  # OB-4（#150）：入門期不開戰、不給招
    if blocked is not None:
        raise WorldActionError(blocked)
    if solution.kind == "opportunity":
        if not opportunity_available(library, char, solution):
            raise WorldActionError("機遇的條件不成立（裝備的技能沒有需要的關鍵字）")
        if trigger.skeleton in char.opportunities:
            raise WorldActionError("這個機遇已經拿過了")
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
    if solution.kind == "opportunity":
        return _opportunity(library, world, char, action, trigger, solution)
    return _combat(library, world, char, action, trigger, solution, now)


MAX_SKILL_TIER = 5
"""技能階級上限（``SkillDef.tier``）。"""


def opportunity_tier_bonus(
    library: ContentLibrary, world: WorldState, char: CharacterState, skeleton: str
) -> int:
    """機遇三選一高幾階（07 7.6）：``fnv1a64("{技能種子}:opportunity:{骨架}")`` 擲
    ``randint(0, 999) < tier_up_permille``，且本角色高 1 階的次數還沒到 ``tier_up_per_season``、
    角色階級 +1 不超過上限 → 1；否則 0。不動角色的亂數計數。"""
    rules = rules_of(library).opportunity
    if char.opportunity_tier_ups >= rules.tier_up_per_season:
        return 0
    if hero_tier(library, char.level) + 1 > MAX_SKILL_TIER:
        return 0
    rng = Rng(fnv1a64(f"{skill_seed(world, char)}:opportunity:{skeleton}".encode()))
    return 1 if rng.randint(0, 999) < rules.tier_up_permille else 0


def _opportunity_offer(  # noqa: PLR0917 — make_offer 的參數
    library: ContentLibrary,
    char: CharacterState,
    run: RunState,
    keyword: str | None,
    bonus: int,
    trigger: EventTrigger,
) -> tuple[SkillOffer, Literal["llm", "composer"]]:
    """機遇的完整技能三選一（6L-2）：先問生成內容的供應者要 LLM 版（:mod:`trpg.world.generated`），
    拿不到或不合格就照常用組合器與技能池同步算。"""
    view = world_library(library)
    keywords = () if keyword is None else (keyword,)

    def compute() -> SkillOffer:
        return make_offer(
            view,
            run,
            "complete",
            region_keywords=keywords,
            tier_bonus=bonus,
            pinned_keyword=keyword,  # 5B-4d：三張都帶觸發情境的關鍵字（07 7.6）
            region=trigger.region,  # 6L-1（#126）：取得地點的區域
        )

    key = offer_key(
        view,
        run,
        "complete",
        region_keywords=keywords,
        tier_bonus=bonus,
        pinned_keyword=keyword,
        region=trigger.region,
    )
    if key is None:
        return compute(), "composer"
    request = opportunity_request(
        char, run, key, keyword=keyword, tier_bonus=bonus, region=trigger.region
    )
    tier = character_tier(view, run.level) + bonus

    def accept(gen: OfferGen) -> OfferGen | None:
        if gen.source == "composer":
            return gen
        return gen if checked_offer(gen.offer, tier) is not None else None

    gen = supply(request, OfferGen, OfferGen(key=request.key), accept)
    if gen.source == "llm" and gen.offer is not None:
        return gen.offer, "llm"
    return compute(), "composer"


def _opportunity(  # noqa: PLR0917 — 一個解法的完整結算
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: EventSolveAction,
    trigger: EventTrigger,
    solution: SolutionDef,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    bonus = opportunity_tier_bonus(library, world, char, trigger.skeleton)
    run = as_run(char, seed=skill_seed(world, char)).model_copy(
        update={"offers_made": char.offers_made}
    )
    made, made_by = _opportunity_offer(
        library, char, run, solution.requires_keyword, bonus, trigger
    )
    solved = EventSolvedEvent(
        skeleton=trigger.skeleton,
        solution=action.solution,
        solution_kind="opportunity",
        tier_bonus=bonus,
    )
    char = char.model_copy(
        update={
            "pending_event": None,
            "opportunities": tuple(sorted({*char.opportunities, trigger.skeleton})),
            "opportunity_tier_ups": char.opportunity_tier_ups + bonus,
        }
    )
    char, offered = store_offer(
        char,
        trigger.skeleton,
        "opportunity",
        made,
        source="opportunity",
        guaranteed=trigger.guaranteed,  # 5D-2b：三選一標題用保底的「誰」
        region=trigger.region,
        made_by=made_by,
    )
    return world, char, (solved, offered, _resolved(trigger, action.solution, "success"))


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
    solution: SolutionDef,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    place = here(library, char)
    table = library.world_encounters.get(char.region)
    listed = table is not None and place.id in table.location_by_id()
    if place.level_max is None or not listed:
        raise WorldActionError(f"{place.name_zh}打不起來（這裡沒有敵人）")
    result, char = make_encounter(library, world, char, place, now, objective=solution.objective)
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
