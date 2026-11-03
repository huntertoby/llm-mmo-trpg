"""經驗、升級與角色階級（Phase 5A-6；``docs/phases/Phase5計畫.md`` 11.2～11.3）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from tests.world.helpers import NOON, PARTY, hero, make_encounter, make_world, with_rules
from tests.world.test_situations import at_event, peddler, sure
from trpg.content.library import ContentLibrary
from trpg.content.world_rules import HeroGrowthRules
from trpg.world.actions import (
    BattleEndedEvent,
    FightAction,
    InsightGainedEvent,
    LeveledUpEvent,
    SkillTierChangedEvent,
)
from trpg.world.battle import _elite_first_kills, auto_steps
from trpg.world.encounters import EncounterLineup, LineupMember, elite_kinds
from trpg.world.growth import gain_xp, hero_tier, world_library
from trpg.world.state import CharacterState
from trpg.world.step import max_hp, new_character, world_step

MakeChar = Callable[..., CharacterState]


def _thresholds(library: ContentLibrary) -> tuple[int, ...]:
    assert library.world_rules is not None
    return library.world_rules.hero_growth.level_thresholds


def test_hero_tier_follows_07_7_6(library: ContentLibrary) -> None:
    assert [hero_tier(library, lv) for lv in range(1, 11)] == [1, 1, 1, 2, 2, 2, 2, 3, 3, 3]
    assert hero_tier(library, 12) == 3


def test_hero_growth_rules_validated() -> None:
    with pytest.raises(ValidationError, match="不遞減"):
        HeroGrowthRules(skill_tier_by_level=(2, 1))
    assert HeroGrowthRules().level_cap == 10


def test_world_library_keeps_prototype_table(library: ContentLibrary) -> None:
    view = world_library(library)
    assert view.roguelite.offer_tier(3) == 1
    assert view.roguelite.offer_tier(4) == 2
    assert library.roguelite.offer_tier(3) == 2  # 原型的表不變（[1,1,2,2,3,3]）
    assert world_library(library) is view


def test_gain_xp_levels_up_with_points_insight_and_hp(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = make_char()
    per_level = library.roguelite.attribute_points_per_level
    xp = _thresholds(library)[1]  # 第 2 道門檻 → 3 級
    up, events = gain_xp(library, make_world(), char, xp)
    assert up.level == 3
    assert up.xp == xp
    assert up.attribute_points == 2 * per_level
    assert up.insight == 4  # 每級 2 點（06 6.34.2）
    assert up.hp == char.hp + max_hp(library, up) - max_hp(library, char)
    leveled = [e for e in events if isinstance(e, LeveledUpEvent)]
    assert [(e.level, e.insight, e.skill_tier) for e in leveled] == [(2, 2, 1), (3, 4, 1)]
    assert not any(isinstance(e, SkillTierChangedEvent) for e in events)  # 3 級仍是 1 階
    assert up.hero.skills == char.hero.skills


def test_reaching_level_4_retiers_skills(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    up, events = gain_xp(library, make_world(), char, _thresholds(library)[2])
    assert up.level == 4
    assert up.skill_tier == 2
    changed = next(e for e in events if isinstance(e, SkillTierChangedEvent))
    assert (changed.from_tier, changed.to_tier) == (1, 2)
    assert all(s.endswith("_t2") for s in up.hero.skills)
    assert {s.id for s in up.generated_skills} == set(up.hero.skills)
    assert all(s.tier == 2 for s in up.generated_skills)


def test_level_cap(library: ContentLibrary, make_char: MakeChar) -> None:
    capped = with_rules(library, hero_growth={"level_cap": 3})
    up, _ = gain_xp(capped, make_world(), make_char(), 10_000)
    assert up.level == 3
    assert up.xp == 10_000  # 到頂後經驗照累積、不換算（代決 5A6-5）


def test_old_character_without_tier_syncs_once(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    old = make_char(skill_tier=None)
    up, events = gain_xp(library, make_world(), old, _thresholds(library)[0])
    assert up.skill_tier == 1
    changed = next(e for e in events if isinstance(e, SkillTierChangedEvent))
    assert changed.from_tier is None
    assert up.hero.skills == old.hero.skills  # 同一階不改 ID


def test_no_level_no_events(library: ContentLibrary, make_char: MakeChar) -> None:
    up, events = gain_xp(library, make_world(), make_char(), 50)
    assert (up.level, up.xp, events) == (1, 50, [])


def test_battle_xp_levels_up_immediately(library: ContentLibrary) -> None:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(
        update={
            "location": "ferry_steps",
            "xp": _thresholds(library)[0] - 1,
            "mercenaries": PARTY,
        }
    )  # 差 1 點升 2 級
    for seed in range(16):
        start = char.model_copy(
            update={
                "pending_encounter": make_encounter(
                    "ferry_steps", seed=seed, battle_map="cliff_outpost"
                )
            }
        )
        result = world_step(
            library, make_world(), start, FightAction(steps=auto_steps(library, start)), NOON
        )
        ended = next(e for e in result.events if isinstance(e, BattleEndedEvent))
        if ended.won:
            break
    else:
        pytest.fail("找不到會贏的種子")
    assert result.char.level == 2
    assert result.char.insight == 2  # 只有升級給的，一般戰鬥不給（06 6.34.2）
    assert any(isinstance(e, LeveledUpEvent) for e in result.events)


def test_situation_xp_levels_up_immediately(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = sure(library, "peddler_safe_path", "success")
    char = at_event(make_char(xp=_thresholds(library)[0] - 1), "wounded_peddler", strong=True)
    result = world_step(lib, make_world(), char, peddler(), NOON)
    assert result.char.xp >= _thresholds(library)[0]
    assert result.char.level == 2
    leveled = [e for e in result.events if isinstance(e, LeveledUpEvent)]
    assert [e.level for e in leveled] == [2]


def test_elite_first_kill_gives_insight_once(library: ContentLibrary, make_char: MakeChar) -> None:
    lineup = EncounterLineup(
        region="cloud_ridge",
        location="north_slope",
        group="g",
        members=(LineupMember(unit="mist_wolf", affix="berserk"), LineupMember(unit="mist_wolf")),
    )
    assert elite_kinds(library, lineup) == ("mist_wolf+berserk",)
    char, events = _elite_first_kills(library, make_char(), lineup)
    assert char.insight == 1
    assert char.elite_kills == ("mist_wolf+berserk",)
    assert [e.source for e in events if isinstance(e, InsightGainedEvent)] == [
        "elite:mist_wolf+berserk"
    ]
    again, more = _elite_first_kills(library, char, lineup)
    assert again.insight == 1
    assert more == []
