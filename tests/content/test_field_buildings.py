"""實地地圖的只畫欄位（Phase 6B-ART1）：``buildings`` 與物件的 ``look``。

- 建築只能疊在牆格或門格上，不可蓋到出口、超出地圖或彼此重疊；``look`` 只收認得的家具外觀；
- 內容：霧渡鎮 4 棟、餘燼集 4 棟，7 間室內的物件都有對應的 ``look``；
- **地圖格子完全不變**：拿掉 ``buildings`` 與 ``look`` 之後，9 張圖的內容雜湊和加欄位之前一樣
  （地形、高度、物件位置與種類、出口、門、NPC、設施…全部包含在內）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.fields import BUILDING_KINDS, OBJECT_LOOKS, FieldMapDef, field_map_report
from trpg.content.library import ContentLibrary, load_library

RULE_HASHES = {
    "mist_ferry": "a61d852dabbe372c",
    "ember_market": "09394be96fcc38a9",
    "mist_ferry_tavern": "ebd0fe8e191b16d6",
    "mist_ferry_smithy": "cc3547241585eae6",
    "ember_market_tavern": "3be107763b1f7474",
    "ember_market_smithy": "c04cf5a9f7359b39",
    "capital_tavern": "c8a479b818675a4f",
    "capital_smithy": "9e60faf83bb3ce70",
    "capital_mentor_hall": "b88e2811a2734684",
}
"""6B-ART1 加欄位之前（e8c6735b）的內容雜湊：排除 ``buildings`` 與物件 ``look`` 後的排序鍵 JSON。"""

INTERIORS = (
    "mist_ferry_tavern",
    "mist_ferry_smithy",
    "ember_market_tavern",
    "ember_market_smithy",
    "capital_tavern",
    "capital_smithy",
    "capital_mentor_hall",
)


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _rule_hash(field: FieldMapDef) -> str:
    data = field.model_dump(mode="json", exclude={"buildings"})
    for o in data["objects"]:
        o.pop("look", None)
    text = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@pytest.mark.parametrize("map_id", sorted(RULE_HASHES))
def test_rule_content_unchanged(library: ContentLibrary, map_id: str) -> None:
    assert _rule_hash(library.field_maps[map_id]) == RULE_HASHES[map_id]


def test_town_buildings(library: ContentLibrary) -> None:
    mist = library.field_maps["mist_ferry"]
    assert [b.kind for b in mist.buildings] == ["tavern", "smithy", "hall", "house"]
    ember = library.field_maps["ember_market"]
    assert sorted(b.kind for b in ember.buildings) == [
        "forge_house",
        "scrap_house",
        "scrap_house",
        "scrap_house",
    ]
    for field in (mist, ember):
        doors = {d.at for d in field.doors}
        covered = {c for b in field.buildings for c in b.cells()}
        assert doors <= covered  # 兩扇門都畫在建築正面
        assert all(b.kind in BUILDING_KINDS for b in field.buildings)


@pytest.mark.parametrize("map_id", INTERIORS)
def test_interior_looks(library: ContentLibrary, map_id: str) -> None:
    field = library.field_maps[map_id]
    looks = [o.look for o in field.objects if o.look is not None]
    assert looks, map_id
    assert all(look in OBJECT_LOOKS for look in looks)


def test_content_still_passes_report(library: ContentLibrary) -> None:
    report = field_map_report(
        library.field_maps,
        world_maps=library.world_maps,
        terrain=library.ruleset.terrain.by_id(),
        objects=library.ruleset.objects.by_id(),
        core=library.ruleset.core,
    )
    assert report.errors == ()
    assert not [w for w in report.warnings if "建築外觀" in w]


def _town(**extra: Any) -> dict[str, Any]:
    """6×6：上兩列是牆，(2, 1) 是門（石地），左邊有出口。"""
    return {
        "id": "t",
        "region": "cloud_ridge",
        "location": "mist_ferry",
        "size": [6, 6],
        "heights": "\n".join(["000000"] * 6),
        "terrain": "\n".join(["######", "##.###", "......", "......", "......", "......"]),
        "legend": {".": "stone", "#": "wall"},
        "entry": [3, 4],
        "exits": [{"id": "to_x", "at": [[0, 3]], "to": "x", "arrive": "to_t"}],
        "doors": [{"id": "d", "at": [2, 1], "to": "room"}],
        **extra,
    }


def test_building_on_walls_and_door_ok() -> None:
    field = FieldMapDef.model_validate(
        _town(buildings=[{"kind": "tavern", "at": [0, 0], "size": [6, 2]}])
    )
    assert field.buildings[0].cells()[0] == (0, 0)


@pytest.mark.parametrize(
    ("building", "message"),
    [
        ({"kind": "house", "at": [0, 0], "size": [6, 3]}, "不是牆也不是門"),
        ({"kind": "house", "at": [4, 0], "size": [3, 2]}, "超出地圖範圍"),
        ({"kind": "house", "at": [0, 0], "size": [0, 2]}, "至少 1×1"),
    ],
)
def test_building_problems(building: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        FieldMapDef.model_validate(_town(buildings=[building]))


def test_building_cannot_cover_exit() -> None:
    raw = _town(buildings=[{"kind": "house", "at": [0, 0], "size": [1, 4]}])
    raw["terrain"] = "\n".join(["######", "##.###", "#.....", "#.....", "......", "......"])
    with pytest.raises(ValidationError, match="蓋到出口"):
        FieldMapDef.model_validate(raw)


def test_buildings_cannot_overlap() -> None:
    raw = _town(
        buildings=[
            {"kind": "house", "at": [0, 0], "size": [3, 2]},
            {"kind": "house", "at": [2, 0], "size": [2, 1]},
        ]
    )
    with pytest.raises(ValidationError, match="重疊"):
        FieldMapDef.model_validate(raw)


def test_object_look_validated() -> None:
    ok = FieldMapDef.model_validate(
        _town(objects=[{"at": [4, 4], "kind": "crate", "look": "barrel"}])
    )
    assert ok.objects[0].look == "barrel"
    with pytest.raises(ValidationError):
        FieldMapDef.model_validate(
            _town(objects=[{"at": [4, 4], "kind": "crate", "look": "piano"}])
        )


def test_unknown_kind_is_warning(library: ContentLibrary) -> None:
    fields = dict(library.field_maps)
    raw = fields["mist_ferry"].model_dump(mode="json")
    raw["buildings"][3]["kind"] = "pagoda"
    fields["mist_ferry"] = FieldMapDef.model_validate(raw)
    report = field_map_report(
        fields,
        world_maps=library.world_maps,
        terrain=library.ruleset.terrain.by_id(),
        objects=library.ruleset.objects.by_id(),
        core=library.ruleset.core,
    )
    assert report.errors == ()
    assert any("pagoda" in w for w in report.warnings)
