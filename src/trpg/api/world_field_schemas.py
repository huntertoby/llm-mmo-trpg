"""世界畫面的實地地圖（Phase 6B-2；``docs/phases/Phase6計畫.md`` 3.5）。

格式照戰鬥畫面的 ``TileView``／``ObjectView`` 的欄位名稱（``x``、``y``、``height``、``terrain``、
``surface``、``kind``），6B-3 可以直接組成 ``DrawModel``。隱藏的門（還沒發現）不給。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import DollLook
from trpg.content.races import RaceLook
from trpg.engine.view import AppearanceView

__all__ = [
    "FieldDoorView",
    "FieldExitView",
    "FieldFacilityView",
    "FieldGearLookView",
    "FieldHeroView",
    "FieldNpcView",
    "FieldObjectView",
    "FieldPositionView",
    "FieldStoneTargetView",
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
    walkable: bool = True
    """角色站得上去（6B-3 前端算路徑用；同 ``field_grid``：地形、物件、NPC、隱藏門）。"""


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


class FieldStoneTargetView(_ApiModel):
    """站在傳送石上時可以傳去的另一顆（已解鎖；6B-3 的「傳送」按鈕用）。"""

    id: str
    name_zh: str
    """傳送石所在地點的名稱。"""


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


class FieldGearLookView(_ApiModel):
    slot: str
    appearance: AppearanceView = AppearanceView()


class FieldHeroView(_ApiModel):
    """主角的紙娃娃外觀（6B-3；欄位同戰鬥的 ``UnitView``，純顯示）。"""

    template_id: str
    doll_look: DollLook | None = None
    weapon_id: str
    weapon_class: str
    race_look: RaceLook | None = None
    equipment: tuple[FieldGearLookView, ...] = ()


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
    max_climb: int = 1
    """一步最多往上爬幾層（``core.max_climb_height``；6B-3 前端算路徑用）。"""
    hero: FieldHeroView | None = None
    """主角外觀（6B-3）。"""
    stone_targets: tuple[FieldStoneTargetView, ...] = ()
    """站在傳送石上時：其他已解鎖的傳送石（依 ID 排序；沒站在傳送石上＝空）。"""
