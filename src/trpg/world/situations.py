"""情境判定的引擎半（Phase 5B-2；``docs/phases/Phase5計畫.md`` 第 9 節；09 9.6.4）。

純函式：吃「已經過 pydantic 驗證的提議」
（:class:`~trpg.content.world_situations.SituationProposal`），不呼叫 LLM、不讀玩家文字。流程：

1. **合法性**：角色身上有事件、模板屬於該事件的骨架、提議的屬性與方法在模板允許的清單、難度
   調整在 ±``dc_shift_max`` 內。不合法拋 :class:`~trpg.world.errors.WorldActionError`，狀態不變。
2. **用心清單**：每一筆的事實編號都對照 :func:`situation_facts`（引擎狀態）逐筆核對，核對不到不算；
   同一項只算一次；加值最多 ``care_max``。
3. **擲骰**：``check`` 串流一律擲兩顆 d20；持有模板的 ``advantage_threads`` ＝優勢（取高）、提議的
   劣勢（取低）、兩者都有＝抵銷。總值＝骰值＋屬性修正＋用心加值＋種族加值，對 ``base_dc ± 調整``。
4. **三段結果**：成功／部分成功（差 ``partial_margin`` 內）／失敗，照模板的表給獎懲（預算內）、
   留線頭，清掉事件（第一次送出即定案）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventSkeletonDef, SolutionDef, ThreadDef
from trpg.content.world_situations import (
    CARE_ITEMS,
    Outcome,
    SituationFact,
    SituationOutcomeDef,
    SituationProposal,
    SituationRules,
    SituationTemplateDef,
    proposal_problems,
)
from trpg.shared.types import Attribute
from trpg.world.actions import (
    CareResult,
    EventResolvedEvent,
    LocationRevealedEvent,
    SituationAction,
    SituationCheckEvent,
    SituationResultEvent,
    ThreadAddedEvent,
    ThreadPushedOutEvent,
    WorldEvent,
)
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.rng import STREAM_CHECK, draw
from trpg.world.state import (
    CharacterState,
    EventTrigger,
    LocationRef,
    NextBattleMod,
    WorldState,
)
from trpg.world.threads import active_threads, add_thread

__all__ = [
    "CheckRoll",
    "attribute_modifier",
    "held_threads",
    "opportunity_available",
    "resolve_situation",
    "situation_facts",
    "situation_rules",
    "situation_template",
]

_EXCHANGE_FACT = "supplies"


# ---------------------------------------------------------------------------
# 查表
# ---------------------------------------------------------------------------


def situation_rules(library: ContentLibrary) -> SituationRules:
    rules = library.world_event_content.situations.rules
    if rules is None:
        raise WorldError("內容庫沒有 world/situation_rules.yaml")
    return rules


def situation_template(
    library: ContentLibrary, region: str, template_id: str
) -> SituationTemplateDef:
    """``region`` 的情境模板；沒有拋 :class:`WorldActionError`。"""
    table = library.world_event_content.situations.templates.get(region)
    template = None if table is None else table.template_by_id().get(template_id)
    if template is None:
        raise WorldActionError(f"{region} 沒有情境模板 {template_id}")
    return template


def _skeleton(library: ContentLibrary, region: str, skeleton_id: str) -> EventSkeletonDef:
    table = library.world_event_content.events.get(region)
    skeleton = None if table is None else table.skeleton_by_id().get(skeleton_id)
    if skeleton is None:
        raise WorldError(f"{region} 沒有事件骨架 {skeleton_id}")
    return skeleton


def _thread_defs(library: ContentLibrary) -> dict[str, ThreadDef]:
    """所有區域的線頭定義（ID 跨區不重複）。"""
    out: dict[str, ThreadDef] = {}
    for table in library.world_event_content.events.values():
        out.update(table.thread_by_id())
    return out


def held_threads(world: WorldState, char: CharacterState, now: int) -> tuple[str, ...]:
    """角色現在持有的有效線頭 ID（個人＋世界級），排序、不重複。"""
    ids = {t.thread for t in active_threads(char.threads, now)}
    ids |= {t.thread for t in active_threads(world.threads, now)}
    return tuple(sorted(ids))


def _max_hp(library: ContentLibrary, char: CharacterState) -> int:
    """最大 HP（同 :func:`trpg.world.step.max_hp`；本模組被 ``step`` 匯入，不能反過來匯入它）。"""
    core = library.ruleset.core
    return core.run_max_hp(char.hero.max_hp, char.hero.attributes[Attribute.CON], char.level)


def _reveal(char: CharacterState, location: str) -> CharacterState:
    refs = [*char.revealed, LocationRef(region=char.region, location=location)]
    refs.sort(key=LocationRef.key)
    return char.model_copy(update={"revealed": tuple(refs)})


def attribute_modifier(library: ContentLibrary, char: CharacterState, attribute: Attribute) -> int:
    """屬性修正 ＝ ``(屬性 − ability_mod_base) // ability_mod_divisor``（同感知判定與引擎檢定）。"""
    core = library.ruleset.core
    return (char.hero.attributes[attribute] - core.ability_mod_base) // core.ability_mod_divisor


