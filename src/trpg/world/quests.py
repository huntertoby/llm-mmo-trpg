"""任務狀態機（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16.6）。

任務結構與獎勵是資料（``content/world/quests/``，09 9.2 storylet），本模組只依資料推進：

- **接任務**（:func:`accept_quest`）：在給任務的 NPC 所在地點、好感度不是敵視、``start`` 條件成立。
- **每個世界動作之後**（:func:`advance_quests`）：先依事件結果表調好感度，再核對每個進行中任務目前
  步驟的條件（狀態型看動作之後的狀態，事件型看這個動作的事件），成立就完成這一步並發獎勵：經驗
  （5A-SIM2 份數，``gain_xp`` 當下升級）、靈感（任務鏈段落）、好感度、劇情旗標、劇情技能、技能
  三選一。同一個動作內可連續完成多步，但事件型條件只認一次。
- **技能三選一**（07 7.6）：重用 roguelite 的候選產生器（``make_offer``，``world_library`` 的角色
  階級），候選存進角色的 ``pending_offers``，選的時候不重抽（:func:`take_offer`）。
- **劇情技能**（07 7.6）：骨架固定、每人相同；照角色階級、完整技能強度，放進備用。6L-2：向生成內容
  的供應者（:mod:`trpg.world.generated`）要依玩家關鍵字換過元素、名稱與描述的版本
  （:mod:`trpg.world.story_gen`，骨架與預算不變）；拿不到就用內容版。
- **取得地點**（6L-2，#126）：學到的技能記進 ``skill_regions``（劇情技能＝任務所在區域；三選一＝
  出題時記下的區域）。

純函式：不讀時間（``now`` 由呼叫者傳入）、不耗世界亂數串流（候選用角色技能種子，同閃現）、不呼叫
LLM（生成內容由供應者給，重播只讀日誌）。不合法的動作拋 :class:`WorldActionError`，狀態不變。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_quests import (
    AffinityAtLeast,
    AnyOf,
    AtLocation,
    Flashed,
    GrowthDone,
    HasFlag,
    HoldThread,
    LeafCondition,
    QuestCondition,
    QuestDef,
    QuestStepDef,
    QuestStepReached,
    QuestTable,
    SituationDone,
    SkillOfferReward,
    Talked,
    WinBattle,
)
from trpg.roguelite.errors import ChoiceError, RunError
from trpg.roguelite.flashes import owned_skills, with_acquired
from trpg.roguelite.names import unique_skill_name
from trpg.roguelite.offers import make_offer, skill_defs, take_candidate
from trpg.roguelite.state import RunState, SkillOffer
from trpg.world.actions import (
    AcceptQuestAction,
    BattleEndedEvent,
    BattleStartedEvent,
    EventResolvedEvent,
    FlashPickedEvent,
    InsightGainedEvent,
    OfferPickAction,
    QuestCompletedEvent,
    QuestStartedEvent,
    QuestStepDoneEvent,
    SituationCheckEvent,
    SkillDissolvedEvent,
    SkillInheritedEvent,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    StorySkillGrantedEvent,
    TalkedEvent,
    WorldEvent,
)
from trpg.world.affinity import (
    affinity_rules,
    change_affinity,
    rank_at_least,
    rank_of,
    social_of,
)
from trpg.world.common import rules_of
from trpg.world.errors import WorldActionError
from trpg.world.generated import StoryGen, supply
from trpg.world.growth import (
    as_run,
    at_service,
    char_library,
    from_run,
    gain_xp,
    skill_seed,
    with_skill_region,
    world_library,
    xp_to_level,
)
from trpg.world.situations import held_threads
from trpg.world.state import (
    CharacterState,
    DeferredOffer,
    PendingOffer,
    QuestState,
    WorldState,
)
from trpg.world.story_gen import story_base, story_request, themed_story_skill

__all__ = [
    "accept_quest",
    "advance_quests",
    "condition_holds",
    "defers_offer",
    "has_flashed",
    "issue_deferred_offers",
    "offer_bias",
    "quest_def",
    "quest_home",
    "quest_table",
    "store_offer",
    "take_offer",
]


# ---------------------------------------------------------------------------
# 查表
# ---------------------------------------------------------------------------


def quest_table(library: ContentLibrary, region: str) -> QuestTable | None:
    return library.world_quests.quests.get(region)


def quest_def(library: ContentLibrary, region: str, quest_id: str) -> QuestDef | None:
    return library.world_quests.quest(region, quest_id)


def _npc_location(library: ContentLibrary, region: str, npc: str) -> str | None:
    table = library.world_event_content.npcs.get(region)
    card = None if table is None else table.npc_by_id().get(npc)
    return None if card is None else card.location


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


def _skill_keywords(library: ContentLibrary, char: CharacterState, skill_id: str) -> frozenset[str]:
    skill = library.skills.get(skill_id)
    if skill is None:
        skill = next((s for s in char.generated_skills if s.id == skill_id), None)
    if skill is None:
        return frozenset()
    return frozenset(library.ruleset.skill_keywords(skill).all())


def _won(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent], leaf: WinBattle
) -> bool:
    """這個動作打贏的那一場符合 ``leaf``（地點、陣容、天氣、用過的技能關鍵字；5B-4b）。"""
    started = next((e for e in events if isinstance(e, BattleStartedEvent)), None)
    ended = next((e for e in events if isinstance(e, BattleEndedEvent)), None)
    if started is None or ended is None or not ended.won:
        return False
    if leaf.location is not None and started.location != leaf.location:
        return False
    if leaf.group is not None and started.lineup.group != leaf.group:
        return False
    if leaf.weather and started.weather not in leaf.weather:
        return False
    if leaf.skill_keywords:
        wanted = set(leaf.skill_keywords)
        return any(wanted & _skill_keywords(library, char, s) for s in ended.skills_used)
    return True


def has_flashed(char: CharacterState) -> bool:
    """角色閃現過至少一招（有任何一招的閃現紀錄；6F-2，#132）。"""
    return any(state.records for state in char.flash.values())


