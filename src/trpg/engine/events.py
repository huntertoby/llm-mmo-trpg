"""戰鬥事件（pydantic discriminated union，以 ``type`` 區分）。

- 事件只描述 **發生了什麼**，不含任何顯示文字；繁體中文紀錄由 ``trpg.cli`` 的渲染器產生。
- 每個事件帶 ``seq``（整場戰鬥遞增，從 0 開始）與 ``round``（發生時的輪數）。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.shared.types import Attribute, Element, ObjectId, Pos, Surface, Team, UnitId

__all__ = [
    "EVENT_ADAPTER",
    "EVENT_LIST_ADAPTER",
    "AdvantageState",
    "AttackRolled",
    "BattleEnded",
    "BattleStarted",
    "ChainLimitReached",
    "CheckRolled",
    "DamageCause",
    "DamageDealt",
    "EffectFizzled",
    "ElementTouched",
    "EndReason",
    "EnteredDeadlyTerrain",
    "EnvironmentEnded",
    "EnvironmentStarted",
    "Event",
    "EventBase",
    "Healed",
    "InitiativeRolled",
    "InitiativeTieBroken",
    "ManeuverRolled",
    "MapEventTriggered",
    "MoveBlocked",
    "MoveMode",
    "ObjectAttacked",
    "ObjectCreated",
    "ObjectDamaged",
    "ObjectDestroyCause",
    "ObjectDestroyed",
    "ObjectExploded",
    "ObjectIgnited",
    "ObjectMoved",
    "PushResisted",
    "ReactionDeclined",
    "ReactionTriggered",
    "RoundEnded",
    "RoundStarted",
    "StatusApplied",
    "StatusRemoved",
    "SurfaceChanged",
    "SurfaceEntered",
    "TerrainChanged",
    "TurnEnded",
    "TurnOrderSet",
    "TurnStarted",
    "UnitDowned",
    "UnitEscaped",
    "UnitFell",
    "UnitMoved",
    "UnitSpawned",
    "UnitStoodUp",
]

type AdvantageState = Literal["none", "advantage", "disadvantage"]
type DamageCause = Literal[
    "attack", "fall", "deadly_terrain", "status", "effect", "explosion", "conduct", "surface"
]
"""``attack``：普攻與反應攻擊；``explosion``：爆炸；``conduct``：雷電沿水擴散；
``surface``：站在表面上（毒、聖光）。"""
type ObjectDestroyCause = Literal["damage", "burned", "explosion", "filled", "fell", "effect"]
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


class TurnEnded(EventBase):
    type: Literal["turn_ended"] = "turn_ended"
    unit_id: UnitId
    ap_carried: int


type EndReason = Literal[
    "eliminate", "round_limit", "escaped", "escape_failed", "defended", "point_lost"
]
"""``eliminate``：一方全滅；``escaped``：我方全員撤離；``escape_failed``：撤離超時；
``defended``：守點成功；``point_lost``：守點被占領；``round_limit``：輪數上限（平手）。"""


class BattleEnded(EventBase):
    type: Literal["battle_ended"] = "battle_ended"
    winner: Team | None
    reason: EndReason


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
    reason: Literal["out_of_bounds", "occupied", "obstacle", "too_high"]


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
    """命中判定：``total = natural + hit_modifier + proficiency + situational + cover``。

    ``cover`` 為半掩護的修正（0 或負值），``cover_object_id`` 為提供掩護的物件（Phase 1C）。
    """

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
    cover: int = 0
    cover_object_id: ObjectId | None = None


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
    pos: Pos | None = None
    weather_permille: int = 1000
    """天氣的元素傷害倍率（‰）。"""
    multiplier_permille: int = 1000
    """其他倍率（格擋 500）。"""
    base_amount: int | None = None
    """套用目標自身的元素修正與格擋等倍率 **之前** 的傷害（已含暴擊骰與天氣）。

    雷電擴散以此為基準（Phase 1C 決定 #3），每個被擴散的單位再各自套用自己的元素修正。
    ``None`` 表示與 ``amount`` 相同（以最大 HP 比例計算的傷害）。"""


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


# ---------------------------------------------------------------------------
# Phase 1B：物件、表面、地形
# ---------------------------------------------------------------------------


class ObjectAttacked(EventBase):
    """普攻以物件為目標（一律命中）。"""

    type: Literal["object_attacked"] = "object_attacked"
    attacker_id: UnitId
    object_id: ObjectId


class ObjectDamaged(EventBase):
    type: Literal["object_damaged"] = "object_damaged"
    object_id: ObjectId
    pos: Pos
    source_id: UnitId | None
    cause: DamageCause
    element: Element
    rolls: tuple[int, ...]
    amount: int
    hp_before: int
    hp_after: int


class ObjectDestroyed(EventBase):
    type: Literal["object_destroyed"] = "object_destroyed"
    object_id: ObjectId
    kind: str
    pos: Pos
    cause: ObjectDestroyCause


class ObjectIgnited(EventBase):
    """物件著火，``rounds`` 次環境回合後摧毀。"""

    type: Literal["object_ignited"] = "object_ignited"
    object_id: ObjectId
    pos: Pos
    rounds: int


class ObjectExploded(EventBase):
    type: Literal["object_exploded"] = "object_exploded"
    object_id: ObjectId
    pos: Pos
    radius: int
    source_id: UnitId | None


class ObjectMoved(EventBase):
    type: Literal["object_moved"] = "object_moved"
    object_id: ObjectId
    from_pos: Pos
    to_pos: Pos


class ObjectCreated(EventBase):
    type: Literal["object_created"] = "object_created"
    object_id: ObjectId
    kind: str
    pos: Pos


class SurfaceChanged(EventBase):
    """表面改變（``cause``：``effect``、``expired``、``interaction:<規則 ID>``、``weather``……）。"""

    type: Literal["surface_changed"] = "surface_changed"
    pos: Pos
    before: Surface
    after: Surface
    remaining: int | None
    cause: str


class TerrainChanged(EventBase):
    type: Literal["terrain_changed"] = "terrain_changed"
    pos: Pos
    height_before: int
    height_after: int
    terrain_before: str
    terrain_after: str


class ElementTouched(EventBase):
    """元素觸及一格（由 ``element_touch`` 效果產生，互動表據此產生後續效果）。"""

    type: Literal["element_touched"] = "element_touched"
    pos: Pos
    element: Element
    source_id: UnitId | None
    direction: tuple[int, int] | None
    push_distance: int
    damage: int
    objects_only: bool


class SurfaceEntered(EventBase):
    type: Literal["surface_entered"] = "surface_entered"
    unit_id: UnitId
    pos: Pos
    surface: Surface


class CheckRolled(EventBase):
    """屬性檢定（例如冰面滑倒）：``total = roll + modifier ≥ dc`` 即通過。"""

    type: Literal["check_rolled"] = "check_rolled"
    unit_id: UnitId
    reason: str
    attr: Attribute
    roll: int
    modifier: int
    total: int
    dc: int
    success: bool
    fail_status: str | None = None
    """檢定失敗時獲得的狀態（由觸發表套用）。"""


class EffectFizzled(EventBase):
    """效果沒有發生（例如障礙物無處可放）。"""

    type: Literal["effect_fizzled"] = "effect_fizzled"
    effect_kind: str
    pos: Pos | None
    reason: str


# ---------------------------------------------------------------------------
# Phase 1B：技巧動作、推擊、反應
# ---------------------------------------------------------------------------


class ManeuverRolled(EventBase):
    """技巧動作的對抗判定（推擊：力量 vs 力量；絆倒：敏捷 vs 敏捷）。"""

    type: Literal["maneuver_rolled"] = "maneuver_rolled"
    maneuver: Literal["shove", "trip"]
    attacker_id: UnitId
    target_id: UnitId
    natural: int
    modifier: int
    proficiency: int
    total: int
    target_number: int
    success: bool


class PushResisted(EventBase):
    """``steadfast`` 使推擊距離減少。"""

    type: Literal["push_resisted"] = "push_resisted"
    unit_id: UnitId
    requested: int
    distance: int


class ReactionTriggered(EventBase):
    type: Literal["reaction_triggered"] = "reaction_triggered"
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None
    stamina_spent: int


class ReactionDeclined(EventBase):
    """``prompt`` 反應被拒絕。"""

    type: Literal["reaction_declined"] = "reaction_declined"
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None


# ---------------------------------------------------------------------------
# Phase 1B：環境回合、地圖事件、勝利條件
# ---------------------------------------------------------------------------


class EnvironmentStarted(EventBase):
    type: Literal["environment_started"] = "environment_started"


class EnvironmentEnded(EventBase):
    type: Literal["environment_ended"] = "environment_ended"


class MapEventTriggered(EventBase):
    type: Literal["map_event_triggered"] = "map_event_triggered"
    index: int
    kind: Literal["spawn_units", "terrain_change"]


class UnitSpawned(EventBase):
    type: Literal["unit_spawned"] = "unit_spawned"
    unit_id: UnitId
    template_id: str
    team: Team
    pos: Pos


class UnitEscaped(EventBase):
    """單位抵達出口，離開戰場。"""

    type: Literal["unit_escaped"] = "unit_escaped"
    unit_id: UnitId
    pos: Pos


type Event = Annotated[
    BattleStarted
    | InitiativeRolled
    | InitiativeTieBroken
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
    | ChainLimitReached
    | ObjectAttacked
    | ObjectDamaged
    | ObjectDestroyed
    | ObjectIgnited
    | ObjectExploded
    | ObjectMoved
    | ObjectCreated
    | SurfaceChanged
    | TerrainChanged
    | ElementTouched
    | SurfaceEntered
    | CheckRolled
    | EffectFizzled
    | ManeuverRolled
    | PushResisted
    | ReactionTriggered
    | ReactionDeclined
    | EnvironmentStarted
    | EnvironmentEnded
    | MapEventTriggered
    | UnitSpawned
    | UnitEscaped,
    Field(discriminator="type"),
]

EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
EVENT_LIST_ADAPTER: TypeAdapter[list[Event]] = TypeAdapter(list[Event])