def opportunity_available(
    library: ContentLibrary, char: CharacterState, solution: SolutionDef
) -> bool:
    """機遇解法的條件是否成立（18.4 補充：裝備的技能中任何一招帶 ``requires_keyword``）。

    非機遇解法回傳 ``False``；機遇沒有條件時回傳 ``True``。
    """
    if solution.kind != "opportunity":
        return False
    keyword = solution.requires_keyword
    if keyword is None:
        return True
    for skill_id in char.hero.skills:
        skill = library.skills.get(skill_id)
        if skill is not None and keyword in library.ruleset.skill_keywords(skill).all():
            return True
    return False


# ---------------------------------------------------------------------------
# 用心清單的事實
# ---------------------------------------------------------------------------


def situation_facts(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    template: SituationTemplateDef,
    now: int,
) -> tuple[SituationFact, ...]:
    """引擎核對得到的事實（給外層交給 LLM 挑、給引擎核對），依清單項目、事實編號排序。

    ① ``clue`` ``thread:<id>``：持有的有效線頭；② ``npc_bond`` ``npc:<id>``：骨架相關的 NPC 中、
    角色持有以他為對象的線頭（過去互動的紀錄）；③ ``exchange`` ``supplies``：拿得出交換用的補給；
    ④ ``weakness`` ``weakness:<id>``：模板的情境弱點（還要方法相符才算）。
    """
    rules = situation_rules(library)
    defs = _thread_defs(library)
    held = held_threads(world, char, now)
    facts: list[SituationFact] = []
    for thread_id in held:
        thread = defs.get(thread_id)
        text = thread.text_zh if thread is not None else thread_id
        facts.append(SituationFact(item="clue", fact=f"thread:{thread_id}", text_zh=text))
    skeleton = _skeleton(library, char.region, template.skeleton)
    npc_table = library.world_event_content.npcs.get(char.region)
    cards = {} if npc_table is None else npc_table.npc_by_id()
    for npc_id in sorted(skeleton.npcs):
        bonds = [defs[t] for t in held if t in defs and defs[t].npc == npc_id]
        if bonds:
            name = cards[npc_id].name_zh if npc_id in cards else npc_id
            text = f"{name}（{'、'.join(b.text_zh for b in bonds)}）"
            facts.append(SituationFact(item="npc_bond", fact=f"npc:{npc_id}", text_zh=text))
    if char.supplies >= rules.exchange_supplies:
        text = f"拿出 {rules.exchange_supplies} 份補給交換"
        facts.append(SituationFact(item="exchange", fact=_EXCHANGE_FACT, text_zh=text))
    for weakness in template.weaknesses:
        fact = f"weakness:{weakness.id}"
        facts.append(SituationFact(item="weakness", fact=fact, text_zh=weakness.text_zh))
    order = {item: i for i, item in enumerate(CARE_ITEMS)}
    facts.sort(key=lambda f: (order[f.item], f.fact))
    return tuple(facts)


