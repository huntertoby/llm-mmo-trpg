"""大世界地點圖（Phase 5A-1）：``world/maps/*.yaml``、``regions.yaml`` 的 ``map_pool``。

雲嶺的連線是初稿（Q1，玩法 PM 可能改），所以這裡不寫死連線條數，只驗規則。
"""

from __future__ import annotations

import shutil
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import load_content_file
from trpg.content.world_map import (
    MAX_LOCATIONS,
    MIN_LOCATIONS,
    LocationDef,
    LocationMapDef,
    world_map_problems,
)
from trpg.shared.errors import ContentError

_COMMON = {"open_plain", "corridor", "ruined_heights", "bridge_chasm"}
_ELEMENTAL = {"forest", "swamp", "frozen_lake", "oil_depot"}
_REGION_IDS = ("cloud_ridge", "crystal_crown", "arcane_hub", "ashen_waste", "frost_tide")


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def cloud(library: ContentLibrary) -> LocationMapDef:
    return library.world_maps["cloud_ridge"]


# ---- 測試用的最小合法地點圖 ----


def _loc(loc_id: str, kind: str = "camp", **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"id": loc_id, "name_zh": loc_id, "kind": kind, "pos": {"x": 0, "y": 0}}
    if kind not in {"town", "gate"}:
        data["level_min"] = 1
    if kind in {"camp", "elite_lair", "secret"}:
        data["battle_maps"] = ["swamp"]
    data.update(extra)
    return data


def _small_map(count: int = MIN_LOCATIONS) -> dict[str, Any]:
    """小鎮 ``t`` ＋ ``count - 1`` 個營地排成一串（``c1``–``c2``–…）。"""
    locations = [_loc("t", "town")] + [_loc(f"c{i}") for i in range(1, count)]
    ids = [loc["id"] for loc in locations]
    edges = [[a, b] for a, b in pairwise(ids)]
    return {
        "region": "cloud_ridge",
        "name_zh": "測試",
        "level_min": 1,
        "level_max": 6,
        "town": "t",
        "locations": locations,
        "edges": edges,
    }


def _with_location(data: dict[str, Any], index: int, **changes: Any) -> dict[str, Any]:
    locations = [dict(loc) for loc in data["locations"]]
    locations[index].update(changes)
    return {**data, "locations": locations}


def _bad(data: dict[str, Any], *fragments: str) -> None:
    with pytest.raises(ValidationError) as info:
        LocationMapDef.model_validate(data)
    text = str(info.value)
    for fragment in fragments:
        assert fragment in text


# ---- 實際內容 ----


def test_cloud_ridge_loaded(cloud: LocationMapDef) -> None:
    assert len(cloud.locations) == 18
    assert MIN_LOCATIONS <= len(cloud.locations) <= MAX_LOCATIONS
    assert cloud.town == "mist_ferry"
    assert (cloud.level_min, cloud.level_max) == (1, 6)
    hidden = sorted(loc.id for loc in cloud.locations if loc.hidden)
    assert hidden == ["crane_cliff", "elixir_cave"]
    assert cloud.edges  # 條數是初稿，不寫死
    assert "18 個地點" in cloud.summary()
    assert "隱藏 2" in cloud.summary()


def test_cloud_ridge_locations_follow_18_3(cloud: LocationMapDef) -> None:
    by_id = cloud.location_by_id()
    assert by_id["mist_ferry"].kind == "town"
    assert by_id["cloud_summit"].kind == "boss"
    assert by_id["cloud_summit"].battle_maps == ("cloud_summit",)  # Boss 專屬地圖（5F-2）
    gate = by_id["ashen_ferry"]
    assert (gate.kind, gate.gate_to, gate.unlock_flag) == (
        "gate",
        "ashen_waste",
        "mist_tide_success",
    )
    assert by_id["elixir_cave"].reveal == ("situation",)
    assert by_id["crane_cliff"].reveal == ("perception_nearby", "quest_clue", "friend_footprint")
    assert (by_id["bamboo_path"].level_min, by_id["bamboo_path"].level_max) == (1, 2)
    assert by_id["ferry_steps"].level_max == 1  # 省略＝同 level_min


def test_cloud_ridge_cross_file(library: ContentLibrary, cloud: LocationMapDef) -> None:
    assert world_map_problems(cloud, regions=library.regions, maps=library.maps) == []
    assert library.regions is not None
    pool = set(library.regions.region_by_id()["cloud_ridge"].map_pool)
    archetypes = {library.maps[m].archetype for loc in cloud.locations for m in loc.battle_maps}
    assert archetypes - {"boss"} <= pool  # Boss 地圖只在 boss 地點（validator 檢查，5F-2）
    assert "oil_depot" not in archetypes


