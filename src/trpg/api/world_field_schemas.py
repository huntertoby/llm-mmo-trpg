"""世界畫面的實地地圖（Phase 6B-2；``docs/phases/Phase6計畫.md`` 3.5）。

格式照戰鬥畫面的 ``TileView``／``ObjectView`` 的欄位名稱（``x``、``y``、``height``、``terrain``、
``surface``、``kind``），6B-3 可以直接組成 ``DrawModel``。隱藏的門（還沒發現）不給。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = [
    "FieldDoorView",
    "FieldExitView",
    "FieldFacilityView",
    "FieldNpcView",
    "FieldObjectView",
    "FieldPositionView",
    "FieldStoneView",
    "FieldTileView",
    "FieldView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FieldTileView(_ApiModel):
    x: int
    y: int
    height: int
    terrain: str
    surface: str = "none"
    """初始表面（``water``、``fire``…；沒有＝``none``）。"""


class FieldObjectView(_ApiModel):
    id: str
    """``o<x>_<y>``（一格最多一個物件）。"""
    kind: str
    x: int
    y: int


class FieldExitView(_ApiModel):
    id: str
    cells: tuple[tuple[int, int], ...]
    to: str
    to_name_zh: str
    """目的地點的名稱（室內圖的出口＝所屬地點）。"""


class FieldDoorView(_ApiModel):
    id: str
    x: int
    y: int
    to: str
    to_name_zh: str
    """室內圖的名稱，或隱藏地點的名稱。"""


class FieldStoneView(_ApiModel):
    id: str
    x: int
    y: int
    unlocked: bool


class FieldNpcView(_ApiModel):
    id: str
    name_zh: str
    x: int
    y: int


class FieldFacilityView(_ApiModel):
    kind: str
    """``shop``、``smithy``、``tavern``、``mentor``、``notice_board``、``hire``、``enchanter``。"""
    x: int
    y: int


class FieldPositionView(_ApiModel):
    x: int
    y: int
    facing: Literal["n", "e", "s", "w"]


class FieldView(_ApiModel):
    map_id: str
    name_zh: str
    region: str
    location: str
    interior: bool
    width: int
    height: int
    tiles: tuple[FieldTileView, ...]
    """逐列（y 由上到下、x 由左到右）。"""
    objects: tuple[FieldObjectView, ...]
    exits: tuple[FieldExitView, ...]
    doors: tuple[FieldDoorView, ...]
    stones: tuple[FieldStoneView, ...]
    npcs: tuple[FieldNpcView, ...]
    facilities: tuple[FieldFacilityView, ...]
    me: FieldPositionView
    """自己的位置與朝向。"""
