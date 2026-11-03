"""實地地圖上的世界動作與事件（Phase 6B-2；``docs/phases/Phase6計畫.md`` 第 3 節）。

- ``walk``：沿一串四方向相鄰的格子走（一次最多規則 ``field.walk_max_steps`` 格，30）；中途碰到
  出口、門、傳送石就停在那一格並觸發。走格子不花時間、補給，也不擲遇敵（21.10 第 2 條）。
- ``use_teleport_stone``：站在傳送石上，傳到另一顆已解鎖的傳送石（21.2）。
- ``sneak``、``use_field_object``（6C-5）：潛行、點情境物件（:mod:`trpg.world.field_things`）。

邏輯在 :mod:`trpg.world.field`。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.world.state import Facing

__all__ = [
    "WALK_PATH_CAP",
    "EventMarkedEvent",
    "FieldEnteredEvent",
    "FieldObjectUsedEvent",
    "SneakAction",
    "SneakStartedEvent",
    "TeleportStoneUnlockedEvent",
    "TeleportStoneUsedEvent",
    "UseFieldObjectAction",
    "UseTeleportStoneAction",
    "WalkAction",
    "WalkedEvent",
]

type XY = tuple[int, int]

WALK_PATH_CAP: Final = 30
"""``walk`` 請求格式的路徑長度上限（6C-R2：規則數值改在 ``rules.yaml`` 的 ``field.walk_max_steps``，
不得超過這個值；要放寬時同時改這裡並重產 OpenAPI 與前端型別）。"""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WalkAction(_Model):
    """沿 ``path`` 走：每一格都要和前一格（第一格和目前位置）四方向相鄰。日誌記整串路徑，重播逐格
    重算。"""

    kind: Literal["walk"] = "walk"
    # 一次最多幾格照規則 field.walk_max_steps（6C-R2；trpg.world.field.walk 檢查）；這裡的上限只是
    # 請求格式（WALK_PATH_CAP；docstring 會進 OpenAPI 快照，所以說明寫在註解）。
    path: tuple[XY, ...] = Field(min_length=1, max_length=WALK_PATH_CAP)


class UseTeleportStoneAction(_Model):
    """站在傳送石上，傳到已解鎖的另一顆（``to`` 是傳送石 ID）。"""

    kind: Literal["use_teleport_stone"] = "use_teleport_stone"
    to: str = Field(pattern=ID_PATTERN)


type StopReason = Literal["end", "exit", "door", "stone", "enemy", "event"]
"""``walk`` 停下的原因：走完、踩到出口、門、傳送石、碰到敵人（6C-1：走進視野或相鄰）、碰到地圖上
的事件「！」（6C-5：站上或四方向相鄰）。"""

type EnterVia = Literal["exit", "door", "teleport_stone"]


class WalkedEvent(_Model):
    """走了幾格（``steps`` 是實際走過的格子，不含起點）。"""

    kind: Literal["walked"] = "walked"
    map: str
    steps: tuple[XY, ...]
    x: int
    y: int
    facing: Facing
    stopped: StopReason


class FieldEnteredEvent(_Model):
    """換到另一張實地地圖或室內圖（``map`` 是 ``None``＝目的地點還沒有實地地圖）。"""

    kind: Literal["field_entered"] = "field_entered"
    map: str | None
    location: str
    x: int | None = None
    y: int | None = None
    via: EnterVia


class TeleportStoneUnlockedEvent(_Model):
    kind: Literal["teleport_stone_unlocked"] = "teleport_stone_unlocked"
    stone: str


class TeleportStoneUsedEvent(_Model):
    kind: Literal["teleport_stone_used"] = "teleport_stone_used"
    from_stone: str
    to_stone: str
    region: str
    location: str


# ---------------------------------------------------------------------------
# 6C-5 地圖上的東西（邏輯在 trpg.world.field_things）
# ---------------------------------------------------------------------------


class SneakAction(_Model):
    """潛行（Q7，21.4「取代趕路」）：花 ``hasten.cost`` 補給，到進入下一張地圖為止敵人視野減半。"""

    kind: Literal["sneak"] = "sneak"


class UseFieldObjectAction(_Model):
    """點了站在旁邊的情境物件（``situation_objects`` 的 ``id``；21.6「走到旁邊點了就開」）。"""

    kind: Literal["use_field_object"] = "use_field_object"
    object: str = Field(pattern=ID_PATTERN)


class SneakStartedEvent(_Model):
    kind: Literal["sneak_started"] = "sneak_started"
    supplies_spent: int
    supplies_left: int


class EventMarkedEvent(_Model):
    """進入地圖時擲出的事件放在事件點上（地圖上的「！」，21.6）；碰到才開事件卡。"""

    kind: Literal["event_marked"] = "event_marked"
    location: str
    map: str
    x: int
    y: int
    spot: str


class FieldObjectUsedEvent(_Model):
    kind: Literal["field_object_used"] = "field_object_used"
    map: str
    object: str
    use: Literal["event", "encounter"]