def test_cloud_ridge_is_connected_without_hidden(cloud: LocationMapDef) -> None:
    # 規則本身由 validator 保證；這裡再從外部走一次，確認資料符合
    hidden = {loc.id for loc in cloud.locations if loc.hidden}
    visible = sorted(loc.id for loc in cloud.locations if not loc.hidden)
    seen = {cloud.town}
    frontier = [cloud.town]
    while frontier:
        current = frontier.pop()
        for nxt in cloud.neighbors(current):
            if nxt not in seen and nxt not in hidden:
                seen.add(nxt)
                frontier.append(nxt)
    assert sorted(seen) == visible
    for secret in sorted(hidden):
        assert cloud.neighbors(secret)


def test_neighbors_sorted(cloud: LocationMapDef) -> None:
    assert cloud.neighbors("mist_ferry") == ("ashen_ferry", "ferry_steps", "hunter_hut")
    for loc in cloud.locations:
        found = cloud.neighbors(loc.id)
        assert list(found) == sorted(found)
    with pytest.raises(KeyError):
        cloud.neighbors("nowhere")


def test_region_map_pools(library: ContentLibrary) -> None:
    assert library.regions is not None
    by_id = library.regions.region_by_id()
    for region_id in _REGION_IDS:
        pool = set(by_id[region_id].map_pool)
        assert len(by_id[region_id].map_pool) == 7
        assert pool >= _COMMON
        assert len(pool & _ELEMENTAL) == 3


@pytest.mark.parametrize("bad", [["swamp", "swamp"], ["test"], ["training"], ["boss"]])
def test_region_map_pool_validation(bad: list[str]) -> None:
    from trpg.content.regions import RegionDef  # noqa: PLC0415

    with pytest.raises(ValidationError):
        RegionDef.model_validate({"id": "x", "name_zh": "x", "map_pool": bad})


# ---- 單檔驗證 ----


def test_small_map_is_valid() -> None:
    m = LocationMapDef.model_validate(_small_map())
    assert len(m.locations) == MIN_LOCATIONS
    LocationMapDef.model_validate(_small_map(MAX_LOCATIONS))


@pytest.mark.parametrize("count", [MIN_LOCATIONS - 1, MAX_LOCATIONS + 1])
def test_location_count(count: int) -> None:
    _bad(_small_map(count), "地點數")


def test_duplicate_location_id() -> None:
    data = _with_location(_small_map(), 2, id="c1")
    _bad(data, "c1 重複")


def test_town_rules() -> None:
    _bad(_with_location(_small_map(), 0, kind="camp", level_min=1, battle_maps=["swamp"]), "town")
    _bad(_with_location(_small_map(), 1, kind="town", level_min=None, battle_maps=[]), "恰好 1 個")
    _bad({**_small_map(), "town": "c1"}, "不是本區的小鎮")


def test_level_rules() -> None:
    _bad(_with_location(_small_map(), 0, level_min=1), "不可填建議等級")
    no_level = _small_map()
    del no_level["locations"][1]["level_min"]
    _bad(no_level, "level_min")
    _bad(_with_location(_small_map(), 1, level_min=3, level_max=2), "小於")
    _bad(_with_location(_small_map(), 1, level_min=7), "超出區域範圍")
    _bad(_with_location(_small_map(), 1, level_max=9), "超出區域範圍")
    _bad({**_small_map(), "level_min": 5, "level_max": 4}, "大於")
    m = LocationMapDef.model_validate(_with_location(_small_map(), 1, level_min=3))
    assert m.locations[1].level_max == 3


def test_battle_map_rules() -> None:
    _bad(_with_location(_small_map(), 1, battle_maps=[]), "至少要有 1 張")
    _bad(_with_location(_small_map(), 0, battle_maps=["swamp"]), "不可有戰鬥地圖")
    _bad(_with_location(_small_map(), 1, battle_maps=["swamp", "swamp"]), "重複")
    ok = _with_location(_small_map(), 1, kind="ruin", battle_maps=[])
    LocationMapDef.model_validate(ok)


def test_hidden_rules() -> None:
    _bad(_with_location(_small_map(), 14, kind="secret"), "必須是隱藏地點")
    _bad(_with_location(_small_map(), 14, hidden=True), "reveal")
    _bad(_with_location(_small_map(), 0, hidden=True, reveal=["situation"]), "不可隱藏")
    leaf = _with_location(_small_map(), 14, kind="secret", hidden=True, reveal=["situation"])
    LocationMapDef.model_validate(leaf)


def test_hint_only_for_hidden(cloud: LocationMapDef) -> None:
    """提示語只有隱藏地點可填（5B-5）；雲嶺兩個隱藏地點都有提示語。"""
    _bad(_with_location(_small_map(), 14, hint_zh="一條小路"), "hint_zh")
    hinted = _with_location(
        _small_map(), 14, kind="secret", hidden=True, reveal=["situation"], hint_zh="一條小路"
    )
    LocationMapDef.model_validate(hinted)
    assert all(loc.hint_zh for loc in cloud.locations if loc.hidden)


def test_gate_rules() -> None:
    gate: dict[str, Any] = {"kind": "gate", "level_min": None, "battle_maps": []}
    _bad(_with_location(_small_map(), 14, **gate), "gate_to")
    _bad(_with_location(_small_map(), 1, gate_to="ashen_waste"), "只有傳送點")
    _bad(_with_location(_small_map(), 14, **gate, gate_to="cloud_ridge"), "不可是本區")
    LocationMapDef.model_validate(_with_location(_small_map(), 14, **gate, gate_to="ashen_waste"))


