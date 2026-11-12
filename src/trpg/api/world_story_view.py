"""大世界事件與任務的顯示資料（Phase 5B-5；``docs/phases/Phase5計畫.md`` 18.4、18.5）：事件卡、
情境判定、判定結果、這裡的 NPC 與好感度、對話、任務日誌、可接的任務、技能三選一、線頭、酒館傳聞、
事件句子。

規則一律呼叫 ``trpg.world``（允許的事實、條件、好感度級別）；這裡只組裝文字。給玩家看的內容文字一律
先套 :func:`trpg.world.narration.story_masks`（還沒發現的隱藏地點用提示語，玩法 PM 2026-11-03）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from trpg.api.run_presenter import offer_out
from trpg.api.world_growth_view import next_battle_lines
from trpg.api.world_story_schemas import (
    CareLineView,
    CiteFactView,
    DialogLineView,
    EventSolutionView,
    EventView,
    NpcHereView,
    PendingOfferView,
    QuestHereView,
    QuestLogView,
    QuestStepView,
    SituationResultView,
    SituationView,
    StoryView,
    ThreadView,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventSkeletonDef, SolutionDef, ThreadDef
from trpg.content.world_narration import StoryText, mask_text
from trpg.content.world_quests import AffinityRank, QuestDef
from trpg.content.world_situations import Outcome, SituationTemplateDef
from trpg.shared.types import Attribute
from trpg.world.actions import (
    AffinityChangedEvent,
    EventLeftEvent,
    EventTriggeredEvent,
    LocationRevealedEvent,
    NarrateAction,
    NarratedEvent,
    OpportunityHintEvent,
    QuestCompletedEvent,
    QuestStartedEvent,
    QuestStepDoneEvent,
    RumorsHeardEvent,
    SituationCheckEvent,
    SituationResultEvent,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    StorySkillGrantedEvent,
    TalkedEvent,
    ThreadAddedEvent,
    ThreadPushedOutEvent,
    WorldEvent,
)
from trpg.world.affinity import affinity_of, affinity_rules, rank_of, social_of
from trpg.world.common import here, world_map_of
from trpg.world.growth import as_run, at_service, skill_seed, world_library
from trpg.world.narration import region_npcs, region_skeletons, story_masks
from trpg.world.opening_limits import solution_problem
from trpg.world.quests import condition_holds, quest_table
from trpg.world.situations import (
    opportunity_available,
    situation_fact_keywords,
    situation_facts,
    situation_rules,
)
from trpg.world.state import CharacterState, ThreadState, WorldState
from trpg.world.threads import active_threads

__all__ = [
    "dialog_lines",
    "event_view",
    "npcs_here",
    "pending_offer_view",
    "quest_log",
    "quests_here",
    "rumor_lines",
    "situation_result_view",
    "story_event_line",
    "thread_views",
]

SOLUTION_KIND_ZH: Final[dict[str, str]] = {
    "combat": "戰鬥",
    "situation": "情境判定",
    "parley": "交涉",
    "abandon": "放棄",
    "opportunity": "機遇",
}
CARE_ZH: Final[dict[str, str]] = {
    "clue": "線索",
    "npc_bond": "和 NPC 的往來",
    "exchange": "交換條件",
    "weakness": "針對弱點",
}
OUTCOME_ZH: Final[dict[Outcome, str]] = {
    "success": "成功",
    "partial": "部分成功",
    "failure": "失敗",
}
MODE_ZH: Final[dict[str, str]] = {
    "normal": "一般",
    "advantage": "優勢（兩顆取高）",
    "disadvantage": "劣勢（兩顆取低）",
}
QUEST_KIND_ZH: Final[dict[str, str]] = {
    "starter": "新手",
    "main": "主線",
    "chain": "任務鏈",
    "hidden": "隱藏",
}
RANK_TALK_ZH: Final[dict[AffinityRank, str]] = {
    "hostile": "敵視：不肯多說，也不給任務",
    "cold": "冷淡：沒什麼好說的",
    "neutral": "中立：會說一般傳聞",
    "friendly": "友善：還會透露隱藏任務的入口",
    "trusted": "信賴：連祕密都肯說",
}
LATER_ZH: Final = "之後開放"
LEAVE_ZH: Final = "走到別的地點，這件事就此作罷。"
_CITABLE: Final = ("clue", "npc_bond", "exchange")
_HOUR: Final = 3600
_DAY: Final = 24 * _HOUR


def _num(value: int) -> str:
    return f"−{-value}" if value < 0 else str(value)


def _signed(value: int) -> str:
    return f"＋{value}" if value >= 0 else f"−{-value}"


def _attrs_zh(attributes: Sequence[Attribute]) -> str:
    return "、".join(a.display_name for a in attributes)


def story_view(story: StoryText, source: str, *, authored: bool = False) -> StoryView:
    """``authored``：文字是內容寫好的專用旁白（機遇保底，5B-4e），不是降級模板（5D-4）。"""
    kind: Literal["llm", "fallback", "authored"] = "llm" if source == "llm" else "fallback"
    if authored and kind == "fallback":
        kind = "authored"
    return StoryView(text_zh=story.text_zh, more_zh=story.more_zh, source=kind)


def _thread_defs(library: ContentLibrary) -> dict[str, ThreadDef]:
    out: dict[str, ThreadDef] = {}
    for table in library.world_event_content.events.values():
        out.update(table.thread_by_id())
    return out


def _location_name(library: ContentLibrary, region: str, location: str) -> str:
    found = world_map_of(library, region).location_by_id().get(location)
    return found.name_zh if found is not None else location


def _npc_name(library: ContentLibrary, region: str, npc: str) -> str:
    card = region_npcs(library, region).get(npc)
    return card.name_zh if card is not None else npc


# ---------------------------------------------------------------------------
# 事件卡
# ---------------------------------------------------------------------------


def _template_for(
    library: ContentLibrary, region: str, skeleton: str, solution: int
) -> SituationTemplateDef | None:
    table = library.world_event_content.situations.templates.get(region)
    if table is None:
        return None
    return next(
        (t for t in table.templates if t.skeleton == skeleton and t.solution == solution), None
    )


def _busy_zh(char: CharacterState) -> str | None:
    if char.pending_encounter is not None:
        return "先處理眼前的遭遇"
    if char.pending_flash is not None:
        return "先選完閃現的變化"
    if char.pending_offers:
        return "先選完任務給的技能"
    return None


def _can_fight_here(library: ContentLibrary, char: CharacterState) -> bool:
    """所在地點能開一般遭遇（同 ``trpg.world.solutions`` 戰鬥解法的前提）。"""
    place = here(library, char)
    table = library.world_encounters.get(char.region)
    return place.level_max is not None and table is not None and place.id in table.location_by_id()


def _held_thread(char: CharacterState, thread: str | None, now: int) -> ThreadState | None:
    if thread is None:
        return None
    return next((t for t in char.threads if t.thread == thread and t.expires_at > now), None)


def _opportunity_problem(
    library: ContentLibrary, char: CharacterState, solution: SolutionDef
) -> str | None:
    """機遇（5B-4c，同 ``trpg.world.solutions`` 的檢查）：條件不成立、這個機遇拿過了。"""
    pending = char.pending_event
    if pending is not None and pending.skeleton in char.opportunities:
        return "這個機遇已經拿過了"
    if not opportunity_available(library, char, solution):
        keyword = solution.requires_keyword or ""
        found = library.keywords.by_id().get(keyword)
        return f"要裝備帶「{found.name_zh if found is not None else keyword}」的技能"
    return None


def _solution_problem(
    library: ContentLibrary,
    char: CharacterState,
    solution: SolutionDef,
    *,
    has_template: bool,
    busy: str | None,
    waivable: bool,
) -> str | None:
    if solution.kind == "situation":
        return busy if has_template else LATER_ZH
    blocked = busy or solution_problem(char, solution.kind)  # OB-4（#150）：入門期不開戰、不給招
    if blocked is not None:
        return blocked
    if solution.kind == "opportunity":
        return _opportunity_problem(library, char, solution)
    if solution.kind == "combat" and not _can_fight_here(library, char):
        return "這裡打不起來"
    if solution.kind == "parley" and not waivable and char.supplies < solution.cost_supplies:
        return f"補給不足（要 {solution.cost_supplies}）"
    return None


def _solutions(
    library: ContentLibrary,
    char: CharacterState,
    skeleton: EventSkeletonDef,
    *,
    in_battle: bool,
    now: int,
    masks: Mapping[str, str],
) -> tuple[EventSolutionView, ...]:
    pending = char.pending_event
    if in_battle or (pending is not None and pending.combat_solution is not None):
        busy: str | None = "戰鬥中"
    else:
        busy = _busy_zh(char)
    defs = _thread_defs(library)
    out: list[EventSolutionView] = []
    for index, solution in enumerate(skeleton.solutions):
        template = (
            _template_for(library, char.region, skeleton.id, index)
            if solution.kind == "situation"
            else None
        )
        held = _held_thread(char, solution.waive_thread, now) if solution.kind == "parley" else None
        waive_def = (
            defs.get(solution.waive_thread) if held is not None and solution.waive_thread else None
        )
        problem = _solution_problem(
            library,
            char,
            solution,
            has_template=template is not None,
            busy=busy,
            waivable=held is not None,
        )
        attributes = template.attributes if template is not None else solution.attributes
        out.append(
            EventSolutionView(
                index=index,
                kind=solution.kind,
                kind_zh=SOLUTION_KIND_ZH.get(solution.kind, solution.kind),
                note_zh=solution.note_zh,
                hint_zh=solution.hint_zh,
                attributes_zh=_attrs_zh(attributes),
                template=template.id if template is not None else None,
                available=problem is None,
                unavailable_zh=problem,
                cost_supplies=solution.cost_supplies,
                waive_thread=solution.waive_thread if held is not None else None,
                waive_zh=(mask_text(waive_def.text_zh, masks) if waive_def is not None else None),
                can_pay=char.supplies >= solution.cost_supplies,
            )
        )
    return tuple(out)


def _facts(
    library: ContentLibrary,
    world: WorldState,
    *,
    char: CharacterState,
    template: SituationTemplateDef,
    now: int,
    masks: Mapping[str, str],
) -> tuple[CiteFactView, ...]:
    keywords = situation_fact_keywords(library, world, char, template, now)
    return tuple(
        CiteFactView(
            fact=f.fact,
            item=f.item,
            item_zh=CARE_ZH[f.item],
            text_zh=mask_text(f.text_zh, masks),
            insert_zh=_insert_text(keywords.get(f.fact, ()), masks),
        )
        for f in situation_facts(library, world, char, template, now)
        if f.item in _CITABLE
    )


def _insert_text(keywords: Sequence[str], masks: Mapping[str, str]) -> str | None:
    """點選引用時插進回答的文字（5C-3d）：第一個沒被遮住的關鍵詞（引擎比對一定過）；都被遮住＝``None``。"""
    return next((k for k in keywords if mask_text(k, masks) == k), None)


def _situation_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    *,
    now: int,
    narration: NarrateAction,
    masks: Mapping[str, str],
) -> SituationView | None:
    assert narration.template is not None
    table = library.world_event_content.situations.templates.get(char.region)
    template = None if table is None else table.template_by_id().get(narration.template)
    if template is None or char.pending_event is None:
        return None
    if template.skeleton != char.pending_event.skeleton:
        return None
    methods = {m.id: m.name_zh for m in situation_rules(library).methods}
    return SituationView(
        template=template.id,
        note_zh=template.note_zh,
        attributes_zh=_attrs_zh(template.attributes),
        methods_zh="、".join(methods.get(m, m) for m in template.methods),
        base_dc=template.base_dc,
        story=story_view(narration.story, narration.source),
        facts=_facts(library, world, char=char, template=template, now=now, masks=masks),
    )


def event_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    narrations: Sequence[NarrateAction],
    *,
    in_battle: bool = False,
) -> EventView | None:
    """事件卡（有 ``pending_event`` 時）。``narrations`` 是這個事件觸發之後的敘述（日誌順序）。"""
    trigger = char.pending_event
    if trigger is None:
        return None
    skeleton = region_skeletons(library, char.region).get(trigger.skeleton)
    if skeleton is None:
        return None
    masks = story_masks(library, char)
    opening = next((n for n in reversed(narrations) if n.scene == "event"), None)
    situation = next((n for n in reversed(narrations) if n.scene == "situation"), None)
    story = opening.story if opening is not None else None
    who = skeleton.who_for(guaranteed=trigger.guaranteed)  # 5B-4f：保底有專用的「誰」
    follows = None
    if trigger.follows_thread is not None:
        defn = _thread_defs(library).get(trigger.follows_thread)
        follows = mask_text(defn.text_zh, masks) if defn is not None else None
    return EventView(
        skeleton=skeleton.id,
        location_name_zh=_location_name(library, char.region, trigger.location),
        actor_zh=mask_text(story.actor_zh if story else who, masks),
        motive_zh=mask_text(story.motive_zh if story else skeleton.want_zh, masks),
        story=story_view(
            story,
            opening.source,
            authored=trigger.guaranteed and story.text_zh == skeleton.guarantee_text_zh,
        )
        if story is not None and opening
        else None,
        who_zh=mask_text(who, masks),
        want_zh=mask_text(skeleton.want_zh, masks),
        obstacle_zh=mask_text(skeleton.obstacle_zh, masks),
        stakes_zh=mask_text(skeleton.stakes_zh, masks),
        follows_zh=follows,
        solutions=_solutions(library, char, skeleton, in_battle=in_battle, now=now, masks=masks),
        leave_zh=LEAVE_ZH,
        situation=(
            _situation_view(library, world, char, now=now, narration=situation, masks=masks)
            if situation is not None
            else None
        ),
        art=skeleton.art,  # 6C-ART2：只畫
        region=char.region,
    )


# ---------------------------------------------------------------------------
# 判定結果
# ---------------------------------------------------------------------------


def _effects(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent]
) -> list[str]:
    masks = story_masks(library, char)
    defs = _thread_defs(library)
    out: list[str] = []
    for event in events:
        if isinstance(event, SituationResultEvent):
            if event.xp:
                out.append(f"獲得 {event.xp} 經驗")
            if event.supplies_delta:
                out.append(f"補給 {_signed(event.supplies_delta)}")
            if event.hp_lost:
                out.append(f"HP −{event.hp_lost}")
            out += next_battle_lines(library, event.next_battle)
        elif isinstance(event, ThreadAddedEvent):
            defn = defs.get(event.thread)
            text = mask_text(defn.text_zh, masks) if defn is not None else event.thread
            out.append(f"留下線頭：{text}")
        elif isinstance(event, LocationRevealedEvent) and event.method == "situation":
            out.append(f"發現了隱藏地點：{_location_name(library, char.region, event.location)}")
    return out


def _fact_text(
    library: ContentLibrary,
    char: CharacterState,
    template: SituationTemplateDef | None,
    fact: str,
) -> str:
    """用心清單的事實編號 → 中文（``thread:<id>``、``npc:<id>``、``supplies``、
    ``weakness:<id>``）。"""
    kind, _, ref = fact.partition(":")
    if kind == "thread":
        defn = _thread_defs(library).get(ref)
        return defn.text_zh if defn is not None else ref
    if kind == "npc":
        return _npc_name(library, char.region, ref)
    if kind == "weakness" and template is not None:
        found = next((w for w in template.weaknesses if w.id == ref), None)
        return found.text_zh if found is not None else ref
    if fact == "supplies":
        return "拿出補給交換"
    return fact


def situation_result_view(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent]
) -> SituationResultView | None:
    """這次請求的情境判定明細（沒有判定為 ``None``）。"""
    check = next((e for e in events if isinstance(e, SituationCheckEvent)), None)
    if check is None:
        return None
    table = library.world_event_content.situations.templates.get(char.region)
    template = None if table is None else table.template_by_id().get(check.template)
    methods = {m.id: m.name_zh for m in situation_rules(library).methods}
    masks = story_masks(library, char)
    outcome = next(
        (e for e in events if isinstance(e, NarratedEvent) and e.scene == "outcome"), None
    )
    return SituationResultView(
        template=check.template,
        note_zh=template.note_zh if template is not None else check.template,
        attribute_zh=check.attribute.display_name,
        method_zh=methods.get(check.method, check.method),
        dice=check.dice,
        mode_zh=MODE_ZH[check.mode],
        roll=check.roll,
        attribute_mod=check.attribute_mod,
        care=tuple(
            CareLineView(
                item_zh=CARE_ZH[c.item],
                text_zh=mask_text(_fact_text(library, char, template, c.fact), masks),
                counted=c.counted,
                reason_zh=c.reason_zh,
            )
            for c in check.care
        ),
        care_bonus=check.care_bonus,
        race_bonus=check.race_bonus,
        total=check.total,
        base_dc=check.base_dc,
        dc_shift=check.dc_shift,
        dc=check.dc,
        outcome=check.outcome,
        outcome_zh=OUTCOME_ZH[check.outcome],
        effects_zh=tuple(_effects(library, char, events)),
        story=story_view(outcome.story, outcome.source) if outcome is not None else None,
        source=check.source,
    )


# ---------------------------------------------------------------------------
# NPC 與對話
# ---------------------------------------------------------------------------


def _rank_range(library: ContentLibrary, rank: AffinityRank) -> tuple[str, str]:
    rules = affinity_rules(library)
    ranks = list(rules.ranks)
    for i, defn in enumerate(ranks):
        if defn.id == rank:
            hi = ranks[i + 1].min - 1 if i + 1 < len(ranks) else rules.max_value
            return defn.name_zh, f"{defn.name_zh}（{_num(defn.min)}～{_num(hi)}）"
    return rank, rank  # pragma: no cover — 級別一定在表裡


def npcs_here(library: ContentLibrary, char: CharacterState) -> tuple[NpcHereView, ...]:
    """所在地點的 NPC 與好感度（9.6.7 #5：玩家看得到；級距照 #116）。"""
    out: list[NpcHereView] = []
    for card in sorted(region_npcs(library, char.region).values(), key=lambda c: c.id):
        if card.location != char.location:
            continue
        rank = rank_of(library, char, card.id)
        rank_zh, range_zh = _rank_range(library, rank)
        out.append(
            NpcHereView(
                id=card.id,
                name_zh=card.name_zh,
                role_zh=card.role_zh,
                affinity=affinity_of(char, card.id),
                rank=rank,
                rank_zh=rank_zh,
                range_zh=range_zh,
                talk_zh=RANK_TALK_ZH[rank],
                portrait=card.portrait,
            )
        )
    return tuple(out)


