"""灰燼荒原的內容（Phase 5F-5a；``docs/phases/Phase5計畫.md`` 39.3、39.4）。"""

from __future__ import annotations

from typing import Any, get_args

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.world_encounters import EncounterTable, encounter_table_problems
from trpg.content.world_map import LocationKind
from trpg.content.world_season import GoalSpec, SeasonContent, season_problems
from trpg.shared.types import Element

REGION = "ashen_waste"


def test_ashen_map(library: ContentLibrary) -> None:
    world_map = library.world_maps[REGION]
    assert world_map.town == "ember_market"
    assert (world_map.level_min, world_map.level_max) == (5, 9)
    assert len(world_map.locations) == 18 and len(world_map.edges) == 17  # 19.3 扣掉裂界門
    places = world_map.location_by_id()
    assert places["ash_ferry"].gate_to == "cloud_ridge"
    assert [loc.id for loc in world_map.locations if loc.hidden] == ["obsidian_valley"]
    assert places["molten_heart_pit"].unlock_flag == "heart_pit_open"
    assert places["molten_heart_pit"].battle_maps == ("molten_heart_pit",)
    villages = sorted(loc.id for loc in world_map.locations if loc.kind == "village")
    assert villages == [
        "ash_well_village",
        "iron_forge_village",
        "old_iron_post",
        "red_sand_village",
    ]
    cloud_gate = library.world_maps["cloud_ridge"].location_by_id()["ashen_ferry"]
    assert (cloud_gate.gate_to, cloud_gate.unlock_flag) == (REGION, "ashen_waste_open")


def test_ashen_content_loaded(library: ContentLibrary) -> None:
    assert len(library.world_event_content.events[REGION].skeletons) == 16
    assert {n.id for n in library.world_event_content.npcs[REGION].npcs} == {
        "iron_lady",
        "greybeard",
        "smith_lu",
        "scavenger_laotie",
        "priestess_helin",
        "overseer_scar",
    }
    quests = library.world_quests.quests[REGION]
    main = quests.quest_by_id()["main_ashen_heart"]
    assert main.kind == "main" and len(main.steps) == 5
    assert main.steps[2].reward.story_skill == "skill_cold_front"  # 約第 6 天的劇情技能（19.6.1）
    assert library.world_economy.shops[REGION].shops[0].npc == "iron_lady"
    loot = library.world_loot
    assert loot is not None and loot.region(REGION).keywords == ("ignite", "prone", "poisoned")
    assert loot.bosses["ashen_heart"].material == "item_molten_heart"
    season = library.world_season
    assert season is not None
    assert "heart_pit_boss" in {s.id for s in season.seal_keys.sources}
    breach = season.event_by_id()["lava_breach"]
    assert breach.on_success.seal_keys == 5 and breach.on_success.flags == ("heart_pit_open",)
    assert [b.region for b in season.bounties].count(REGION) == 3


def test_goal_locations_need_region() -> None:
    with pytest.raises(ValidationError, match="region"):
        GoalSpec(kind="battle_won", count=1, locations=("red_sand_village",))
    with pytest.raises(ValidationError, match="不能寫"):
        GoalSpec(kind="camped", count=1, region=REGION, locations=("red_sand_village",))


def _season_problems(library: ContentLibrary, data: dict[str, Any]) -> list[str]:
    assert library.regions is not None
    return season_problems(
        SeasonContent.model_validate(data),
        world_maps=library.world_maps,
        encounters=library.world_encounters,
        catalog=library.enemy_catalog(),
        weather_ids=set(library.weather),
        region_ids={r.id for r in library.regions.regions},
        location_kinds=get_args(LocationKind.__value__),
    )


def test_goal_locations_checked(library: ContentLibrary) -> None:
    assert library.world_season is not None
    data = library.world_season.model_dump(mode="json")
    assert _season_problems(library, data) == []
    event = next(e for e in data["world_events"] if e["id"] == "lava_breach")
    event["goal"]["locations"] = ["red_sand_village", "nowhere"]
    assert _season_problems(library, data) == [
        "世界事件 lava_breach：區域 ashen_waste 沒有地點 nowhere"
    ]


def test_armor_mods_unit_must_be_in_a_group(library: ContentLibrary) -> None:
    table = library.world_encounters[REGION]
    data = table.model_dump(mode="json")
    pit = next(loc for loc in data["locations"] if loc["location"] == "molten_heart_pit")
    pit["armor_mods"]["unit"] = "heart_ember_lizard"
    assert (
        encounter_table_problems(
            EncounterTable.model_validate(data),
            world_map=library.world_maps[REGION],
            catalog=library.enemy_catalog(),
        )
        == []
    )
    pit["armor_mods"]["unit"] = "lava_beetle"
    problems = encounter_table_problems(
        EncounterTable.model_validate(data),
        world_map=library.world_maps[REGION],
        catalog=library.enemy_catalog(),
    )
    assert problems == ["地點 molten_heart_pit：armor_mods 的 lava_beetle 不在任何陣容裡"]


def test_5f5b_balance_values(library: ContentLibrary) -> None:
    """5F-5b 的平衡值（模擬見 docs/archive/phases/Phase5F-5b報告.md）：荒原熔岩獸群的
    熔核攻擊傷害 ×2.25；灰燼之心戰另用殼縫餘燼蜥（×1.5）；灰燼之心 HP 160、火抗 −75% 不動。"""
    statuses = library.ruleset.statuses.by_id()
    assert statuses["molten_burst"].damage_dealt_permille == 2250
    assert statuses["frost_ember_burst"].damage_dealt_permille == 2250
    assert statuses["heart_ember_burst"].damage_dealt_permille == 1500
    heart = library.unit("ashen_heart")
    assert heart.max_hp == 160 and heart.element_mods[Element.FIRE] == -750
    spawns = [s.template for p in heart.phases for s in p.spawns]
    assert spawns == ["heart_ember_lizard", "heart_ember_lizard"]  # GB-2：殼縫東西兩側各 1 隻
    lizard, court = library.unit("ember_lizard"), library.unit("heart_ember_lizard")
    same = {"attributes", "max_hp", "speed", "armor_bonus", "weapon", "skills", "element_mods"}
    assert court.model_dump(include=same) == lizard.model_dump(include=same)
    group = next(g for g in library.world_encounters[REGION].groups if g.id == "ashen_heart_court")
    assert "ember_lizard" not in group.units  # 熔心坑只用殼縫餘燼蜥