def test_edge_rules() -> None:
    data = _small_map()
    _bad({**data, "edges": [*data["edges"], ["c1", "nowhere"]]}, "nowhere")
    _bad({**data, "edges": [*data["edges"], ["c1", "c1"]]}, "自己連自己")
    _bad({**data, "edges": [*data["edges"], ["c2", "c1"]]}, "重複")


def test_connectivity_rules() -> None:
    data = _small_map()
    _bad({**data, "edges": data["edges"][:-1]}, "走不到", "c14")
    # c5 隱藏，c6 之後只能經過 c5 才到 → 隱藏地點是唯一通路
    hidden_cut = _with_location(data, 5, kind="secret", hidden=True, reveal=["quest_clue"])
    _bad(hidden_cut, "唯一通路", "c6")
    # 加一條繞過 c5 的路就通過
    bypass = {**hidden_cut, "edges": [*hidden_cut["edges"], ["c4", "c6"]]}
    LocationMapDef.model_validate(bypass)


def test_bfs_independent_of_edge_order(cloud: LocationMapDef) -> None:
    data = cloud.model_dump()
    flipped = dict(data)
    flipped["edges"] = [(b, a) for a, b in reversed(data["edges"])]
    other = LocationMapDef.model_validate(flipped)
    for loc in cloud.locations:
        assert other.neighbors(loc.id) == cloud.neighbors(loc.id)
    # 隱藏地點的唯一通路檢查在反序後同樣成立
    cut = [e for e in data["edges"] if set(e) != {"north_slope", "crystal_rift"}]
    cut = [e for e in cut if set(e) != {"sword_tomb", "crystal_rift"}]
    cut.append(("crane_cliff", "crystal_rift"))
    for edges in (cut, list(reversed(cut))):
        with pytest.raises(ValidationError, match="唯一通路"):
            LocationMapDef.model_validate({**data, "edges": edges})


def test_loading_twice_is_identical(library: ContentLibrary) -> None:
    path = library.root / "world" / "maps" / "cloud_ridge.yaml"
    first = load_content_file(path, LocationMapDef)
    second = load_content_file(path, LocationMapDef)
    assert first.model_dump() == second.model_dump()


def test_location_def_alone() -> None:
    loc = LocationDef.model_validate(_loc("a", level_min=2))
    assert loc.level_max == 2


# ---- 跨檔案 ----


def test_cross_file_problems(library: ContentLibrary) -> None:
    data = _small_map()
    data = _with_location(data, 1, battle_maps=["nowhere_map"])
    data = _with_location(data, 2, battle_maps=["oil_depot"])
    data = _with_location(data, 3, battle_maps=["bandit_lair"])
    data = _with_location(
        data, 14, kind="gate", level_min=None, battle_maps=[], gate_to="no_region"
    )
    m = LocationMapDef.model_validate(data)
    problems = world_map_problems(m, regions=library.regions, maps=library.maps)
    assert problems == sorted(problems)
    text = "\n".join(problems)
    assert "未知的戰鬥地圖 nowhere_map" in text
    assert "oil_depot 不在本區地圖池內" in text
    assert "Boss 地圖 bandit_lair" in text
    assert "未知的區域 no_region" in text
    unknown_region = LocationMapDef.model_validate({**_small_map(), "region": "nowhere"})
    found = world_map_problems(unknown_region, regions=library.regions, maps=library.maps)
    assert any("未知的區域 nowhere" in p for p in found)
    assert world_map_problems(LocationMapDef.model_validate(_small_map()), regions=None, maps={})


def test_boss_map_allowed_on_boss_location(library: ContentLibrary) -> None:
    data = _with_location(_small_map(), 14, kind="boss", battle_maps=["bandit_lair"])
    m = LocationMapDef.model_validate(data)
    assert world_map_problems(m, regions=library.regions, maps=library.maps) == []


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def test_bad_file_raises_content_error(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "maps" / "cloud_ridge.yaml"
    text = path.read_text(encoding="utf-8").replace("[swamp]", "[oil_depot]")
    path.write_text(text, encoding="utf-8", newline="\n")
    with pytest.raises(ContentError, match="地圖池"):
        load_library(content)


def test_file_name_must_match_region(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    maps_dir = content / "world" / "maps"
    shutil.copy(maps_dir / "cloud_ridge.yaml", maps_dir / "zz_copy.yaml")
    with pytest.raises(ContentError, match="cloud_ridge"):
        load_library(content)


def test_without_world_folder(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    shutil.rmtree(content / "world")
    lib = load_library(content)
    assert lib.world_maps == {}
    assert set(lib.maps) == set(library.maps)


def test_world_map_listed_in_library_files(library: ContentLibrary) -> None:
    rel = [p.relative_to(library.root).as_posix() for p, _ in library.files]
    assert "world/maps/cloud_ridge.yaml" in rel
