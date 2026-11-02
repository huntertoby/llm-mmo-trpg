"""世界動作與世界事件（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.4）。

動作是玩家（經 API）送進來的意圖，進世界動作日誌（``trpg-wlog/1``）；事件是 :func:`world_step`
套用動作時產生的結果（給 API、說書人與前端看），可由日誌重播得到，不另外存。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.content.world_map import RevealMethod
from trpg.world.state import EncounterResult, EventTrigger

__all__ = [
    "CampAction",
    "CampedEvent",
    "EncounterCheckEvent",
    "EncounterEvent",
    "EventCheckEvent",
    "EventLeftEvent",
    "EventTriggeredEvent",
    "LocationRevealedEvent",
    "PerceptionCheckEvent",
    "TravelAction",
    "TraveledEvent",
    "WorldAction",
    "WorldEvent",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


class TravelAction(_Model):
    """走到相鄰地點（09 9.6.7 #9）；``hasten``＝花補給趕路，降低遇敵機率。"""

    kind: Literal["travel"] = "travel"
    to: str = Field(pattern=ID_PATTERN)
    hasten: bool = False


class CampAction(_Model):
    """在目前地點紮營＝營火（09 9.6.11 #114）。"""

    kind: Literal["camp"] = "camp"


type WorldAction = Annotated[TravelAction | CampAction, Field(discriminator="kind")]


# ---------------------------------------------------------------------------
# 事件
# ---------------------------------------------------------------------------


class TraveledEvent(_Model):
    kind: Literal["traveled"] = "traveled"
    from_location: str
    to: str
    hasten: bool
    supplies_spent: int


class EncounterCheckEvent(_Model):
    """遇敵擲骰：``roll``（0～999）< ``chance_permille`` 即遇敵。"""

    kind: Literal["encounter_check"] = "encounter_check"
    location: str
    chance_permille: int
    roll: int
    encountered: bool


class EncounterEvent(_Model):
    kind: Literal["encounter"] = "encounter"
    result: EncounterResult


class PerceptionCheckEvent(_Model):
    """隱藏地點的感知判定：d20 ＋ ``modifier`` ≥ ``dc`` 即成功（#112）。"""

    kind: Literal["perception_check"] = "perception_check"
    location: str
    roll: int
    modifier: int
    dc: int
    success: bool


class LocationRevealedEvent(_Model):
    kind: Literal["location_revealed"] = "location_revealed"
    location: str
    method: RevealMethod


class EventCheckEvent(_Model):
    """事件擲骰（Phase 5B-1）：``roll``（0～999）< ``chance_permille`` 且這一步沒遇敵、有合格骨架
    才觸發。``steps`` 是含這一步、距離上次事件的步數。"""

    kind: Literal["event_check"] = "event_check"
    location: str
    steps: int
    chance_permille: int
    roll: int
    triggered: bool


class EventTriggeredEvent(_Model):
    kind: Literal["event_triggered"] = "event_triggered"
    trigger: EventTrigger


class EventLeftEvent(_Model):
    """離開地點時沒處理的事件作罷（Phase 5B-1 代決 5B1-4）。"""

    kind: Literal["event_left"] = "event_left"
    skeleton: str
    location: str


class CampedEvent(_Model):
    kind: Literal["camped"] = "camped"
    location: str
    supplies_left: int
    hp: int
    mana: int


type WorldEvent = Annotated[
    TraveledEvent
    | EncounterCheckEvent
    | EncounterEvent
    | PerceptionCheckEvent
    | LocationRevealedEvent
    | CampedEvent
    | EventCheckEvent
    | EventTriggeredEvent
    | EventLeftEvent,
    Field(discriminator="kind"),
]
