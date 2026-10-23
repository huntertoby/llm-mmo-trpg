"""戰鬥事件（pydantic discriminated union，以 ``type`` 區分）。

- 事件只描述 **發生了什麼**，不含任何顯示文字；繁體中文紀錄由 ``trpg.cli`` 的渲染器產生。
- 每個事件帶 ``seq``（整場戰鬥遞增，從 0 開始）與 ``round``（發生時的輪數）。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.content.battle import Dice, SummonMode
from trpg.shared.types import Attribute, Element, ObjectId, Pos, Surface, Team, UnitId

__all__ = [
    "EVENT_ADAPTER",
    "EVENT_LIST_ADAPTER",
    "ActivationExpired",
    "AdvantageState",
    "ApGranted",
    "ApRefunded",
    "AttackIntercepted",
    "AttackRolled",
    "BacklashTriggered",
    "BattleEnded",
    "BattleStarted",
    "BombCause",
    "BombExploded",
    "BombTicked",
    "ChainLimitReached",
    "ChargeActivated",
    "CheckRolled",
    "Collided",
    "CollisionObstacle",
    "DamageCause",
    "DamageDealt",
    "DamageRedirected",
    "DeathCheated",
    "DetonateReason",
    "EffectFizzled",
    "ElementTouched",
    "EndReason",
    "EnteredDeadlyTerrain",
    "EnvironmentEnded",
    "EnvironmentStarted",
    "Event",
    "EventBase",
    "FollowupCancelled",
    "FollowupCharged",
    "GambleRolled",
    "GearHpLost",
    "GearTriggered",
    "GuardSet",
    "Healed",
    "InfusedSkillCast",
    "InfusionFizzled",
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
    "ObjectExpired",
    "ObjectExploded",
    "ObjectHurled",
    "ObjectIgnited",
    "ObjectMoved",
    "ObjectToppled",
    "OverloadTriggered",
    "PushResisted",
    "ReactionDeclined",
    "ReactionModeSet",
    "ReactionTriggered",
    "ReactionsGranted",
    "ResourceRestored",
    "RoundEnded",
    "RoundStarted",
    "RuleChangeKindName",
    "RuleChangeTriggered",
    "RuneInscribed",
    "RuneRemovalReason",
    "RuneRemoved",
    "ShieldAbsorbed",
    "ShieldGained",
    "ShotPierced",
    "SkillActivated",
    "SkillCooldownChanged",
    "SkillCopied",
    "SkillFollowup",
    "SkillGrantExpired",
    "SkillGranted",
    "SkillInfused",
    "SkillTriggered",
    "SkillUsed",
    "SnareTriggered",
    "SourceChanged",
    "SourceReason",
    "StacksChanged",
    "StatusApplied",
    "StatusConverted",
    "StatusRemoved",
    "StatusResisted",
    "StatusSaveRolled",
    "SummonCommanded",
    "SummonDetonated",
    "SummonExpired",
    "SummonExpiryReason",
    "SummonModeSet",
    "SummonPulled",
    "SurfaceChanged",
    "SurfaceEntered",
    "TerrainChanged",
    "TotemPulsed",
    "TrapExpired",
    "TrapPlaced",
    "TrapRevealed",
    "TrapTriggered",
    "TriggerLimitReached",
    "TurnEnded",
    "TurnOrderSet",
    "TurnSkipped",
    "TurnStarted",
    "UnitAimed",
    "UnitCharged",
    "UnitDashed",
    "UnitDowned",
    "UnitEscaped",
    "UnitFell",
    "UnitMoved",
    "UnitRan",
    "UnitRevived",
    "UnitSpawned",
    "UnitStoodUp",
    "UnitSummoned",
    "UnitVaulted",
    "WallToppled",
    "WeaponReloaded",
    "ZoneCreated",
    "ZoneExpired",
    "ZoneExpiryReason",
    "ZoneMoved",
    "ZoneTriggered",
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
    "topple",
    "backlash",
]
"""``attack``：普攻與反應攻擊；``explosion``：爆炸；``conduct``：雷電沿水擴散；
``surface``：站在表面上（毒、聖光）；``collision``：撞擊（Phase 3C-3a）；``topple``：被推倒的物件
壓到（Phase 3C-5a）；``backlash``：賭博型技能的反噬（失敗分支、失手反噬；Phase 3D-7a，不會讓
受到的單位 HP 低於 1）。"""
type ObjectDestroyCause = Literal[
    "damage", "burned", "explosion", "filled", "fell", "effect", "hurled", "toppled"
]
"""``hurled``：被投擲後落地碎掉；``toppled``：被推倒（原物件移除，改由倒塌物取代；Phase 3C-5a）。"""
type MoveMode = Literal[
    "walk", "forced", "teleport", "teleported", "dash", "leap", "swap", "shadowstep"
]
"""``walk``：主動移動的一步；``forced``：強制位移（推擊等）；``teleport``：傳送（不墜落）；
``dash``：衝鋒的一步（同步行，會墜落與觸發陷阱）；``leap``：跳躍的落點；``swap``：與另一個單位
交換位置（Phase 3D-2）；``shadowstep``：瞬步到敵人身旁（Phase 3D-8d；不墜落，落點的陷阱、表面
照常結算）。"""


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


class UnitDashed(EventBase):
    """衝鋒（``dash``，Phase 3D-2）開始：``unit_id`` 朝 ``target_id`` 沿 ``path``（含起點與終點，
    相鄰目標時只有起點）前進；每一步另有 ``unit_moved``（``mode: dash``），被擋下時不會走完。"""

    type: Literal["unit_dashed"] = "unit_dashed"
    unit_id: UnitId
    target_id: UnitId
    path: tuple[Pos, ...]


class UnitCharged(EventBase):
    """直線衝撞（``charge_through``，Phase 3D-2c）開始：``unit_id`` 朝 ``target``（選的終點）直線
    衝去，``path`` 是施放者依序經過的格子（含起點、含有單位的格子，終點是實際停下的格子；被擋住時
    比 ``target`` 短）；每個空格另有 ``unit_moved``（``mode: dash``），沿途的敵人各自有命中判定。"""

    type: Literal["unit_charged"] = "unit_charged"
    unit_id: UnitId
    target: Pos
    path: tuple[Pos, ...]


class UnitStoodUp(EventBase):
    type: Literal["unit_stood_up"] = "unit_stood_up"
    unit_id: UnitId
    cost: int


class UnitRan(EventBase):
    """跑步（Phase 3-20）：``bonus`` 為增加的移動點數，``move_points`` 為跑步後剩餘的移動點數。"""

    type: Literal["unit_ran"] = "unit_ran"
    unit_id: UnitId
    bonus: int
    move_points: int


class UnitVaulted(EventBase):
    """攀跳（Phase 3-21b）：``kind`` 為 ``climb``（攀爬上高台）或 ``jump``（跳過缺口）；之後另有一個
    ``unit_moved``（``mode: walk``，``cost`` 為消耗的移動點數）。"""

    type: Literal["unit_vaulted"] = "unit_vaulted"
    unit_id: UnitId
    kind: Literal["climb", "jump"]
    from_pos: Pos
    to_pos: Pos


class GuardSet(EventBase):
    """守護隊友（Phase 3-21a）：``unit_id`` 守護相鄰的 ``ally_id``，到自己的下回合開始。"""

    type: Literal["guard_set"] = "guard_set"
    unit_id: UnitId
    ally_id: UnitId


class UnitAimed(EventBase):
    """瞄準（Phase 3-21a）：下一次需要擲命中的攻擊命中 ``+bonus``。"""

    type: Literal["unit_aimed"] = "unit_aimed"
    unit_id: UnitId
    bonus: int


class WeaponReloaded(EventBase):
    """裝填（Phase 3-24a2）：``unit_id`` 花 ``cost`` AP 把彈匣裝到 ``ammo`` 發。"""

    type: Literal["weapon_reloaded"] = "weapon_reloaded"
    unit_id: UnitId
    ammo: int
    cost: int


class MoveBlocked(EventBase):
    type: Literal["move_blocked"] = "move_blocked"
    unit_id: UnitId
    to_pos: Pos
    reason: Literal["out_of_bounds", "occupied", "obstacle", "too_high", "immovable"]
    forced: bool = False
    """強制位移（推擊）被擋下（Phase 3C-6a）：緊接著的 ``collided`` 事件才是紀錄的主角。"""


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
    modifier_bonus + backstab + ambush``。

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
    backstab: int = 0
    """背刺的命中加值（Phase 3D-8d；0 為不是背刺；暴擊範圍另外擴大
    ``backstab_crit_range_bonus``）。"""
    ambush: int = 0
    """潛行偷襲的命中加值（Phase 3D-8d；攻擊者帶 ``concealed`` 狀態；0 為沒有）。"""


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
    """其他倍率（格擋 500）；穿透後方折扣也包含在內。"""
    pierce_permille: int = 1000
    """穿透後方折扣（‰，已包含在 ``multiplier_permille`` 裡；Phase 3C-6a 供紀錄分開顯示）。"""
    base_amount: int | None = None
    """套用目標自身的元素修正與格擋等倍率 **之前** 的傷害（已含暴擊骰與天氣）。

    雷電擴散以此為基準（Phase 1C 決定 #3），每個被擴散的單位再各自套用自己的元素修正。
    ``None`` 表示與 ``amount`` 相同（以最大 HP 比例計算的傷害）。"""
    status_ppm: int = 1_000_000
    """狀態的傷害倍率（百萬分比）：攻擊者的 ``damage_dealt_permille``（虛弱，只對 ``attack``）
    × 目標的 ``damage_taken_permille``（易傷、護衛，骰值傷害）。"""
    absorbed: int = 0
    """被護盾吸收的點數（Phase 2D-1）。``amount`` 是所有倍率之後、護盾之前的傷害；實際扣血為
    ``amount − absorbed − redirected``（即 ``hp_before − hp_after``，致命以上的過量不算在內）。"""
    redirected: int = 0
    """轉給連結者（``redirect_damage`` 的狀態，Phase 3C-4b）的點數；轉移本身是緊接著的
    ``damage_redirected`` 事件。"""
    exploded: int = 0
    """爆骰（Phase 3D-7b）多擲的骰子數（``rolls`` 已包含它們）。"""
    flat: int = 0
    """固定值（武器的固定傷害等；Phase 3-41b 供紀錄把傷害組成分項顯示）。"""
    scaled_permille: int = 0
    """屬性加成（‰，屬性值 × 倍率；Phase 3-41b）。"""
    block_permille: int = 1000
    """格擋倍率（‰，已包含在 ``multiplier_permille`` 裡；Phase 3-41b 供紀錄分開顯示）。"""
    scale_attr: Attribute | None = None
    """屬性加成的來源屬性（單一屬性時；雙屬性平均或不明時為 ``None``；Phase 3-41b）。"""


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
    cause: Literal["heal", "lifesteal"] = "heal"
    """``lifesteal``：吸血（Phase 3D-8a），施放者回復自己造成傷害的一部分。"""


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
        "stolen",
        "dispelled",
        "revealed",
        "fired",
        "ambushed",
    ]
    """``ambushed``：隱蔽中發動攻擊（潛行偷襲）後脫離隱蔽（Phase 3D-8d）；
    ``fired``：監視（``overwatch``）射擊後結束（Phase 3D-8c）；
    ``dispelled``：被 ``dispel`` 驅散；``revealed``：被 ``reveal`` 移除隱蔽（Phase 3D-8a）；
    ``stolen``：被 ``steal_buff`` 奪走（Phase 3D-1；緊接著對施放者的 ``status_applied``）；
    ``spent``：不死（``undying``）擋下致命傷害後移除（Phase 3C-4a）；
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


