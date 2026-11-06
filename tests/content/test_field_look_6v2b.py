"""實地地圖的 ``look.chasm_style``（Phase 6V-2b，``docs/archive/art/6V-2檢查.md`` 2.2）：
只影響畫法。

- schema 只收 ``default``／``deep_water``，其他值、未知鍵載入時報錯；省略＝``default``；
- 只有灰渡口填 ``deep_water``，其他實地地圖照舊（其他荒原裂谷仍是黑色裂谷畫法）；
- 灰渡口的深淵格仍是 ``chasm``（致命）；規則雜湊（排除 ``look``）不變見 ``test_field_buildings``；
- API 的 ``FieldView.chasm_style`` 照地圖檔給。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.world.helpers import hero
from trpg.api.world_field_view import field_view
from trpg.content.fields import CHASM_STYLES, FieldLook
from trpg.content.library import ContentLibrary
from trpg.world.state import FieldPos
from trpg.world.step import new_character


def test_schema_values() -> None:
    assert CHASM_STYLES == ("default", "deep_water")
    assert FieldLook().chasm_style == "default"
    assert FieldLook.model_validate({"chasm_style": "deep_water"}).chasm_style == "deep_water"
    with pytest.raises(ValidationError):
        FieldLook.model_validate({"chasm_style": "lava_lake"})
    with pytest.raises(ValidationError):
        FieldLook.model_validate({"water_tint": "green"})


def test_only_ash_ferry_uses_deep_water(library: ContentLibrary) -> None:
    deep = sorted(m for m, f in library.field_maps.items() if f.look.chasm_style == "deep_water")
    assert deep == ["ash_ferry"]
    assert library.field_maps["cooling_well"].look.chasm_style == "default"


def test_ash_ferry_chasm_still_deadly(library: ContentLibrary) -> None:
    field = library.field_maps["ash_ferry"]
    assert field.legend["="] == "chasm"
    cells = sum(row.count("=") for row in field.terrain_rows())
    assert cells > 50  # 灰河那一大片仍是深淵格
    assert library.ruleset.terrain_def("chasm").deadly


def test_field_view_carries_chasm_style(library: ContentLibrary) -> None:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    view = field_view(library, char)
    assert view is not None and view.map_id == "mist_ferry" and view.chasm_style == "default"
    moved = char.model_copy(
        update={
            "region": "ashen_waste",
            "location": "ash_ferry",
            "field": FieldPos(map="ash_ferry", x=12, y=6),
        }
    )
    there = field_view(library, moved)
    assert there is not None and there.map_id == "ash_ferry"
    assert there.chasm_style == "deep_water"
