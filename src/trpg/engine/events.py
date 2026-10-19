"""戰鬥事件（pydantic discriminated union，以 ``type`` 區分）。

- 事件只描述 **發生了什麼**，不含任何顯示文字；繁體中文紀錄由 ``trpg.cli`` 的渲染器產生。
- 每個事件帶 ``seq``（整場戰鬥遞增，從 0 開始）與 ``round``（發生時的輪數）。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.content.battle import Dice
from trpg.shared.types import Attribute, Element, ObjectId, Pos, Surface, Team, UnitId

__all__ = [
    "EVENT_ADAPTER",
    "EVENT_LIST_ADAPTER",
    "AdvantageState",
    "ApGranted",
    "AttackIntercepted",
    "AttackRolled",
    "BattleEnded",
    "BattleStarted",
    "ChainLimitReached",
    "CheckRolled",
    "Collided",
    "CollisionObstacle",
    "DamageCause",
    "DamageDealt",
    "DeathCheated",
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
    "ReactionModeSet",
    "ReactionTriggered",
    "RoundEnded",
    "RoundStarted",
    "ShieldAbsorbed",
    "ShieldGained",
    "SkillCooldownChanged",
    "SkillTriggered",
    "SkillUsed",
    "SourceChanged",
    "SourceReason",
    "StacksChanged",
    "StatusApplied",
    "StatusConverted",
    "StatusRemoved",
    "StatusResisted",
    "StatusSaveRolled",
    "SurfaceChanged",
    "SurfaceEntered",
    "TerrainChanged",
    "TrapExpired",
    "TrapPlaced",
    "TrapTriggered",
    "TriggerLimitReached",
    "TurnEnded",
    "TurnOrderSet",
    "TurnSkipped",
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
    "attack",
    "fall",
    "deadly_terrain",
    "status",
    "effect",
    "explosion",
    "conduct",
    "surface",
    "collision",
]
"""``attack``：普攻與反應攻擊；``explosion``：爆炸；``conduct``：雷電沿水擴散；
``surface``：站在表面上（毒、聖光）；``collision``：撞擊（Phase 3C-3a）。"""
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
    mana: int = 0
    max_mana: int = 0


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


type CollisionObstacle = Literal["wall", "edge", "object", "unit", "excess"]
"""撞到什麼：``wall`` 不可走的地形（含過高的階梯）、``edge`` 地圖邊界、``object`` ``blocks_move``
物件、``unit`` 其他單位、``excess`` 沒有撞到東西（技能把推擊距離加到超過上限的部分）。"""


class Collided(EventBase):
    """被強制位移的單位因障礙提前停下，或距離超過上限的部分改為撞擊（Phase 3C-3a）。

    ``shortfall`` 為少走的格數（``excess`` 時為超過上限的格數）；每格造成一次撞擊傷害
    （``DamageDealt.cause == "collision"``，歸給 ``source_id``）。撞到單位時雙方都受傷，撞到
    ``breakable`` 物件時物件也受傷。``dice`` 為 ``None`` 時用 ``core.collision_damage_dice``。
    """

    type: Literal["collided"] = "collided"
    unit_id: UnitId
    obstacle: CollisionObstacle
    shortfall: int = Field(ge=1)
    pos: Pos
    """被擋住的格子（``excess`` 時為單位目前所在格）。"""
    source_id: UnitId | None = None
    """位移的來源單位（推擊者、施放者）；環境造成的位移為 ``None``。"""
    other_id: UnitId | None = None
    """撞到的單位。"""
    object_id: ObjectId | None = None
    """撞到的物件。"""
    dice: Dice | None = None


class UnitFell(EventBase):
    """往下落差達 ``fall_damage_min_drop`` 層以上（``levels`` 為計算傷害的層數）。"""

    type: Literal["unit_fell"] = "unit_fell"
    unit_id: UnitId
    drop: int
    levels: int
    source_id: UnitId | None = None
    """造成墜落的單位（推擊者、降低地形的施放者）；走下去或追溯不到時為 ``None``。"""


class EnteredDeadlyTerrain(EventBase):
    type: Literal["entered_deadly_terrain"] = "entered_deadly_terrain"
    unit_id: UnitId
    pos: Pos
    terrain: str
    source_id: UnitId | None = None
    """讓單位進入致命地形的單位（推擊者、打斷或燒斷橋的人）；追溯不到時為 ``None``。"""


# ---------------------------------------------------------------------------
# 戰鬥
# ---------------------------------------------------------------------------


class AttackRolled(EventBase):
    """命中判定：``total = natural + hit_modifier + proficiency + situational + cover +
    modifier_bonus``。

    ``cover`` 為半掩護的修正（0 或負值），``cover_object_id`` 為提供掩護的物件（Phase 1C）。
    ``modifier_bonus`` 為修正規則的命中加值（Phase 3C-2；預設 0，舊紀錄不受影響）。
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
    skill_id: str | None = None
    """技能的命中判定時為技能 ID（Phase 2A）；普攻為 ``None``。"""
    modifier_bonus: int = 0


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
    status_ppm: int = 1_000_000
    """狀態的傷害倍率（百萬分比）：攻擊者的 ``damage_dealt_permille``（虛弱，只對 ``attack``）
    × 目標的 ``damage_taken_permille``（易傷、護衛，骰值傷害）。"""
    absorbed: int = 0
    """被護盾吸收的點數（Phase 2D-1）。``amount`` 是所有倍率之後、護盾之前的傷害；實際扣血為
    ``amount − absorbed``（即 ``hp_before − hp_after``，致命以上的過量不算在內）。"""


