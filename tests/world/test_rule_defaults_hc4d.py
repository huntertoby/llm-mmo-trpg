"""HC-4d：沒有世界規則時的備用值要和內容檔相同（程式預設值拿掉後，備用值搬到呼叫的地方）。"""

from __future__ import annotations

from trpg.api.world_field_view import NO_RULES_WALK_MAX_STEPS
from trpg.content.library import ContentLibrary
from trpg.world.affinity import DEFAULT_AFFINITY_RULES
from trpg.world.calendar import NO_RULES_CALENDAR
from trpg.world.season import NO_RULES_WEEK_DAYS


def test_no_rules_fallbacks_match_content(library: ContentLibrary) -> None:
    rules = library.world_rules
    assert rules is not None
    assert rules.calendar == NO_RULES_CALENDAR
    assert rules.week_days == NO_RULES_WEEK_DAYS
    assert rules.field.walk_max_steps == NO_RULES_WALK_MAX_STEPS


def test_default_affinity_matches_content(library: ContentLibrary) -> None:
    affinity = library.world_quests.affinity
    assert affinity is not None
    fields = ("min_value", "max_value", "rumors_per_week", "ranks")
    assert {f: getattr(DEFAULT_AFFINITY_RULES, f) for f in fields} == {
        f: getattr(affinity, f) for f in fields
    }
