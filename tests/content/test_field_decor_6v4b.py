"""實地地圖的 ``look.decor``（Phase 6V-4b，``docs/art/6V-3與6V-4檢查.md`` 2 第 3、4 點）。

只畫的裝飾：

- schema：種類、固定尺寸、放射狀鋪法的範圍與圓心；錯誤範例載入時報錯；
- 種類表標示站立／地面（堆箱、晾衣繩站立；花壇、攤布、鋪法在地面）；
- 主城的版面和 6V-4 寫在前端的 ``CAPITAL_DECOR`` 一樣（14 件＋鋪法）；其他地圖沒有裝飾；
- 整件要在地圖內、兩件不疊；規則雜湊（排除 ``look``）不變見 ``test_field_buildings``；
- API 的 ``FieldView.decor`` 照地圖檔給（含圖層）。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.world.helpers import hero
from trpg.api.world_field_view import field_view
from trpg.content.fields import (
    DECOR_FIXED_SIZE,
    DECOR_KINDS,
    DECOR_LAYERS,
    FieldDecor,
    FieldLook,
    FieldMapDef,
)
from trpg.content.library import ContentLibrary, load_library
from trpg.world.state import FieldPos
from trpg.world.step import new_character

CAPITAL_DECOR = [
    ("flower_bed", (12, 9)),
    ("flower_bed", (19, 9)),
    ("flower_bed", (12, 14)),
    ("flower_bed", (19, 14)),
    ("flower_bed", (13, 5)),
    ("flower_bed", (17, 5)),
    ("stall_cloth", (7, 14)),
    ("stall_cloth", (9, 15)),
    ("stall_cloth", (22, 15)),
    ("clothesline", (2, 7)),
    ("crate_stack", (24, 9)),
    ("crate_stack", (29, 13)),
    ("crate_stack", (11, 21)),
    ("crate_stack", (20, 21)),
]
"""6V-4 寫死在 ``client/src/render/plazaDecor.ts`` 的版面（搬進地圖檔之前）。"""


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_kinds_and_layers() -> None:
    assert DECOR_KINDS == (
        "flower_bed",
        "stall_cloth",
        "clothesline",
        "crate_stack",
        "radial_paving",
    )
    assert sorted(DECOR_LAYERS) == sorted(DECOR_KINDS)
    standing = sorted(k for k, v in DECOR_LAYERS.items() if v == "standing")
    assert standing == ["clothesline", "crate_stack"]
    assert FieldDecor(kind="crate_stack", at=(1, 2)).layer == "standing"
    assert FieldDecor(kind="flower_bed", at=(1, 2)).layer == "ground"


def test_schema_ok() -> None:
    assert FieldLook().decor == ()
    line = FieldDecor.model_validate({"kind": "clothesline", "at": [2, 7]})
    assert line.footprint == (3, 1) == DECOR_FIXED_SIZE["clothesline"]
    assert line.cells() == [(2, 7), (3, 7), (4, 7)]
    same = FieldDecor.model_validate({"kind": "clothesline", "at": [2, 7], "size": [3, 1]})
    assert same.footprint == (3, 1)
    pave = FieldDecor.model_validate(
        {"kind": "radial_paving", "at": [11, 9], "size": [10, 6], "center": [15, 11]}
    )
    assert pave.footprint == (10, 6) and len(pave.cells()) == 60


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "fountain_jet", "at": [1, 1]},  # 不認得的種類
        {"kind": "flower_bed", "at": [1, 1], "size": [2, 1]},  # 固定尺寸不符
        {"kind": "flower_bed", "at": [1, 1], "center": [1, 1]},  # 只有鋪法能填圓心
        {"kind": "radial_paving", "at": [1, 1], "size": [3, 3]},  # 鋪法缺圓心
        {"kind": "radial_paving", "at": [1, 1], "center": [2, 2]},  # 鋪法缺範圍
        {"kind": "radial_paving", "at": [1, 1], "size": [3, 3], "center": [9, 9]},  # 圓心不在範圍
        {"kind": "radial_paving", "at": [1, 1], "size": [0, 3], "center": [1, 1]},  # 範圍太小
        {"kind": "crate_stack", "at": [1, 1], "blocks": True},  # 未知欄位（不可擋路）
    ],
)
def test_schema_rejects(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        FieldDecor.model_validate(bad)


def _with_decor(field: FieldMapDef, decor: list[dict[str, Any]]) -> dict[str, Any]:
    data = field.model_dump(mode="json")
    data["look"]["decor"] = decor
    return data


def test_map_level_checks(library: ContentLibrary) -> None:
    capital = library.field_maps["capital"]
    ok = _with_decor(capital, [{"kind": "crate_stack", "at": [24, 9]}])
    assert FieldMapDef.model_validate(ok).look.decor[0].kind == "crate_stack"
    outside = _with_decor(capital, [{"kind": "clothesline", "at": [30, 7]}])  # 3 格寬超出右緣
    with pytest.raises(ValidationError, match="超出地圖範圍"):
        FieldMapDef.model_validate(outside)
    overlap = _with_decor(
        capital,
        [{"kind": "clothesline", "at": [2, 7]}, {"kind": "flower_bed", "at": [4, 7]}],
    )
    with pytest.raises(ValidationError, match="疊在"):
        FieldMapDef.model_validate(overlap)
    # 鋪法底下可以放地面的裝飾（花壇就在鋪法範圍內）
    under = _with_decor(
        capital,
        [
            {"kind": "radial_paving", "at": [11, 9], "size": [10, 6], "center": [15, 11]},
            {"kind": "flower_bed", "at": [12, 9]},
        ],
    )
    assert len(FieldMapDef.model_validate(under).look.decor) == 2


def test_capital_layout_moved_from_client(library: ContentLibrary) -> None:
    decor = library.field_maps["capital"].look.decor
    items = [(d.kind, d.at) for d in decor if d.kind != "radial_paving"]
    assert items == CAPITAL_DECOR
    paving = [d for d in decor if d.kind == "radial_paving"]
    assert len(paving) == 1
    assert (paving[0].at, paving[0].footprint, paving[0].center) == ((11, 9), (10, 6), (15, 11))
    # 鋪法的圓心是傳送石；範圍是四盞源晶燈圍起來的長方形
    capital = library.field_maps["capital"]
    assert capital.teleport_stones[0].at == (15, 11)
    lamps = sorted(o.at for o in capital.objects if o.look == "crystal_lamp")
    assert lamps == [(11, 9), (11, 14), (20, 9), (20, 14)]


def test_only_capital_has_decor(library: ContentLibrary) -> None:
    assert sorted(m for m, f in library.field_maps.items() if f.look.decor) == ["capital"]


def test_field_view_carries_decor(library: ContentLibrary) -> None:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    view = field_view(library, char)
    assert view is not None and view.decor == ()
    moved = char.model_copy(
        update={
            "region": "capital",
            "location": "capital",
            "field": FieldPos(map="capital", x=16, y=11),
        }
    )
    there = field_view(library, moved)
    assert there is not None and there.map_id == "capital"
    assert len(there.decor) == 15
    pave = there.decor[0]
    assert (pave.kind, pave.layer, pave.x, pave.y, pave.width, pave.height) == (
        "radial_paving",
        "ground",
        11,
        9,
        10,
        6,
    )
    assert (pave.center_x, pave.center_y) == (15, 11)
    line = next(d for d in there.decor if d.kind == "clothesline")
    assert (line.layer, line.width, line.height, line.center_x) == ("standing", 3, 1, None)
    assert {d.layer for d in there.decor if d.kind == "crate_stack"} == {"standing"}
    assert {d.layer for d in there.decor if d.kind in ("flower_bed", "stall_cloth")} == {"ground"}