class Healed(EventBase):
    type: Literal["healed"] = "healed"
    target_id: UnitId
    source_id: UnitId | None
    rolls: tuple[int, ...]
    amount: int
    hp_before: int
    hp_after: int
    received_permille: int = 1000
    """目標的狀態治療倍率（‰，中毒 500）。"""


class ShieldGained(EventBase):
    """單位獲得護盾（Phase 2D-1）：``amount`` 為這次的護盾量，``total`` 為取較大值之後的吸收量。"""

    type: Literal["shield_gained"] = "shield_gained"
    unit_id: UnitId
    source_id: UnitId | None
    amount: int
    total: int
    rolls: tuple[int, ...] = ()


class ShieldAbsorbed(EventBase):
    """護盾吸收了一次傷害（先於對應的 ``damage_dealt``）。"""

    type: Literal["shield_absorbed"] = "shield_absorbed"
    unit_id: UnitId
    absorbed: int
    remaining: int


class StatusApplied(EventBase):
    type: Literal["status_applied"] = "status_applied"
    target_id: UnitId
    status_id: str
    duration: int | None
    refreshed: bool
    source_id: UnitId | None


class StatusSaveRolled(EventBase):
    """施加狀態的抵抗判定：攻方（技能的縮放屬性）對守方（狀態的 ``save_attr``）的比例公式。

    ``diminished``：守方正處於該控制類別的遞減期間，``defense_value`` 已乘上遞減倍率。
    ``applied``：攻方成功（狀態會被施加）；失敗時緊接著 ``status_resisted``。
    """

    type: Literal["status_save_rolled"] = "status_save_rolled"
    attacker_id: UnitId
    target_id: UnitId
    status_id: str
    attack_attr: Attribute
    attack_value: int
    save_attr: Attribute
    defense_value: int
    diminished: bool
    natural: int
    modifier: int
    proficiency: int
    total: int
    target_number: int
    applied: bool
    skill_id: str | None = None


class StatusResisted(EventBase):
    """目標抵抗了狀態，沒有被施加。"""

    type: Literal["status_resisted"] = "status_resisted"
    target_id: UnitId
    status_id: str
    source_id: UnitId | None


class StatusConverted(EventBase):
    """Boss 的硬控轉換（``boss_control_conversion``）：``from_status`` 改為施加 ``to_status``。"""

    type: Literal["status_converted"] = "status_converted"
    target_id: UnitId
    from_status: str
    to_status: str
    source_id: UnitId | None