def _verify_care(
    template: SituationTemplateDef,
    proposal: SituationProposal,
    facts: tuple[SituationFact, ...],
    care_max: int,
) -> tuple[tuple[CareResult, ...], int]:
    """逐筆核對用心清單；回傳（明細, 加值）。核對不到、同一項重複的都「不算」。"""
    known = {(f.item, f.fact) for f in facts}
    weaknesses = template.weakness_by_id()
    counted: set[str] = set()
    results: list[CareResult] = []
    for claim in proposal.care:
        reason = ""
        if claim.item in counted:
            reason = "同一項只算一次"
        elif (claim.item, claim.fact) not in known:
            reason = "核對不到這筆事實"
        elif claim.item == "weakness":
            weakness = weaknesses[claim.fact.removeprefix("weakness:")]
            if proposal.method not in weakness.methods:
                reason = "方法沒有針對這個弱點"
        if not reason:
            counted.add(claim.item)
        results.append(
            CareResult(item=claim.item, fact=claim.fact, counted=not reason, reason_zh=reason)
        )
    return tuple(results), min(care_max, len(counted))


# ---------------------------------------------------------------------------
# 擲骰
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckRoll:
    dice: tuple[int, int]
    mode: Literal["normal", "advantage", "disadvantage"]
    roll: int


def _roll(
    world: WorldState, char: CharacterState, *, advantage: bool, disadvantage: bool
) -> tuple[CheckRoll, CharacterState]:
    rng, char = draw(world.season_seed, char, STREAM_CHECK)
    dice = (rng.d20(), rng.d20())
    if advantage and not disadvantage:
        return CheckRoll(dice, "advantage", max(dice)), char
    if disadvantage and not advantage:
        return CheckRoll(dice, "disadvantage", min(dice)), char
    return CheckRoll(dice, "normal", dice[0]), char


def _outcome(total: int, dc: int, partial_margin: int) -> Outcome:
    if total >= dc:
        return "success"
    if total >= dc - partial_margin:
        return "partial"
    return "failure"


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------


def _check_action(
    library: ContentLibrary, char: CharacterState, action: SituationAction
) -> tuple[EventTrigger, SituationTemplateDef]:
    trigger = char.pending_event
    if trigger is None:
        raise WorldActionError("目前沒有事件可以做情境判定")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能做情境判定")
    template = situation_template(library, char.region, action.template)
    if template.skeleton != trigger.skeleton:
        raise WorldActionError(f"情境模板 {template.id} 不屬於目前的事件 {trigger.skeleton}")
    problems = proposal_problems(template, situation_rules(library), action.proposal)
    if problems:
        raise WorldActionError(f"提議不合法：{'；'.join(problems)}")
    return trigger, template


def _location_level(library: ContentLibrary, region: str, location: str) -> int:
    loc = library.world_maps[region].location_by_id().get(location)
    if loc is None or loc.level_max is None:
        return 1
    return loc.level_max


@dataclass
class _Apply:
    """結算中的可變暫存（只在 :func:`resolve_situation` 內部使用）。"""

    world: WorldState
    char: CharacterState
    events: list[WorldEvent]


def _add_threads(
    library: ContentLibrary,
    state: _Apply,
    thread_ids: tuple[str, ...],
    skeleton: str,
    now: int,
) -> None:
    event_rules = library.world_event_content.rules
    if event_rules is None:
        raise WorldError("內容庫沒有 world/event_rules.yaml")
    defs = _thread_defs(library)
    limits = event_rules.threads
    region = state.char.region
    for thread_id in thread_ids:
        scope = defs[thread_id].scope
        if scope == "world":
            threads, pushed = add_thread(
                state.world.threads,
                thread_id,
                skeleton,
                region,
                now,
                limit=limits.world_limit,
                expire_seconds=limits.expire_seconds,
            )
            state.world = state.world.model_copy(update={"threads": threads})
        else:
            threads, pushed = add_thread(
                state.char.threads,
                thread_id,
                skeleton,
                region,
                now,
                limit=limits.personal_limit,
                expire_seconds=limits.expire_seconds,
            )
            state.char = state.char.model_copy(update={"threads": threads})
        state.events += [ThreadPushedOutEvent(thread=t.thread, scope=scope) for t in pushed]
        added = next((t for t in threads if t.thread == thread_id), None)
        if added is not None and added.created_at == now:
            state.events.append(
                ThreadAddedEvent(thread=thread_id, scope=scope, expires_at=added.expires_at)
            )


