"""世界動作與世界事件（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.4）。

動作是玩家（經 API）送進來的意圖，進世界動作日誌（``trpg-wlog/1``）；事件是 :func:`world_step`
套用動作時產生的結果（給 API、說書人與前端看），可由日誌重播得到，不另外存。

5A-4 加上撤退、戰鬥（步驟寫進日誌，重播時重算勝負）、城鎮休息、換技能、傳送。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.content.world_map import RevealMethod
from trpg.engine.actions import Step
from trpg.world.encounters import EncounterLineup
from trpg.world.state import EncounterResult

__all__ = [
    "BattleEndedEvent",
    "BattleStartedEvent",
    "CampAction",
    "CampedEvent",
    "DefeatedEvent",
    "EncounterCheckEvent",
    "EncounterEvent",
    "FightAction",
    "LeveledUpEvent",
    "LoadoutAction",
    "LoadoutChangedEvent",
    "LocationClearedEvent",
    "LocationRevealedEvent",
    "PerceptionCheckEvent",
    "RestAction",
    "RestedEvent",
    "RetreatAction",
    "RetreatedEvent",
    "TeleportAction",
    "TeleportedEvent",
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


class RetreatAction(_Model):
    """看了陣容不打，退回出發地點（09 9.6.6：不開戰、不扣任何東西）。"""

    kind: Literal["retreat"] = "retreat"


class FightAction(_Model):
    """打這場遭遇：``steps`` 是整場戰鬥的步驟（動作與決定，同 ``BattleLog.actions``），套用後戰鬥
    必須已結束。重播時用同一份設定與種子重算勝負（第 2.4 節）。"""

    kind: Literal["fight"] = "fight"
    steps: tuple[Step, ...]


class RestAction(_Model):
    """在城鎮休息：HP、法力、耐力回滿，補給補到初值（09 9.6.7 #2、#11）。"""

    kind: Literal["rest"] = "rest"


class LoadoutAction(_Model):
    """換技能（城鎮或營火；07 7.6）：新的裝備清單，沒裝上的進備用。"""

    kind: Literal["loadout"] = "loadout"
    skills: tuple[str, ...]


class TeleportAction(_Model):
    """傳送到另一區的小鎮（09 9.6.2「城鎮之間用傳送點」）：從城鎮到去過的小鎮，或從傳送點到它通往
    的區域。"""

    kind: Literal["teleport"] = "teleport"
    region: str = Field(pattern=ID_PATTERN)


type WorldAction = Annotated[
    TravelAction
    | CampAction
    | RetreatAction
    | FightAction
    | RestAction
    | LoadoutAction
    | TeleportAction,
    Field(discriminator="kind"),
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


class CampedEvent(_Model):
    kind: Literal["camped"] = "camped"
    location: str
    supplies_left: int
    hp: int
    mana: int


class RetreatedEvent(_Model):
    kind: Literal["retreated"] = "retreated"
    from_location: str
    to: str


class BattleStartedEvent(_Model):
    """開戰：地圖（已換皮成 ``region``）、敵方陣容與等級、天氣、主角開場 HP。"""

    kind: Literal["battle_started"] = "battle_started"
    location: str
    battle_map: str
    region: str
    lineup: EncounterLineup
    enemy_level: int
    weather: str
    hero_hp: int
    fatigued: bool


class BattleEndedEvent(_Model):
    kind: Literal["battle_ended"] = "battle_ended"
    won: bool
    end_reason: str | None
    rounds: int
    hp: int
    mana: int
    xp_gained: int
    level: int


class LeveledUpEvent(_Model):
    kind: Literal["leveled_up"] = "leveled_up"
    level: int
    attribute_points: int
    """升到這級後未分配的屬性點總數。"""


class DefeatedEvent(_Model):
    """全滅（9.6.9 #98）：回小鎮、HP 回滿、下一場疲憊。"""

    kind: Literal["defeated"] = "defeated"
    location: str
    hp: int


class LocationClearedEvent(_Model):
    kind: Literal["location_cleared"] = "location_cleared"
    location: str
    respawn_at: int


class RestedEvent(_Model):
    kind: Literal["rested"] = "rested"
    location: str
    hp: int
    mana: int
    supplies: int


class LoadoutChangedEvent(_Model):
    kind: Literal["loadout_changed"] = "loadout_changed"
    skills: tuple[str, ...]
    bench: tuple[str, ...]


class TeleportedEvent(_Model):
    kind: Literal["teleported"] = "teleported"
    region: str
    location: str


type WorldEvent = Annotated[
    TraveledEvent
    | EncounterCheckEvent
    | EncounterEvent
    | PerceptionCheckEvent
    | LocationRevealedEvent
    | CampedEvent
    | RetreatedEvent
    | BattleStartedEvent
    | BattleEndedEvent
    | LeveledUpEvent
    | DefeatedEvent
    | LocationClearedEvent
    | RestedEvent
    | LoadoutChangedEvent
    | TeleportedEvent,
    Field(discriminator="kind"),
]