class ObjectHurled(EventBase):
    """物件被投擲（Phase 3C-5a ``hurl_object``）：從 ``from_pos`` 舉起、丟向 ``to_pos``（落點）。

    之後依標籤結算：爆炸（``object_exploded``，在落點）、碎掉（``object_destroyed``，原因
    ``hurled``）、放在 ``placed_pos``（落點或附近的空格，``object_moved`` 不另外發出），或沒有
    空格而摧毀（``object_destroyed``，原因 ``hurled``）。``outcome`` 記錄是哪一種。
    """

    type: Literal["object_hurled"] = "object_hurled"
    object_id: ObjectId
    kind: str
    from_pos: Pos
    to_pos: Pos
    source_id: UnitId | None
    outcome: Literal["exploded", "shattered", "placed", "lost"]
    placed_pos: Pos | None = None


class ObjectToppled(EventBase):
    """``topplable`` 物件被推倒（Phase 3C-5a）：往 ``direction`` 倒下，壓住 ``tiles``。

    ``tiles`` 依序、已排除地圖外與不可走的格子，被非破壞物件擋住時只到擋住之前。原物件隨後移除
    （``object_destroyed``，原因 ``toppled``），``rubble_pos`` 產生倒塌物（``object_created``）。
    格上的單位受推倒傷害並倒地、``breakable`` 物件受同樣傷害（由觸發表結算，歸給
    ``source_id``）。
    """

    type: Literal["object_toppled"] = "object_toppled"
    object_id: ObjectId
    kind: str
    pos: Pos
    direction: tuple[int, int]
    tiles: tuple[Pos, ...]
    units: tuple[UnitId, ...]
    """壓到的單位（依壓到的順序）。"""
    objects: tuple[ObjectId, ...]
    """壓到的 ``breakable`` 物件（依壓到的順序）。"""
    rubble_pos: Pos | None
    source_id: UnitId | None


