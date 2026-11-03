"""實地地圖（Phase 6B-1）：``world/fields/`` 的格式、單檔驗證與跨檔案驗證。

表格測試的底稿是內容庫裡的兩張草稿（霧渡鎮、渡口石階）加上兩張室內圖；需要隱藏地點、渡口、Boss
的情形另外用 :func:`_open_map` 拼一張空地圖。
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.fields import (
    FieldMapDef,
    FieldMapReport,
    field_map_problems,
    field_map_report,
    field_progress,
)
from trpg.content.library import ContentLibrary, load_library
from trpg.shared.errors import ContentError

type Raw = dict[str, dict[str, Any]]
type Mutate = Callable[[Raw], None]


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _raw(library: ContentLibrary) -> Raw:
    return {
        k: v.model_dump(mode="json", exclude_defaults=True) for k, v in library.field_maps.items()
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


def _open_map(
    map_id: str,
    location: str,
    *,
    exits: list[dict[str, Any]] | None = None,
    doors: list[dict[str, Any]] | None = None,
    size: tuple[int, int] = (20, 14),
    region: str = "cloud_ridge",
    **extra: Any,
) -> dict[str, Any]:
    """一張全是石地的地圖（入口在正中央）。"""
    w, h = size
    return {
        "id": map_id,
        "region": region,
        "location": location,
        "size": [w, h],
        "heights": "\n".join("0" * w for _ in range(h)),
        "terrain": "\n".join("." * w for _ in range(h)),
        "legend": {".": "stone"},
        "entry": [w // 2, h // 2],
        "exits": exits or [],
        "doors": doors or [],
        **extra,
    }


def _exit(
    exit_id: str, cell: tuple[int, int], to: str, arrive: str, **extra: Any
) -> dict[str, Any]:
    return {"id": exit_id, "at": [list(cell)], "to": to, "arrive": arrive, **extra}


def _herb_valley(door: dict[str, Any] | None = None) -> dict[str, Any]:
    """藥師谷：連到斷崖幫寨、雲海吊橋，和隱藏地點丹爐洞（用門）。"""
    door = door or {"id": "cave_mouth", "at": [5, 5], "to": "elixir_cave", "hidden_until": "reveal"}
    return _open_map(
        "herb_valley",
        "herb_valley",
        exits=[
            _exit("to_cliff_gang_fort", (0, 3), "cliff_gang_fort", "to_herb_valley"),
            _exit("to_cloud_sea_bridge", (19, 3), "cloud_sea_bridge", "to_herb_valley"),
        ],
        doors=[door],
    )


def _elixir_cave(arrive: str = "cave_mouth") -> dict[str, Any]:
    return _open_map(
        "elixir_cave",
        "elixir_cave",
        size=(16, 14),
        exits=[_exit("to_herb_valley", (0, 7), "herb_valley", arrive)],
    )


def _ashen_ferry(**exit_changes: Any) -> dict[str, Any]:
    """往灰燼荒原的渡口（路徑圖寫法）：西接霧渡鎮，東邊尾端出口進入荒原的灰渡口。"""
    cross = _exit("to_ash_ferry", (19, 6), "ash_ferry", "to_ashen_ferry", region="ashen_waste")
    cross.update(exit_changes)
    return _open_map(
        "ashen_ferry",
        "ashen_ferry",
        size=(20, 12),
        exits=[_exit("to_mist_ferry", (0, 6), "mist_ferry", "to_ashen_ferry"), cross],
    )


def _ash_ferry() -> dict[str, Any]:
    return _open_map(
        "ash_ferry",
        "ash_ferry",
        region="ashen_waste",
        size=(20, 12),
        exits=[
            _exit("to_ember_market", (19, 6), "ember_market", "to_ash_ferry"),
            _exit("to_ashen_ferry", (0, 6), "ashen_ferry", "to_ash_ferry", region="cloud_ridge"),
        ],
    )


def _exit_of(raw: Raw, map_id: str, exit_id: str) -> dict[str, Any]:
    return next(e for e in raw[map_id]["exits"] if e["id"] == exit_id)


# ---------------------------------------------------------------------------
# 內容庫
# ---------------------------------------------------------------------------


def test_the_library_loads_the_two_drafts_and_their_interiors(library: ContentLibrary) -> None:
    fields = library.field_maps
    assert sorted(fields) == [
        "ferry_steps",
        "mist_ferry",
        "mist_ferry_smithy",
        "mist_ferry_tavern",
    ]
    town = fields["mist_ferry"]
    assert town.size == (24, 18)
    assert {e.to for e in town.exits} == {"ferry_steps", "hunter_hut", "ashen_ferry"}
    assert {d.to for d in town.doors} == {"mist_ferry_tavern", "mist_ferry_smithy"}
    assert len(town.teleport_stones) == 1
    assert fields["ferry_steps"].size == (20, 12)
    for interior in ("mist_ferry_tavern", "mist_ferry_smithy"):
        assert fields[interior].size == (10, 8)
        assert fields[interior].interior_of == "mist_ferry"
    facilities = {f.id for f in fields["mist_ferry_smithy"].facilities}
    assert facilities == {"smithy", "enchanter"}


def test_the_drafts_pass_and_list_the_unpaired_ends_as_pending(library: ContentLibrary) -> None:
    report = _report(library, _raw(library))
    assert report.errors == ()
    pending = "\n".join(report.pending)
    assert "to_bamboo_path" in pending and "to_hunter_hut" in pending
    assert "to_ashen_ferry" in pending
    assert "to_ferry_steps" not in pending  # 霧渡鎮－渡口石階兩邊都畫了，已經配對
    assert library.field_pending == report.pending
    assert any("傳送石 1 個" in w for w in library.field_warnings)


def test_progress_counts_outdoor_maps_per_region(library: ContentLibrary) -> None:
    progress = field_progress(library.world_maps, library.field_maps)
    assert [(p.region, p.done, p.total) for p in progress] == [
        ("cloud_ridge", 2, 18),
        ("ashen_waste", 0, 18),
    ]


def test_field_maps_reuse_the_battle_map_grid_rules(library: ContentLibrary) -> None:
    """地形 ID、高低差和戰鬥地圖同一套（6C-2 要從實地地圖切出戰場）。"""
    steps = library.field_maps["ferry_steps"]
    terrain = library.ruleset.terrain.by_id()
    assert {tid for row in steps.grid() for _, tid in row} <= set(terrain)
    assert {h for row in steps.grid() for h, _ in row} == {0, 1, 2, 3}


# ---------------------------------------------------------------------------
# 單檔驗證（FieldMapDef）
# ---------------------------------------------------------------------------


def _town(library: ContentLibrary) -> dict[str, Any]:
    return _raw(library)["mist_ferry"]


_SINGLE_FILE_CASES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("size_mismatch", lambda d: d.update(size=[24, 17]), "terrain 應有 17 行"),
    ("row_too_short", lambda d: d.update(terrain=d["terrain"].replace(".", "", 1)), "第 0 行"),
    ("exit_not_on_edge", lambda d: d["exits"][0].update(at=[[11, 5]]), "不在地圖邊緣"),
    ("exit_out_of_bounds", lambda d: d["exits"][0].update(at=[[30, 0]]), "超出地圖範圍"),
    (
        "duplicate_portal_id",
        lambda d: d["doors"][0].update(id="to_hunter_hut"),
        "ID to_hunter_hut 重複",
    ),
    (
        "two_exits_to_one_place",
        lambda d: d["exits"][1].update(to="hunter_hut"),
        "往 cloud_ridge/hunter_hut 的出口重複",
    ),
    ("entry_on_door", lambda d: d.update(entry=[3, 5]), "都在 [3, 5]"),
    ("both_location_and_interior", lambda d: d.update(interior_of="mist_ferry"), "恰好填一個"),
    (
        "unknown_facility",
        lambda d: d["facilities"].append({"at": [1, 1], "id": "bank"}),
        "facilities",
    ),
    ("bad_hidden_until", lambda d: d["doors"][0].update(hidden_until="later"), "hidden_until"),
]


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [c[1:] for c in _SINGLE_FILE_CASES],
    ids=[c[0] for c in _SINGLE_FILE_CASES],
)
def test_single_file_errors_are_caught(
    library: ContentLibrary, mutate: Callable[[dict[str, Any]], None], fragment: str
) -> None:
    data = _town(library)
    mutate(data)
    with pytest.raises(ValidationError) as info:
        FieldMapDef.model_validate(data)
    assert fragment in str(info.value)


def test_interiors_need_an_exit_and_no_doors(library: ContentLibrary) -> None:
    tavern = _raw(library)["mist_ferry_tavern"]
    with pytest.raises(ValidationError, match="至少要有 1 個出口"):
        FieldMapDef.model_validate({**tavern, "exits": []})
    door = {"id": "cellar", "at": [2, 2], "to": "x"}
    with pytest.raises(ValidationError, match="不可有門或傳送石"):
        FieldMapDef.model_validate({**tavern, "doors": [door]})


# ---------------------------------------------------------------------------
# 跨檔案驗證（field_map_report）
# ---------------------------------------------------------------------------


def _drop_exit(map_id: str, exit_id: str) -> Mutate:
    def mutate(raw: Raw) -> None:
        raw[map_id]["exits"] = [e for e in raw[map_id]["exits"] if e["id"] != exit_id]

    return mutate


def _set_exit(map_id: str, exit_id: str, **changes: Any) -> Mutate:
    def mutate(raw: Raw) -> None:
        _exit_of(raw, map_id, exit_id).update(changes)

    return mutate


def _add(*maps: dict[str, Any]) -> Mutate:
    def mutate(raw: Raw) -> None:
        for m in maps:
            raw[m["id"]] = m

    return mutate


def _update(map_id: str, **changes: Any) -> Mutate:
    def mutate(raw: Raw) -> None:
        raw[map_id].update(changes)

    return mutate


def _append(map_id: str, key: str, item: dict[str, Any]) -> Mutate:
    def mutate(raw: Raw) -> None:
        raw[map_id].setdefault(key, []).append(item)

    return mutate


def _drop_map(raw: Raw, map_id: str) -> None:
    del raw[map_id]


def _block_stairs(raw: Raw) -> None:
    raw["ferry_steps"]["objects"] += [{"at": [10, y], "kind": "crate"} for y in range(6, 10)]


def _cloud_summit_with_stone(raw: Raw) -> None:
    raw["cloud_summit"] = _open_map(
        "cloud_summit",
        "cloud_summit",
        size=(12, 8),
        exits=[_exit("to_crystal_rift", (0, 4), "crystal_rift", "to_cloud_summit")],
        teleport_stones=[{"id": "stone_summit", "at": [2, 2]}],
    )


_REPORT_ERROR_CASES: list[tuple[str, Mutate, str]] = [
    # 一條連線＝一對出口
    ("missing_pair", _drop_exit("mist_ferry", "to_ferry_steps"), "缺少往 ferry_steps 的出口"),
    (
        "arrive_points_elsewhere",
        _set_exit("ferry_steps", "to_mist_ferry", arrive="to_hunter_hut"),
        "arrive 不互指",
    ),
    (
        "arrive_unknown",
        _set_exit("ferry_steps", "to_mist_ferry", arrive="to_nowhere"),
        "arrive to_nowhere 不是 mist_ferry 的出口或門",
    ),
    (
        "arrive_not_mutual",
        _set_exit("mist_ferry", "to_ferry_steps", arrive="to_bamboo_path"),
        "arrive 不互指",
    ),
    (
        "exit_without_edge",
        _set_exit("ferry_steps", "to_bamboo_path", to="rain_terraces"),
        "沒有 ferry_steps–rain_terraces 的連線",
    ),
    (
        "exit_to_unknown_place",
        _set_exit("ferry_steps", "to_bamboo_path", to="nowhere"),
        "沒有地點 nowhere",
    ),
    # 走得到、站得上
    ("unreachable_exit", _block_stairs, "從 entry 走不到出口 to_bamboo_path"),
    ("exit_on_a_wall", _set_exit("ferry_steps", "to_bamboo_path", at=[[0, 0]]), "不可站立"),
    ("npc_walled_in", _append("mist_ferry", "npcs", {"at": [3, 3], "id": "smith_shi"}), "不可站立"),
    # ID
    (
        "unknown_terrain",
        _update(
            "ferry_steps",
            legend={".": "stone", '"': "grass", ",": "dirt", "#": "wall", "=": "lava_pool"},
        ),
        "未知的地形：lava_pool",
    ),
    (
        "unknown_object",
        _append("ferry_steps", "objects", {"at": [3, 8], "kind": "no_such_object"}),
        "未知的物件：no_such_object",
    ),
    (
        "unknown_npc",
        _append("mist_ferry", "npcs", {"at": [20, 9], "id": "nobody"}),
        "NPC nobody 不是 cloud_ridge",
    ),
    (
        "npc_elsewhere",
        _append("mist_ferry", "npcs", {"at": [20, 9], "id": "daoist_qingya"}),
        "人設卡在 mist_temple_gate",
    ),
    ("unknown_location", _update("ferry_steps", location="nowhere"), "沒有地點 nowhere"),
    ("unknown_region", _update("ferry_steps", region="nowhere"), "未知的區域 nowhere"),
    (
        "same_location_twice",
        _add({**_open_map("ferry_steps_b", "ferry_steps")}),
        "地點 ferry_steps 已有實地地圖 ferry_steps",
    ),
    # 門與室內圖
    (
        "door_to_nothing",
        lambda raw: raw["mist_ferry"]["doors"][0].update(to="no_room"),
        "不是本地點的室內圖",
    ),
    (
        "door_to_a_normal_place",
        lambda raw: raw["mist_ferry"]["doors"][0].update(to="ferry_steps"),
        "不是隱藏地點",
    ),
    (
        "interior_exit_wrong_door",
        _set_exit("mist_ferry_tavern", "to_mist_ferry", arrive="smithy_door"),
        "不是 mist_ferry 上通往這裡的門",
    ),
    (
        "interior_without_parent",
        lambda raw: _drop_map(raw, "mist_ferry"),
        "所屬的地點 mist_ferry 還沒有實地地圖",
    ),
    # 隱藏地點（21.6）
    (
        "hidden_entrance_without_hidden_until",
        _add(_herb_valley({"id": "cave_mouth", "at": [5, 5], "to": "elixir_cave"})),
        "要寫 hidden_until: reveal",
    ),
    (
        "hidden_entrance_missing",
        _add({**_herb_valley(), "doors": []}),
        "缺少往隱藏地點 elixir_cave 的門",
    ),
    (
        "hidden_place_through_an_exit",
        _add(
            {
                **_herb_valley(),
                "doors": [],
                "exits": [
                    *_herb_valley()["exits"],
                    _exit("to_elixir_cave", (10, 13), "elixir_cave", "to_herb_valley"),
                ],
            }
        ),
        "入口要用 doors",
    ),
    (
        "hidden_side_arrive_mismatch",
        _add(_herb_valley(), _elixir_cave(arrive="other")),
        "arrive other 不是 herb_valley 的出口或門",
    ),
    # 渡口（Q2）與 Boss
    (
        "ferry_map_without_crossing",
        _add({**_ashen_ferry(), "exits": _ashen_ferry()["exits"][:1]}),
        "渡口圖要有通往區域 ashen_waste",
    ),
    (
        "crossing_from_a_normal_place",
        _append(
            "ferry_steps",
            "exits",
            _exit("to_x", (19, 6), "ash_ferry", "to_y", region="ashen_waste"),
        ),
        "只有通往 ashen_waste 的渡口",
    ),
    (
        "crossing_to_unknown_place",
        _add(_ashen_ferry(to="nowhere")),
        "區域 ashen_waste 沒有地點 nowhere",
    ),
    ("boss_with_teleport_stone", _cloud_summit_with_stone, "不可有傳送石"),
]


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [c[1:] for c in _REPORT_ERROR_CASES],
    ids=[c[0] for c in _REPORT_ERROR_CASES],
)
def test_cross_file_errors_are_caught(
    library: ContentLibrary, mutate: Mutate, fragment: str
) -> None:
    raw = _raw(library)
    mutate(raw)
    errors = _report(library, raw).errors
    assert any(fragment in e for e in errors), errors


_REPORT_OK_CASES: list[tuple[str, Mutate]] = [
    ("hidden_place_paired", _add(_herb_valley(), _elixir_cave())),
    ("ferry_as_a_path_map", _add(_ashen_ferry())),
    ("ferry_path_map_paired_across_regions", _add(_ashen_ferry(), _ash_ferry())),
    (
        "ferry_as_just_an_exit",
        _set_exit("mist_ferry", "to_ashen_ferry", to="ash_ferry", region="ashen_waste"),
    ),
]


@pytest.mark.parametrize(
    "mutate", [c[1] for c in _REPORT_OK_CASES], ids=[c[0] for c in _REPORT_OK_CASES]
)
def test_valid_variants_pass(library: ContentLibrary, mutate: Mutate) -> None:
    raw = _raw(library)
    mutate(raw)
    assert _report(library, raw).errors == ()


def test_pairing_across_regions_clears_the_pending_entry(library: ContentLibrary) -> None:
    raw = _raw(library)
    _add(_ashen_ferry(), _ash_ferry())(raw)
    pending = "\n".join(_report(library, raw).pending)
    assert "to_ashen_ferry" not in pending  # 霧渡鎮－渡口、渡口－灰渡口都配對了
    assert "to_ember_market" in pending  # 餘燼集還沒畫


def test_hidden_door_waits_for_the_hidden_map(library: ContentLibrary) -> None:
    raw = _raw(library)
    _add(_herb_valley())(raw)
    report = _report(library, raw)
    assert report.errors == ()
    assert any("cave_mouth" in p for p in report.pending)


def test_size_and_stone_counts_are_only_warnings(library: ContentLibrary) -> None:
    raw = _raw(library)
    _add(_open_map("hunter_hut", "hunter_hut", size=(40, 30)))(raw)
    raw["hunter_hut"]["exits"] = [
        _exit("to_mist_ferry", (20, 29), "mist_ferry", "to_hunter_hut"),
        _exit("to_bamboo_path", (39, 10), "bamboo_path", "to_hunter_hut"),
        _exit("to_winter_lake", (20, 0), "winter_lake", "to_hunter_hut"),
    ]
    raw["mist_ferry"]["teleport_stones"] = []
    report = _report(library, raw)
    assert report.errors == ()
    text = "\n".join(report.warnings)
    assert "hunter_hut：40×30 不在 site 的建議範圍" in text
    assert "城鎮應有 1 個傳送石，目前 0 個" in text
    assert "傳送石 0 個" in text


def test_field_map_problems_is_the_error_list(library: ContentLibrary) -> None:
    raw = _raw(library)
    _drop_exit("mist_ferry", "to_ferry_steps")(raw)
    fields = {k: FieldMapDef.model_validate(v) for k, v in raw.items()}
    problems = field_map_problems(
        fields,
        world_maps=library.world_maps,
        terrain=library.ruleset.terrain.by_id(),
        objects=library.ruleset.objects.by_id(),
        core=library.ruleset.core,
    )
    assert problems == list(_report(library, raw).errors)


# ---------------------------------------------------------------------------
# 載入（資料夾與檔名）
# ---------------------------------------------------------------------------


def _copy_content(library: ContentLibrary, tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(library.root, root)
    return root


def test_loading_rejects_a_misplaced_file_and_cross_file_errors(
    library: ContentLibrary, tmp_path: Path
) -> None:
    root = _copy_content(library, tmp_path)
    fields = root / "world" / "fields" / "cloud_ridge"
    steps = fields / "ferry_steps.yaml"
    moved = fields / "steps.yaml"
    steps.rename(moved)
    with pytest.raises(ContentError, match="室外圖的檔名＝location"):
        load_library(root)
    moved.rename(steps)
    text = steps.read_text(encoding="utf-8").replace("arrive: to_ferry_steps}", "arrive: nope}", 1)
    steps.write_text(text, encoding="utf-8")
    with pytest.raises(ContentError, match="arrive nope"):
        load_library(root)