def _apply_outcome(
    library: ContentLibrary,
    state: _Apply,
    template: SituationTemplateDef,
    outcome: Outcome,
    *,
    level: int,
    exchange_spent: int,
    now: int,
) -> None:
    """照模板的表給獎懲；執行期再對預算截一次（防資料被繞過）。"""
    rules = situation_rules(library)
    budget = rules.budget
    table: SituationOutcomeDef = template.outcome(outcome)
    rew, pen = table.rewards, table.penalties
    char = state.char
    before_supplies = char.supplies + exchange_spent
    supplies_cap = library.world_rules.supplies.max if library.world_rules is not None else 0
    supplies = max(0, char.supplies - pen.supplies)
    supplies = min(supplies_cap, supplies + min(rew.supplies, budget.supplies_max))
    xp = budget.xp_for(level) * rew.xp_permille // 1000
    hp_lost = 0
    if pen.hurt_permille:
        hp_lost = max(0, min(char.hp - 1, _max_hp(library, char) * pen.hurt_permille // 1000))
    mods = [
        *(
            NextBattleMod(kind="buff", status=s, source=template.id)
            for s in rew.buffs[: budget.buffs_max]
        ),
        *(NextBattleMod(kind="debuff", status=s, source=template.id) for s in pen.debuffs),
    ]
    if pen.reinforce:
        mods.append(NextBattleMod(kind="reinforce", source=template.id))
    state.char = char.model_copy(
        update={
            "supplies": supplies,
            "xp": char.xp + xp,
            "hp": char.hp - hp_lost,
            "next_battle": (*char.next_battle, *mods),
        }
    )
    state.events.append(
        SituationResultEvent(
            template=template.id,
            outcome=outcome,
            xp=xp,
            supplies_delta=supplies - before_supplies,
            hp_lost=hp_lost,
            next_battle=tuple(mods),
        )
    )
    for location in rew.reveal[: budget.reveals_max]:
        if not state.char.has_revealed(state.char.region, location):
            state.char = _reveal(state.char, location)
            state.events.append(LocationRevealedEvent(location=location, method="situation"))
    _add_threads(library, state, rew.threads[: budget.threads_max], template.skeleton, now)


def resolve_situation(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: SituationAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """結算一次情境判定（:func:`~trpg.world.step.world_step` 的 ``situation`` 動作）。"""
    trigger, template = _check_action(library, char, action)
    rules = situation_rules(library)
    proposal = action.proposal
    facts = situation_facts(library, world, char, template, now)
    care, care_bonus = _verify_care(template, proposal, facts, rules.check.care_max)
    exchange_spent = 0
    if any(c.counted and c.item == "exchange" for c in care):
        exchange_spent = rules.exchange_supplies
        char = char.model_copy(update={"supplies": char.supplies - exchange_spent})
    held = set(held_threads(world, char, now))
    advantage = any(t in held for t in template.advantage_threads)
    check, char = _roll(world, char, advantage=advantage, disadvantage=proposal.disadvantage)
    attribute_mod = attribute_modifier(library, char, proposal.attribute)
    race = char.hero.race
    race_bonus = (
        rules.check.race_bonus if rules.race_methods.get(race or "") == proposal.method else 0
    )
    total = check.roll + attribute_mod + care_bonus + race_bonus
    dc = template.base_dc + proposal.dc_shift
    outcome = _outcome(total, dc, rules.check.partial_margin)
    state = _Apply(world=world, char=char, events=[])
    state.events.append(
        SituationCheckEvent(
            template=template.id,
            skeleton=template.skeleton,
            attribute=proposal.attribute,
            method=proposal.method,
            base_dc=template.base_dc,
            dc_shift=proposal.dc_shift,
            dc=dc,
            dice=check.dice,
            mode=check.mode,
            roll=check.roll,
            attribute_mod=attribute_mod,
            care=care,
            care_bonus=care_bonus,
            race_bonus=race_bonus,
            total=total,
            outcome=outcome,
            source=action.source,
        )
    )
    level = _location_level(library, trigger.region, trigger.location)
    _apply_outcome(
        library, state, template, outcome, level=level, exchange_spent=exchange_spent, now=now
    )
    state.char = state.char.model_copy(update={"pending_event": None})
    state.events.append(
        EventResolvedEvent(
            skeleton=template.skeleton,
            location=trigger.location,
            solution=template.solution,
            outcome=outcome,
        )
    )
    return state.world, state.char, tuple(state.events)
