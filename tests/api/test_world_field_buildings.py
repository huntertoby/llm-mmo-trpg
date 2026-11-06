"""實地地圖畫面帶出只畫的建築與家具外觀（Phase 6B-ART1）。"""

from __future__ import annotations

import pytest

from tests.world.helpers import hero
from trpg.api.world_field_view import _buildings, field_view
from trpg.content.library import ContentLibrary, load_library
from trpg.world.state import FieldPos, LocationRef
from trpg.world.step import new_character


@pytest.fixture(scope="module")
def real_library() -> ContentLibrary:
    """正式內容（`field_library` 的霧渡鎮是凍結複本，沒有建築）。"""
    return load_library()


def test_buildings_and_looks_in_view(real_library: ContentLibrary) -> None:
    field_library = real_library
    char = new_character(field_library, "alice", hero(field_library), region="cloud_ridge")
    view = field_view(field_library, char)
    assert view is not None and view.map_id == "mist_ferry"
    found = field_library.field_maps["mist_ferry"]
    assert [(b.kind, b.x, b.y, b.width, b.height) for b in view.buildings] == [
        (b.kind, b.at[0], b.at[1], b.size[0], b.size[1]) for b in found.buildings
    ]
    # 霧渡鎮的物件沒有家具外觀（6T-1b 起只有郵筒 postbox）
    assert [o.look for o in view.objects if o.look is not None] == ["postbox"]

    inside = char.model_copy(update={"field": FieldPos(map="mist_ferry_tavern", x=4, y=6)})
    room = field_view(field_library, inside)
    assert room is not None and room.buildings == ()
    tavern = field_library.field_maps["mist_ferry_tavern"]
    assert [(o.x, o.y, o.kind, o.look) for o in room.objects] == [
        (o.at[0], o.at[1], o.kind, o.look) for o in tavern.objects
    ]
    assert {o.look for o in room.objects} == {"bar", "table"}


def test_building_signs_follow_interior(real_library: ContentLibrary) -> None:
    """招牌照門通往的室內設施（6D-ART2；開發 PM 補充 2）：沒有門＝沒有招牌。"""
    lib = real_library
    char = new_character(lib, "alice", hero(lib), region="cloud_ridge")
    view = field_view(lib, char)
    assert view is not None and view.map_id == "mist_ferry"
    assert [b.sign for b in view.buildings] == ["jar", "anvil", None, None]

    def signs(map_id: str) -> list[tuple[str, str | None]]:
        return [(b.kind, b.sign) for b in _buildings(lib, char, lib.field_maps[map_id])]

    assert signs("mist_ferry") == [
        ("tavern", "jar"),
        ("smithy", "anvil"),
        ("hall", None),
        ("house", None),
    ]
    assert signs("ember_market") == [
        ("scrap_house", "jar"),
        ("forge_house", "anvil"),
        ("scrap_house", None),
        ("scrap_house", None),
    ]
    assert signs("capital") == [
        ("mentor_hall", "scroll"),
        ("stone_hall", "jar"),
        ("stone_hall", "anvil"),
        ("tent", None),
        ("tent", None),
        ("fountain", None),
    ]


def test_building_sign_skips_undiscovered_reveal_doors(real_library: ContentLibrary) -> None:
    """6R-P：還沒發現的隱藏門不給招牌（同 ``_doors`` 不顯示它）；發現後才有。"""
    lib = real_library
    char = new_character(lib, "alice", hero(lib), region="cloud_ridge")
    found = lib.field_maps["mist_ferry"]
    doors = tuple(
        d.model_copy(update={"hidden_until": "reveal"}) if d.id == "tavern_door" else d
        for d in found.doors
    )
    hidden = found.model_copy(update={"doors": doors})
    assert [b.sign for b in _buildings(lib, char, hidden)] == [None, "anvil", None, None]
    seen = char.model_copy(
        update={"revealed": (LocationRef(region="cloud_ridge", location="mist_ferry_tavern"),)}
    )
    assert [b.sign for b in _buildings(lib, seen, hidden)] == ["jar", "anvil", None, None]
