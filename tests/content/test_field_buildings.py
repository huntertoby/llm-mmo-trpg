"""實地地圖的只畫欄位（Phase 6B-ART1）：``buildings`` 與物件的 ``look``。

- 建築只能疊在牆格或門格上，不可蓋到出口、超出地圖或彼此重疊；``look`` 只收認得的家具外觀；
- 內容：霧渡鎮 4 棟、餘燼集 4 棟，7 間室內的物件都有對應的 ``look``；
- **地圖格子完全不變**：拿掉 ``buildings`` 與 ``look`` 之後，9 張圖的內容雜湊和加欄位之前一樣
  （地形、高度、物件位置與種類、出口、門、NPC、設施…全部包含在內）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from trpg.content.fields import (
    BUILDING_KINDS,
    OBJECT_LOOKS,
    FieldMapDef,
    ObjectLook,
    field_map_report,
)
from trpg.content.library import ContentLibrary

RULE_HASHES = {
    # 6F-4：導師堂門口加葛蘭（npcs）；6T-1b：郵筒（low_wall）與郵寄設施（post）
    "mist_ferry": "9d35c725cf53b2a5",
    "ember_market": "3b3fe40f486870ec",  # 6T-1b：郵筒（low_wall）與郵寄設施（post）
    "mist_ferry_tavern": "ebd0fe8e191b16d6",
    "mist_ferry_smithy": "cc3547241585eae6",
    "ember_market_tavern": "3be107763b1f7474",
    "ember_market_smithy": "c04cf5a9f7359b39",
    "capital_tavern": "c8a479b818675a4f",
    "capital_smithy": "9e60faf83bb3ce70",
    "capital_mentor_hall": "b88e2811a2734684",
    # RT-5b：守印人移到傳送石旁、南側兩座石碑對準浮橋；6T-1b：再加郵筒（low_wall）與郵寄設施（post）
    # PR-2a：靶場說明卡定稿句、工坊師傅 panel
    # WP-2：許願池、守池人加 panel: wish，說明句改寫
    "capital": "bb704ebd2231259b",  # TXT-2：許願池與守池人定稿字
    "ash_ferry": "ba92570cc37240f9",
}
"""加欄位之前的內容雜湊：排除 ``buildings``、物件 ``look`` 與情境物件 ``figure``（6V-1）後的排序鍵
JSON。前 9 張是 6B-ART1 之前（e8c6735b），主城是 6D-ART2 之前（31f1be3c）。"""

INTERIORS = (
    "mist_ferry_tavern",
    "mist_ferry_smithy",
    "ember_market_tavern",
    "ember_market_smithy",
    "capital_tavern",
    "capital_smithy",
    "capital_mentor_hall",
)


def _rule_hash(field: FieldMapDef) -> str:
    data = field.model_dump(mode="json", exclude={"buildings", "look"})  # 6V-2b：地圖 look 只畫
    for o in data["objects"]:
        o.pop("look", None)
    for key in ("campfires", "event_spots", "situation_objects", "facilities"):
        for s in data[key]:
            s.pop("figure", None)  # 6V-1／6V-3：站在情境物件、設施上的人只畫，不算規則
            s.pop("postman", None)  # 6T-1b：郵差的外觀照人設卡（只畫）
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


def test_object_looks_come_from_the_type() -> None:
    """6R-P：``OBJECT_LOOKS`` 由 ``ObjectLook`` 取出（不另寫一份），順序與不重複都照型別。"""
    assert get_args(ObjectLook.__value__) == OBJECT_LOOKS
    assert len(set(OBJECT_LOOKS)) == len(OBJECT_LOOKS) and "barrel" in OBJECT_LOOKS


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


# ---- 6D-ART2：主城建築與街景 ----


def test_capital_buildings_and_looks(library: ContentLibrary) -> None:
    capital = library.field_maps["capital"]
    assert [(b.kind, b.at, b.size) for b in capital.buildings] == [
        ("mentor_hall", (13, 1), (5, 4)),
        ("stone_hall", (2, 9), (4, 4)),
        ("stone_hall", (25, 10), (4, 3)),
        ("tent", (12, 19), (2, 2)),
        ("tent", (18, 19), (2, 2)),
        ("fountain", (4, 3), (2, 2)),
    ]
    assert all(b.kind in BUILDING_KINDS for b in capital.buildings)
    covered = {c for b in capital.buildings for c in b.cells()}
    assert {d.at for d in capital.doors} <= covered  # 三扇門都在建築範圍內
    looks: dict[str, list[tuple[int, int]]] = {}
    for o in capital.objects:
        if o.look is not None:
            looks.setdefault(o.look, []).append(o.at)
    assert len(looks["sky_bridge"]) == 10
    assert all(o.kind == "wooden_bridge" for o in capital.objects if o.look == "sky_bridge")
    assert sorted(looks["crystal_lamp"]) == [(11, 9), (11, 14), (20, 9), (20, 14)]
    steles = {s.at: s.stele_region for s in capital.situation_objects if s.stele_region}
    assert sorted(looks["stele"]) == sorted(steles)  # 五座橋頭石碑都有紋章的區域
    assert len(steles) == 5


def _pool(kind: str, *, water: bool = True) -> dict[str, Any]:
    raw = _town(buildings=[{"kind": kind, "at": [3, 3], "size": [2, 2]}])
    if water:
        cells = ((3, 3), (4, 3), (3, 4), (4, 4))
        raw["surfaces"] = [{"at": [x, y], "surface": "water"} for x, y in cells]
    return raw


def test_fountain_may_cover_water() -> None:
    field = FieldMapDef.model_validate(_pool("fountain"))
    assert field.buildings[0].kind == "fountain"


@pytest.mark.parametrize(("kind", "water"), [("fountain", False), ("stone_hall", True)])
def test_only_fountain_on_water(kind: str, water: bool) -> None:
    with pytest.raises(ValidationError, match="不是牆也不是門"):
        FieldMapDef.model_validate(_pool(kind, water=water))