def dialog_lines(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent]
) -> tuple[DialogLineView, ...]:
    """這次請求的對話：``talk`` 給的內容、``chat`` 的回話。"""
    masks = story_masks(library, char)
    table = social_of(library, char.region)
    entries = {e.id: e for e in (table.talk if table is not None else ())}
    out: list[DialogLineView] = []
    for event in events:
        if isinstance(event, TalkedEvent):
            name = _npc_name(library, char.region, event.npc)
            if not event.entries:
                out.append(
                    DialogLineView(
                        npc=event.npc, speaker_zh=name, kind="nothing", text_zh="沒什麼好說的。"
                    )
                )
            for entry_id in event.entries:
                entry = entries.get(entry_id)
                if entry is None:
                    continue
                out.append(
                    DialogLineView(
                        npc=event.npc,
                        speaker_zh=name,
                        kind=entry.kind,
                        text_zh=mask_text(entry.text_zh, masks),
                    )
                )
        elif isinstance(event, NarratedEvent) and event.scene == "chat" and event.npc:
            out.append(
                DialogLineView(
                    npc=event.npc,
                    speaker_zh=_npc_name(library, char.region, event.npc),
                    kind="chat",
                    text_zh=event.story.text_zh,
                    more_zh=event.story.more_zh,
                    source=event.source,
                )
            )
    return tuple(out)