class StatusRemoved(EventBase):
    type: Literal["status_removed"] = "status_removed"
    target_id: UnitId
    status_id: str
    reason: Literal[
        "expired",
        "removed",
        "stood_up",
        "depleted",
        "cleansed",
        "source_lost",
        "replaced",
        "stance_ended",
        "downed",
        "thawed",
        "consumed",
        "spent",
    ]
    """``spent``：不死（``undying``）擋下致命傷害後移除（Phase 3C-4a）；
    ``thawed``：受到 ``removed_by_element`` 的元素傷害而解除（冰凍遇火，Phase 2H-1）；
    ``consumed``：被 ``consume_status`` 消耗（Phase 3C-3b）；``replaced``：被新的姿態取代；
    ``stance_ended``：``EndStance`` 取消姿態；``downed``：單位倒下或撤離時移除姿態
    （Phase 2E-2）。"""


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
    how: Literal["push", "shove_aside"] = "push"
    """推動的方式（``shove_aside`` 為互動的「撥開」；風、技能的推擊都是 ``push``）。"""


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
    tile_only: bool = False
    """只套用表面與物件類規則（技能的範圍傷害觸及沒有單位的格子）。"""


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
    maneuver: Literal["shove", "trip", "knock_prone"]
    attacker_id: UnitId
    target_id: UnitId
    natural: int
    modifier: int
    proficiency: int
    total: int
    target_number: int
    success: bool
    skill_id: str | None = None
    """技能的擊倒對抗判定時為技能 ID。"""


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


class AttackIntercepted(EventBase):
    """替隊友擋攻擊（Phase 2E-2 ``intercept``）：``attacker_id`` 對 ``target_id`` 的單體攻擊已命中，
    傷害與其他效果改為作用在 ``guardian_id`` 身上（``skill_id`` 為攻擊所用的技能，普攻為
    ``None``）。之後是攻擊對守護者結算的事件。"""

    type: Literal["attack_intercepted"] = "attack_intercepted"
    guardian_id: UnitId
    attacker_id: UnitId
    target_id: UnitId
    skill_id: str | None = None


class ReactionModeSet(EventBase):
    """玩家改了自己某條反應規則的模式（``set_reaction_mode``）。"""

    type: Literal["reaction_mode_set"] = "reaction_mode_set"
    unit_id: UnitId
    reaction: str
    mode: Literal["auto", "prompt", "off"]


class ReactionDeclined(EventBase):
    """``prompt`` 反應被拒絕。"""

    type: Literal["reaction_declined"] = "reaction_declined"
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None


# ---------------------------------------------------------------------------
# Phase 2A：技能
# ---------------------------------------------------------------------------


class SkillUsed(EventBase):
    """施放者使用技能（代價已支付）。

    ``tiles`` 為影響的格子（依 (y, x) 排序）；``mana_after`` 為使用後的法力；``hp_spent`` 為
    支付的 HP；``cooldown`` 為設定的冷卻回合（沒有冷卻為 ``None``）。
    """

    type: Literal["skill_used"] = "skill_used"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    ap: int
    mana: int
    mana_after: int
    hp_spent: int = 0
    cooldown: int | None = None
    tiles: tuple[Pos, ...]
    source: int = 0
    """花費的源力（傳說技能，Phase 3C-4a；之後另有 ``source_changed``）。"""


class SkillTriggered(EventBase):
    """被動技能觸發（Phase 2E-1）。

    ``trigger``：觸發時機 ID（``skill_triggers.yaml``）；修正規則的命中後效果為
    ``modifier_on_hit``（Phase 3C-2，沒有代價）；
    ``other_id``：該時機的另一方（沒有為 ``None``）；
    ``trigger_depth``：觸發深度（動作本身為 0，由動作直接引起的觸發為 1，觸發產生的觸發再 +1）。
    之後是技能效果原本的事件。
    """

    type: Literal["skill_triggered"] = "skill_triggered"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    trigger: str
    other_id: UnitId | None
    trigger_depth: int
    mana: int = 0
    mana_after: int = 0
    hp_spent: int = 0
    cooldown: int | None = None


class TriggerLimitReached(EventBase):
    """觸發會讓 ``trigger_depth`` 超過 ``max_trigger_depth``，所以沒有結算。"""

    type: Literal["trigger_limit_reached"] = "trigger_limit_reached"
    unit_id: UnitId
    skill_id: str
    depth: int


class SkillCooldownChanged(EventBase):
    """技能的冷卻回合改變（使用後設定、自己回合開始時 −1）。"""

    type: Literal["skill_cooldown_changed"] = "skill_cooldown_changed"
    unit_id: UnitId
    skill_id: str
    remaining: int


class StacksChanged(EventBase):
    """層數改變（Phase 2E-3）：``before`` → ``after``。

    ``reason``：``gained``（``add_stack``）、``consumed``（``consume_stack``）、``expired``
    （``expires_after_rounds`` 到期）。
    """

    type: Literal["stacks_changed"] = "stacks_changed"
    unit_id: UnitId
    stack_id: str
    before: int
    after: int
    reason: Literal["gained", "consumed", "expired"]
    source_id: UnitId | None = None


