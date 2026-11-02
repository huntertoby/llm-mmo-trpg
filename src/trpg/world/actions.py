"""世界動作與世界事件（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.4）。

動作是玩家（經 API）送進來的意圖，進世界動作日誌（``trpg-wlog/1``）；事件是 :func:`world_step`
套用動作時產生的結果（給 API、說書人與前端看），可由日誌重播得到，不另外存。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.content.world_events import ThreadScope
from trpg.content.world_map import RevealMethod
from trpg.content.world_situations import (
    PLAYER_TEXT_LIMIT,
    CareItem,
    Outcome,
    SituationProposal,
)
from trpg.shared.types import Attribute
from trpg.world.state import EncounterResult, EventTrigger, NextBattleMod

__all__ = [
    "CampAction",
    "CampedEvent",
    "CareResult",
    "EncounterCheckEvent",
    "EncounterEvent",
    "EventCheckEvent",
    "EventLeftEvent",
    "EventResolvedEvent",
    "EventTriggeredEvent",
    "LocationRevealedEvent",
    "PerceptionCheckEvent",
    "SituationAction",
    "SituationCheckEvent",
    "SituationResultEvent",
    "ThreadAddedEvent",
    "ThreadPushedOutEvent",
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


class SituationAction(_Model):
    """對目前的事件做情境判定（Phase 5B-2；09 9.6.4）。

    ``proposal`` 是 LLM（或降級）提議、已經過 pydantic 驗證；引擎另外檢查合法性。提議、來源、
    prompt 版本與玩家原文都隨動作進世界動作日誌，重播照紀錄、不再呼叫 LLM（10 第 10 節）。
    ``player_text`` 只是紀錄（引擎不讀內容；給 LLM 時包在 ``<player_input>``）。
    """

    kind: Literal["situation"] = "situation"
    template: str = Field(pattern=ID_PATTERN)
    player_text: str = Field(default="", max_length=PLAYER_TEXT_LIMIT)
    proposal: SituationProposal
    source: Literal["llm", "fallback"] = "fallback"
    """``llm``＝LLM 的提議；``fallback``＝模型不可用或提議一直不合法時的降級提議。"""
    prompt_version: str | None = Field(default=None, max_length=64)


type WorldAction = Annotated[
    TravelAction | CampAction | SituationAction, Field(discriminator="kind")
]


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


class CareResult(_Model):
    """用心清單一筆的核對結果（核對不到「不算」，不是錯誤）。"""

    item: CareItem
    fact: str
    counted: bool
    reason_zh: str = ""
    """不算的原因（算的時候空字串）。"""


class SituationCheckEvent(_Model):
    """情境判定的擲骰明細（Phase 5B-2）。總值 ＝ ``roll`` ＋ 屬性修正 ＋ 用心加值 ＋ 種族加值。"""

    kind: Literal["situation_check"] = "situation_check"
    template: str
    skeleton: str
    attribute: Attribute
    method: str
    base_dc: int
    dc_shift: int
    dc: int
    dice: tuple[int, int]
    """一律擲兩顆 d20（亂數消耗固定）。"""
    mode: Literal["normal", "advantage", "disadvantage"]
    roll: int
    """採用的骰值（一般＝第一顆、優勢取高、劣勢取低）。"""
    attribute_mod: int
    care: tuple[CareResult, ...]
    care_bonus: int
    race_bonus: int
    total: int
    outcome: Outcome
    source: Literal["llm", "fallback"]


class SituationResultEvent(_Model):
    """情境判定的獎懲（照模板的表與預算；Phase 5B-2）。"""

    kind: Literal["situation_result"] = "situation_result"
    template: str
    outcome: Outcome
    xp: int
    supplies_delta: int
    """補給的淨變化（含用心清單 ③ 拿出來的補給）。"""
    hp_lost: int
    next_battle: tuple[NextBattleMod, ...]
    """這次新增的下一場戰鬥修正。"""


class ThreadAddedEvent(_Model):
    kind: Literal["thread_added"] = "thread_added"
    thread: str
    scope: ThreadScope
    expires_at: int


class ThreadPushedOutEvent(_Model):
    """線頭滿了，最舊的被擠掉（提前結束）。"""

    kind: Literal["thread_pushed_out"] = "thread_pushed_out"
    thread: str
    scope: ThreadScope


class EventResolvedEvent(_Model):
    """事件以某個解法結束（Phase 5B-2：情境判定）。"""

    kind: Literal["event_resolved"] = "event_resolved"
    skeleton: str
    location: str
    solution: int
    """骨架 ``solutions`` 的索引。"""
    outcome: Outcome


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
    | EventLeftEvent
    | SituationCheckEvent
    | SituationResultEvent
    | ThreadAddedEvent
    | ThreadPushedOutEvent
    | EventResolvedEvent,
    Field(discriminator="kind"),
]