def rumor_lines(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent]
) -> tuple[str, ...]:
    """這次請求在酒館聽到的傳聞文字。"""
    heard = next((e for e in events if isinstance(e, RumorsHeardEvent)), None)
    if heard is None:
        return ()
    table = social_of(library, char.region)
    rumors = {r.id: r for r in (table.rumors if table is not None else ())}
    masks = story_masks(library, char)
    return tuple(mask_text(rumors[r].text_zh, masks) for r in heard.rumors if r in rumors)


# ---------------------------------------------------------------------------
# 任務
# ---------------------------------------------------------------------------


def _quest_text(defn: QuestDef, masks: Mapping[str, str]) -> tuple[str, str]:
    return mask_text(defn.name_zh, masks), mask_text(defn.summary_zh, masks)


def quest_log(library: ContentLibrary, char: CharacterState) -> tuple[QuestLogView, ...]:
    """任務日誌（依任務 ID；進行中與完成的都列）。"""
    table = quest_table(library, char.region)
    if table is None:
        return ()
    defs = table.quest_by_id()
    masks = story_masks(library, char)
    out: list[QuestLogView] = []
    for state in char.quests:
        defn = defs.get(state.quest)
        if defn is None:
            continue
        name, summary = _quest_text(defn, masks)
        steps = tuple(
            QuestStepView(
                text_zh=mask_text(step.text_zh, masks),
                done=i < state.steps_done,
                current=not state.done and i == state.steps_done,
            )
            for i, step in enumerate(defn.steps)
        )
        out.append(
            QuestLogView(
                id=defn.id,
                name_zh=name,
                kind_zh=QUEST_KIND_ZH.get(defn.kind, defn.kind),
                summary_zh=summary,
                giver_zh=_npc_name(library, char.region, defn.giver) if defn.giver else None,
                steps=steps,
                done=state.done,
            )
        )
    return tuple(out)


