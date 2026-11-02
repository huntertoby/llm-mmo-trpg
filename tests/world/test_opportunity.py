"""機遇解法的結算（Phase 5B-4c；``docs/phases/Phase5計畫.md`` 21.4；07 7.6）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_situations import at_event
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    EventResolvedEvent,
    EventSolveAction,
    EventSolvedEvent,
    OfferPickAction,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
)
from trpg.world.errors import WorldActionError
from trpg.world.growth import hero_tier
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
