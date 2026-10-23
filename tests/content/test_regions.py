"""區域主題（Phase 3-37a）：``regions.yaml``、地圖 ``region``／``look`` 的清理與戰場視圖。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef
from trpg.content.regions import RegionTable, sanitize_map_theme

_REGION_IDS = {"cloud_ridge", "crystal_crown", "arcane_hub", "ashen_waste", "frost_tide"}


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _map(library: ContentLibrary, **extra: object) -> MapDef:
    data = library.maps["open_plain"].model_dump()
    data.update(extra)
    return MapDef.model_validate(data)


def test_region_table_has_five_regions(library: ContentLibrary) -> None:
    assert library.regions is not None
    assert set(library.regions.region_by_id()) == _REGION_IDS
    assert library.regions.default_region == "crystal_crown"


def test_only_cloud_ridge_maps_have_a_theme(library: ContentLibrary) -> None:
    # 3-37b：玩法 PM 決定只把 bridge_chasm、dark_forest 標雲嶺；其他維持預設，look 不覆寫
    assert library.map_warnings == ()
    assert {k for k, m in library.maps.items() if m.region is not None} == {
        "bridge_chasm",
        "dark_forest",
    }
    assert {m.region for m in library.maps.values()} == {None, "cloud_ridge"}
    assert all(m.look == {} for m in library.maps.values())
    assert library.maps["bridge_chasm"].name_zh == "雲海吊橋"
    assert library.maps["dark_forest"].name_zh == "竹林"


def test_valid_theme_kept(library: ContentLibrary) -> None:
    assert library.regions is not None
    m = _map(library, region="cloud_ridge", look={"wall": "canyon_rock", "water_tint": "green"})
    out, warnings = sanitize_map_theme(m, library.regions)
    assert warnings == []
    assert out.region == "cloud_ridge"
    assert out.look == {"wall": "canyon_rock", "water_tint": "green"}


def test_unknown_values_dropped_with_warning(library: ContentLibrary) -> None:
    assert library.regions is not None
    m = _map(library, region="nowhere", look={"wall": "marble", "sky": "red", "floor": "paddy"})
    out, warnings = sanitize_map_theme(m, library.regions)
    assert out.region is None
    assert out.look == {"floor": "paddy"}
    assert len(warnings) == 3


def test_map_schema_accepts_any_theme_strings(library: ContentLibrary) -> None:
    m = _map(library, region="whatever", look={"x": "y"})
    assert m.region == "whatever"


def test_map_schema_rejects_bad_region_id(library: ContentLibrary) -> None:
    with pytest.raises(ValidationError):
        _map(library, region="Not Valid")


def test_table_validation() -> None:
    with pytest.raises(ValidationError):
        RegionTable.model_validate(
            {"default_region": "a", "regions": [{"id": "b", "name_zh": "乙"}]}
        )
    with pytest.raises(ValidationError):
        RegionTable.model_validate(
            {
                "default_region": "a",
                "regions": [{"id": "a", "name_zh": "甲", "look": {"wall": "x"}}],
                "look_keys": [{"key": "wall", "values": ["y"]}],
            }
        )


def test_battle_view_carries_theme(library: ContentLibrary) -> None:
    from tests.engine.helpers import make_state, spawn  # noqa: PLC0415
    from trpg.engine.view import project_for  # noqa: PLC0415
    from trpg.shared.types import Team  # noqa: PLC0415

    assert library.regions is not None
    base = _map(library, region="cloud_ridge", look={"floor": "paddy"})
    m, _ = sanitize_map_theme(base, library.regions)
    spawns = [spawn(Team.ALLY, (0, 3)), spawn(Team.ENEMY, (9, 6))]
    view = project_for(make_state(m, spawns), Team.ALLY)
    assert view.region == "cloud_ridge"
    assert view.look == {"floor": "paddy"}
    plain = project_for(make_state(library.maps["open_plain"], spawns), Team.ALLY)
    assert plain.region is None
    assert plain.look == {}


def test_load_library_survives_unknown_theme(tmp_path: Path, library: ContentLibrary) -> None:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    path = content / "maps" / "open_plain.yaml"
    extra = "\nregion: nowhere\nlook: {wall: marble, floor: paddy}\n"
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    lib = load_library(content)
    assert lib.maps["open_plain"].region is None
    assert lib.maps["open_plain"].look == {"floor": "paddy"}
    assert len(lib.map_warnings) == 2
