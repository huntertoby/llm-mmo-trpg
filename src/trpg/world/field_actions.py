"""實地地圖上的世界動作與事件（Phase 6B-2；``docs/phases/Phase6計畫.md`` 第 3 節）。

- ``walk``：沿一串四方向相鄰的格子走（一次最多 :data:`WALK_MAX_STEPS` 格）；中途碰到出口、門、
  傳送石就停在那一格並觸發。走格子不花時間、補給，也不擲遇敵（21.10 第 2 條）。
- ``use_teleport_stone``：站在傳送石上，傳到另一顆已解鎖的傳送石（21.2）。

邏輯在 :mod:`trpg.world.field`。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.world.state import Facing

__all__ = [
    "WALK_MAX_STEPS",
    "FieldEnteredEvent",
    "TeleportStoneUnlockedEvent",
    "TeleportStoneUsedEvent",
    "UseTeleportStoneAction",
    "WalkAction",
    "WalkedEvent",
]

WALK_MAX_STEPS: Final = 30
"""一次 ``walk`` 最多幾格（第 3.2 節）。"""

type XY = tuple[int, int]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WalkAction(_Model):
    """沿 ``path`` 走：每一格都要和前一格（第一格和目前位置）四方向相鄰。日誌記整串路徑，重播逐格
    重算。"""

    kind: Literal["walk"] = "walk"
    path: tuple[XY, ...] = Field(min_length=1, max_length=WALK_MAX_STEPS)


class UseTeleportStoneAction(_Model):
    """站在傳送石上，傳到已解鎖的另一顆（``to`` 是傳送石 ID）。"""

    kind: Literal["use_teleport_stone"] = "use_teleport_stone"
    to: str = Field(pattern=ID_PATTERN)


type StopReason = Literal["end", "exit", "door", "stone"]
"""``walk`` 停下的原因：走完、踩到出口、門、傳送石。"""

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
