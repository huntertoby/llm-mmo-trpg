"""戰鬥事件（命中、傷害、治療、護盾、狀態、技巧動作、推擊、反應）。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from trpg.engine.events.base import AdvantageState, DamageCause, EventBase
from trpg.shared.types import Attribute, Element, ObjectId, Pos, UnitId

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
    cover_unit_id: UnitId | None = Field(default=None, exclude_if=lambda v: v is None)
    """盾兵掩護（RG-1，#162）：替目標擋遠程攻擊的盾兵（``cover`` 是它的命中修正）；沒有時不輸出。
    塔盾詞條「盾陣」（RG-4，#163）時是帶盾陣的隊友，並且 ``cover_formation`` 為真。"""
    cover_formation: bool = Field(default=False, exclude_if=lambda v: not v)
    """``cover_unit_id`` 是盾陣（RG-4）而不是盾兵；不是時不輸出。"""
    modifier_bonus: int = 0
    backstab: int = 0
    """背刺的命中加值（Phase 3D-8d；0 為不是背刺；暴擊範圍另外擴大
    ``backstab_crit_range_bonus``）。"""
    ambush: int = 0
    """潛行偷襲的命中加值（Phase 3D-8d；攻擊者帶 ``concealed`` 狀態；0 為沒有）。"""
    no_turn: Literal["concealed", "silent"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    """這次近戰攻擊的目標不轉向（BS-1，#157，06 6.21.1）：``concealed`` 從隱蔽中出手、``silent``
    無聲（手持匕首類的修正規則）；照常轉向（含遠程、打自己）時為 ``None``，不輸出。和 ``backstab``
    一起成立時，紀錄與預覽顯示「背刺・無聲（不會轉身）」。"""
    hit_tile: Pos | None = Field(default=None, exclude_if=lambda v: v is None)
    """打中巨型目標的那一格（GB-1b，05 5.12.4 第 2、4 點）：單體＝離攻擊者最近的佔格，範圍技＝範圍內
    離範圍中心最近的佔格（同距離 (y, x) 小）；演出落點用它。一格的目標為 ``None``，不輸出。"""


class ConductBlocked(EventBase):
    """雷電擴散被「每輪一次」擋下（BAL-13d，#78）：``unit_id`` 本輪已受過擴散傷害，這次的擴散不結算
    （不改數值，只讓戰鬥紀錄看得到）。``source_id`` 是引發擴散的單位。"""

    type: Literal["conduct_blocked"] = "conduct_blocked"
    unit_id: UnitId
    source_id: UnitId | None = None


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
    chain_permille: int = 1000
    """連鎖衰減（‰，已包含在 ``multiplier_permille`` 裡，也乘在 ``base_amount`` 上；BAL-13c）。"""
    base_amount: int | None = None
    """套用目標自身的元素修正與格擋等倍率 **之前** 的傷害（已含暴擊骰與天氣）。

    雷電擴散以此為基準（Phase 1C 決定 #3），每個被擴散的單位再各自套用自己的元素修正。
    ``None`` 表示與 ``amount`` 相同（以最大 HP 比例計算的傷害）。"""
    status_ppm: int = 1_000_000
    """狀態的傷害倍率（百萬分比）：攻擊者的 ``damage_dealt_permille``（虛弱，只對 ``attack``）
    × 目標的 ``damage_taken_permille``（易傷、護衛，骰值傷害）。"""
    absorbed: int = 0
    """被護盾吸收的點數（Phase 2D-1）。``amount`` 是所有倍率之後、護盾之前的傷害；實際扣血為
    ``amount − absorbed − redirected − shared``（即 ``hp_before − hp_after``，致命以上的過量
    不算在內）。"""
    redirected: int = 0
    """轉給連結者（``redirect_damage`` 的狀態，Phase 3C-4b）的點數；轉移本身是緊接著的
    ``damage_redirected`` 事件。"""
    shared: int = 0
    """分給同門（``share_damage`` 的狀態，Phase 5A-M2「連心」）的總點數；實際扣血為
    ``amount − absorbed − redirected − shared``。每名同門各一個緊接著的 ``damage_redirected``。"""
    formation_permille: int = 1000
    """攻擊者的陣法倍率（‰，Phase 5A-M2「劍陣」；已包含在 ``status_ppm`` 裡，供紀錄分開顯示）。"""
    ward_permille: int = 1000
    """目標受到的護陣倍率（‰，Phase 5A-M2b；已包含在 ``status_ppm`` 裡，供紀錄分開顯示）。"""
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
    """目標受到的治療倍率（‰）：狀態（中毒 500）× 站在水上（``wet_heal_permille``，BAL-16b）。"""
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
    status_id: str = "shielded"
    """吸收傷害的護盾狀態（3W-2b：有附帶效果的護盾是另一種狀態）。"""
    source_id: UnitId | None = None
    melee: bool = False
    """這次傷害是相鄰的攻擊（近戰；反傷的條件）。"""


class ShieldEnded(EventBase):
    """帶附帶效果的護盾結束了（Phase 3W-2b）：被打破（``broken``，``breaker_id`` 是造成傷害的單位）
    或到期。結束回復、破盾造表面與破盾施加狀態由這個事件觸發。"""

    type: Literal["shield_ended"] = "shield_ended"
    unit_id: UnitId
    status_id: str
    broken: bool
    breaker_id: UnitId | None = None


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
        "upkeep",
    ]
    """``ambushed``：隱蔽中發動攻擊（潛行偷襲）後脫離隱蔽（Phase 3D-8d）；
    ``fired``：監視（``overwatch``）射擊後結束（Phase 3D-8c）；
    ``dispelled``：被 ``dispel`` 驅散；``revealed``：被 ``reveal`` 移除隱蔽（Phase 3D-8a）；
    ``stolen``：被 ``steal_buff`` 奪走（Phase 3D-1；緊接著對施放者的 ``status_applied``）；
    ``spent``：免死（``undying``）擋下致命傷害後移除（Phase 3C-4a）；
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
    """``steadfast`` 使推擊距離減少；``immovable``（石像，Phase 3-33e2a）使推擊完全無效；
    ``race_stonewall``（矮人種族技）使推擊完全無效、``race_heavy``（獸人環境被動）在危險地形旁
    少推 1 格（Phase 3R-2）。"""

    type: Literal["push_resisted"] = "push_resisted"
    unit_id: UnitId
    requested: int
    distance: int
    reason: Literal["steadfast", "immovable", "race_stonewall", "race_heavy"] = "steadfast"


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
    decoy: bool = False
    """``True`` 為狐火誘餌（Phase 3R-2b）：攻擊在擲命中之前轉向誘餌而落空，誘餌隨即消散。"""


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