def _growth_ops(events: Sequence[WorldEvent]) -> set[str]:
    """這個動作完成的成長動作（5B-4b 導師任務鏈）。"""
    ops: set[str] = set()
    for event in events:
        if isinstance(event, FlashPickedEvent):
            ops.add("flash" if event.slot is None else "reflash")
        elif isinstance(event, SkillDissolvedEvent):
            ops.add("dissolve")
        elif isinstance(event, SkillInheritedEvent):
            ops.add("inherit")
    return ops


def _leaf_holds(  # noqa: PLR0911 — 每種條件一個分支，拆開反而難讀
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    leaf: LeafCondition,
    *,
    events: Sequence[WorldEvent],
    now: int,
) -> bool:
    if isinstance(leaf, AtLocation):
        return char.location == leaf.location
    if isinstance(leaf, HoldThread):
        return leaf.thread in held_threads(world, char, now)
    if isinstance(leaf, AffinityAtLeast):
        return rank_at_least(rank_of(library, char, leaf.npc), leaf.rank)
    if isinstance(leaf, QuestStepReached):
        state = char.quest_state(leaf.quest)
        return state is not None and state.steps_done >= leaf.step
    if isinstance(leaf, WinBattle):
        return _won(library, char, events, leaf)
    if isinstance(leaf, HasFlag):
        return leaf.flag in char.story_flags
    if isinstance(leaf, Flashed):  # 6F-2（#132）：閃現過至少一招（新手第一次也算）
        return has_flashed(char)
    if isinstance(leaf, GrowthDone):
        return bool(_growth_ops(events).intersection(leaf.ops))
    if isinstance(leaf, SituationDone):
        return any(
            isinstance(e, SituationCheckEvent)
            and e.skeleton == leaf.skeleton
            and (not leaf.templates or e.template in leaf.templates)
            and e.outcome in leaf.outcomes
            for e in events
        )
    if isinstance(leaf, Talked):
        return any(isinstance(e, TalkedEvent) and e.npc == leaf.npc for e in events)
    raise AssertionError(leaf)  # pragma: no cover


def condition_holds(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    condition: QuestCondition,
    *,
    events: Sequence[WorldEvent],
    now: int,
) -> bool:
    """條件是否成立（``events``＝這個動作的事件；狀態型條件看 ``char``、``world``）。"""
    if isinstance(condition, AnyOf):
        return any(
            _leaf_holds(library, world, char, leaf, events=events, now=now)
            for leaf in condition.conditions
        )
    return _leaf_holds(library, world, char, condition, events=events, now=now)