class ShotPierced(EventBase):
    """穿透技能（``pierce``，Phase 3C-5b）的射線穿過了 ``penetrable`` 物件：``objects``（依路線
    順序）受全額傷害，``behind`` 的單位只受 ``behind_permille``‰ 的傷害。``route`` 是施放者與
    目標之間的路線（不含兩端；直線為影響範圍）。沒有穿過任何物件時不發出。"""

    type: Literal["shot_pierced"] = "shot_pierced"
    unit_id: UnitId
    skill_id: str
    objects: tuple[ObjectId, ...]
    object_tiles: tuple[Pos, ...]
    behind: tuple[UnitId, ...]
    behind_permille: int
    route: tuple[Pos, ...]


class ObjectCreated(EventBase):
    type: Literal["object_created"] = "object_created"
    object_id: ObjectId
    kind: str
    pos: Pos


class ObjectExpired(EventBase):
    """暫時障礙（``create_obstacle`` 的 ``duration``）到期自動移除；不算被摧毀。"""

    type: Literal["object_expired"] = "object_expired"
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
    maneuver: Literal["shove", "trip", "knock_prone", "teleport", "swap"]
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
    resist_bonus: int = 0
    """目標的抵抗加成（Phase 3D-2b：傳送敵人、傳送到致命地形）；已從 ``total`` 扣除（``modifier``
    不含它）。其他對抗判定為 0。"""


class PushResisted(EventBase):
    """``steadfast`` 使推擊距離減少；``immovable``（石像，Phase 3-33e2a）使推擊完全無效。"""

    type: Literal["push_resisted"] = "push_resisted"
    unit_id: UnitId
    requested: int
    distance: int
    reason: Literal["steadfast", "immovable"] = "steadfast"


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
    guard: bool = False
    """``True`` 為「守護」動作的轉移（Phase 3-21a），否則為 ``intercept`` 反應技。"""


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
    stamina: int = 0
    """花費的耐力（武器技，Phase 3H-2）；``stamina_after`` 為使用後的耐力。"""
    stamina_after: int = 0
    hp_spent: int = 0
    cooldown: int | None = None
    tiles: tuple[Pos, ...]
    source: int = 0
    """花費的源力（傳說技能，Phase 3C-4a；之後另有 ``source_changed``）。"""
    variant: str | None = None
    """生效的戰場變奏 ID（Phase 3-25a，6.24）；基礎型態為 ``None``。"""


