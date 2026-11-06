"""戰鬥流程事件（開戰、先攻、輪與回合、結束）。"""

from __future__ import annotations

from typing import Literal

from trpg.engine.events.base import EventBase
from trpg.shared.types import Team, UnitId

# ---------------------------------------------------------------------------
# 戰鬥流程
# ---------------------------------------------------------------------------


class BattleStarted(EventBase):
    type: Literal["battle_started"] = "battle_started"
    map_id: str
    seed: int


class InitiativeRolled(EventBase):
    type: Literal["initiative_rolled"] = "initiative_rolled"
    unit_id: UnitId
    roll: int
    modifier: int
    total: int


class InitiativeTieBroken(EventBase):
    """先攻總值與敏捷值都相同的一組單位，以戰鬥亂數決定的順序。"""

    type: Literal["initiative_tie_broken"] = "initiative_tie_broken"
    total: int
    dex: int
    order: tuple[UnitId, ...]


class TurnOrderSet(EventBase):
    type: Literal["turn_order_set"] = "turn_order_set"
    order: tuple[UnitId, ...]


class RoundStarted(EventBase):
    type: Literal["round_started"] = "round_started"


class RoundEnded(EventBase):
    type: Literal["round_ended"] = "round_ended"


class TurnStarted(EventBase):
    type: Literal["turn_started"] = "turn_started"
    unit_id: UnitId
    ap: int
    move_points: int
    mana: int = 0
    max_mana: int = 0
    stamina: int = 0
    max_stamina: int = 0
    stamina_gained: int = 0  # 這個回合開始回復的耐力（3H-5；0 ＝ 沒有回復或已滿）


class TurnSkipped(EventBase):
    """回合開始時因 ``skip_turn`` 狀態（暈眩）直接結束回合。"""

    type: Literal["turn_skipped"] = "turn_skipped"
    unit_id: UnitId
    status_id: str


class TurnEnded(EventBase):
    type: Literal["turn_ended"] = "turn_ended"
    unit_id: UnitId
    ap_carried: int


type EndReason = Literal[
    "eliminate",
    "round_limit",
    "escaped",
    "escape_failed",
    "defended",
    "point_lost",
    "leader_defeated",
]
"""``eliminate``：一方全滅；``escaped``：我方全員撤離；``escape_failed``：撤離超時；
``defended``：守點成功；``point_lost``：守點被占領；``round_limit``：輪數上限（平手）；
``leader_defeated``：Boss 戰頭目倒下、護衛撤退（我方勝，BAL-16a）。"""


class GuardsRetreated(EventBase):
    """Boss 戰頭目倒下（``leader_retreat``，BAL-16a／16b2，#86）：``leader_ids`` 的頭目全部倒下，
    ``unit_ids`` 的其餘敵人撤退（不算倒下、不給擊殺、不掉落）；緊接著是 ``battle_ended``
    （``leader_defeated``）。"""

    type: Literal["guards_retreated"] = "guards_retreated"
    leader_ids: tuple[UnitId, ...]
    unit_ids: tuple[UnitId, ...]


class BattleEnded(EventBase):
    type: Literal["battle_ended"] = "battle_ended"
    winner: Team | None
    reason: EndReason