# ---------------------------------------------------------------------------
# Phase 3C-4a：源力與改寫規則型原語
# ---------------------------------------------------------------------------

type SourceReason = Literal["skill", "well", "kill_elite"]
"""源力改變的原因：``skill`` 施放傳說技能的花費、``well`` 進入源泉格、``kill_elite`` 擊倒精英。"""


class SourceChanged(EventBase):
    """源力改變（Phase 3C-4a）：``before`` → ``after``（已截斷在 0 與上限之間）。

    ``skill_id``：``skill`` 時為花費源力的技能；``pos``：``well`` 時為源泉格（之後消失）；
    ``other_id``：``kill_elite`` 時為被擊倒的精英。
    """

    type: Literal["source_changed"] = "source_changed"
    unit_id: UnitId
    before: int
    after: int
    reason: SourceReason
    skill_id: str | None = None
    pos: Pos | None = None
    other_id: UnitId | None = None


class ApGranted(EventBase):
    """``grant_ap``：``unit_id`` 獲得 ``amount`` AP（已扣掉超過本回合上限的部分）。

    ``deferred``：目標不在自己的回合，AP 在它下次回合開始時才加上（``ap_after`` 為屆時的待加
    AP）。"""

    type: Literal["ap_granted"] = "ap_granted"
    unit_id: UnitId
    source_id: UnitId
    amount: int
    ap_after: int
    deferred: bool = False


class DeathCheated(EventBase):
    """不死（``cheat_death`` 的狀態）擋下致命傷害：HP 留在 1，之後移除該狀態（``spent``）。"""

    type: Literal["death_cheated"] = "death_cheated"
    unit_id: UnitId
    status_id: str
    prevented: int
    """多擋下的傷害（原本會扣到 0 以下的部分 ＋ 1）。"""


# ---------------------------------------------------------------------------
# Phase 2E-3：陷阱
# ---------------------------------------------------------------------------


class TrapPlaced(EventBase):
    """放置者放下陷阱（對放置者陣營以外的玩家隱藏；事件紀錄是全知的）。"""

    type: Literal["trap_placed"] = "trap_placed"
    owner_id: UnitId
    team: Team
    pos: Pos
    skill_id: str
    trigger: Literal["enter", "delay"]
    rounds: int


class TrapTriggered(EventBase):
    """陷阱觸發並移除；之後是陷阱效果的事件。``unit_id`` 是踩到的敵人（``delay`` 為 ``None``）。

    ``tiles``：觸發時實際受影響的格子（以陷阱格為中心展開 ``trap.shape``，依 (y, x) 排序固定；
    Phase 2F-1 3.4）。省略時為空，向下相容舊紀錄（不須升版 ``LOG_FORMAT``）。
    """

    type: Literal["trap_triggered"] = "trap_triggered"
    owner_id: UnitId
    pos: Pos
    skill_id: str
    cause: Literal["enter", "delay"]
    unit_id: UnitId | None = None
    trigger_depth: int = 0
    tiles: tuple[Pos, ...] = ()


class TrapExpired(EventBase):
    """陷阱消失而沒有觸發：``timeout`` 為 ``enter`` 陷阱輪數到了，``source_lost`` 為放置者離場。"""

    type: Literal["trap_expired"] = "trap_expired"
    owner_id: UnitId
    pos: Pos
    skill_id: str
    reason: Literal["timeout", "source_lost"]


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
    | Collided
    | UnitFell
    | EnteredDeadlyTerrain
    | AttackRolled
    | DamageDealt
    | Healed
    | ShieldGained
    | ShieldAbsorbed
    | StatusApplied
    | StatusRemoved
    | StatusSaveRolled
    | StatusResisted
    | StatusConverted
    | TurnSkipped
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
    | ReactionModeSet
    | AttackIntercepted
    | EnvironmentStarted
    | EnvironmentEnded
    | MapEventTriggered
    | UnitSpawned
    | UnitEscaped
    | SkillUsed
    | SkillCooldownChanged
    | SkillTriggered
    | TriggerLimitReached
    | StacksChanged
    | TrapPlaced
    | TrapTriggered
    | TrapExpired
    | SourceChanged
    | ApGranted
    | DeathCheated,
    Field(discriminator="type"),
]

EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
EVENT_LIST_ADAPTER: TypeAdapter[list[Event]] = TypeAdapter(list[Event])
