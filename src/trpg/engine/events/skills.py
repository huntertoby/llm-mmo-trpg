"""技能事件（使用、追擊、觸發、堆疊、裝備、啟動與授予）。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from trpg.engine.events.base import EventBase
from trpg.shared.types import Pos, UnitId

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
    移動時範圍跟著移動）。``anchored``（BAL-21a，``followup.anchor: cast_tile``）時 ``pos`` 是施放時
    選的格子、``tiles`` 以它為中心，之後不隨施放者移動。"""

    type: Literal["followup_charged"] = "followup_charged"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    release: str
    pos: Pos
    tiles: tuple[Pos, ...]
    direction: str | None = None
    """定向蓄力（Phase 3J-2，龍的蓄力吐息）的方向；複合技能的延遲段為 ``None``。"""
    anchored: bool = False
    """落在施放時選的格子（BAL-21a）；``False``＝以施放者為中心、跟著施放者移動。"""
    lock_target_id: UnitId | None = Field(default=None, exclude_if=lambda v: v is None)
    """瞄準預告（RG-1，#162，``lock_on``）瞄準的單位：``pos``／``tiles`` 是他瞄準當下的格子，
    施放者下一個自己的回合開始時對他射出；不是瞄準時為 ``None``、不輸出。"""


class FollowupCancelled(EventBase):
    """延遲段（Phase 3F-4b）取消：``downed`` 施放者倒下、``controlled`` 被暈眩或冰凍
    （``skip_turn`` 的狀態）、``silenced`` 法術型蓄力被沉默打斷（Phase 5A-M1b）、
    ``expired`` 被攻擊才釋放的延遲段到下回合開始都沒被攻擊、
    ``replaced`` 施放了另一個延遲段、``form_left`` 蓄力吐息的形態解除了（Phase 3J-2）、
    ``part_broken`` 頭目的部位被打破（PB-1a，``seal_skill``／``interrupt_charge``）、
    ``interrupted`` 瞄準中（RG-1 ``lock_on``）被近戰攻擊命中。"""

    type: Literal["followup_cancelled"] = "followup_cancelled"
    unit_id: UnitId
    skill_id: str
    name_zh: str
    reason: Literal[
        "downed",
        "controlled",
        "silenced",
        "expired",
        "replaced",
        "form_left",
        "part_broken",
        "interrupted",
    ]


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
# Phase 3D-6：常駐傳說啟動、技能授予、賭博型技能
# ---------------------------------------------------------------------------


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