def _all_hold(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    conditions: Sequence[QuestCondition],
    *,
    events: Sequence[WorldEvent],
    now: int,
) -> bool:
    return all(condition_holds(library, world, char, c, events=events, now=now) for c in conditions)


# ---------------------------------------------------------------------------
# 接任務
# ---------------------------------------------------------------------------


def accept_quest(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: AcceptQuestAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """接任務（16.6）；不合法拋 :class:`WorldActionError`。"""
    quest = quest_def(library, char.region, action.quest)
    if quest is None:
        raise WorldActionError(f"這一區沒有任務 {action.quest}")
    if char.quest_state(quest.id) is not None:
        raise WorldActionError(f"已經接過任務「{quest.name_zh}」")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能接任務")
    if quest.giver is not None:
        if _npc_location(library, char.region, quest.giver) != char.location:
            raise WorldActionError(f"要到給任務的人所在的地方才能接「{quest.name_zh}」")
        if rank_of(library, char, quest.giver) == "hostile":
            raise WorldActionError("對方敵視你，不肯給你任務")
    if not _all_hold(library, world, char, quest.start, events=(), now=now):
        raise WorldActionError(f"還沒達成「{quest.name_zh}」的開始條件")
    states = sorted([*char.quests, QuestState(quest=quest.id, started_at=now)], key=_quest_key)
    char = char.model_copy(update={"quests": tuple(states)})
    return char, (QuestStartedEvent(quest=quest.id, quest_kind=quest.kind),)


def _quest_key(state: QuestState) -> str:
    return state.quest


# ---------------------------------------------------------------------------
# 每個動作之後
# ---------------------------------------------------------------------------


def advance_quests(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Sequence[WorldEvent],
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    """事件好感度＋推進進行中的任務（16.6）；沒有對到任何東西時不變、不發事件。"""
    char, out = _event_affinity(library, char, events)
    table = quest_table(library, char.region)
    if table is None:
        return char, out
    quests = table.quest_by_id()
    for state in char.quests:
        quest = quests.get(state.quest)
        if state.done or quest is None:
            continue
        char, done = _advance_one(library, world, char, quest, events=events, now=now)
        out += done
    return char, out


def _event_affinity(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent]
) -> tuple[CharacterState, list[WorldEvent]]:
    table = social_of(library, char.region)
    out: list[WorldEvent] = []
    if table is None or not table.event_affinity:
        return char, out
    for event in events:
        if not isinstance(event, EventResolvedEvent):  # 情境判定、交涉、戰鬥解法（5B-4b）
            continue
        for row in table.event_affinity:
            if row.skeleton == event.skeleton and row.outcome == event.outcome:
                char, changed = change_affinity(
                    library, char, row.npc, row.delta, f"event:{row.skeleton}"
                )
                out.append(changed)
    return char, out


def _advance_one(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    quest: QuestDef,
    *,
    events: Sequence[WorldEvent],
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    out: list[WorldEvent] = []
    used_event = False
    while True:
        state = char.quest_state(quest.id)
        assert state is not None
        if state.done:
            return char, out
        step = quest.steps[state.steps_done]
        if used_event and step.has_event_condition():
            return char, out  # 事件型條件同一個動作只認一次
        if not _all_hold(library, world, char, step.when, events=events, now=now):
            return char, out
        used_event = used_event or step.has_event_condition()
        char, done = _complete_step(library, world, char, quest, step=step, state=state, now=now)
        out += done


def _step_affinity(library: ContentLibrary, step: QuestStepDef) -> dict[str, int]:
    """完成這一步的好感度：有關的 NPC 各 +``quest_step_delta``（18.7.6），再加上 ``reward.affinity``
    （同一 NPC 合併；0 不發事件）。"""
    bonus = affinity_rules(library).quest_step_delta
    total = dict(step.reward.affinity)
    for npc in step.npcs:
        total[npc] = total.get(npc, 0) + bonus
    return {npc: delta for npc, delta in total.items() if delta}


def _with_state(char: CharacterState, state: QuestState) -> CharacterState:
    states = [state if q.quest == state.quest else q for q in char.quests]
    return char.model_copy(update={"quests": tuple(states)})


def _complete_step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    quest: QuestDef,
    *,
    step: QuestStepDef,
    state: QuestState,
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    reward = step.reward
    index = state.steps_done + 1
    finished = index == len(quest.steps)
    char = _with_state(
        char,
        state.model_copy(
            update={
                "steps_done": index,
                "done": finished,
                "completed_at": now if finished else None,
            }
        ),
    )
    xp = 0
    if reward.xp_source is not None:
        xp = rules_of(library).xp.xp_for(reward.xp_source, reward.xp_level)
    if reward.level_to is not None:  # 6F-4 C2：補到剛好這一級（新手鏈每步升 1 級）
        xp = max(xp, xp_to_level(library, char, reward.level_to))
    out: list[WorldEvent] = [
        QuestStepDoneEvent(
            quest=quest.id,
            step=step.id,
            index=index,
            xp=xp,
            insight=reward.insight,
            flags=reward.flags,
        )
    ]
    if xp:
        char, leveled = gain_xp(library, world, char, xp)
        out += leveled
    if reward.insight:
        char = char.model_copy(update={"insight": char.insight + reward.insight})
        out.append(
            InsightGainedEvent(
                source=f"quest:{quest.id}", amount=reward.insight, insight=char.insight
            )
        )
    for npc, delta in sorted(_step_affinity(library, step).items()):
        char, changed = change_affinity(library, char, npc, delta, f"quest:{quest.id}")
        out.append(changed)
    if reward.flags:
        flags = tuple(sorted({*char.story_flags, *reward.flags}))
        char = char.model_copy(update={"story_flags": flags})
    if reward.story_skill is not None:
        char, granted = _grant_story_skill(library, char, quest, step, reward.story_skill)
        out += granted
    if reward.offer is not None:
        if defers_offer(char, quest):  # OB-2（#150 第 2 點）：入門期先保留，不出題
            char = _defer_offer(char, quest, index - 1)
        else:
            char, offered = _offer(library, world, char, quest, step=step, offer=reward.offer)
            out.append(offered)
    if finished:
        out.append(QuestCompletedEvent(quest=quest.id))
    return char, out


# ---------------------------------------------------------------------------
# 劇情技能與三選一
# ---------------------------------------------------------------------------


def _grant_story_skill(
    library: ContentLibrary,
    char: CharacterState,
    quest: QuestDef,
    step: QuestStepDef,
    skill_id: str,
) -> tuple[CharacterState, list[WorldEvent]]:
    table = quest_table(library, char.region)
    assert table is not None
    base = table.story_skill_by_id()[skill_id]
    run = as_run(char)
    if skill_id in owned_skills(run):
        return char, []  # 已擁有就不再給
    content = story_base(library, char, base)
    request = story_request(library, char, content, char.region)
    fallback = StoryGen(key=request.key, skill=content.id)
    themed: dict[str, SkillDef] = {}

    def accept(gen: StoryGen) -> StoryGen | None:
        made = themed_story_skill(library, request, gen)
        if made is None:
            return None
        themed["skill"] = made
        return gen

    gen = supply(request, StoryGen, fallback, accept)
    skill = themed.get("skill", content) if gen.source == "llm" else content
    run = _add_to_bench(run, skill, library)
    run = with_acquired(run, skill.id, complete=True)
    event = StorySkillGrantedEvent(quest=quest.id, step=step.id, skill=skill.id, source=gen.source)
    return with_skill_region(from_run(char, run), skill.id, char.region), [event]


def _add_to_bench(run: RunState, skill: SkillDef, library: ContentLibrary) -> RunState:
    generated = {s.id: s for s in run.generated_skills}
    if skill.id not in library.skills:
        generated[skill.id] = skill
    return run.model_copy(
        update={
            "bench": tuple(sorted({*run.bench, skill.id})),
            "generated_skills": tuple(generated[k] for k in sorted(generated)),
        }
    )


def defers_offer(char: CharacterState, quest: QuestDef) -> bool:
    """入門期（#150 第 2 點，``opening.stage == "starter"``）新手任務的三選一先保留：正式選定時依
    選的武器與關鍵字再出題（:func:`issue_deferred_offers`）。其他角色、其他任務照舊當場出題。"""
    return char.opening is not None and char.opening.stage == "starter" and quest.kind == "starter"


def _defer_offer(char: CharacterState, quest: QuestDef, step_index: int) -> CharacterState:
    """記進 ``opening.deferred_offers``（依完成順序；``offers_made`` 不動，出題時才算）。"""
    assert char.opening is not None
    deferred = (*char.opening.deferred_offers, DeferredOffer(quest=quest.id, step=step_index))
    opening = char.opening.model_copy(update={"deferred_offers": deferred})
    return char.model_copy(update={"opening": opening})


def quest_home(library: ContentLibrary, quest_id: str) -> tuple[str, QuestDef] | None:
    """任務所在的（區域, 任務定義）：依區域 ID 排序找第一個有這個任務的任務表；沒有＝``None``。"""
    tables = library.world_quests.quests
    for region in sorted(tables):
        quest = tables[region].quest_by_id().get(quest_id)
        if quest is not None:
            return region, quest
    return None


def issue_deferred_offers(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> tuple[CharacterState, list[WorldEvent]]:
    """正式選定時（OB-2，#150 第 3 點）把入門期保留的三選一依序出題：規則同當場出題的
    :func:`_offer`（同一個角色技能種子、同一個 ``offers_made`` 計數、``mix``／``min_passive``／偏向
    照任務資料），只是主角已經換成正式的武器與起始技能；取得地點是任務所在的區域（不是選定時人在的
    城鎮）。``deferred_offers`` 留著不清（重選時要照它重新出題，OB-3；選到的招靠它記進
    ``granted_skills``，:func:`take_offer`）。任務資料裡找不到的（內容改過）略過。"""
    assert char.opening is not None
    out: list[WorldEvent] = []
    for deferred in char.opening.deferred_offers:
        home = quest_home(library, deferred.quest)
        if home is None or deferred.step >= len(home[1].steps):
            continue
        region, quest = home
        step = quest.steps[deferred.step]
        if step.reward.offer is None:
            continue
        char, offered = _offer(
            library, world, char, quest, step=step, offer=step.reward.offer, region=region
        )
        out.append(offered)
    return char, out


def _offer(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    quest: QuestDef,
    *,
    step: QuestStepDef,
    offer: SkillOfferReward,
    region: str | None = None,
) -> tuple[CharacterState, WorldEvent]:
    """``region``：取得地點的區域（省略＝角色當下的區域；延後出題時傳任務所在的區域）。"""
    region = char.region if region is None else region
    run = as_run(char, seed=skill_seed(world, char)).model_copy(
        update={"offers_made": char.offers_made}
    )
    reason = "complete" if offer.kind == "complete" else "level_up"
    made = make_offer(
        world_library(library),
        run,
        reason,
        region_keywords=offer_bias(library, region, quest, offer),
        mix=None if offer.mix is None else offer.mix.as_tuple(),
        min_passive=offer.min_passive,
        region=region,  # 6L-1（#126）：取得地點的區域
    )
    return store_offer(char, quest.id, step.id, made, region=region)


def offer_bias(
    library: ContentLibrary, region: str, quest: QuestDef, offer: SkillOfferReward
) -> tuple[str, ...]:
    """三選一新方向的偏向關鍵字（5B-4b，07 7.6）：``bias_keywords`` 有填就用它；否則區域任務鏈
    （``chain``）用本區的 ``region_keywords``；其他任務不偏向。"""
    if offer.bias_keywords:
        return offer.bias_keywords
    table = quest_table(library, region)
    if quest.kind != "chain" or table is None:
        return ()
    return table.region_keywords


def store_offer(
    char: CharacterState,
    quest: str,
    step: str,
    offer: SkillOffer,
    *,
    source: Literal["quest", "opportunity"] = "quest",
    guaranteed: bool = False,
    region: str | None = None,
    made_by: Literal["llm", "composer"] = "composer",
) -> tuple[CharacterState, WorldEvent]:
    """把產生好的三選一存進 ``pending_offers``（計數 +1）；任務與機遇（5B-4c）共用。
    ``guaranteed``（5D-2b）：保底觸發的機遇。``region``（6L-2）：取得地點的區域；``made_by``：
    候選的來源（機遇的 LLM 版）。"""
    pending = PendingOffer(
        quest=quest, step=step, offer=offer, source=source, guaranteed=guaranteed, region=region
    )
    char = char.model_copy(
        update={
            "pending_offers": (*char.pending_offers, pending),
            "offers_made": char.offers_made + 1,
        }
    )
    event = SkillOfferedEvent(
        quest=quest,
        step=step,
        reason=offer.reason,
        candidates=tuple(s.id for s in offer.candidates),
        source=source,
        made_by=made_by,
    )
    return char, event


def take_offer(
    library: ContentLibrary, char: CharacterState, action: OfferPickAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """選第一組待選的三選一（16.6）：跳過、裝上（城鎮與營火）或放進備用。"""
    if not char.pending_offers:
        raise WorldActionError("沒有待選的技能三選一")
    pending, rest = char.pending_offers[0], char.pending_offers[1:]
    offer = pending.offer
    if action.pick is None:
        if action.replace is not None:
            raise WorldActionError("沒有選候選時不能指定要替換的技能")
        event = SkillOfferTakenEvent(
            quest=pending.quest,
            step=pending.step,
            skill=None,
            placed="skipped",
            source=pending.source,
        )
        return char.model_copy(update={"pending_offers": rest}), (event,)
    if not 0 <= action.pick < len(offer.candidates):
        raise WorldActionError(f"候選索引必須是 0～{len(offer.candidates) - 1}，收到 {action.pick}")
    service = char.pending_encounter is None and at_service(library, char)
    if action.replace is not None and not service:
        raise WorldActionError("只有城鎮與營火能換技能；野外學到的技能會放進備用")
    lib = char_library(library, char)  # 有誓約時被動欄位少 1 格（5C-3）
    run = as_run(char)
    placed: str = "bench"
    try:
        if not service:
            raise ChoiceError("野外：放進備用")
        taken = take_candidate(lib, run, offer, action.pick, action.replace)
        placed = "equipped"
    except ChoiceError as exc:
        if action.replace is not None:
            raise WorldActionError(str(exc)) from exc
        taken = _bench_candidate(lib, run, offer.candidates[action.pick])
    except RunError as exc:  # pragma: no cover — 其他 roguelite 錯誤
        raise WorldActionError(str(exc)) from exc
    skill_id = _new_skill(run, taken)
    taken = with_acquired(taken, skill_id, complete=offer.reason == "complete")
    region = char.region if pending.region is None else pending.region
    char = from_run(char, taken).model_copy(update={"pending_offers": rest})
    char = with_skill_region(char, skill_id, region)  # 6L-2（#126）：取得地點的界域
    char = _note_granted(library, char, pending, skill_id)  # OB-2：重選時要收回的招
    event = SkillOfferTakenEvent(
        quest=pending.quest,
        step=pending.step,
        skill=skill_id,
        placed="equipped" if placed == "equipped" else "bench",
        source=pending.source,
    )
    return char, (event,)


def _note_granted(
    library: ContentLibrary, char: CharacterState, pending: PendingOffer, skill_id: str
) -> CharacterState:
    """正式選定後、開局還沒結束時，從延後的新手三選一選到的招記進 ``opening.granted_skills``
    （#150 第 5 點重選時要收回的招；其他來源的三選一不記）。"""
    opening = char.opening
    if opening is None or opening.stage != "chosen" or pending.source != "quest":
        return char
    home = quest_home(library, pending.quest)
    steps = () if home is None else home[1].steps
    ours = any(
        d.quest == pending.quest and d.step < len(steps) and steps[d.step].id == pending.step
        for d in opening.deferred_offers
    )
    if not ours or skill_id in opening.granted_skills:
        return char
    granted = (*opening.granted_skills, skill_id)
    return char.model_copy(
        update={"opening": opening.model_copy(update={"granted_skills": granted})}
    )


def _bench_candidate(library: ContentLibrary, run: RunState, skill: SkillDef) -> RunState:
    # 生成技能：撞名時加「（二）」（同 roguelite take_candidate）
    if skill.id not in library.skills:
        owned = skill_defs(library, run, [*run.hero.skills, *run.bench])
        skill = unique_skill_name(skill, (s.name_zh for s in owned if s.id != skill.id))
    return _add_to_bench(run, skill, library)


def _new_skill(before: RunState, after: RunState) -> str:
    added = sorted(set(owned_skills(after)) - set(owned_skills(before)))
    assert added, "選了候選卻沒有學到新技能"
    return added[0]
