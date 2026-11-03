"""主城實地地圖與室內圖（Phase 6D-4；玩法 PM 主城草稿）。

主城不在任何區域的地點圖裡、沒有走路的出口（只能傳送抵達）；安全區沒有敵人與營火；功能型 NPC 沒有
人設卡，站位寫成 facilities 或 situation_objects；五座浮橋與橋頭石碑是情境物件。
"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.content.fields import (
    CAPITAL_LOCATION,
    CAPITAL_REGION,
    FieldMapDef,
    FieldMapReport,
    field_map_report,
    field_progress,
)
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import passable_grid, reachable_from

type XY = tuple[int, int]
type Raw = dict[str, dict[str, Any]]

INTERIORS = {
    "capital_mentor_hall": "mentor_hall_door",
    "capital_tavern": "tavern_door",
    "capital_smithy": "smithy_door",
}
"""室內圖 → 主城上通往它的門。"""

FIVE_REGIONS = ("arcane_hub", "ashen_waste", "cloud_ridge", "crystal_crown", "frost_tide")

OUTDOOR_FACILITIES = {"notice_board", "hire"}
INTERIOR_FACILITIES = {
    "capital_mentor_hall": {"mentor"},
    "capital_tavern": {"tavern"},
    "capital_smithy": {"smithy", "enchanter"},
}
OUTDOOR_SPOTS = {
    "seal_altar",
    "rift_projection",
    "boss_stele",
    "seal_keeper",
    "wishing_pool",
    "pool_keeper",
    "training_range",
    "workshop_master",
    "shadow_league_desk",
    "loadout_pavilion",
    *(f"bridge_{r}" for r in FIVE_REGIONS),
    *(f"stele_{r}" for r in FIVE_REGIONS),
}
INTERIOR_SPOTS = {
    "capital_mentor_hall": {"scribe", "grimoire_shelf"},
    "capital_tavern": set(),
    "capital_smithy": set(),
}
FUNCTIONAL_NPCS = {
    # 草稿第 2 節的功能型 NPC → (地圖, 站位所在的清單, ID)
    "殿主": ("capital_mentor_hall", "facilities", "mentor"),
    "書記": ("capital_mentor_hall", "situation_objects", "scribe"),
    "酒館老闆": ("capital_tavern", "facilities", "tavern"),
    "鐵匠": ("capital_smithy", "facilities", "smithy"),
    "附魔師": ("capital_smithy", "facilities", "enchanter"),
    "守印人": ("capital", "situation_objects", "seal_keeper"),
    "傭兵管事": ("capital", "facilities", "hire"),
    "守池人": ("capital", "situation_objects", "pool_keeper"),
    "工坊師傅": ("capital", "situation_objects", "workshop_master"),
}


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _capital_maps(library: ContentLibrary) -> dict[str, FieldMapDef]:
    return {k: v for k, v in library.field_maps.items() if v.region == CAPITAL_REGION}


def _reach(library: ContentLibrary, field: FieldMapDef) -> set[XY]:
    terrain = library.ruleset.terrain.by_id()
    passable = passable_grid(field, terrain, library.ruleset.objects.by_id())
    return set(reachable_from(field.entry, field.grid(), passable, library.ruleset.core))


def _near(cell: XY, reach: set[XY]) -> bool:
    x, y = cell
    return any(c in reach for c in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))


def _object_at(field: FieldMapDef, cell: XY) -> str | None:
    return next((o.kind for o in field.objects if o.at == cell), None)


# ---------------------------------------------------------------------------
# 內容庫
# ---------------------------------------------------------------------------


def test_capital_and_three_interiors_are_loaded(library: ContentLibrary) -> None:
    maps = _capital_maps(library)
    assert set(maps) == {"capital", *INTERIORS}
    town = maps["capital"]
    assert town.location == CAPITAL_LOCATION
    assert town.size == (32, 24)
    assert town.layout_for(None) == "capital"
    for interior in INTERIORS:
        assert maps[interior].interior_of == CAPITAL_LOCATION
        assert maps[interior].size == (10, 8)


def test_capital_is_outside_every_location_map(library: ContentLibrary) -> None:
    assert CAPITAL_REGION not in library.world_maps
    for world_map in library.world_maps.values():
        assert CAPITAL_LOCATION not in world_map.location_by_id()
    for field in library.field_maps.values():
        assert all(e.region != CAPITAL_REGION for e in field.exits), field.id
        assert all(e.to != CAPITAL_LOCATION or field.is_capital for e in field.exits), field.id


def test_capital_has_no_walking_exits_and_one_stone(library: ContentLibrary) -> None:
    town = library.field_maps["capital"]
    assert town.exits == ()
    assert [s.id for s in town.teleport_stones] == ["stone_capital"]
    stone = town.teleport_stones[0].at
    assert abs(stone[0] - town.entry[0]) + abs(stone[1] - town.entry[1]) == 1  # 抵達點在傳送石旁
    assert 11 <= stone[0] <= 20 and 9 <= stone[1] <= 14  # 中央廣場


def test_capital_is_a_safe_zone(library: ContentLibrary) -> None:
    for field in _capital_maps(library).values():
        assert field.spawns == (), field.id
        assert field.campfires == (), field.id
        assert field.event_spots == (), field.id  # 主城沒有自己的事件骨架
        assert field.npcs == (), field.id  # 功能型 NPC 沒有人設卡（草稿待確認 2）


def test_progress_and_report_are_clean(library: ContentLibrary) -> None:
    progress = field_progress(library.world_maps, library.field_maps)
    assert [(p.region, p.done, p.total) for p in progress] == [
        ("cloud_ridge", 18, 18),
        ("ashen_waste", 18, 18),
        (CAPITAL_REGION, 1, 1),
    ]
    assert sum(1 for f in library.field_maps.values() if f.is_interior) == 7
    assert library.field_warnings == ()
    assert library.field_pending == ()


# ---------------------------------------------------------------------------
# 設施、NPC 站位、浮橋
# ---------------------------------------------------------------------------


def test_every_facility_from_the_draft_is_on_the_map(library: ContentLibrary) -> None:
    maps = _capital_maps(library)
    town = maps["capital"]
    assert {f.id for f in town.facilities} == OUTDOOR_FACILITIES
    assert {s.id for s in town.situation_objects} == OUTDOOR_SPOTS
    for interior in INTERIORS:
        assert {f.id for f in maps[interior].facilities} == INTERIOR_FACILITIES[interior]
        assert {s.id for s in maps[interior].situation_objects} == INTERIOR_SPOTS[interior]


@pytest.mark.parametrize("npc", sorted(FUNCTIONAL_NPCS))
def test_functional_npcs_stand_where_you_can_reach_them(library: ContentLibrary, npc: str) -> None:
    map_id, kind, spot_id = FUNCTIONAL_NPCS[npc]
    field = library.field_maps[map_id]
    spots = field.facilities if kind == "facilities" else field.situation_objects
    cell = next(s.at for s in spots if s.id == spot_id)
    reach = _reach(library, field)
    assert cell in reach, (npc, cell)  # 站位本身是走得到的空格（不是牆或物件）


@pytest.mark.parametrize("map_id", ["capital", *sorted(INTERIORS)])
def test_every_spot_is_reachable(library: ContentLibrary, map_id: str) -> None:
    field = library.field_maps[map_id]
    reach = _reach(library, field)
    for spot in (*field.facilities, *field.situation_objects):
        assert _near(spot.at, reach), (map_id, spot.id, spot.at)


@pytest.mark.parametrize("region", FIVE_REGIONS)
def test_five_bridges_with_a_stele_each(library: ContentLibrary, region: str) -> None:
    town = library.field_maps["capital"]
    spots = {s.id: s.at for s in town.situation_objects}
    bridge, stele = spots[f"bridge_{region}"], spots[f"stele_{region}"]
    x, y = bridge
    assert x in (0, town.width - 1) or y in (0, town.height - 1)  # 伸到雲的邊緣
    assert _object_at(town, bridge) == "wooden_bridge"
    assert town.grid()[y][x][1] == "chasm"
    assert _object_at(town, stele) == "stone_pillar"
    reach = _reach(library, town)
    assert bridge in reach
    assert _near(stele, reach)
    assert max(abs(bridge[0] - stele[0]), abs(bridge[1] - stele[1])) <= 2  # 石碑在橋頭


def test_bridges_count(library: ContentLibrary) -> None:
    town = library.field_maps["capital"]
    ids = [s.id for s in town.situation_objects]
    assert len([i for i in ids if i.startswith("bridge_")]) == 5
    assert len([i for i in ids if i.startswith("stele_")]) == 5


# ---------------------------------------------------------------------------
# 門與室內
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("interior_id", sorted(INTERIORS))
def test_doors_pair_with_interior_exits(library: ContentLibrary, interior_id: str) -> None:
    town = library.field_maps["capital"]
    room = library.field_maps[interior_id]
    door_id = INTERIORS[interior_id]
    door = town.portal(door_id)
    assert door is not None and door.to == interior_id
    assert getattr(door, "hidden_until", None) is None
    assert room.doors == () and room.teleport_stones == ()
    assert len(room.exits) == 1
    exit_ = room.exits[0]
    assert exit_.to == CAPITAL_LOCATION and exit_.arrive == door_id
    town_reach, room_reach = _reach(library, town), _reach(library, room)
    assert door.at in town_reach
    x, y = door.at
    outside = [c for c in ((x, y + 1), (x, y - 1), (x - 1, y), (x + 1, y)) if c in town_reach]
    assert outside, door_id  # 門外有站得上的格子
    assert all(c in room_reach for c in exit_.at)


def test_draft_building_positions(library: ContentLibrary) -> None:
    """草稿第 1 節的大致位置：導師殿在北、酒館在西、鐵匠鋪在東。"""
    town = library.field_maps["capital"]
    doors = {d.to: d.at for d in town.doors}
    assert doors["capital_mentor_hall"][1] <= 6 and 12 <= doors["capital_mentor_hall"][0] <= 19
    assert doors["capital_tavern"][0] <= 7 and 9 <= doors["capital_tavern"][1] <= 14
    assert doors["capital_smithy"][0] >= 24 and 9 <= doors["capital_smithy"][1] <= 13


# ---------------------------------------------------------------------------
# 驗證抓得到的錯
# ---------------------------------------------------------------------------


def _raw(library: ContentLibrary) -> Raw:
    return {
        k: v.model_dump(mode="json", exclude_defaults=True)
        for k, v in library.field_maps.items()
        if v.is_capital
    }


def _report(library: ContentLibrary, raw: Raw) -> FieldMapReport:
    fields = {k: FieldMapDef.model_validate(v) for k, v in raw.items()}
    return field_map_report(
        fields,
        world_maps=library.world_maps,
        terrain=library.ruleset.terrain.by_id(),
        objects=library.ruleset.objects.by_id(),
        core=library.ruleset.core,
        npcs={
            r: {n.id: n.location for n in t.npcs}
            for r, t in library.world_event_content.npcs.items()
        },
    )


def test_the_capital_alone_passes(library: ContentLibrary) -> None:
    report = _report(library, _raw(library))
    assert report == FieldMapReport()


CASES: list[tuple[str, dict[str, Any], str]] = [
    (
        "walking_exit",
        {"exits": [{"id": "to_mist_ferry", "at": [[16, 0]], "to": "mist_ferry", "arrive": "x"}]},
        "主城沒有走路的出口",
    ),
    ("spawn", {"spawns": [{"at": [16, 12], "group": "wolves"}]}, "不可有 spawns"),
    ("campfire", {"campfires": [{"at": [16, 12], "id": "fire"}]}, "不可有 campfires"),
    ("no_stone", {"teleport_stones": []}, "主城要有 1 個傳送石，目前 0 個"),
    (
        "two_stones",
        {
            "teleport_stones": [
                {"id": "stone_capital", "at": [15, 11]},
                {"id": "stone_capital_2", "at": [14, 11]},
            ]
        },
        "主城要有 1 個傳送石，目前 2 個",
    ),
    ("npc", {"npcs": [{"at": [14, 12], "id": "guide"}]}, "沒有人設卡"),
    ("location", {"location": "mist_ferry"}, "主城的 location 必須是 capital"),
]


@pytest.mark.parametrize(("change", "patch", "message"), CASES, ids=[c[0] for c in CASES])
def test_capital_rules_are_enforced(
    library: ContentLibrary, change: str, patch: dict[str, Any], message: str
) -> None:
    raw = _raw(library)
    raw["capital"] = {**raw["capital"], **patch}
    report = _report(library, raw)
    assert any(message in e for e in report.errors), (change, report.errors)


def test_capital_doors_only_lead_to_capital_interiors(library: ContentLibrary) -> None:
    raw = _raw(library)
    doors = [
        *raw["capital"]["doors"],
        {"id": "odd_door", "at": [16, 13], "to": "mist_ferry_tavern"},
    ]
    raw["capital"] = {**raw["capital"], "doors": doors}
    report = _report(library, raw)
    assert any("odd_door：mist_ferry_tavern 不是主城的室內圖" in e for e in report.errors)


def test_safe_zone_covers_capital_interiors(library: ContentLibrary) -> None:
    raw = _raw(library)
    raw["capital_tavern"] = {
        **raw["capital_tavern"],
        "spawns": [{"at": [4, 5], "group": "rats"}],
    }
    report = _report(library, raw)
    assert any("capital_tavern：主城是安全區" in e for e in report.errors)


def test_region_maps_cannot_walk_into_the_capital(library: ContentLibrary) -> None:
    raw = {
        k: v.model_dump(mode="json", exclude_defaults=True)
        for k, v in library.field_maps.items()
        if v.is_capital or k == "mist_ferry"
    }
    town = raw["mist_ferry"]
    exit_ = {
        "id": "to_capital",
        "at": [[23, 3]],
        "to": "capital",
        "arrive": "x",
        "region": "capital",
    }
    raw["mist_ferry"] = {**town, "exits": [*town["exits"], exit_]}
    report = _report(library, raw)
    assert any("區域 capital 沒有地點 capital" in e for e in report.errors)
