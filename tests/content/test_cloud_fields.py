"""雲嶺實地地圖的內容（Phase 6C-3、6C-4；Phase 6 計畫第 4 節）。

``test_fields.py`` 測格式與驗證本身；這裡測內容庫裡實際畫好的雲嶺地圖：

- 每張圖通過 :func:`field_map_report`，兩端都畫了的連線都配對，沒畫的一端列為待補；
- 出口內側 1 格站得上、出口與入口互相走得到，木橋這類打得斷的物件不是唯一通路；
- ``spawns`` 用這個地點遭遇表裡的陣容、巡邏路線沿直線走得通，``event_spots`` 用這個地點的事件骨架；
- 接觸點切得出合法的 12×12 戰場（敵方起始區 4 格、我方 3 格；正式的切法在 6C-2）；
- 營火、傳送石的數量照玩法 PM 草稿；
- 隱藏地點（丹爐洞、鶴歸崖）的入口是相鄰地圖上 ``hidden_until: reveal`` 的門；
- 雲頂觀前廳只從源晶裂痕進入，沒有敵人、營火、傳送石、事件點；
- 6C-4 交件時雲嶺 18／18，除了往灰燼荒原的那一項之外沒有待補。
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import pytest

from trpg.content.fields import FieldMapDef, field_map_report
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef, check_map, passable_grid, reachable_from
from trpg.shared.types import Team

type XY = tuple[int, int]

REGION = "cloud_ridge"

MAPS_6C3 = (
    "mist_ferry",
    "ferry_steps",
    "bamboo_path",
    "hunter_hut",
    "rain_terraces",
    "mist_temple_gate",
    "cliff_gang_fort",
    "old_pine_altar",
    "ashen_ferry",
)
"""6C-3 的 9 張（從霧渡鎮往外，含往灰燼荒原的渡口）。"""

MAPS_6C4 = (
    "cloud_sea_bridge",
    "herb_valley",
    "elixir_cave",
    "north_slope",
    "winter_lake",
    "sword_tomb",
    "crystal_rift",
    "crane_cliff",
    "cloud_summit",
)
"""6C-4 的 9 張（其餘地點，含兩個隱藏地點與雲頂觀前廳）。"""

ALL_MAPS = MAPS_6C3 + MAPS_6C4

HIDDEN = {"elixir_cave": "herb_valley", "crane_cliff": "north_slope"}
"""隱藏地點 → 畫入口（門）的相鄰地圖（草稿第 10、13 張）。"""

CAMPFIRES = {
    "hunter_hut": 1,
    "mist_temple_gate": 1,
    "old_pine_altar": 1,
    "herb_valley": 1,
    "winter_lake": 1,
}
"""草稿第 0 節：固定營火 5 個（獵戶小屋、青霧觀山門、古松祭壇、藥師谷、冬湖）。"""

STONES = {"mist_ferry": 1, "rain_terraces": 1, "cloud_sea_bridge": 1, "crystal_rift": 1}
"""草稿第 0 節：傳送石雨中梯田、雲海吊橋、源晶裂痕，加城鎮 1 個。"""

CUT = 12
"""就地開打切出的戰場邊長（21.4）。"""

CONTACTS: list[tuple[str, str, XY, XY]] = [
    # (地圖, 陣容, 敵人所在, 我方所在)：駐守點與巡邏路線上的接觸點
    ("ferry_steps", "bandit_raiders", (9, 6), (5, 7)),
    ("ferry_steps", "bandit_shield_line", (15, 7), (18, 5)),
    ("ferry_steps", "bandit_shield_line", (4, 7), (2, 9)),
    ("bamboo_path", "mist_wolf_pack", (16, 2), (15, 6)),
    ("bamboo_path", "bandit_wolf_handler", (9, 8), (10, 10)),
    ("bamboo_path", "bandit_wolf_handler", (4, 5), (1, 4)),
    ("hunter_hut", "hunter_beasts", (11, 3), (11, 7)),
    ("hunter_hut", "hunter_beasts", (19, 3), (21, 8)),
    ("rain_terraces", "terrace_clash", (16, 2), (12, 5)),
    ("rain_terraces", "sect_patrol", (5, 8), (5, 11)),
    ("rain_terraces", "sect_patrol", (20, 8), (21, 10)),
    ("cliff_gang_fort", "cliff_gang_core", (11, 9), (4, 9)),
    ("cliff_gang_fort", "cliff_gang_hounds", (20, 10), (16, 8)),
    ("cliff_gang_fort", "cliff_gang_hounds", (20, 4), (17, 6)),
    ("old_pine_altar", "altar_wardens", (3, 8), (8, 11)),
    # 6C-4
    ("cloud_sea_bridge", "sword_array", (10, 3), (13, 4)),
    ("cloud_sea_bridge", "bridge_patrol", (9, 8), (9, 13)),
    ("cloud_sea_bridge", "bridge_patrol", (9, 4), (6, 5)),
    ("herb_valley", "valley_keepers", (12, 12), (7, 12)),
    ("herb_valley", "valley_beasts", (6, 15), (4, 15)),
    ("herb_valley", "valley_beasts", (17, 15), (17, 12)),
    ("elixir_cave", "furnace_steward", (7, 6), (2, 6)),
    ("elixir_cave", "furnace_tide", (12, 11), (10, 9)),
    ("north_slope", "north_slope_pack", (4, 4), (7, 9)),
    ("north_slope", "north_slope_pack", (4, 4), (12, 5)),
    ("winter_lake", "lake_hunters", (20, 12), (15, 15)),
    ("winter_lake", "lake_bears", (13, 6), (12, 10)),
    ("winter_lake", "lake_bears", (13, 6), (12, 3)),
    ("sword_tomb", "tomb_array", (12, 9), (12, 14)),
    ("sword_tomb", "tomb_swordsmen", (10, 2), (10, 5)),
    ("sword_tomb", "tomb_swordsmen", (20, 10), (18, 12)),
    ("crystal_rift", "rift_wraiths", (12, 4), (10, 7)),
    ("crystal_rift", "rift_scavengers", (12, 13), (7, 14)),
    ("crane_cliff", "crane_nest", (6, 2), (7, 6)),
    ("crane_cliff", "crane_cliff_bear", (5, 10), (9, 11)),
]


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _field(library: ContentLibrary, location: str) -> FieldMapDef:
    return next(
        f for f in library.field_maps.values() if f.region == REGION and f.location == location
    )


def _passable(library: ContentLibrary, field: FieldMapDef) -> list[list[bool]]:
    return passable_grid(field, library.ruleset.terrain.by_id(), library.ruleset.objects.by_id())


def _reach(library: ContentLibrary, field: FieldMapDef, start: XY) -> set[XY]:
    return reachable_from(start, field.grid(), _passable(library, field), library.ruleset.core)


# ---------------------------------------------------------------------------
# 範圍、驗證、配對
# ---------------------------------------------------------------------------


def test_all_eighteen_maps_are_drawn_and_pass(library: ContentLibrary) -> None:
    drawn = {f.location for f in library.field_maps.values() if f.region == REGION and f.location}
    locations = {loc.id for loc in library.world_maps[REGION].locations}
    assert drawn == locations == set(ALL_MAPS)
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
    # 6C-4 畫完後：尺寸都在 21.3 的範圍內，傳送石數也對，雲嶺沒有任何警告
    assert not [w for w in report.warnings if REGION in w]
    assert not [w for w in report.warnings if "建議範圍" in w]


def test_only_the_ashen_waste_crossing_is_pending(library: ContentLibrary) -> None:
    """6C-4 交件：雲嶺內沒有待補；只剩往灰燼荒原（6D-1）的那一項。"""
    ours = [line for line in library.field_pending if f"→ {REGION}/" in line]
    assert ours == []
    cross = [line for line in library.field_pending if "ashen_ferry" in line]
    assert len(cross) == 1
    assert "→ ashen_waste/ash_ferry" in cross[0]


def test_every_edge_between_drawn_maps_is_a_mutual_pair(library: ContentLibrary) -> None:
    world_map = library.world_maps[REGION]
    drawn = {f.location for f in library.field_maps.values() if f.region == REGION}
    pending = "\n".join(library.field_pending)
    for a, b in world_map.edges:
        if a in HIDDEN or b in HIDDEN:
            continue  # 隱藏地點的連線是門配出口（test_hidden_places_are_entered_through_a_hidden_door）
        if a in drawn and b in drawn:
            fa, fb = _field(library, a), _field(library, b)
            ab = next(e for e in fa.exits if e.to == b)
            ba = next(e for e in fb.exits if e.to == a)
            assert (ab.arrive, ba.arrive) == (ba.id, ab.id), (a, b)
        else:
            for here, there in ((a, b), (b, a)):
                if here in drawn and there not in drawn:
                    assert f"{REGION}/{there}：對面還沒有實地地圖" in pending, (here, there)


def test_pending_only_points_at_maps_not_drawn_yet(library: ContentLibrary) -> None:
    drawn = {(f.region, f.location) for f in library.field_maps.values() if f.location}
    for line in library.field_pending:
        target = line.split(" → ", 1)[1].split("：", 1)[0]
        region, location = target.split("/")
        assert (region, location) not in drawn, line


def test_the_ferry_crosses_into_the_ashen_waste(library: ContentLibrary) -> None:
    ferry = _field(library, "ashen_ferry")
    cross = [e for e in ferry.exits if e.region == "ashen_waste"]
    assert [(e.to, e.arrive) for e in cross] == [("ash_ferry", "to_ashen_ferry")]
    assert ferry.spawns == () and ferry.event_spots == ()


@pytest.mark.parametrize(("hidden", "host"), sorted(HIDDEN.items()))
def test_hidden_places_are_entered_through_a_hidden_door(
    library: ContentLibrary, hidden: str, host: str
) -> None:
    """隱藏地點的連線不用出口：相鄰地圖畫一扇 ``hidden_until: reveal`` 的門，隱藏地點那一側用出口
    回來、``arrive`` 指向那扇門（21.6；Phase 6 計畫 2.3 第 2 條）。"""
    host_map, secret = _field(library, host), _field(library, hidden)
    assert library.world_maps[REGION].location_by_id()[hidden].hidden
    assert not [e for e in host_map.exits if e.to == hidden]
    doors = [d for d in host_map.doors if d.to == hidden]
    assert len(doors) == 1
    assert doors[0].hidden_until == "reveal"
    assert [(e.to, e.arrive) for e in secret.exits] == [(host, doors[0].id)]
    # 洞口站得上、從入口走得到，也走得回來
    door = doors[0].at
    assert _passable(library, host_map)[door[1]][door[0]]
    assert door in _reach(library, host_map, host_map.entry)
    assert host_map.entry in _reach(library, host_map, door)


def test_cloud_summit_hall_is_only_reached_from_the_rift(library: ContentLibrary) -> None:
    """雲頂觀前廳 12×8（18.3、21.4）：只從源晶裂痕進入；Boss 戰照舊用 Boss 地圖，所以前廳沒有敵人、
    營火、傳送石、事件點；觀門與霧牆是情境物件（6C-1／6C-5 接）。"""
    hall = _field(library, "cloud_summit")
    assert hall.size == (12, 8)
    assert [(e.to, e.arrive) for e in hall.exits] == [("crystal_rift", "to_cloud_summit")]
    assert hall.doors == ()
    assert hall.teleport_stones == ()
    assert hall.spawns == ()
    assert hall.campfires == ()
    assert hall.event_spots == ()
    assert [s.id for s in hall.situation_objects] == ["summit_gate"]
    rift = _field(library, "crystal_rift")
    assert "rift_mist_wall" in {s.id for s in rift.situation_objects}
    into = sorted(
        f.id for f in library.field_maps.values() for e in f.exits if e.to == "cloud_summit"
    )
    assert into == ["crystal_rift"]


def test_hidden_entrances_use_hidden_until(library: ContentLibrary) -> None:
    locations = library.world_maps[REGION].location_by_id()
    for field in library.field_maps.values():
        if field.region != REGION:
            continue
        for door in field.doors:
            if door.to in locations:
                assert locations[door.to].hidden, (field.id, door.id)
                assert door.hidden_until == "reveal", (field.id, door.id)


def test_mist_ferry_keeps_the_6b1_anchor_cells(library: ContentLibrary) -> None:
    """6B-2 用霧渡鎮的入口、出口、門與傳送石；6C-3 補齊草稿時不搬動它們。"""
    town = _field(library, "mist_ferry")
    assert town.entry == (11, 9)
    assert {e.id: e.at for e in town.exits} == {
        "to_hunter_hut": ((11, 0), (12, 0)),
        "to_ferry_steps": ((23, 8), (23, 9)),
        "to_ashen_ferry": ((3, 17), (4, 17)),
    }
    assert {d.id: d.at for d in town.doors} == {"tavern_door": (3, 5), "smithy_door": (18, 5)}
    assert [s.at for s in town.teleport_stones] == [(12, 8)]
    assert town.spawns == ()  # 城鎮是安全區


# ---------------------------------------------------------------------------
# 走得到、安全
# ---------------------------------------------------------------------------


def _inward(cell: XY, size: XY) -> XY:
    x, y = cell
    w, h = size
    if x == 0:
        return (1, y)
    if x == w - 1:
        return (x - 1, y)
    if y == 0:
        return (x, 1)
    return (x, y - 1) if y == h - 1 else cell


@pytest.mark.parametrize("location", ALL_MAPS)
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


@pytest.mark.parametrize("location", ALL_MAPS)
def test_no_breakable_bridge_is_the_only_way(library: ContentLibrary, location: str) -> None:
    """致命地形不可以擋住唯一通路：拿掉架在深淵上的物件（木橋、薄冰）後，出口、門、傳送石、NPC
    旁邊照樣走得到。"""
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


# ---------------------------------------------------------------------------
# 敵人、事件、營火、傳送石
# ---------------------------------------------------------------------------


def _segment(a: XY, b: XY) -> list[XY]:
    (ax, ay), (bx, by) = a, b
    assert ax == bx or ay == by, f"巡邏的相鄰轉折點要在同一行或同一列：{a} → {b}"
    if ax == bx:
        step = 1 if by >= ay else -1
        return [(ax, y) for y in range(ay, by + step, step)]
    step = 1 if bx >= ax else -1
    return [(x, ay) for x in range(ax, bx + step, step)]


def _route(patrol: tuple[XY, ...] | list[XY]) -> list[XY]:
    """巡邏路線經過的每一格（轉折點之間沿直線）。"""
    return [c for a, b in pairwise(patrol) for c in _segment(a, b)]


@pytest.mark.parametrize("location", ALL_MAPS)
def test_spawns_use_this_places_groups_and_walkable_patrols(
    library: ContentLibrary, location: str
) -> None:
    field = _field(library, location)
    table = library.world_encounters[REGION]
    groups = {g.group for loc in table.locations if loc.location == location for g in loc.groups}
    assert {s.group for s in field.spawns} <= groups
    assert len(field.spawns) <= 3  # 草稿第 0 節：一張圖最多 3 隊
    assert sum(1 for s in field.spawns if s.patrol) <= 1  # 巡邏每張圖 0～1 隊
    passable = _passable(library, field)
    core = library.ruleset.core
    grid = field.grid()
    for spawn in field.spawns:
        route = list(spawn.patrol)
        if not route:
            continue
        cells = _route(route)
        assert spawn.at in cells
        assert all(passable[y][x] for x, y in cells), spawn.group
        for (ax, ay), (bx, by) in pairwise(cells):
            # 來回都走得了：相鄰兩格的高低差不超過一步能爬的高度
            assert abs(grid[by][bx][0] - grid[ay][ax][0]) <= core.max_climb_height


def test_each_spawn_has_a_contact_point(library: ContentLibrary) -> None:
    listed = {(m, g) for m, g, _, _ in CONTACTS}
    for location in ALL_MAPS:
        for spawn in _field(library, location).spawns:
            assert (location, spawn.group) in listed


def _event_places(library: ContentLibrary) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for skeleton in library.world_event_content.events[REGION].skeletons:
        for place in skeleton.locations:
            out.setdefault(place, set()).add(skeleton.id)
    return out


def test_event_spots_use_this_places_skeletons(library: ContentLibrary) -> None:
    places = _event_places(library)
    for field in library.field_maps.values():
        if field.region != REGION or field.place not in ALL_MAPS:
            continue
        ids = [s.id for s in field.event_spots]
        assert set(ids) <= places.get(field.place, set()), field.id
        assert len(ids) <= 3  # 草稿待確認 10：每張圖 1～3 個事件點
    # 這段畫了的地點，事件骨架都有地方放（城鎮的說書人在酒館室內）
    spots = {
        (f.place, s.id)
        for f in library.field_maps.values()
        if f.region == REGION
        for s in f.event_spots
    }
    for location in ALL_MAPS:
        for event_id in sorted(places.get(location, set())):
            assert (location, event_id) in spots, (location, event_id)


def test_campfires_and_stones_follow_the_draft(library: ContentLibrary) -> None:
    for location in ALL_MAPS:
        field = _field(library, location)
        assert len(field.campfires) == CAMPFIRES.get(location, 0), location
        assert len(field.teleport_stones) == STONES.get(location, 0), location
    stone_ids = sorted(s.id for loc in ALL_MAPS for s in _field(library, loc).teleport_stones)
    assert stone_ids == [
        "stone_cloud_sea_bridge",
        "stone_crystal_rift",
        "stone_mist_ferry",
        "stone_rain_terraces",
    ]
    assert sum(CAMPFIRES.values()) == 5  # 草稿第 0 節：固定營火 5 個


# ---------------------------------------------------------------------------
# 就地開打：接觸點切出 12×12
# ---------------------------------------------------------------------------


def _window_origin(center: XY, size: XY) -> XY:
    """以 ``center`` 為中心的 12×12；越過地圖邊緣就往內推（草稿待確認 12）。"""
    w, h = size
    x0 = min(max(center[0] - CUT // 2, 0), max(w - CUT, 0))
    y0 = min(max(center[1] - CUT // 2, 0), max(h - CUT, 0))
    return x0, y0


def _zone(cells: set[XY], anchor: XY, count: int, taken: set[XY]) -> list[XY]:
    ordered = sorted(
        (c for c in cells if c not in taken),
        key=lambda c: (abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]), c[1], c[0]),
    )
    return ordered[:count]


def cut_battlefield(
    library: ContentLibrary, field: FieldMapDef, enemy_at: XY, ally_at: XY
) -> MapDef:
    """測試用的切地圖（6C-2 才是正式的切法）：以兩人中點為中心切 12×12，敵方起始區取敵人附近
    走得到的 4 格、我方取我方附近走得到的 3 格。"""
    center = ((enemy_at[0] + ally_at[0]) // 2, (enemy_at[1] + ally_at[1]) // 2)
    x0, y0 = _window_origin(center, field.size)
    rows = range(y0, y0 + CUT)
    heights = "\n".join(field.height_rows()[y][x0 : x0 + CUT] for y in rows)
    terrain = "\n".join(field.terrain_rows()[y][x0 : x0 + CUT] for y in rows)

    def inside(at: XY) -> bool:
        return x0 <= at[0] < x0 + CUT and y0 <= at[1] < y0 + CUT

    def shift(at: XY) -> list[int]:
        return [at[0] - x0, at[1] - y0]

    data: dict[str, Any] = {
        "id": f"cut_{field.id}",
        "name_zh": "接觸點",
        "archetype": "open_plain",
        "size": [CUT, CUT],
        "heights": heights,
        "terrain": terrain,
        "legend": field.legend,
        "objects": [{"at": shift(o.at), "kind": o.kind} for o in field.objects if inside(o.at)],
        "surfaces": [
            {"at": shift(s.at), "surface": s.surface.value} for s in field.surfaces if inside(s.at)
        ],
        "start_zones": {"ally": [], "enemy": []},
    }
    probe = MapDef.model_validate({**data, "start_zones": {"ally": [[0, 0]], "enemy": [[0, 1]]}})
    passable = passable_grid(
        probe, library.ruleset.terrain.by_id(), library.ruleset.objects.by_id()
    )
    grid = probe.grid()
    core = library.ruleset.core
    e_local = (enemy_at[0] - x0, enemy_at[1] - y0)
    a_local = (ally_at[0] - x0, ally_at[1] - y0)
    enemy = _zone(reachable_from(e_local, grid, passable, core), e_local, 4, set())
    ally = _zone(reachable_from(a_local, grid, passable, core), a_local, 3, set(enemy))
    data["start_zones"] = {"ally": [list(c) for c in ally], "enemy": [list(c) for c in enemy]}
    return MapDef.model_validate(data)


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