class SkillFollowup(EventBase):
    """複合技能（Phase 3F-3a，6.23）的第二段開始結算：``origin`` 是第二段的原點（「位移 → 動作」為
    位移段的落點），``tiles`` 是第二段影響的格子（依 (y, x) 排序）。之後是第二段的命中、傷害等
    事件；位移被擋下時沒有這個事件，改為 ``effect_fizzled``（``effect_kind: followup``）。"""

    type: Literal["skill_followup"] = "skill_followup"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    when: str
    origin: Pos
    tiles: tuple[Pos, ...]


class FollowupCharged(EventBase):
    """延遲段（Phase 3F-4b，6.23 #5）開始等待：施放者身上帶著 ``charging``。``release`` 是釋放時機
    （``next_turn``／``attacked``），``pos``／``tiles`` 是以施放者目前位置推算的預計範圍（施放者
    移動時範圍跟著移動）。"""

    type: Literal["followup_charged"] = "followup_charged"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    release: str
    pos: Pos
    tiles: tuple[Pos, ...]


class FollowupCancelled(EventBase):
    """延遲段（Phase 3F-4b）取消：``downed`` 施放者倒下、``controlled`` 被暈眩或冰凍
    （``skip_turn`` 的狀態）、``expired`` 被攻擊才釋放的延遲段到下回合開始都沒被攻擊、
    ``replaced`` 施放了另一個延遲段。"""

    type: Literal["followup_cancelled"] = "followup_cancelled"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    reason: Literal["downed", "controlled", "expired", "replaced"]


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
    stamina: int = 0
    """花費的耐力（武器技，Phase 3H-2）；``stamina_after`` 為使用後的耐力。"""
    stamina_after: int = 0
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
    （``expires_after_rounds`` 到期）、``overload``（超載到達門檻而清空，Phase 3D-7b）。
    """

    type: Literal["stacks_changed"] = "stacks_changed"
    unit_id: UnitId
    stack_id: str
    before: int
    after: int
    reason: Literal["gained", "consumed", "expired", "overload"]
    source_id: UnitId | None = None


class OverloadTriggered(EventBase):
    """超載（Phase 3D-7b）：層數累積到 ``threshold``，持有者立刻承受反噬（緊接著的傷害與狀態事件）
    並清空層數（``stacks_changed``，原因 ``overload``）。"""

    type: Literal["overload_triggered"] = "overload_triggered"
    unit_id: UnitId
    stack_id: str
    stacks: int
    threshold: int


class GearHpLost(EventBase):
    """裝備的代價（Phase 3G-G1，例如 ``affix_cost_blood``）：回合開始時失去 HP。不是傷害（不觸發
    受傷類觸發、不受抗性與護盾影響），也不會致死（最低剩 1）。"""

    type: Literal["gear_hp_lost"] = "gear_hp_lost"
    unit_id: UnitId
    affix_id: str
    amount: int
    hp_before: int
    hp_after: int


class GearTriggered(EventBase):
    """裝備的觸發詞條觸發（Phase 3G-G3a；第 6 類）。

    ``trigger``：觸發時機 ID（``skill_triggers.yaml``）；``other_id``：該時機的另一方；
    ``trigger_depth``：觸發深度（同 ``skill_triggered``）。之後是效果原本的事件。
    """

    type: Literal["gear_triggered"] = "gear_triggered"
    unit_id: UnitId
    affix_id: str
    name_zh: str
    trigger: str
    other_id: UnitId | None
    trigger_depth: int


class ChargeActivated(EventBase):
    """裝備的充能詞條被啟動（Phase 3G-G3a；第 7 類，``activate_charge`` 動作）：花掉
    ``stacks_spent``
    層 ``stack_id`` 與 ``ap_spent`` AP，之後是效果原本的事件。"""

    type: Literal["charge_activated"] = "charge_activated"
    unit_id: UnitId
    affix_id: str
    name_zh: str
    stack_id: str
    stacks_spent: int
    ap_spent: int
    target_id: UnitId | None


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


class ApRefunded(EventBase):
    """擊殺時效果 ``refund_ap``（Phase 3D-8b）：``unit_id`` 獲得 ``amount`` AP（已扣掉超過 AP 上限的
    部分；用專用的效果，不是 ``grant_ap``）。"""

    type: Literal["ap_refunded"] = "ap_refunded"
    unit_id: UnitId
    skill_id: str
    amount: int
    ap_after: int


class UnitRevived(EventBase):
    """復活（``revive``，Phase 3D-8b）：倒下的 ``unit_id`` 以 ``hp`` 站起來，站在 ``pos``（原位置
    ``from_pos`` 被占用或不能站立時為最近的空格）；``source_id`` 是施放者。"""

    type: Literal["unit_revived"] = "unit_revived"
    unit_id: UnitId
    source_id: UnitId
    skill_id: str
    hp: int
    pos: Pos
    from_pos: Pos


class BombTicked(EventBase):
    """定時炸彈（``delayed_damage``，Phase 3D-8b）的環境回合倒數：``unit_id`` 身上的炸彈還剩
    ``remaining`` 輪（歸零時改發 ``bomb_exploded``）。"""

    type: Literal["bomb_ticked"] = "bomb_ticked"
    unit_id: UnitId
    remaining: int
    pos: Pos
    radius: int


type BombCause = Literal["timer", "downed"]
"""炸彈爆炸的原因：倒數歸零、攜帶者倒下。"""


class BombExploded(EventBase):
    """定時炸彈在 ``pos`` 爆炸（Phase 3D-8b）：攜帶者 ``unit_id``（``cause: downed`` 時已倒下）、
    施放者 ``source_id``；影響範圍是 ``tiles``（半徑 ``radius`` 內的格子）。受傷的單位由其後的
    ``damage_dealt`` 事件說明。"""

    type: Literal["bomb_exploded"] = "bomb_exploded"
    unit_id: UnitId
    source_id: UnitId
    skill_id: str
    pos: Pos
    radius: int
    element: Element
    cause: BombCause
    tiles: tuple[Pos, ...] = ()


class DeathCheated(EventBase):
    """不死（``cheat_death`` 的狀態）擋下致命傷害：HP 留在 1，之後移除該狀態（``spent``）。"""

    type: Literal["death_cheated"] = "death_cheated"
    unit_id: UnitId
    status_id: str
    prevented: int
    """多擋下的傷害（原本會扣到 0 以下的部分 ＋ 1）。"""


class DamageRedirected(EventBase):
    """``redirect_damage`` 的連結：``from_id`` 受到的傷害有 ``amount`` 點轉給 ``to_id``（施放者）。
    ``to_id`` 直接扣 HP（不經護盾、抗性與元素修正）；不死狀態照常生效。"""

    type: Literal["damage_redirected"] = "damage_redirected"
    from_id: UnitId
    to_id: UnitId
    status_id: str
    amount: int
    hp_before: int
    hp_after: int


class ReactionsGranted(EventBase):
    """``extra_reaction``：``unit_id`` 本輪的反應次數上限 +``amount``（共 ``total`` 次額外）。"""

    type: Literal["reactions_granted"] = "reactions_granted"
    unit_id: UnitId
    source_id: UnitId
    amount: int
    total: int


class ResourceRestored(EventBase):
    """``restore_resource``（Phase 3D-1）：``unit_id`` 的 ``resource`` 回復了。``mana``：法力
    +``amount``（實際回復量），``mana_after`` 為回復後的法力；``cooldown``：``skill_ids`` 的冷卻各
    −``amount``（每個技能另有 ``skill_cooldown_changed``）。"""

    type: Literal["resource_restored"] = "resource_restored"
    unit_id: UnitId
    source_id: UnitId
    resource: Literal["mana", "cooldown"]
    amount: int
    mana_after: int | None
    skill_ids: tuple[str, ...]


class SkillCopied(EventBase):
    """``copy_skill``：``unit_id`` 立即複製施放 ``source_id`` 本輪最後施放的 ``skill_id``
    （不扣法力、不進冷卻、不花源力；後續是一般的施放結算）。"""

    type: Literal["skill_copied"] = "skill_copied"
    unit_id: UnitId
    source_id: UnitId
    skill_id: str
    name_zh: str
    tiles: tuple[Pos, ...]


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


class TrapRevealed(EventBase):
    """``reveal`` 揭露了敵方陷阱（Phase 3D-8a）：``team`` 的玩家之後看得到它。只給揭露者的陣營
    （見 ``event_filter``）；``unit_id`` 是施放者。"""

    type: Literal["trap_revealed"] = "trap_revealed"
    unit_id: UnitId
    team: Team
    pos: Pos
    skill_id: str


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


class UnitSummoned(EventBase):
    """召喚物出現（Phase 3D-4a）：``owner_id`` 以 ``skill_id`` 召喚 ``template_id``，排在先攻順序
    ``order_index`` 的位置（緊接在召喚者之後），在召喚者第 ``expires_round`` 輪的回合結束時消失。"""

    type: Literal["unit_summoned"] = "unit_summoned"
    unit_id: UnitId
    owner_id: UnitId
    template_id: str
    team: Team
    pos: Pos
    skill_id: str
    expires_round: int
    order_index: int
    orphan: bool = False
    """召喚者已不在場（Phase 3D-6，規則改變 ``on_downed_spawn`` 的分身）：在第 ``expires_round``
    輪的環境回合消失。"""
    max_hp: int | None = None
    """召喚物依施放者等級與屬性成長後的最大 HP（Phase 3-33b；舊紀錄沒有）。"""
    infusion: str | None = None
    """灌注的關鍵字（Phase 3-33b）；沒有灌注時 ``None``。"""


type SummonExpiryReason = Literal[
    "expired", "owner_gone", "limit", "sacrificed", "detonated", "toppled"
]
"""召喚物消失的原因：``expired`` 到期、``owner_gone`` 召喚者倒下或撤離、``limit`` 超過同時存在的
上限（最舊的消失）、``sacrificed`` 被召喚者獻祭（``sacrifice_summon``，Phase 3-24c）、
``detonated`` 自爆（爆裂傀儡，Phase 3-33e2a）、``toppled`` 土牆被推倒。"""


class SummonExpired(EventBase):
    """召喚物消失（Phase 3D-4a），離開戰場與先攻順序。"""

    type: Literal["summon_expired"] = "summon_expired"
    unit_id: UnitId
    owner_id: UnitId
    reason: SummonExpiryReason
    pos: Pos


class SummonModeSet(EventBase):
    """召喚物的模式改變（Phase 3-33c）：``owner_id`` 把召喚物 ``unit_id`` 切換為 ``mode``
    （``reason="order"``，集火帶 ``target_id``），或集火目標離場使牠退回跟隨
    （``reason="target_gone"``，
    ``target_id`` 為離場的目標）。"""

    type: Literal["summon_mode_set"] = "summon_mode_set"
    unit_id: UnitId
    owner_id: UnitId
    mode: SummonMode
    target_id: UnitId | None = None
    reason: Literal["order", "target_gone"] = "order"


class SummonCommanded(EventBase):
    """召喚者指揮召喚物（Phase 3-33c）：之後是牠的移動與攻擊事件（``dest`` 為移動的終點，沒有移動
    時 ``None``；``target_id`` 為普攻目標，沒有攻擊時 ``None``）。"""

    type: Literal["summon_commanded"] = "summon_commanded"
    unit_id: UnitId
    owner_id: UnitId
    dest: Pos | None = None
    target_id: UnitId | None = None


class SkillInfused(EventBase):
    """施放者 ``owner_id`` 把技能灌注給召喚物 ``unit_id``（Phase 3-33d）：代價已支付（``ap`` 是
    灌注的 AP，``mana``／``mana_after``／``hp_spent``／``cooldown`` 同 ``skill_used``；冷卻之後另有
    ``skill_cooldown_changed``）。召喚物在下一個自己的回合開始時施放。"""

    type: Literal["skill_infused"] = "skill_infused"
    unit_id: UnitId
    owner_id: UnitId
    skill_id: str
    name_zh: str
    ap: int
    mana: int
    mana_after: int
    stamina: int = 0
    """花費的耐力（武器技，Phase 3H-2）；``stamina_after`` 為使用後的耐力。"""
    stamina_after: int = 0
    hp_spent: int = 0
    cooldown: int | None = None


class InfusedSkillCast(EventBase):
    """召喚物 ``unit_id`` 施放灌注的技能（Phase 3-33d）：原點是牠的位置 ``origin``，``target_id``／
    ``target_pos``／``direction`` 是依模式選的目標，``tiles`` 是影響的格子（依 (y, x)）；之後是
    命中、傷害等事件。"""

    type: Literal["infused_skill_cast"] = "infused_skill_cast"
    unit_id: UnitId
    owner_id: UnitId
    skill_id: str
    name_zh: str
    origin: Pos
    target_id: UnitId | None = None
    target_pos: Pos | None = None
    direction: str | None = None
    tiles: tuple[Pos, ...] = ()


type InfusionFizzleReason = Literal["no_target", "controlled", "downed", "gone"]
"""灌注沒有施放的原因：``no_target`` 依模式選不到合法目標、``controlled`` 回合開始時被暈眩等
跳過回合的狀態控制、``downed`` 施放前被打倒、``gone`` 施放前消失（到期、召喚者離場、超過上限、
被獻祭；Phase 3-33e2b）。法力與冷卻都不退。"""


class InfusionFizzled(EventBase):
    """召喚物 ``unit_id`` 的灌注技能沒有施放就失效（Phase 3-33d；法力與冷卻不退）。"""

    type: Literal["infusion_fizzled"] = "infusion_fizzled"
    unit_id: UnitId
    owner_id: UnitId
    skill_id: str
    name_zh: str
    reason: InfusionFizzleReason


class SnareTriggered(EventBase):
    """藤蔓 ``unit_id`` 纏住了踏入相鄰格的敵人 ``target_id``（Phase 3-33e2b；接著是緩速與倒地的
    ``status_applied``）。"""

    type: Literal["snare_triggered"] = "snare_triggered"
    unit_id: UnitId
    target_id: UnitId
    status_id: str
    prone: bool


class SummonPulled(EventBase):
    """吸引圖騰 ``unit_id`` 把敵人 ``target_id`` 從 ``from_pos`` 往自己拉近 1 格（Phase 3-33e2b；
    接著是強制移動的 ``unit_moved``，拉進表面、陷阱照常結算）。"""

    type: Literal["summon_pulled"] = "summon_pulled"
    unit_id: UnitId
    target_id: UnitId
    from_pos: Pos


class TotemPulsed(EventBase):
    """圖騰的光環（Phase 3D-4b）：圖騰 ``unit_id`` 在自己的回合開始時，讓 ``targets`` 內的友方
    獲得 ``status_id``（接著是各目標的 ``status_applied``）。"""

    type: Literal["totem_pulsed"] = "totem_pulsed"
    unit_id: UnitId
    status_id: str
    duration: int
    radius: int
    targets: list[UnitId]


type DetonateReason = Literal["arrived", "adjacent", "downed"]
"""自爆的時機：走到敵人相鄰、回合開始時已相鄰、被打倒。"""


class SummonDetonated(EventBase):
    """召喚物自爆（Phase 3-33e2a，爆裂傀儡）：``unit_id`` 在 ``pos`` 爆炸，``radius`` 格內的敵人
    ``targets`` 受傷（接著是各目標的 ``damage_dealt``），``reason`` 為 ``arrived``（走到敵人相鄰）、
    ``adjacent``（回合開始時已相鄰）或 ``downed``（被打倒）。"""

    type: Literal["summon_detonated"] = "summon_detonated"
    unit_id: UnitId
    pos: Pos
    radius: int
    reason: DetonateReason
    targets: list[UnitId]


class WallToppled(EventBase):
    """土牆被推倒（Phase 3-33e2a）：``unit_id`` 往 ``direction`` 倒下，壓住 ``tiles``；壓到的單位
    ``units`` 與 ``breakable`` 物件 ``objects`` 受推倒傷害，單位並倒地（由觸發表結算，歸給
    ``source_id``）。土牆隨後消失（``summon_expired``，原因 ``toppled``）。"""

    type: Literal["wall_toppled"] = "wall_toppled"
    unit_id: UnitId
    pos: Pos
    direction: tuple[int, int]
    tiles: tuple[Pos, ...]
    units: tuple[UnitId, ...]
    objects: tuple[ObjectId, ...]
    source_id: UnitId | None


class ZoneCreated(EventBase):
    """施放者建立持續區域（Phase 3D-5）。``cells`` 是建立時的格子；``direction``／``speed`` 只有
    ``moving``；``expires_round`` 見 :class:`~trpg.engine.state.ZoneState`。"""

    type: Literal["zone_created"] = "zone_created"
    zone_id: int
    owner_id: UnitId
    skill_id: str
    anchor: Literal["tile", "caster", "moving"]
    when: Literal["enter", "turn_start", "both"]
    affects: Literal["enemies", "allies", "all"]
    cells: tuple[Pos, ...]
    expires_round: int
    direction: str | None = None
    speed: int = 0
    surface: Surface | None = None


class ZoneMoved(EventBase):
    """移動型區域在環境回合前進一格（Phase 3D-5；``speed`` 2 時一次環境回合有兩個事件）。
    ``cells`` 是前進後的格子（走到牆壁或地圖外的格子已移除）。跟隨型區域跟著施放者移動時不發
    事件（格子由施放者位置決定）。"""

    type: Literal["zone_moved"] = "zone_moved"
    zone_id: int
    owner_id: UnitId
    skill_id: str
    direction: str
    cells: tuple[Pos, ...]


class ZoneTriggered(EventBase):
    """區域對 ``unit_id`` 結算效果（Phase 3D-5）：``enter`` 進入區域（含區域建立、移動或跟隨到他
    身上）、``turn_start`` 回合開始時站在區域內；之後是效果的事件。"""

    type: Literal["zone_triggered"] = "zone_triggered"
    zone_id: int
    owner_id: UnitId
    skill_id: str
    unit_id: UnitId
    cause: Literal["enter", "turn_start"]
    trigger_depth: int = 0


type ZoneExpiryReason = Literal["timeout", "owner_gone", "limit", "blocked"]
"""區域消失的原因（Phase 3D-5）：到期、施放者離場（跟隨型）、超過上限（最舊的）、移動型的格子
全部走到牆壁或地圖外。"""


class ZoneExpired(EventBase):
    """持續區域消失（Phase 3D-5）。"""

    type: Literal["zone_expired"] = "zone_expired"
    zone_id: int
    owner_id: UnitId
    skill_id: str
    reason: ZoneExpiryReason
    cells: tuple[Pos, ...] = ()
    """消失前的格子（跟隨型為施放者當時位置展開的格子，施放者已倒下時為空）。"""


class RuneInscribed(EventBase):
    """施放者在 ``pos`` 刻下符文（Phase 3-23 ``inscribe``）：恰好帶 ``element`` 或 ``tag`` 之一，
    ``remaining`` 為剩餘的環境回合數。同一施放者在同一格再刻一次視為更新（舊的先以
    ``replaced`` 移除）。"""

    type: Literal["rune_inscribed"] = "rune_inscribed"
    rune_id: int
    owner_id: UnitId
    pos: Pos
    element: Element | None = None
    tag: str | None = None
    remaining: int


type RuneRemovalReason = Literal["expired", "limit", "detonated", "replaced"]
"""符文消失的原因（Phase 3-23）：到期、超過同時存在的上限（最舊的）、被引爆、同格重刻。"""


class RuneRemoved(EventBase):
    """符文消失（Phase 3-23）。``detonated`` 是消耗型原語 ``detonate_runes`` 的「讀取」。"""

    type: Literal["rune_removed"] = "rune_removed"
    rune_id: int
    owner_id: UnitId
    pos: Pos
    element: Element | None = None
    tag: str | None = None
    reason: RuneRemovalReason


class SkillActivated(EventBase):
    """常駐類傳說啟動（Phase 3D-6；緊接在 ``skill_used`` 與 ``source_changed`` 之後）。

    ``activation``：``timed`` 限時（``expires_round`` 那一輪持有者的回合開始時結束）或 ``battle``
    整場（``expires_round`` 為 ``None``）。``rule``：規則改變型傳說引用的規則改變 ID，修正型為
    ``None``。"""

    type: Literal["skill_activated"] = "skill_activated"
    unit_id: UnitId
    skill_id: str
    activation: Literal["timed", "battle"]
    expires_round: int | None = None
    rule: str | None = None


class SkillGranted(EventBase):
    """暫時獲得技能（``grant_skill``，Phase 3D-8c）：``unit_id`` 的技能列多了 ``skill_id``，持續
    ``duration`` 輪（在 ``unit_id`` 自己的回合結束時倒數）。``source_id`` 是施放者；``refreshed``：
    目標已經暫時擁有這個技能，只刷新了剩餘輪數。"""

    type: Literal["skill_granted"] = "skill_granted"
    unit_id: UnitId
    source_id: UnitId
    skill_id: str
    duration: int
    refreshed: bool = False


class SkillGrantExpired(EventBase):
    """暫時獲得的技能期滿消失（Phase 3D-8c；``unit_id`` 的回合結束時）；該技能的冷卻與使用次數
    紀錄一併清除。"""

    type: Literal["skill_grant_expired"] = "skill_grant_expired"
    unit_id: UnitId
    skill_id: str


class GambleRolled(EventBase):
    """賭注擲骰（Phase 3D-7a；命中判定之後、技能效果結算之前）：擲一次 d1000，``roll`` 不超過
    ``chance_permille`` 為成功（結算 ``win``），否則失敗（結算 ``lose``）。"""

    type: Literal["gamble_rolled"] = "gamble_rolled"
    unit_id: UnitId
    skill_id: str
    roll: int
    chance_permille: int
    success: bool


class BacklashTriggered(EventBase):
    """失手反噬（``cost.on_miss``，Phase 3D-7a）：攻擊沒有命中任何敵人，之後是反噬效果的事件。"""

    type: Literal["backlash_triggered"] = "backlash_triggered"
    unit_id: UnitId
    skill_id: str


class ActivationExpired(EventBase):
    """限時傳說（``activation: timed``）時間到，不再生效（Phase 3D-6；持有者的回合開始時）。"""

    type: Literal["activation_expired"] = "activation_expired"
    unit_id: UnitId
    skill_id: str


type RuleChangeKindName = Literal[
    "element_heals_allies", "push_any_object", "pass_through_apply", "on_downed_spawn"
]


class RuleChangeTriggered(EventBase):
    """規則改變生效了一次（Phase 3D-6；之後是實際的後果事件）。

    - ``element_heals_allies``：``other_id`` 是原本要受傷的友方（之後是 ``healed``）；
    - ``push_any_object``：``object_id`` 是原本推不動的物件（之後是 ``object_moved``）；
    - ``pass_through_apply``：``other_id`` 是經過的敵人（之後是狀態的抵抗與 ``status_applied``）；
    - ``on_downed_spawn``：持有者倒下（之後是 ``unit_summoned`` 或 ``effect_fizzled``）。
    """

    type: Literal["rule_change_triggered"] = "rule_change_triggered"
    unit_id: UnitId
    skill_id: str
    rule: str
    kind: RuleChangeKindName
    other_id: UnitId | None = None
    object_id: ObjectId | None = None
    amount: int = 0
    """``element_heals_allies``：被轉為治療的原本傷害。"""


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
    | UnitRan
    | UnitVaulted
    | GuardSet
    | UnitAimed
    | WeaponReloaded
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
    | ObjectHurled
    | ObjectToppled
    | ShotPierced
    | ObjectCreated
    | ObjectExpired
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
    | UnitSummoned
    | SummonExpired
    | SummonModeSet
    | SummonCommanded
    | SkillInfused
    | InfusedSkillCast
    | InfusionFizzled
    | SnareTriggered
    | SummonPulled
    | TotemPulsed
    | SummonDetonated
    | WallToppled
    | SkillUsed
    | SkillCooldownChanged
    | SkillTriggered
    | TriggerLimitReached
    | StacksChanged
    | TrapPlaced
    | TrapRevealed
    | TrapTriggered
    | TrapExpired
    | SourceChanged
    | ApGranted
    | ApRefunded
    | UnitRevived
    | BombTicked
    | BombExploded
    | DeathCheated
    | DamageRedirected
    | ReactionsGranted
    | ResourceRestored
    | UnitDashed
    | UnitCharged
    | SkillCopied
    | SkillFollowup
    | FollowupCharged
    | FollowupCancelled
    | ZoneCreated
    | ZoneMoved
    | ZoneTriggered
    | ZoneExpired
    | RuneInscribed
    | RuneRemoved
    | SkillActivated
    | ActivationExpired
    | SkillGranted
    | SkillGrantExpired
    | RuleChangeTriggered
    | GambleRolled
    | BacklashTriggered
    | OverloadTriggered
    | GearHpLost
    | GearTriggered
    | ChargeActivated,
    Field(discriminator="type"),
]

EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
EVENT_LIST_ADAPTER: TypeAdapter[list[Event]] = TypeAdapter(list[Event])
