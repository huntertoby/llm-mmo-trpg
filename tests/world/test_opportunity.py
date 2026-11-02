"""機遇解法的結算（Phase 5B-4c；``docs/phases/Phase5計畫.md`` 21.4；07 7.6）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world, with_rules
from tests.world.test_situations import at_event
from trpg.content.library import ContentLibrary
from trpg.skillgen.candidates import skill_has_keywords
from trpg.world.actions import (
    EventResolvedEvent,
    EventSolveAction,
    EventSolvedEvent,
    EventTriggeredEvent,
    OfferPickAction,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    TalkAction,
    WorldEvent,
)
from trpg.world.errors import WorldActionError
from trpg.world.events import (
    guaranteed_opportunity,
    mark_met_opportunities,
    roll_event,
    season_day,
)
from trpg.world.growth import hero_tier, world_library
from trpg.world.solutions import opportunity_tier_bonus
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

ALTAR = "storm_altar"
OPPORTUNITY = 0  # 骨架 12 的第 0 個解法＝機遇（帶「帶電」技能靠近）
CHARGED = "skill_chain_lightning"


def _charged(char: CharacterState) -> CharacterState:
    """第一招換成帶「帶電」關鍵字的技能（機遇的條件）。"""
    skills = (CHARGED, *char.hero.skills[1:])
    return char.model_copy(update={"hero": char.hero.model_copy(update={"skills": skills})})


def _at_altar(char: CharacterState) -> CharacterState:
    return at_event(char, ALTAR, "old_pine_altar")


def test_condition_required(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _at_altar(make_char())
    with pytest.raises(WorldActionError, match="條件不成立"):
        world_step(library, make_world(), char, EventSolveAction(solution=OPPORTUNITY), NOON)


def test_opportunity_gives_complete_offer(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _at_altar(_charged(make_char()))
    result = world_step(library, make_world(), char, EventSolveAction(solution=OPPORTUNITY), NOON)
    after = result.char
    assert after.pending_event is None
    assert after.opportunities == (ALTAR,)
    assert len(after.pending_offers) == 1
    pending = after.pending_offers[0]
    assert (pending.source, pending.quest, pending.step) == ("opportunity", ALTAR, "opportunity")
    assert pending.offer.reason == "complete"  # 機遇給完整技能（07 7.6）
    assert len(pending.offer.candidates) == 3
    # 5B-4d：三張都帶觸發情境的關鍵字（07 7.6；雷擊點 → 帶電）
    assert all(t.keywords[:1] == ("charged",) for t in pending.offer.tags)
    lib = world_library(library)
    assert all(skill_has_keywords(s, ("charged",), lib) for s in pending.offer.candidates)
    assert after.offers_made == char.offers_made + 1
    kinds = [type(e) for e in result.events]
    assert kinds[:3] == [EventSolvedEvent, SkillOfferedEvent, EventResolvedEvent]
    solved = result.events[0]
    assert isinstance(solved, EventSolvedEvent) and solved.solution_kind == "opportunity"
    offered = result.events[1]
    assert isinstance(offered, SkillOfferedEvent) and offered.source == "opportunity"
    resolved = result.events[2]
    assert isinstance(resolved, EventResolvedEvent) and resolved.outcome == "success"
    tier = hero_tier(library, char.level) + solved.tier_bonus
    assert pending.offer.tier == tier
    assert all(s.tier == tier for s in pending.offer.candidates)
    # 選一招：學到（野外放進備用），事件的來源照記
    picked = world_step(library, make_world(), after, OfferPickAction(pick=0), NOON)
    taken = next(e for e in picked.events if isinstance(e, SkillOfferTakenEvent))
    assert taken.source == "opportunity" and taken.skill is not None
    assert taken.skill in picked.char.bench
    assert not picked.char.pending_offers


def test_same_opportunity_only_once(library: ContentLibrary, make_char: MakeChar) -> None:
    again = _at_altar(_charged(make_char(opportunities=(ALTAR,))))
    with pytest.raises(WorldActionError, match="已經拿過"):
        world_step(library, make_world(), again, EventSolveAction(solution=OPPORTUNITY), NOON)
    # 其他解法不受影響（體質硬撐）
    assert again.pending_event is not None


def test_tier_up_chance_and_season_cap(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    chars = [_charged(make_char(f"c{i}")) for i in range(300)]
    bonuses = [opportunity_tier_bonus(library, world, c, ALTAR) for c in chars]
    rate = sum(bonuses) * 1000 // len(bonuses)
    assert 100 <= rate <= 200, rate  # 150‰ 上下（確定性種子）
    lucky = chars[bonuses.index(1)]
    capped = lucky.model_copy(update={"opportunity_tier_ups": 1})
    assert opportunity_tier_bonus(library, world, capped, ALTAR) == 0  # 每季最多 1 次
    assert opportunity_tier_bonus(library, world, lucky, ALTAR) == 1  # 確定性
    result = world_step(
        library, world, _at_altar(lucky), EventSolveAction(solution=OPPORTUNITY), NOON
    )
    assert result.char.opportunity_tier_ups == 1
    assert result.char.pending_offers[0].offer.tier == hero_tier(library, lucky.level) + 1
    solved = next(e for e in result.events if isinstance(e, EventSolvedEvent))
    assert solved.tier_bonus == 1


# ---------------------------------------------------------------------------
# 第 7 天前保底 1 次（Phase 5B-4d；Phase5計畫 25.4；07 7.6）
# ---------------------------------------------------------------------------

DAY = 86_400
DAY6 = NOON + 5 * DAY  # 賽季第 6 天的中午（白天：骨架 12 本來只在雷雨夜）


def _arrive(
    library: ContentLibrary, char: CharacterState, now: int, *, encountered: bool = False
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    rolled = roll_event(
        library,
        make_world(),
        char.model_copy(update={"location": "old_pine_altar"}),
        encountered=encountered,
        now=now,
    )
    return rolled.char, rolled.events


def test_guarantee_from_day_6(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    assert season_day(world, NOON) == 1
    assert season_day(world, DAY6) == 6
    at_altar = make_char(location="old_pine_altar")
    assert guaranteed_opportunity(library, world, at_altar, DAY6 - DAY) is None  # 第 5 天
    assert guaranteed_opportunity(library, world, at_altar, DAY6) is not None
    char, events = _arrive(library, make_char(), DAY6)
    trigger = char.pending_event
    assert trigger is not None
    assert (trigger.skeleton, trigger.candidates, trigger.guaranteed) == (ALTAR, (ALTAR,), True)
    assert trigger.day_phase == "day"  # 不看時段
    assert any(isinstance(e, EventTriggeredEvent) for e in events)
    # 擲骰照舊消耗：亂數計數和沒保底時相同
    plain, _ = _arrive(library, make_char(), DAY6 - DAY)
    assert char.rng_counters == plain.rng_counters
    # 第 7 天以後還沒遇過的照樣保底（代決 5B4d-4）
    assert guaranteed_opportunity(library, world, at_altar, DAY6 + 5 * DAY) is not None


def test_no_guarantee_when_met_taken_or_fighting(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    met = make_char(location="old_pine_altar", met_opportunities=(ALTAR,))
    assert guaranteed_opportunity(library, world, met, DAY6) is None
    taken = make_char(location="old_pine_altar", opportunities=(ALTAR,))
    assert guaranteed_opportunity(library, world, taken, DAY6) is None
    elsewhere = make_char(location="rain_terraces")
    assert guaranteed_opportunity(library, world, elsewhere, DAY6) is None
    char, _ = _arrive(library, make_char(), DAY6, encountered=True)  # 遇敵那步不出事件
    assert char.pending_event is None
    off = with_rules(library, opportunity={"guarantee_from_day": 0})
    assert guaranteed_opportunity(off, world, make_char(location="old_pine_altar"), DAY6) is None


def test_met_opportunities_recorded(library: ContentLibrary, make_char: MakeChar) -> None:
    char, events = _arrive(library, make_char(), DAY6)
    marked = mark_met_opportunities(library, char, events)
    assert marked.met_opportunities == (ALTAR,)
    assert mark_met_opportunities(library, marked, events) is marked
    # 沒有機遇事件的動作不記
    talked = world_step(library, make_world(), make_char(), TalkAction(npc="granny_du"), NOON)
    assert talked.char.met_opportunities == ()


def test_guarantee_waives_keyword_5b4e(library: ContentLibrary, make_char: MakeChar) -> None:
    """5B-4e：保底觸發的機遇不檢查「需要帶電技能」，三張照樣帶帶電；一般觸發照舊要檢查。"""
    char, _ = _arrive(library, make_char(), DAY6)  # 沒有帶電技能
    trigger = char.pending_event
    assert trigger is not None and trigger.guaranteed
    result = world_step(library, make_world(), char, EventSolveAction(solution=OPPORTUNITY), DAY6)
    pending = result.char.pending_offers[0]
    assert pending.source == "opportunity"
    assert all(t.keywords[:1] == ("charged",) for t in pending.offer.tags)
    lib = world_library(library)
    assert all(skill_has_keywords(s, ("charged",), lib) for s in pending.offer.candidates)
    # 資料關掉時照 5B-4d（代決 5B4d-5）
    strict = with_rules(library, opportunity={"guarantee_waives_keyword": False})
    with pytest.raises(WorldActionError, match="條件不成立"):
        world_step(strict, make_world(), char, EventSolveAction(solution=OPPORTUNITY), DAY6)
    # 一般觸發（不是保底）照舊要帶電技能
    plain = char.model_copy(
        update={"pending_event": trigger.model_copy(update={"guaranteed": False})}
    )
    with pytest.raises(WorldActionError, match="條件不成立"):
        world_step(library, make_world(), plain, EventSolveAction(solution=OPPORTUNITY), DAY6)
