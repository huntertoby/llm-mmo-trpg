"""練等套用（Phase 5A-SIM2）：經驗份數、門檻、隊友成長、遭遇表的等級門檻與遠程上限。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

from tests.world.helpers import NOON
from trpg.content.library import ContentLibrary
from trpg.world.battle import grow_allies, prepare_battle
from trpg.world.common import rules_of
from trpg.world.encounters import lineup_templates, roll_lineup
from trpg.world.growth import world_level_for
from trpg.world.state import CharacterState, EncounterResult


def _encounter(location: str, seed: int) -> EncounterResult:
    return EncounterResult(
        region="cloud_ridge",
        location=location,
        level=4,
        battle_map=None,
        battle_seed=seed,
        weather="fog",
        day_phase="day",
        at=NOON,
    )


def test_xp_share_scales_with_location_level(library: ContentLibrary) -> None:
    xp = rules_of(library).xp
    assert [xp.share_xp(n) for n in (1, 5, 10)] == [100, 140, 190]
    assert xp.xp_for("elite", 5) == 420
    assert xp.xp_for("situation_success", 1) == 50
    assert xp.xp_for("situation_partial", 1) == 25


def test_level_thresholds_from_world_rules(library: ContentLibrary) -> None:
    thresholds = rules_of(library).hero_growth.level_thresholds
    assert thresholds == (950, 3800, 8600, 14350, 20200, 26050, 31950, 37800, 43650)
    assert world_level_for(library, 0) == 1
    assert world_level_for(library, thresholds[0] - 1) == 1
    assert world_level_for(library, thresholds[0]) == 2
    assert world_level_for(library, thresholds[-1]) == 10


def test_allies_grow_with_hero_level(
    library: ContentLibrary, make_char: Callable[..., CharacterState]
) -> None:
    char = make_char().model_copy(
        update={"pending_encounter": _encounter("cliff_gang_fort", 3), "level": 5}
    )
    prepared = prepare_battle(library, char)
    allies = [u for u in prepared.setup.units[1:] if u.team.name == "ALLY"]
    assert allies and all(u.template.level == 5 for u in allies)
    same, skills = grow_allies(library, allies, 1)
    assert [u.template.level for u in same] != [] and skills == ()


def test_bear_needs_level_gate(library: ContentLibrary) -> None:
    table = library.world_encounters["cloud_ridge"]
    seeds = range(60)
    # 寒湖是 4 級地點：石背熊會出現
    kinds = {
        m.unit for s in seeds for m in roll_lineup(library, _encounter("winter_lake", s)).members
    }
    assert "stoneback_bear" in kinds
    # 門檻調到 5 級：石背熊全部換成霧狼
    locations = tuple(
        loc.model_copy(
            update={
                "unit_min_levels": tuple(
                    g.model_copy(update={"min_level": 5}) for g in loc.unit_min_levels
                )
            }
        )
        for loc in table.locations
    )
    gated = dataclasses.replace(
        library,
        world_encounters={"cloud_ridge": table.model_copy(update={"locations": locations})},
    )
    kinds = {
        m.unit for s in seeds for m in roll_lineup(gated, _encounter("winter_lake", s)).members
    }
    assert "stoneback_bear" not in kinds
    assert "mist_wolf" in kinds


def test_cloud_sea_bridge_at_most_one_ranged(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    for seed in range(200):
        lineup = roll_lineup(library, _encounter("cloud_sea_bridge", seed))
        templates = lineup_templates(library, lineup)
        assert sum(catalog.is_ranged(t) for t in templates) <= 1
