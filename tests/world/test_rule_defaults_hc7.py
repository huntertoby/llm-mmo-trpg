"""HC-7 a.2：大世界的規則數字搬進 content；沒有世界規則就報錯，真的需要的備用值只在載入層留一份。"""

from __future__ import annotations

import dataclasses

import pytest

from trpg.content.library import ContentLibrary
from trpg.content.world_quests import NO_FILE_AFFINITY_RULES, WorldQuestContent
from trpg.content.world_rules import FALLBACK_CALENDAR
from trpg.world.affinity import affinity_rules
from trpg.world.calendar import calendar_of, day_of
from trpg.world.clock import refresh_day
from trpg.world.errors import WorldError
from trpg.world.opening_limits import opening_end_level, starter_steps
from trpg.world.season import week_days

NOON = 1_700_000_000


def test_fallbacks_match_content(library: ContentLibrary) -> None:
    rules = library.world_rules
    assert rules is not None
    assert rules.calendar == FALLBACK_CALENDAR
    affinity = library.world_quests.affinity
    fields = ("min_value", "max_value", "rumors_per_week", "ranks")
    assert {f: getattr(NO_FILE_AFFINITY_RULES, f) for f in fields} == {
        f: getattr(affinity, f) for f in fields
    }


def test_clock_without_calendar_uses_the_one_fallback(library: ContentLibrary) -> None:
    for now in (NOON, NOON + 6 * 3600, NOON + 13 * 3600):
        assert refresh_day(now) == day_of(library, now)


def test_world_rules_are_required(library: ContentLibrary) -> None:
    bare = dataclasses.replace(library, world_rules=None)
    with pytest.raises(WorldError, match=r"world/rules\.yaml"):
        calendar_of(bare)
    with pytest.raises(WorldError, match=r"world/rules\.yaml"):
        week_days(bare)


def test_affinity_fallback_lives_in_the_loader(library: ContentLibrary) -> None:
    assert affinity_rules(dataclasses.replace(library, world_quests=WorldQuestContent())) == (
        NO_FILE_AFFINITY_RULES
    )


def test_opening_numbers_come_from_newcomer(library: ContentLibrary) -> None:
    newcomer = library.world_newcomer
    assert newcomer is not None and newcomer.range is not None
    assert (opening_end_level(library), starter_steps(library)) == (4, 2)
    assert newcomer.range.trial_keywords_max == 2
    with pytest.raises(WorldError, match=r"world/newcomer\.yaml"):
        opening_end_level(dataclasses.replace(library, world_newcomer=None))
