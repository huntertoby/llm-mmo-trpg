"""灰燼荒原實地地圖的內容（Phase 6D-1、6D-2；Phase 6 計畫第 6 節）。

寫法比照 ``test_cloud_fields.py``（切 12×12 的輔助函式、出口內側、巡邏路線直接沿用）：

- 18 張都通過 :func:`field_map_report`，每條連線都配對，荒原沒有待補、沒有警告；
- 灰渡口和雲嶺「往灰燼荒原的渡口」的跨區出口互指；
- 出口內側 1 格站得上、出口與入口互相走得到，木橋這類打得斷的物件不是唯一通路；
- ``spawns`` 用這個地點遭遇表裡的陣容、巡邏路線沿直線走得通，``event_spots`` 用這個地點的事件骨架；
- 接觸點切得出合法的 12×12 戰場（敵方起始區 4 格、我方 3 格；正式的切法在 6C-2）；
- 區域題目「怕水」：每張有戰鬥的圖至少一處水；
- 營火 5 個、傳送石野外 3 個加餘燼集 1 個（玩法 PM 草稿第 0 節）；
- 黑曜谷（隱藏）的入口是焦油坑上 ``hidden_until: reveal`` 的門，黑曜谷的出口 arrive 指回那扇門；
- 三村落（6D-2）：守點目標是情境物件，駐守在村口外、離目標 6 格內，接觸點切出的 12×12 包含目標
  （切不到的村落改用守點模板，草稿待確認 3）；
- 熔心坑前廳：坑口 ``pit_gate``、廢墟要塞那一側的熔岩封口 ``pit_lava_seal``；
  Boss 地圖的冷卻井是物件（CW-1，打破造水 3×3）；
- 餘燼集（小鎮）：傳送石 1 個、設施與 NPC 站位；
- 餘燼集室內（6D-3）：酒館、爐叔鐵鋪兩扇門與室內圖互指，設施、爐叔、酒館老兵的事件點在室內，
  站位從入口走得到、相鄰格站得上。
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from tests.content.test_cloud_fields import CUT, _inward, _route, _window_origin, cut_battlefield
from trpg.content.fields import FieldMapDef, field_map_report
from trpg.content.library import ContentLibrary
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
"""6D-1 的 9 張：從灰渡口往外，照草稿出口表的連通順序。"""

MAPS_6D2 = (
    "ember_market",
    "red_sand_village",
    "ash_well_village",
    "iron_forge_village",
    "obsidian_valley",
    "lava_cave",
    "horned_altar",
    "ruined_fortress",
    "molten_heart_pit",
)
"""6D-2 的 9 張：餘燼集城鎮外圖（室內圖在 6D-3）、三村落、黑曜谷、熔岩洞窟、角魔古祭壇、廢墟要塞、
熔心坑前廳。"""

MAPS = MAPS_6D1 + MAPS_6D2

COMBAT_FREE = {"ash_ferry", "ember_market", "molten_heart_pit"}
"""沒有就地戰鬥的地圖：傳送類地點、小鎮（安全區）、Boss 前廳（Boss 戰走坑口，照 21.4
不切 12×12）。"""

CAMPFIRES = {
    "old_iron_post": 1,
    "cooling_well": 1,
    "red_sand_village": 1,
    "ash_well_village": 1,
    "iron_forge_village": 1,
}
"""草稿第 0 節的 5 個營火。"""

STONES = {"old_iron_post": 1, "tar_pits": 1, "ruined_fortress": 1, "ember_market": 1}
"""草稿第 0 節的 3 個野外傳送石（哨站、焦油坑、廢墟要塞）加上餘燼集的 1 個。"""

VILLAGES: dict[str, tuple[str, str]] = {
    # 地點: (守點目標的情境物件, 村口外的駐守陣容)
    "red_sand_village": ("red_sand_well", "village_raid_light"),
    "ash_well_village": ("ash_well", "village_raid_mid"),
    "iron_forge_village": ("iron_forge_anvil", "village_raid_heavy"),
}
"""三村落（21.9 第 20 條；草稿第 0 節、待確認 2、3）：碰到駐守就是守點戰。"""

TEMPLATE_FALLBACK: set[str] = set()
"""接觸點切出的 12×12 包不到守點目標、改用地點守點模板的村落（草稿待確認 3、21.4）。目前三村落都
切得到，所以是空的；以後改圖切不到時加進來，報告註明。"""

DEFEND_RADIUS = 6
"""駐守點離守點目標的距離上限（曼哈頓距離；草稿第 0 節「6 格以內」取比較嚴的算法）。"""

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
    # 6D-2
    ("red_sand_village", "village_raid_light", (11, 3), (11, 6)),
    ("red_sand_village", "village_raid_light", (11, 3), (7, 2)),
    ("ash_well_village", "village_raid_mid", (12, 15), (12, 12)),
    ("ash_well_village", "village_raid_mid", (12, 15), (8, 16)),
    ("iron_forge_village", "village_raid_heavy", (6, 9), (9, 9)),
    ("iron_forge_village", "village_raid_heavy", (6, 9), (4, 6)),
    ("obsidian_valley", "obsidian_frost", (4, 10), (8, 11)),
    ("obsidian_valley", "obsidian_mix", (11, 3), (7, 6)),
    ("lava_cave", "cave_beetles", (6, 6), (3, 8)),
    ("lava_cave", "cave_lord", (12, 15), (8, 15)),
    ("lava_cave", "beetle_line", (9, 9), (7, 11)),
    ("lava_cave", "beetle_line", (20, 9), (20, 6)),
    ("horned_altar", "altar_wraiths", (14, 14), (14, 11)),
    ("horned_altar", "altar_wraiths", (14, 14), (9, 14)),
    ("ruined_fortress", "fortress_bandits", (13, 10), (12, 14)),
    ("ruined_fortress", "fortress_bandits", (13, 10), (9, 9)),
    ("ruined_fortress", "fortress_beasts", (21, 12), (22, 14)),
    ("ruined_fortress", "fortress_beasts", (21, 16), (17, 16)),
]


def _field(library: ContentLibrary, location: str, region: str = REGION) -> FieldMapDef:
    return next(
        f for f in library.field_maps.values() if f.region == region and f.location == location
    )


def _interiors(library: ContentLibrary, location: str) -> list[FieldMapDef]:
    """這個地點的室內圖（依 ID 排序）。"""
    return sorted(
        (
            f
            for f in library.field_maps.values()
            if f.region == REGION and f.interior_of == location
        ),
        key=lambda f: f.id,
    )


def _passable(library: ContentLibrary, field: FieldMapDef) -> list[list[bool]]:
    return passable_grid(field, library.ruleset.terrain.by_id(), library.ruleset.objects.by_id())


def _reach(library: ContentLibrary, field: FieldMapDef, start: XY) -> set[XY]:
    return reachable_from(start, field.grid(), _passable(library, field), library.ruleset.core)


def _manhattan(a: XY, b: XY) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------------------
# 範圍、驗證、配對
# ---------------------------------------------------------------------------


def test_all_18_maps_are_drawn_and_pass(library: ContentLibrary) -> None:
    drawn = {f.location for f in library.field_maps.values() if f.region == REGION and f.location}
    assert drawn == set(MAPS)
    assert drawn == {loc.id for loc in library.world_maps[REGION].locations}
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
    # 尺寸都在 21.3 的範圍內；野外傳送石 3 個在 2～3 的範圍內，荒原沒有警告
    assert not [w for w in report.warnings if REGION in w]
    assert not [w for w in report.warnings if "建議範圍" in w]


def test_nothing_is_pending(library: ContentLibrary) -> None:
    """18 張都畫了：荒原沒有待補（餘燼集的兩扇門也都有室內圖，6D-3）。"""
    assert not [line for line in library.field_pending if REGION in line]
    assert not [line for line in library.field_pending if any(m in line for m in MAPS)]


def test_every_edge_is_a_mutual_pair(library: ContentLibrary) -> None:
    world_map = library.world_maps[REGION]
    locations = world_map.location_by_id()
    paired = 0
    for a, b in world_map.edges:
        if locations[a].hidden or locations[b].hidden:
            continue  # 隱藏地點的連線是門配出口（見 test_obsidian_valley_...）
        fa, fb = _field(library, a), _field(library, b)
        ab = next(e for e in fa.exits if e.to == b)
        ba = next(e for e in fb.exits if e.to == a)
        assert (ab.arrive, ba.arrive) == (ba.id, ab.id), (a, b)
        paired += 1
    # 地點圖 17 條連線扣掉隱藏的焦油坑－黑曜谷
    assert paired == 16


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
    """黑曜谷（隱藏）：焦油坑不畫出口，只畫一扇 ``hidden_until: reveal`` 的門（西北岩壁的窄縫）；
    黑曜谷那一側是東南的出口，arrive 指回那扇門。"""
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
    valley = _field(library, "obsidian_valley")
    assert [(e.id, e.to, e.arrive) for e in valley.exits] == [
        ("to_tar_pits", "tar_pits", "obsidian_valley_crack")
    ]
    assert valley.doors == ()
    assert valley.teleport_stones == ()
    w, h = valley.size
    assert all(x >= w * 2 // 3 and y >= h // 2 for x, y in valley.exits[0].at)  # 東南
    assert not [line for line in library.field_pending if "obsidian" in line]


def test_hidden_entrances_use_hidden_until(library: ContentLibrary) -> None:
    locations = library.world_maps[REGION].location_by_id()
    interiors = {f.id for f in library.field_maps.values() if f.is_interior}
    for location in MAPS:
        for door in _field(library, location).doors:
            if door.to in interiors:
                continue  # 通往室內圖的門（餘燼集，6D-3）另外測
            assert locations[door.to].hidden, (location, door.id)
            assert door.hidden_until == "reveal", (location, door.id)


# ---------------------------------------------------------------------------
# 走得到、安全
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("location", MAPS)
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


@pytest.mark.parametrize("location", MAPS)
def test_no_breakable_bridge_is_the_only_way(library: ContentLibrary, location: str) -> None:
    """致命地形（岩漿、深淵、冰窟）不可以擋住唯一通路：拿掉架在上面的物件（木橋、薄冰）後，出口、
    門、傳送石、情境物件照樣走得到。"""
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
    targets += [s.at for s in field.situation_objects if location in MAPS_6D2]
    assert all(c in reach for c in targets)


@pytest.mark.parametrize("location", sorted(set(MAPS) - COMBAT_FREE))
def test_every_combat_map_has_water(library: ContentLibrary, location: str) -> None:
    """區域題目「怕水」（6.2；草稿待確認 5）：每張有戰鬥的圖至少一處水表面。"""
    field = _field(library, location)
    assert field.spawns
    assert any(s.surface is Surface.WATER for s in field.surfaces)


# ---------------------------------------------------------------------------
# 敵人、事件、營火、傳送石
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("location", MAPS)
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
    for location in MAPS:
        for spawn in _field(library, location).spawns:
            assert (location, spawn.group) in listed


def test_event_spots_use_this_places_skeletons(library: ContentLibrary) -> None:
    places: dict[str, set[str]] = {}
    for skeleton in library.world_event_content.events[REGION].skeletons:
        for place in skeleton.locations:
            places.setdefault(place, set()).add(skeleton.id)
    for location in MAPS:
        field = _field(library, location)
        ids = [s.id for s in field.event_spots]
        assert set(ids) <= places.get(location, set()), location
        assert len(ids) == len(set(ids)) <= 3
        # 這個地點的事件骨架都有地方放（室外或這個地點的室內圖，6D-3）
        for interior in _interiors(library, location):
            ids += [s.id for s in interior.event_spots]
        assert len(ids) == len(set(ids)), location
        assert set(ids) == places.get(location, set()), location


def test_campfires_stones_and_situation_objects_follow_the_draft(library: ContentLibrary) -> None:
    for location in MAPS:
        field = _field(library, location)
        assert len(field.campfires) == CAMPFIRES.get(location, 0), location
        assert len(field.teleport_stones) == STONES.get(location, 0), location
    stone_ids = sorted(s.id for loc in MAPS for s in _field(library, loc).teleport_stones)
    assert stone_ids == [
        "stone_ember_market",
        "stone_old_iron_post",
        "stone_ruined_fortress",
        "stone_tar_pits",
    ]
    assert sum(CAMPFIRES.values()) == 5
    well = _field(library, "cooling_well")
    assert [s.id for s in well.situation_objects] == ["cooling_well_relic"]
    altar = _field(library, "horned_altar")
    assert [s.id for s in altar.situation_objects] == ["horned_fire_altar"]
    assert [n.id for n in altar.npcs] == ["priestess_helin"]
    fortress = _field(library, "ruined_fortress")
    assert {s.id for s in fortress.situation_objects} == {"fortress_stele", "pit_lava_seal"}


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


# ---------------------------------------------------------------------------
# 6D-2：三村落的守點戰、熔心坑前廳、餘燼集
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("location", sorted(VILLAGES))
def test_village_raiders_stand_outside_the_gate_near_the_defend_target(
    library: ContentLibrary, location: str
) -> None:
    """守點目標是情境物件（站得上、走得到）；唯一的駐守就是守點戰的陣容，站在土牆外的村口、
    離守點目標 6 格以內。"""
    target_id, group = VILLAGES[location]
    field = _field(library, location)
    targets = [s for s in field.situation_objects if s.id == target_id]
    assert len(targets) == 1
    target = targets[0].at
    passable = _passable(library, field)
    assert passable[target[1]][target[0]]
    assert target in _reach(library, field, field.entry)
    assert [(s.group, s.patrol) for s in field.spawns] == [(group, ())]
    raid = field.spawns[0].at
    assert _manhattan(raid, target) <= DEFEND_RADIUS
    # 村口外：把土牆的缺口補起來，入口照樣走得到駐守點，但走不到守點目標
    walls = [o for o in field.objects if o.kind == "earth_wall"]
    assert walls
    gate = _gate_cells(field)
    assert gate
    closed = field.model_copy(
        update={
            "objects": field.objects
            + tuple(o.model_copy(update={"at": c}) for o, c in zip(walls, gate, strict=False))
        }
    )
    reach = _reach(library, closed, field.entry)
    assert raid in reach
    assert target not in reach


def _gate_cells(field: FieldMapDef) -> list[XY]:
    """土牆圈上的缺口（村口）：土牆外框的邊上沒有土牆的格子。"""
    walls = {o.at for o in field.objects if o.kind == "earth_wall"}
    xs = [x for x, _ in walls]
    ys = [y for _, y in walls]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    frame = [(x, y0) for x in range(x0, x1 + 1)] + [(x, y1) for x in range(x0, x1 + 1)]
    frame += [(x0, y) for y in range(y0 + 1, y1)] + [(x1, y) for y in range(y0 + 1, y1)]
    return [c for c in frame if c not in walls]


@pytest.mark.parametrize("location", sorted(VILLAGES))
def test_village_contact_cuts_include_the_defend_target(
    library: ContentLibrary, location: str
) -> None:
    """守點目標附近的接觸點切得出合法的 12×12，而且戰場包含守點目標、雙方都走得到它；切不到的
    村落改用守點模板（草稿待確認 3），要列在 ``TEMPLATE_FALLBACK``。"""
    target_id, group = VILLAGES[location]
    field = _field(library, location)
    target = next(s.at for s in field.situation_objects if s.id == target_id)
    contacts = [(e, a) for m, g, e, a in CONTACTS if m == location and g == group]
    assert len(contacts) >= 2
    if location in TEMPLATE_FALLBACK:
        return
    terrain = library.ruleset.terrain.by_id()
    objects = library.ruleset.objects.by_id()
    for enemy_at, ally_at in contacts:
        center = ((enemy_at[0] + ally_at[0]) // 2, (enemy_at[1] + ally_at[1]) // 2)
        x0, y0 = _window_origin(center, field.size)
        assert x0 <= target[0] < x0 + CUT and y0 <= target[1] < y0 + CUT, (enemy_at, ally_at)
        battle = cut_battlefield(library, field, enemy_at, ally_at)
        assert check_map(battle, terrain, library.ruleset.core, objects) == []
        local = (target[0] - x0, target[1] - y0)
        cut_pass = passable_grid(battle, terrain, objects)
        assert cut_pass[local[1]][local[0]]
        reach = reachable_from(local, battle.grid(), cut_pass, library.ruleset.core)
        assert set(battle.start_zones[Team.ENEMY]) & reach
        assert set(battle.start_zones[Team.ALLY]) & reach


def test_iron_forge_lava_pool_is_fenced(library: ContentLibrary) -> None:
    """鐵爐村的熔岩取熱池用矮牆整圈圍起來：每一格岩漿的四鄰不是岩漿就是矮牆。"""
    field = _field(library, "iron_forge_village")
    lava = {
        (x, y)
        for y, row in enumerate(field.grid())
        for x, (_, tid) in enumerate(row)
        if tid == "lava"
    }
    assert lava
    fence = {o.at for o in field.objects if o.kind == "low_wall"}
    for x, y in lava:
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            assert n in lava or n in fence, n


def test_molten_heart_pit_antechamber(library: ContentLibrary) -> None:
    """熔心坑前廳（Boss 前廳 12×8）：沒有敵人、營火、事件、傳送石；坑口 ``pit_gate`` 走得到；
    熔岩封口 ``pit_lava_seal`` 在廢墟要塞往熔心坑的出口旁；Boss 地圖的 4 口冷卻井是物件（CW-1）。"""
    hall = _field(library, "molten_heart_pit")
    location = library.world_maps[REGION].location_by_id()["molten_heart_pit"]
    assert hall.layout_for(location) == "boss"
    assert hall.size == (12, 8)
    assert hall.spawns == () and hall.campfires == () and hall.event_spots == ()
    assert hall.teleport_stones == () and hall.doors == ()
    assert [s.id for s in hall.situation_objects] == ["pit_gate"]
    assert hall.situation_objects[0].at in _reach(library, hall, hall.entry)
    # 裝飾性的熔岩裂縫：沒有可走的岩漿格
    assert "lava" not in hall.legend.values()
    assert [e.to for e in hall.exits] == ["ruined_fortress"]
    assert all(x == 0 for x, _ in hall.exits[0].at)  # 西
    # 廢墟要塞那一側：熔岩封口在東邊出口旁
    fortress = _field(library, "ruined_fortress")
    seal = next(s.at for s in fortress.situation_objects if s.id == "pit_lava_seal")
    exit_ = next(e for e in fortress.exits if e.to == "molten_heart_pit")
    assert min(_manhattan(seal, c) for c in exit_.at) <= 2
    assert all(x == fortress.width - 1 for x, _ in exit_.at)  # 東
    boss = library.maps["molten_heart_pit"]
    wells = sorted(o.at for o in boss.objects if o.kind == "cooling_well")
    assert wells == [(3, 4), (3, 8), (7, 4), (8, 8)]


def test_ember_market_town(library: ContentLibrary) -> None:
    """餘燼集（小鎮 24×18）：安全區、傳送石 1 個、鐵娘與灰鬚站在鎮上（灰鬚在酒館外的牆邊，19.5）、
    商店／懸賞板／導師；酒館與爐叔鐵鋪各一扇門（6D-3）。"""
    town = _field(library, "ember_market")
    assert town.size == (24, 18)
    assert town.spawns == () and town.campfires == ()
    assert [s.id for s in town.teleport_stones] == ["stone_ember_market"]
    assert {n.id for n in town.npcs} == {"iron_lady", "greybeard"}
    # 6T-1b：郵寄（post）
    assert {f.id for f in town.facilities} == {"shop", "notice_board", "mentor", "post"}
    assert {e.to for e in town.exits} == {"ash_ferry", "scorched_outskirts", "old_iron_post"}
    assert {(d.id, d.at, d.to) for d in town.doors} == {
        ("tavern_door", (3, 5), "ember_market_tavern"),
        ("smithy_door", (19, 5), "ember_market_smithy"),
    }
    passable = _passable(library, town)
    reach = _reach(library, town, town.entry)
    for door in town.doors:
        x, y = door.at
        assert passable[y][x] and door.at in reach, door.id
        assert door.hidden_until is None
        # 門外一格（南邊）站得上：從室內出來的落腳處
        assert passable[y + 1][x] and (x, y + 1) in reach, door.id
    for npc in town.npcs:
        assert npc.at in reach, npc.id
    # 酒館老兵移進室內，鎮上不放事件點
    assert town.event_spots == ()


INTERIORS: dict[str, tuple[str, set[str], set[str], set[str]]] = {
    # 室內圖: (鎮上的門, 設施, NPC, 事件點)
    "ember_market_tavern": ("tavern_door", {"tavern", "hire"}, set(), {"tavern_veteran"}),
    "ember_market_smithy": ("smithy_door", {"smithy", "enchanter"}, {"smith_lu"}, set()),
}
"""餘燼集的兩張室內圖（6D-3；草稿第 2 張、19.5）。酒館老兵沒有人設卡，只放事件點。"""


def test_ember_market_has_exactly_two_interiors(library: ContentLibrary) -> None:
    assert [f.id for f in _interiors(library, "ember_market")] == sorted(INTERIORS)
    # 荒原其他地點沒有室內圖
    others = {f.interior_of for f in library.field_maps.values() if f.region == REGION}
    assert others - {None} == {"ember_market"}


@pytest.mark.parametrize("interior_id", sorted(INTERIORS))
def test_ember_market_interiors(library: ContentLibrary, interior_id: str) -> None:
    door_id, facilities, npcs, spots = INTERIORS[interior_id]
    town = _field(library, "ember_market")
    room = library.field_maps[interior_id]
    assert room.interior_of == "ember_market" and room.region == REGION
    assert room.size == (10, 8)
    assert room.doors == () and room.teleport_stones == () and room.spawns == ()
    # 門與出口互指：鎮上的門通往這張室內圖，室內圖的出口回到餘燼集、arrive 指向那扇門
    door = next(d for d in town.doors if d.id == door_id)
    assert door.to == interior_id
    assert len(room.exits) == 1
    exit_ = room.exits[0]
    assert exit_.to == "ember_market" and exit_.arrive == door_id and exit_.region is None
    # 設施、NPC、事件點照草稿與 19.5
    assert {f.id for f in room.facilities} == facilities
    assert {n.id for n in room.npcs} == npcs
    assert {s.id for s in room.event_spots} == spots
    # 站位：入口走得到出口、NPC、事件點；設施（櫃檯、鐵砧、石柱）旁邊至少一格走得到
    passable = _passable(library, room)
    reach = _reach(library, room, room.entry)
    for cell in exit_.at:
        x, y = _inward(cell, room.size)
        assert passable[y][x] and room.entry in _reach(library, room, cell), cell
    for at in [n.at for n in room.npcs] + [s.at for s in room.event_spots]:
        assert at in reach, at
    for facility in room.facilities:
        x, y = facility.at
        near = {(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))}
        assert near & reach, facility.id
    # 爐叔站在鐵砧旁
    if "smith_lu" in npcs:
        smith = next(n for n in room.npcs if n.id == "smith_lu")
        anvil = next(f for f in room.facilities if f.id == "smithy")
        assert _manhattan(smith.at, anvil.at) == 1
