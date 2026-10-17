"""戰鬥事件（pydantic discriminated union，以 ``type`` 區分）。

- 事件只描述 **發生了什麼**，不含任何顯示文字；繁體中文紀錄由 ``trpg.cli`` 的渲染器產生。
- 每個事件帶 ``seq``（整場戰鬥遞增，從 0 開始）與 ``round``（發生時的輪數）。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.shared.types import Element, Pos, Team, UnitId

__all__ = [
    "EVENT_ADAPTER",
    "EVENT_LIST_ADAPTER",
    "AdvantageState",
    "AttackRolled",
    "BattleEnded",
    "BattleStarted",
    "ChainLimitReached",
    "DamageCause",
    "DamageDealt",
    "EnteredDeadlyTerrain",
    "Event",
    "EventBase",
    "Healed",
    "InitiativeRolled",
    "MoveBlocked",
    "MoveMode",
    "RoundEnded",
    "RoundStarted",
    "StatusApplied",
    "StatusRemoved",
    "TurnEnded",
    "TurnOrderSet",
    "TurnStarted",
    "UnitDowned",
    "UnitFell",
    "UnitMoved",
    "UnitStoodUp",
]

type AdvantageState = Literal["none", "advantage", "disadvantage"]
type DamageCause = Literal["attack", "fall", "deadly_terrain", "status", "effect"]
type MoveMode = Literal["walk", "forced", "teleport"]
"""``walk``：主動移動的一步；``forced``：強制位移（推擊等）；``teleport``：傳送（不墜落）。"""


class EventBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seq: int = Field(ge=0)
    round: int = Field(ge=1)


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


class TurnEnded(EventBase):
    type: Literal["turn_ended"] = "turn_ended"
    unit_id: UnitId
    ap_carried: int


class BattleEnded(EventBase):
    type: Literal["battle_ended"] = "battle_ended"
    winner: Team | None
    reason: Literal["eliminate", "round_limit"]


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------


class UnitMoved(EventBase):
    type: Literal["unit_moved"] = "unit_moved"
    unit_id: UnitId
    from_pos: Pos
    to_pos: Pos
    mode: MoveMode
    cost: int


class UnitStoodUp(EventBase):
    type: Literal["unit_stood_up"] = "unit_stood_up"
    unit_id: UnitId
    cost: int


class MoveBlocked(EventBase):
    type: Literal["move_blocked"] = "move_blocked"
    unit_id: UnitId
    to_pos: Pos
    reason: Literal["out_of_bounds", "occupied"]


class UnitFell(EventBase):
    """往下落差達 ``fall_damage_min_drop`` 層以上（``levels`` 為計算傷害的層數）。"""

    type: Literal["unit_fell"] = "unit_fell"
    unit_id: UnitId
    drop: int
    levels: int


class EnteredDeadlyTerrain(EventBase):
    type: Literal["entered_deadly_terrain"] = "entered_deadly_terrain"
    unit_id: UnitId
    pos: Pos
    terrain: str


# ---------------------------------------------------------------------------
# 戰鬥
# ---------------------------------------------------------------------------


class AttackRolled(EventBase):
    """命中判定：``total = natural + hit_modifier + proficiency + situational``。"""

    type: Literal["attack_rolled"] = "attack_rolled"
    attacker_id: UnitId
    target_id: UnitId
    rolls: tuple[int, ...]
    advantage: AdvantageState
    natural: int
    attack_value: int
    defense_value_permille: int
    hit_modifier: int
    proficiency: int
    situational: int
    total: int
    target_number: int
    hit: bool
    crit: bool


class DamageDealt(EventBase):
    type: Literal["damage_dealt"] = "damage_dealt"
    target_id: UnitId
    source_id: UnitId | None
    cause: DamageCause
    element: Element
    rolls: tuple[int, ...]
    crit: bool
    element_mod_ppm: int
    """元素修正（百萬分比，1_000_000 = ×1）。"""
    amount: int
    hp_before: int
    hp_after: int


class Healed(EventBase):
    type: Literal["healed"] = "healed"
    target_id: UnitId
    source_id: UnitId | None
    rolls: tuple[int, ...]
    amount: int
    hp_before: int
    hp_after: int


class StatusApplied(EventBase):
    type: Literal["status_applied"] = "status_applied"
    target_id: UnitId
    status_id: str
    duration: int | None
    refreshed: bool
    source_id: UnitId | None


class StatusRemoved(EventBase):
    type: Literal["status_removed"] = "status_removed"
    target_id: UnitId
    status_id: str
    reason: Literal["expired", "removed", "stood_up"]


class UnitDowned(EventBase):
    type: Literal["unit_downed"] = "unit_downed"
    unit_id: UnitId


class ChainLimitReached(EventBase):
    """連鎖深度超過上限，``effect_kind`` 的效果沒有入列。"""

    type: Literal["chain_limit_reached"] = "chain_limit_reached"
    effect_kind: str
    depth: int


type Event = Annotated[
    BattleStarted
    | InitiativeRolled
    | TurnOrderSet
    | RoundStarted
    | RoundEnded
    | TurnStarted
    | TurnEnded
    | BattleEnded
    | UnitMoved
    | UnitStoodUp
    | MoveBlocked
    | UnitFell
    | EnteredDeadlyTerrain
    | AttackRolled
    | DamageDealt
    | Healed
    | StatusApplied
    | StatusRemoved
    | UnitDowned
    | ChainLimitReached,
    Field(discriminator="type"),
]

EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
EVENT_LIST_ADAPTER: TypeAdapter[list[Event]] = TypeAdapter(list[Event])
