"""源力、改寫規則型原語、形態與規則改寫事件。"""

from __future__ import annotations

from typing import Literal

from trpg.engine.events.base import EventBase
from trpg.shared.types import Element, ObjectId, Pos, UnitId

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
    """免死（``cheat_death`` 的狀態）擋下致命傷害：HP 留在 1，之後移除該狀態（``spent``）。"""

    type: Literal["death_cheated"] = "death_cheated"
    unit_id: UnitId
    status_id: str
    prevented: int
    """多擋下的傷害（原本會扣到 0 以下的部分 ＋ 1）。"""


class DamageRedirected(EventBase):
    """``redirect_damage`` 的連結：``from_id`` 受到的傷害有 ``amount`` 點轉給 ``to_id``（施放者）；
    或分傷（``share_damage``，Phase 5A-M2「連心」）：``from_id`` 的傷害分 ``amount`` 點給同門
    ``to_id``。
    ``to_id`` 直接扣 HP（不經護盾、抗性與元素修正）；免死狀態照常生效。"""

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
# Phase 3J：形態、架勢、規則改寫、誓約
# ---------------------------------------------------------------------------


class FormEntered(EventBase):
    """進入形態（Phase 3J-1a，6.30）：``element`` 是進入時選的元素（沒有選擇為 ``None``）；
    ``max_hp``／``hp`` 是進入後的最大 HP 與目前 HP。之後是進入獎勵的事件（護盾、治療、傷害……）。"""

    type: Literal["form_entered"] = "form_entered"
    unit_id: UnitId
    form_id: str
    skill_id: str | None = None
    element: Element | None = None
    max_hp: int
    hp: int


type FormLeaveReason = Literal[
    "cancelled", "switched", "stance", "downed", "escaped", "upkeep", "battle_end", "released"
]
"""離開形態的原因：``cancelled`` 自己取消（``end_stance``）、``switched`` 切換到別的形態、
``stance`` 進入一般姿態、``downed`` 倒下、``escaped`` 撤離、``upkeep`` 維持費不夠自動解除、
``battle_end`` 戰鬥結束、``released`` 技能的 ``leave_form`` 效果解除（Phase 3J-4c）。"""


class FormLeft(EventBase):
    """離開形態（Phase 3J-1a）：之後該形態冷卻 ``cooldown`` 回合；``max_hp``／``hp`` 是離開後的
    最大 HP 與目前 HP（最大 HP 減回、目前 HP 不超過上限）。"""

    type: Literal["form_left"] = "form_left"
    unit_id: UnitId
    form_id: str
    reason: FormLeaveReason
    cooldown: int
    max_hp: int
    hp: int


class FormUpkeepPaid(EventBase):
    """回合開始付形態的維持費（Phase 3J-1a）：``resource`` 是 ``stamina``（物理形態）或
    ``mana``（心智形態），``remaining`` 是付完後剩下的量。付不起時不發出，改發 ``form_left``
    （``reason: upkeep``）。"""

    type: Literal["form_upkeep_paid"] = "form_upkeep_paid"
    unit_id: UnitId
    form_id: str
    resource: Literal["stamina", "mana"]
    amount: int
    remaining: int


class StanceUpkeepPaid(EventBase):
    """回合開始付一般姿態的維持費（Phase 3W-2b，``SkillDef.stance_upkeep``）：``resource`` 是
    ``stamina``（武器技）或 ``mana``（法術技），``remaining`` 是付完後剩下的量。付不起時不發出，
    改發 ``status_removed``（``reason: upkeep``）。"""

    type: Literal["stance_upkeep_paid"] = "stance_upkeep_paid"
    unit_id: UnitId
    skill_id: str
    status_id: str
    resource: Literal["stamina", "mana"]
    amount: int
    remaining: int


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


class OathBroken(EventBase):
    """違反誓約（Phase 5C-3，06 6.26）：``at_end`` 為 ``False``（戰鬥中）時之後移除加成、施加破誓；
    ``True`` 時是戰鬥結束時判定「每場至少……」沒達到（沒有效果）。``check`` 是判定種類。"""

    type: Literal["oath_broken"] = "oath_broken"
    unit_id: UnitId
    template: str
    check: str
    at_end: bool = False
