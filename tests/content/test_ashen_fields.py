"""灰燼荒原實地地圖的內容（Phase 6D-1；Phase 6 計畫第 6 節）。

寫法比照 ``test_cloud_fields.py``（切 12×12 的輔助函式、出口內側、巡邏路線直接沿用）：

- 每張圖通過 :func:`field_map_report`，兩端都畫了的連線都配對，沒畫的一端列為待補；
- 灰渡口和雲嶺「往灰燼荒原的渡口」的跨區出口互指；
- 出口內側 1 格站得上、出口與入口互相走得到，木橋這類打得斷的物件不是唯一通路；
- ``spawns`` 用這個地點遭遇表裡的陣容、巡邏路線沿直線走得通，``event_spots`` 用這個地點的事件骨架；
- 接觸點切得出合法的 12×12 戰場（敵方起始區 4 格、我方 3 格；正式的切法在 6C-2）；
- 區域題目「怕水」：每張有戰鬥的圖至少一處水；
- 營火、傳送石的數量照玩法 PM 草稿（這段畫到的部分）；
- 黑曜谷（隱藏，6D-2）的入口是焦油坑上 ``hidden_until: reveal`` 的門。
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from tests.content.test_cloud_fields import _inward, _route, cut_battlefield
from trpg.content.fields import FieldMapDef, field_map_report
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import check_map, passable_grid, reachable_from
from trpg.shared.types import Surface, Team

type XY = tuple[int, int]

REGION = "ashen_waste"

MAPS_6D1 = (
    "ash_ferry",
    "scorched_outskirts",
    "old_iron_post",
    "deadwood_forest",
    "ash_mire",
    "cooling_well",
    "gang_convoy_road",
    "tar_pits",
    "overseer_camp",
)
"""6D-1 的 9 張：從灰渡口往外，照草稿出口表的連通順序；餘燼集城鎮圖（6D-3）、三村落、熔心坑、
黑曜谷（6D-2）不在這段。"""

COMBAT_FREE = {"ash_ferry"}
"""沒有戰鬥的地圖（傳送類地點）。"""

CAMPFIRES = {"old_iron_post": 1, "cooling_well": 1}
"""草稿第 0 節的 5 個營火中，這段畫到的 2 個（其餘赤沙村、灰井村、鐵爐村在 6D-2）。"""

STONES = {"old_iron_post": 1, "tar_pits": 1}
"""草稿第 0 節的 3 個野外傳送石中，這段畫到的 2 個（廢墟要塞在 6D-2，餘燼集 1 個在 6D-3）。"""

PENDING = {
    ("ash_ferry", "ember_market"),
    ("scorched_outskirts", "ember_market"),
    ("scorched_outskirts", "red_sand_village"),
    ("old_iron_post", "ember_market"),
    ("ash_mire", "ash_well_village"),
    ("tar_pits", "lava_cave"),
    ("tar_pits", "obsidian_valley"),
    ("overseer_camp", "iron_forge_village"),
}
"""連到 6D-2、6D-3 範圍的出口與門（對面還沒畫）。"""

CONTACTS: list[tuple[str, str, XY, XY]] = [
    # (地圖, 陣容, 敵人所在, 我方所在)：駐守點與巡邏路線上的接觸點
    ("scorched_outskirts", "lizard_swarm", (12, 9), (8, 9)),
    ("scorched_outskirts", "hound_pack", (5, 15), (7, 12)),
    ("scorched_outskirts", "hound_pack", (18, 15), (20, 13)),
    ("old_iron_post", "scavenger_beasts", (5, 15), (5, 12)),
    ("old_iron_post", "scavenger_beasts", (18, 15), (18, 12)),
    ("deadwood_forest", "deadwood_sulfur", (12, 5), (12, 9)),
    ("deadwood_forest", "colossus_smoke", (7, 14), (7, 16)),
    ("deadwood_forest", "colossus_smoke", (17, 14), (18, 11)),
    ("ash_mire", "mire_slugs", (12, 8), (12, 13)),
    ("ash_mire", "mire_mix", (5, 15), (4, 12)),
    ("ash_mire", "mire_mix", (17, 15), (20, 13)),
    ("cooling_well", "well_guardians", (12, 12), (8, 14)),
    ("cooling_well", "well_guardians", (12, 12), (16, 11)),
    ("gang_convoy_road", "convoy_guard", (12, 9), (8, 9)),
    ("gang_convoy_road", "convoy_raid", (19, 13), (15, 12)),
    ("tar_pits", "tar_tortoises", (17, 5), (13, 5)),
    ("tar_pits", "tar_brood", (7, 13), (10, 14)),
    ("tar_pits", "lizard_brood", (6, 16), (8, 14)),
    ("tar_pits", "lizard_brood", (19, 16), (20, 14)),
    ("overseer_camp", "overseer_crew", (9, 7), (9, 10)),
    ("overseer_camp", "overseer_guard", (4, 6), (1, 6)),
]


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _field(library: ContentLibrary, location: str, region: str = REGION) -> FieldMapDef:
    return next(
        f for f in library.field_maps.values() if f.region == region and f.location == location
    )


def _passable(library: ContentLibrary, field: FieldMapDef) -> list[list[bool]]:
    return passable_grid(field, library.ruleset.terrain.by_id(), library.ruleset.objects.by_id())


def _reach(library: ContentLibrary, field: FieldMapDef, start: XY) -> set[XY]:
    return reachable_from(start, field.grid(), _passable(library, field), library.ruleset.core)


# ---------------------------------------------------------------------------
# 範圍、驗證、配對
# ---------------------------------------------------------------------------


def test_the_6d1_maps_are_drawn_and_pass(library: ContentLibrary) -> None:
    drawn = {f.location for f in library.field_maps.values() if f.region == REGION and f.location}
    assert drawn == set(MAPS_6D1)
    assert drawn <= {loc.id for loc in library.world_maps[REGION].locations}
    report = field_map_report(
        library.field_maps,
        world_maps=library.world_maps,
        terrain=library.ruleset.terrain.by_id(),
        objects=library.ruleset.objects.by_id(),
        core=library.ruleset.core,
        npcs={
            r: {n.id: n.location for n in t.npcs}
            for r, t in library.world_event_content.npcs.items()
        },
    )
    assert report.errors == ()
    assert report.pending == library.field_pending
    # 尺寸都在 21.3 的範圍內；野外傳送石 2 個在 2～3 的範圍內，荒原沒有警告
    assert not [w for w in report.warnings if REGION in w]
    assert not [w for w in report.warnings if "建議範圍" in w]


def test_pending_is_exactly_the_links_into_later_segments(library: ContentLibrary) -> None:
    ours = sorted(
        line
        for line in library.field_pending
        if line.startswith("實地地圖 ") and line.split(" ", 2)[1] in MAPS_6D1
    )
    got = set()
    for line in ours:
        here = line.split(" ", 2)[1]
        there = line.split(f"→ {REGION}/", 1)[1].split("：", 1)[0]
        got.add((here, there))
    assert got == PENDING
    assert len(ours) == len(PENDING)
    drawn = set(MAPS_6D1)
    assert not [t for _, t in PENDING if t in drawn]


def test_every_edge_between_drawn_maps_is_a_mutual_pair(library: ContentLibrary) -> None:
    world_map = library.world_maps[REGION]
    locations = world_map.location_by_id()
    drawn = set(MAPS_6D1)
    pending = "\n".join(library.field_pending)
    paired = 0
    for a, b in world_map.edges:
        if locations[a].hidden or locations[b].hidden:
            continue  # 隱藏地點的連線是門配出口（見 test_obsidian_valley_...）
        if a in drawn and b in drawn:
            fa, fb = _field(library, a), _field(library, b)
            ab = next(e for e in fa.exits if e.to == b)
            ba = next(e for e in fb.exits if e.to == a)
            assert (ab.arrive, ba.arrive) == (ba.id, ab.id), (a, b)
            paired += 1
        else:
            for here, there in ((a, b), (b, a)):
                if here in drawn and there not in drawn:
                    assert f"{REGION}/{there}：對面還沒有實地地圖" in pending, (here, there)
    # 焦土－枯木林、哨站－灰泥沼、哨站－冷卻井、枯木林－運輸道、冷卻井－焦油坑、運輸道－督工營
    assert paired == 6


def test_ash_ferry_pairs_with_the_cloud_ridge_crossing(library: ContentLibrary) -> None:
    """灰渡口西南的棧橋盡頭＝雲嶺「往灰燼荒原的渡口」西端（草稿待確認 12）：兩個跨區出口互指，
    雲嶺那一項待補消失。"""
    here = _field(library, "ash_ferry")
    there = _field(library, "ashen_ferry", "cloud_ridge")
    cross = [e for e in here.exits if e.region == "cloud_ridge"]
    assert [(e.id, e.to, e.arrive) for e in cross] == [
        ("to_ashen_ferry", "ashen_ferry", "to_ash_ferry")
    ]
    back = [e for e in there.exits if e.region == REGION]
    assert [(e.id, e.to, e.arrive) for e in back] == [
        ("to_ash_ferry", "ash_ferry", "to_ashen_ferry")
    ]
    assert not [line for line in library.field_pending if "ash_ferry" in line and "cloud" in line]
    # 傳送類地點：沒有敵人、事件、營火、傳送石
    assert here.spawns == () and here.event_spots == ()
    assert here.campfires == () and here.teleport_stones == ()
    # 棧橋盡頭在西南：西邊緣的南半
    assert all(x == 0 and y >= here.height // 2 for x, y in cross[0].at)


def test_obsidian_valley_is_entered_through_a_hidden_door(library: ContentLibrary) -> None:
    """黑曜谷（隱藏，6D-2）：焦油坑不畫出口，只畫一扇 ``hidden_until: reveal`` 的門
    （西北岩壁的窄縫）；
    對面還沒畫，配對待補。"""
    assert library.world_maps[REGION].location_by_id()["obsidian_valley"].hidden
    tar = _field(library, "tar_pits")
    assert not [e for e in tar.exits if e.to == "obsidian_valley"]
    doors = [d for d in tar.doors if d.to == "obsidian_valley"]
    assert len(doors) == 1
    assert doors[0].hidden_until == "reveal"
    x, y = doors[0].at
    assert x < tar.width // 3 and y < tar.height // 3  # 西北
    assert _passable(library, tar)[y][x]
    assert doors[0].at in _reach(library, tar, tar.entry)
    assert tar.entry in _reach(library, tar, doors[0].at)


def test_hidden_entrances_use_hidden_until(library: ContentLibrary) -> None:
    locations = library.world_maps[REGION].location_by_id()
    for location in MAPS_6D1:
        for door in _field(library, location).doors:
            assert locations[door.to].hidden, (location, door.id)
            assert door.hidden_until == "reveal", (location, door.id)


# ---------------------------------------------------------------------------
# 走得到、安全
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("location", MAPS_6D1)
def test_exits_have_a_standable_inner_cell_and_lead_back_to_entry(
    library: ContentLibrary, location: str
) -> None:
    field = _field(library, location)
    passable = _passable(library, field)
    for exit_ in field.exits:
        for cell in exit_.at:
            x, y = _inward(cell, field.size)
            assert passable[y][x], (exit_.id, cell)
            assert field.entry in _reach(library, field, cell), (exit_.id, cell)


@pytest.mark.parametrize("location", MAPS_6D1)
def test_no_breakable_bridge_is_the_only_way(library: ContentLibrary, location: str) -> None:
    """致命地形（岩漿、深淵）不可以擋住唯一通路：拿掉架在上面的物件（木橋）後，出口、門、傳送石
    照樣走得到。"""
    field = _field(library, location)
    objects = library.ruleset.objects.by_id()
    solid = field.model_copy(
        update={
            "objects": tuple(o for o in field.objects if not objects[o.kind].has_tag("over_chasm"))
        }
    )
    reach = _reach(library, solid, field.entry)
    targets = [c for e in field.exits for c in e.at]
    targets += [d.at for d in field.doors] + [s.at for s in field.teleport_stones]
    assert all(c in reach for c in targets)


@pytest.mark.parametrize("location", sorted(set(MAPS_6D1) - COMBAT_FREE))
def test_every_combat_map_has_water(library: ContentLibrary, location: str) -> None:
    """區域題目「怕水」（6.2；草稿待確認 5）：每張有戰鬥的圖至少一處水表面。"""
    field = _field(library, location)
    assert field.spawns
    assert any(s.surface is Surface.WATER for s in field.surfaces)


# ---------------------------------------------------------------------------
# 敵人、事件、營火、傳送石
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("location", MAPS_6D1)
def test_spawns_use_this_places_groups_and_walkable_patrols(
    library: ContentLibrary, location: str
) -> None:
    field = _field(library, location)
    table = library.world_encounters[REGION]
    groups = {g.group for loc in table.locations if loc.location == location for g in loc.groups}
    assert {s.group for s in field.spawns} <= groups
    assert len(field.spawns) <= 3
    assert sum(1 for s in field.spawns if s.patrol) <= 1
    if location in COMBAT_FREE:
        assert field.spawns == ()
    passable = _passable(library, field)
    core = library.ruleset.core
    grid = field.grid()
    for spawn in field.spawns:
        if not spawn.patrol:
            continue
        cells = _route(spawn.patrol)
        assert spawn.at in cells
        assert all(passable[y][x] for x, y in cells), spawn.group
        for (ax, ay), (bx, by) in pairwise(cells):
            assert abs(grid[by][bx][0] - grid[ay][ax][0]) <= core.max_climb_height


def test_each_spawn_has_a_contact_point(library: ContentLibrary) -> None:
    listed = {(m, g) for m, g, _, _ in CONTACTS}
    for location in MAPS_6D1:
        for spawn in _field(library, location).spawns:
            assert (location, spawn.group) in listed


def test_event_spots_use_this_places_skeletons(library: ContentLibrary) -> None:
    places: dict[str, set[str]] = {}
    for skeleton in library.world_event_content.events[REGION].skeletons:
        for place in skeleton.locations:
            places.setdefault(place, set()).add(skeleton.id)
    for location in MAPS_6D1:
        field = _field(library, location)
        ids = [s.id for s in field.event_spots]
        assert set(ids) <= places.get(location, set()), location
        assert len(ids) == len(set(ids)) <= 3
        # 這個地點的事件骨架都有地方放
        assert set(ids) == places.get(location, set()), location


def test_campfires_stones_and_situation_objects_follow_the_draft(library: ContentLibrary) -> None:
    for location in MAPS_6D1:
        field = _field(library, location)
        assert len(field.campfires) == CAMPFIRES.get(location, 0), location
        assert len(field.teleport_stones) == STONES.get(location, 0), location
    stone_ids = sorted(s.id for loc in MAPS_6D1 for s in _field(library, loc).teleport_stones)
    assert stone_ids == ["stone_old_iron_post", "stone_tar_pits"]
    well = _field(library, "cooling_well")
    assert [s.id for s in well.situation_objects] == ["cooling_well_relic"]


def test_old_iron_post_hosts_laotie(library: ContentLibrary) -> None:
    post = _field(library, "old_iron_post")
    assert [n.id for n in post.npcs] == ["scavenger_laotie"]


# ---------------------------------------------------------------------------
# 就地開打：接觸點切出 12×12
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "group", "enemy_at", "ally_at"),
    CONTACTS,
    ids=[f"{m}-{g}-{e[0]}_{e[1]}" for m, g, e, _ in CONTACTS],
)
def test_contact_points_cut_a_legal_12x12(
    library: ContentLibrary, location: str, group: str, enemy_at: XY, ally_at: XY
) -> None:
    field = _field(library, location)
    terrain = library.ruleset.terrain.by_id()
    passable = _passable(library, field)
    assert passable[enemy_at[1]][enemy_at[0]] and passable[ally_at[1]][ally_at[0]]
    spawn = next(s for s in field.spawns if s.group == group)
    if spawn.patrol:
        assert enemy_at in _route(spawn.patrol)
    else:
        assert enemy_at == spawn.at
    battle = cut_battlefield(library, field, enemy_at, ally_at)
    assert len(battle.start_zones[Team.ENEMY]) == 4
    assert len(battle.start_zones[Team.ALLY]) == 3
    problems = check_map(battle, terrain, library.ruleset.core, library.ruleset.objects.by_id())
    assert problems == []