def quests_here(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[QuestHereView, ...]:
    """在這裡可以接的任務：給任務的人在這裡（或沒有給的人）；隱藏任務只在開始條件成立時列出。"""
    table = quest_table(library, char.region)
    if table is None:
        return ()
    cards = region_npcs(library, char.region)
    masks = story_masks(library, char)
    out: list[QuestHereView] = []
    for defn in table.quests:
        if char.quest_state(defn.id) is not None:
            continue
        giver = cards.get(defn.giver) if defn.giver is not None else None
        if defn.giver is not None and (giver is None or giver.location != char.location):
            continue
        ready = all(
            condition_holds(library, world, char, c, events=(), now=now) for c in defn.start
        )
        if defn.kind == "hidden" and not ready:
            continue
        problem: str | None = None
        if not ready:
            problem = "還沒達成開始條件"
        elif giver is not None and rank_of(library, char, giver.id) == "hostile":
            problem = "對方敵視你，不肯給你任務"
        elif (busy := _busy_zh(char)) is not None:
            problem = busy
        name, summary = _quest_text(defn, masks)
        out.append(
            QuestHereView(
                id=defn.id,
                name_zh=name,
                kind_zh=QUEST_KIND_ZH.get(defn.kind, defn.kind),
                summary_zh=summary,
                giver_zh=giver.name_zh if giver is not None else None,
                can_accept=problem is None,
                problem_zh=problem,
            )
        )
    return tuple(out)


def pending_offer_view(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> PendingOfferView | None:
    """第一組待選的技能三選一（07 7.6）。"""
    if not char.pending_offers:
        return None
    pending = char.pending_offers[0]
    masks = story_masks(library, char)
    if pending.source == "opportunity":  # 機遇（5B-4c）：quest＝骨架 ID
        events = library.world_event_content.events.get(char.region)
        skeleton = events.skeleton_by_id().get(pending.quest) if events is not None else None
        name_zh = (  # 5D-2b：保底觸發的那次用保底的「誰」
            mask_text(skeleton.who_for(guaranteed=pending.guaranteed), masks)
            if skeleton is not None
            else pending.quest
        )
        step_zh = "機遇"
    else:
        table = quest_table(library, char.region)
        defn = table.quest_by_id().get(pending.quest) if table is not None else None
        step = next((s for s in defn.steps if s.id == pending.step), None) if defn else None
        name_zh = mask_text(defn.name_zh, masks) if defn is not None else pending.quest
        step_zh = mask_text(step.text_zh, masks) if step is not None else pending.step
    run = as_run(char, seed=skill_seed(world, char))
    offer = offer_out(world_library(library), run, pending.offer)
    assert offer is not None
    service = char.pending_encounter is None and at_service(library, char)
    return PendingOfferView(
        quest_name_zh=name_zh,
        step_zh=step_zh,
        offer=offer,
        can_replace=service,
        place_zh=(
            "在城鎮或營火：選了可以直接裝上（欄位滿時指定要換掉的技能）。"
            if service
            else "在野外：選了先放進備用，回城鎮或營火再換上。"
        ),
    )


# ---------------------------------------------------------------------------
# 線頭
# ---------------------------------------------------------------------------


def _remaining_zh(seconds: int) -> str:
    if seconds < _HOUR:
        return "不到 1 小時後到期"
    days, rest = divmod(seconds, _DAY)
    hours = rest // _HOUR
    if days == 0:
        return f"{hours} 小時後到期"
    return f"{days} 天 {hours} 小時後到期" if hours else f"{days} 天後到期"


def thread_views(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[ThreadView, ...]:
    """持有的有效線頭（個人＋世界，依 ID）。"""
    defs = _thread_defs(library)
    masks = story_masks(library, char)
    seen: dict[str, ThreadState] = {}
    for state in (*active_threads(char.threads, now), *active_threads(world.threads, now)):
        seen.setdefault(state.thread, state)
    out: list[ThreadView] = []
    for thread_id in sorted(seen):
        state = seen[thread_id]
        defn = defs.get(thread_id)
        if defn is None:
            continue
        location = None
        if defn.hints_location is not None:
            location = mask_text(_location_name(library, state.region, defn.hints_location), masks)
        out.append(
            ThreadView(
                id=thread_id,
                text_zh=mask_text(defn.text_zh, masks),
                scope=defn.scope,
                scope_zh="世界" if defn.scope == "world" else "個人",
                expires_zh=_remaining_zh(state.expires_at - now),
                npc_zh=_npc_name(library, state.region, defn.npc) if defn.npc else None,
                location_zh=location,
            )
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# 事件句子
# ---------------------------------------------------------------------------


def _quest_name(library: ContentLibrary, char: CharacterState, quest: str) -> str:
    table = quest_table(library, char.region)
    defn = table.quest_by_id().get(quest) if table is not None else None
    return mask_text(defn.name_zh, story_masks(library, char)) if defn is not None else quest


def _event_story_line(
    library: ContentLibrary, char: CharacterState, event: WorldEvent
) -> str | None:
    masks = story_masks(library, char)
    skeletons = region_skeletons(library, char.region)
    if isinstance(event, EventTriggeredEvent):
        trigger = event.trigger
        found = skeletons.get(trigger.skeleton)
        who = (
            mask_text(found.who_for(guaranteed=trigger.guaranteed), masks)
            if found is not None
            else trigger.skeleton
        )
        place = _location_name(library, trigger.region, trigger.location)
        return f"在{place}遇到一件事：{who}。"
    if isinstance(event, EventLeftEvent):
        found = skeletons.get(event.skeleton)
        who = (  # 5D-2b：保底觸發的那次用保底的「誰」
            mask_text(found.who_for(guaranteed=event.guaranteed), masks)
            if found is not None
            else event.skeleton
        )
        return (
            f"離開了{_location_name(library, char.region, event.location)}，「{who}」的事就此作罷。"
        )
    if isinstance(event, ThreadAddedEvent | ThreadPushedOutEvent):
        defn = _thread_defs(library).get(event.thread)
        text = mask_text(defn.text_zh, masks) if defn is not None else event.thread
        if isinstance(event, ThreadAddedEvent):
            return f"留下線頭：{text}。"
        return f"線頭太多，「{text}」被擠掉了。"
    return None


def _check_line(event: WorldEvent) -> str | None:
    if isinstance(event, SituationCheckEvent):
        mods = event.attribute_mod + event.care_bonus + event.race_bonus
        return (
            f"情境判定（{event.attribute.display_name}）：d20={event.roll}"
            f"{_signed(mods)}＝{event.total}，DC {event.dc}：{OUTCOME_ZH[event.outcome]}。"
        )
    if isinstance(event, SituationResultEvent):
        parts = [f"獲得 {event.xp} 經驗"] if event.xp else []
        if event.supplies_delta:
            parts.append(f"補給 {_signed(event.supplies_delta)}")
        if event.hp_lost:
            parts.append(f"HP −{event.hp_lost}")
        if event.next_battle:
            parts.append("下一場戰鬥會受影響")
        return f"判定結果：{'、'.join(parts)}。" if parts else None
    return None


def _quest_story_line(
    library: ContentLibrary, char: CharacterState, event: WorldEvent
) -> str | None:
    if isinstance(event, QuestStartedEvent):
        return f"接下任務「{_quest_name(library, char, event.quest)}」。"
    if isinstance(event, QuestStepDoneEvent):
        gains = [f"＋{event.xp} 經驗"] if event.xp else []
        if event.insight:
            gains.append(f"＋{event.insight} 靈感")
        extra = f"（{'、'.join(gains)}）" if gains else ""
        return f"任務「{_quest_name(library, char, event.quest)}」完成第 {event.index} 步{extra}。"
    if isinstance(event, QuestCompletedEvent):
        return f"完成任務「{_quest_name(library, char, event.quest)}」！"
    return None


def _skill_story_line(event: WorldEvent, names: Mapping[str, str]) -> str | None:
    if isinstance(event, SkillOfferedEvent):
        source = "機遇" if event.source == "opportunity" else "任務"
        return f"{source}給了技能三選一：先選一招（或跳過）。"
    if isinstance(event, SkillOfferTakenEvent):
        if event.skill is None:
            return (
                "跳過了機遇給的技能。" if event.source == "opportunity" else "跳過了任務給的技能。"
            )
        where = "裝上" if event.placed == "equipped" else "放進備用"
        return f"學會「{names.get(event.skill, event.skill)}」，{where}。"
    if isinstance(event, StorySkillGrantedEvent):
        return f"得到劇情技能「{names.get(event.skill, event.skill)}」（放進備用）。"
    return None


def _social_line(library: ContentLibrary, char: CharacterState, event: WorldEvent) -> str | None:
    if isinstance(event, AffinityChangedEvent):
        name = _npc_name(library, char.region, event.npc)
        to_zh, _ = _rank_range(library, event.rank)
        line = f"{name}的好感度 {_signed(event.delta)}（{_num(event.value)}・{to_zh}）"
        if event.from_rank != event.rank:
            from_zh, _ = _rank_range(library, event.from_rank)
            line += f"：{from_zh} → {to_zh}"
        return line + "。"
    if isinstance(event, TalkedEvent):
        name = _npc_name(library, char.region, event.npc)
        rank_zh, _ = _rank_range(library, event.rank)
        return f"和{name}說話（{rank_zh}）。"
    if isinstance(event, RumorsHeardEvent):
        return f"在酒館聽到 {len(event.rumors)} 則本週傳聞。"
    if isinstance(event, OpportunityHintEvent):
        return event.text_zh  # 5B-4e：機遇提示（內容庫的整句）
    return None


def story_event_line(
    library: ContentLibrary, char: CharacterState, event: WorldEvent, names: Mapping[str, str]
) -> str | None:
    """事件、情境判定、線頭、任務、好感度、說話、酒館的句子（5B-5）；其他事件為 ``None``。"""
    return (
        _event_story_line(library, char, event)
        or _check_line(event)
        or _quest_story_line(library, char, event)
        or _skill_story_line(event, names)
        or _social_line(library, char, event)
    )
