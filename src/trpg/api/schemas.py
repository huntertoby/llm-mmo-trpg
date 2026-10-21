"""API 的請求與回應模型（Phase 3-2）。

引擎的 pydantic 模型（``Action``、``Pending``、``BattleView``、``OrderSet``……）直接當 API 格式；
這裡只定義 API 專屬的外層與 ``Preview``（引擎的 dataclass，含完整狀態，不能直接外流）的公開版本。

機率與期望值以 **整數千分比** 表示（``*_permille``、``*_milli``，四捨五入），與引擎的 ‰ 慣例一致。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.engine.actions import Action, FollowupTarget, Step, UseSkill
from trpg.engine.ai.orders import IgnoredOrder, OrderSet
from trpg.engine.preview import (
    DamageRange,
    GambleOutcome,
    GrantInfo,
    HurlInfo,
    Outcome,
    PierceInfo,
    Preview,
    ReviveInfo,
    StatusChance,
    SummonInfo,
    TargetPreview,
    ToppleInfo,
)
from trpg.engine.results import Pending
from trpg.engine.view import BattleView
from trpg.shared.rng import MASK64
from trpg.shared.types import ObjectId, Pos, Team, UnitId

__all__ = [
    "Awaiting",
    "BattleHistory",
    "BattleOutcome",
    "BattleResponse",
    "BombOut",
    "BombPreviewOut",
    "BuildSummary",
    "ChargeOut",
    "CoverOut",
    "CreateBattleRequest",
    "DamageOut",
    "DecisionRequest",
    "Glossary",
    "GlossaryEntry",
    "GrantPreviewOut",
    "HealOut",
    "HistoryStepOut",
    "HurlOut",
    "InteractOptionOut",
    "MapSummary",
    "OutcomeOut",
    "PierceObjectOut",
    "PierceOut",
    "PreviewOut",
    "ReviveOut",
    "RunOptionOut",
    "SkillReasons",
    "StatusChanceOut",
    "StepOut",
    "TargetOut",
    "TelegraphChangeOut",
    "TelegraphOut",
    "ToppleOut",
    "UpcomingEventOut",
    "permille",
    "preview_out",
]

type XY = tuple[int, int]

Awaiting = Literal["action", "decision", "ended", "stalled"]
"""伺服器在等什麼：主角的動作、主角的反應決定、戰鬥已結束；``stalled`` 只在自動推進超過步數
上限（500）之後出現。"""


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# 內容
# ---------------------------------------------------------------------------


class MapSummary(_ApiModel):
    id: str
    name_zh: str
    archetype: str
    width: int
    height: int


class BuildSummary(_ApiModel):
    id: str
    name_zh: str
    theme_zh: str
    skills: tuple[str, ...]
    max_mana: int = 0
    """主角（未分配屬性點前）的法力上限；工坊試玩比對技能法力需求用。"""
    max_hp: int = 0
    """主角（未分配屬性點前）的 HP 上限（開新一輪畫面用）。"""
    weapon: str = ""
    weapon_name_zh: str = ""
    """主角的武器（ID 與中文名）。"""


class SkillReasons(_ApiModel):
    """主角灰掉的技能 → 引擎的拒絕理由（繁體中文）；可以用的技能不在表內（Phase 3-5c-2）。"""

    reasons: dict[str, str]


class GlossaryEntry(_ApiModel):
    id: str
    name_zh: str
    description_zh: str | None = None
    tags: tuple[str, ...] = ()
    rules_zh: tuple[str, ...] = ()
    """靜態規則說明（Phase 3-15）：地形、表面、物件「會怎樣」的中文短句，由內容資料產生。"""


class Glossary(_ApiModel):
    """名詞對照表（由內容庫產生）：ID → 中文名與簡短說明。"""

    terrain: tuple[GlossaryEntry, ...]
    surfaces: tuple[GlossaryEntry, ...]
    objects: tuple[GlossaryEntry, ...]
    statuses: tuple[GlossaryEntry, ...]
    stacks: tuple[GlossaryEntry, ...]
    reactions: tuple[GlossaryEntry, ...]
    elements: tuple[GlossaryEntry, ...]
    attributes: tuple[GlossaryEntry, ...]


# ---------------------------------------------------------------------------
# 戰鬥
# ---------------------------------------------------------------------------


class CreateBattleRequest(_ApiModel):
    """建立戰鬥。``ally_builds`` 省略時與 ``trpg battle --ally-build <hero_build>`` 相同，以標準
    隊友補齊到 3 人；給了（可以是空串列）就只用 ``hero_build`` ＋ 這些 build。"""

    map_id: str
    seed: int = Field(ge=0, le=MASK64)
    hero_build: str
    ally_builds: tuple[str, ...] | None = None
    max_rounds: int = Field(default=30, ge=1, le=200)
    custom_skills: tuple[dict[str, Any], ...] = ()
    """技能工坊「裝上試玩」（Phase 3F-1）：自訂技能定義（技能定義的 JSON，與
    ``/api/workshop/check`` 的 ``skill`` 同格式）。每個都必須通過驗證，以 ``Ruleset.with_skills``
    加入規則包、裝到主角身上（裝備上限照常檢查）；不合法時 422 並列出中文原因。"""
    replace_skills: tuple[str, ...] = ()
    """要從主角身上拿掉的技能 ID；自訂技能依序放進被拿掉的位置，多出來的接在最後（空欄位）。"""
    opponents: str | None = None
    """靶場（地圖類型 ``training``）的對手：``content/workshop.yaml`` 的 ``opponents`` 之一
    （``dummy`` 木樁、``fighting`` 會反擊），省略為第一個。其他地圖不可填。"""


class DecisionRequest(_ApiModel):
    accept: bool
    """反應詢問：是否使用反應；``copy_skill`` 選目標：``false`` 為放棄施放（不付代價）。"""
    copy_cast: UseSkill | None = None
    """``copy_skill`` 選目標（``pending.kind == "copy_skill"``）時，複製技能的選取（從回應的
    ``copy_options`` 挑一個）；反應詢問不使用。"""
    followup_target: FollowupTarget | None = None
    """複合技能第二段選目標（``pending.kind == "followup"``，Phase 3F-4a）時，第二段的選取（從
    回應的 ``followup_options`` 挑一個的 ``followup_target``）；``accept: false`` 為放棄第二段
    （第一段已經結算）。"""


class StepOut(_ApiModel):
    """自動推進中結算的一步。``actor_id`` 與 ``step`` 在開場時為 ``None``。

    ``events`` 已依我方視角過濾（:func:`trpg.engine.event_filter.filter_events`），每個事件是
    事件的 JSON 再加上 ``text``（繁體中文描述；沒有描述的事件不含此鍵）。``seq`` 保留原值，
    過濾後可能跳號。
    """

    actor_id: UnitId | None
    step: Step | None
    events: tuple[dict[str, Any], ...]
    view: BattleView
    """這一步結算後的戰場（我方視角）；前端逐步播放時用。"""


class TelegraphChangeOut(_ApiModel):
    """預告的一項變化（:class:`trpg.engine.environment.TelegraphChange` ＋ 中文 ``text``）。"""

    kind: str
    pos: Pos | None
    before: str | None
    after: str | None
    object_id: ObjectId | None
    unit_id: UnitId | None
    amount: int | None
    tiles: tuple[Pos, ...] = ()
    """持續區域（Phase 3D-5）：``zone_moved`` 前進後的格子、``zone_expired`` 消失前的格子。"""
    text: str


class BurningOut(_ApiModel):
    object_id: ObjectId
    pos: Pos
    remaining: int
    """還能撐幾次環境回合。"""
    text: str


class BombOut(_ApiModel):
    """帶著定時炸彈的單位（Phase 3D-8b）：倒數、爆炸半徑與波及的格子。"""

    unit_id: UnitId
    pos: Pos
    remaining: int
    """還要幾次環境回合爆炸（1 ＝ 下一次環境回合爆炸）。"""
    radius: int
    tiles: tuple[Pos, ...]
    explodes: bool
    text: str


class ChargeOut(_ApiModel):
    """等待中的延遲段（Phase 3F-4b）：施放者、技能、釋放時機與以施放者目前位置推算的預計範圍。"""

    unit_id: UnitId
    skill_id: str
    name_zh: str
    release: str
    """``next_turn``（施放者下回合開始時釋放）或 ``attacked``（下回合開始前被敵人攻擊就釋放）。"""
    remaining: int
    """還要幾回合（1 ＝ 施放者下回合開始）。"""
    pos: Pos
    tiles: tuple[Pos, ...]
    text: str


class UpcomingEventOut(_ApiModel):
    round: int
    kind: str
    tiles: tuple[XY, ...]
    text: str


class TelegraphOut(_ApiModel):
    """下一次環境回合（本輪結束時）將發生的變化（Phase 3-4b）。以我方看得見的狀態模擬，
    不含隱藏陷阱與亂數狀態。"""

    round: int
    changes: tuple[TelegraphChangeOut, ...]
    burning: tuple[BurningOut, ...]
    upcoming: tuple[UpcomingEventOut, ...]
    """再下一輪結束時的地圖事件（提前一輪預告）。"""
    bombs: tuple[BombOut, ...] = ()
    """目前帶著定時炸彈的單位與倒數（Phase 3D-8b）。"""
    charges: tuple[ChargeOut, ...] = ()
    """等待中的延遲段（Phase 3F-4b；在施放者的回合開始時結算，不在環境回合）。"""


class InteractOptionOut(_ApiModel):
    """主角相鄰的可推動物件的一種互動（推、往左撥、往右撥）及其是否合法（Phase 3C-1）。
    ``legal_actions`` 只列合法的；這裡連不合法的也列出，讓介面灰掉並顯示原因。"""

    object_id: ObjectId
    mode: Literal["push", "shove_aside"]
    side: Literal["left", "right"] | None
    legal: bool
    reason: str | None
    """不合法的原因（繁體中文）；合法時 ``None``。"""
    to_pos: Pos | None
    """物件會移到的格子（即使不合法也給出）；會被推出地圖左／上緣時 ``None``。"""


class RunOptionOut(_ApiModel):
    """跑步（Phase 3-20）目前是否合法與原因；``legal_actions`` 只在合法時列出 ``run``，這裡讓介面在
    不合法時灰掉按鈕並顯示原因（「已經跑過了」「被定身，不能跑」「AP 不足」）。"""

    legal: bool
    reason: str | None
    """不合法的原因（繁體中文）；合法時 ``None``。"""
    ap_cost: int
    move_bonus: int
    """跑步增加的移動點數。"""


class FollowupOptionOut(_ApiModel):
    """複合技能第二段的一個合法選取（Phase 3F-4a，``pending.kind == "followup"`` 時）：
    ``followup_target`` 原樣放進 ``DecisionRequest``；``tiles`` 是這個選取影響的格子
    （依 (y, x)）。"""

    followup_target: FollowupTarget
    tiles: tuple[XY, ...]


class BattleOutcome(_ApiModel):
    winner: Team | None
    """``None`` 為平手。"""
    end_reason: str | None
    round: int


class HistoryStepOut(_ApiModel):
    """戰鬥紀錄的一步：只有事件（含中文 ``text``），不含戰場視圖。"""

    events: tuple[dict[str, Any], ...]


class BattleHistory(_ApiModel):
    """到目前為止戰鬥發生過的事件（依序；重新整理或讀檔後還原戰鬥紀錄用）。"""

    steps: tuple[HistoryStepOut, ...]


class BattleResponse(_ApiModel):
    """建立、讀取、動作、決定、戰術指令共用的回應。"""

    battle_id: str
    hero_id: UnitId
    awaiting: Awaiting
    initial_view: BattleView
    """本次請求開始推進 **之前** 的戰場（建立戰鬥時為開場事件之後、第一個動作之前）；沒有推進時
    與 ``view`` 相同。"""
    view: BattleView
    legal_actions: tuple[Action, ...]
    """輪到主角（``awaiting == "action"``）時的合法動作（含 ``end_turn``）；其他時候為空。"""
    interact_options: tuple[InteractOptionOut, ...]
    """輪到主角時，相鄰可推動物件的互動選項（含不合法與原因）；其他時候為空。"""
    pending: Pending | None
    copy_options: tuple[UseSkill, ...]
    """``pending.kind == "copy_skill"`` 時，複製技能（``pending.copy_skill_id``）目前所有合法的
    選取（``DecisionRequest.copy_cast`` 從中挑一個）；其他時候為空。"""
    run_option: RunOptionOut | None = None
    """輪到主角時，跑步是否合法與原因（Phase 3-20）；其他時候 ``None``。"""
    followup_options: tuple[FollowupOptionOut, ...] = ()
    """``pending.kind == "followup"``（Phase 3F-4a）時，複合技能（``pending.skill_id``）第二段
    從施放者目前位置所有合法的選取；其他時候為空。"""
    """主角的反應詢問（只有公開欄位）。"""
    orders: OrderSet
    """我方隊友目前的戰術指令。"""
    orders_ignored: tuple[IgnoredOrder, ...]
    """目前指令中已經無法執行的（例如集火的目標已倒下）與原因；AI 會略過它們。"""
    telegraph: TelegraphOut
    """下一次環境回合的預告。"""
    steps: tuple[StepOut, ...]
    """這次請求推進的每一步（依序）。"""
    outcome: BattleOutcome | None
    """戰鬥結束時的勝負與原因。"""


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def permille(value: Fraction | None) -> int | None:
    """``Fraction`` → 四捨五入的整數千分比（``None`` 照舊）。"""
    if value is None:
        return None
    scaled = value * 1000
    return (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)


def _milli(value: Fraction) -> int:
    result = permille(value)
    assert result is not None
    return result


class DamageOut(_ApiModel):
    minimum: int
    maximum: int
    expected_milli: int
    """期望傷害 ×1000（已乘上命中率）。"""
    expected_if_hit_milli: int


class OutcomeOut(_ApiModel):
    kind: str
    unit_id: UnitId | None
    object_id: ObjectId | None
    pos: XY | None
    detail: str | None


class StatusChanceOut(_ApiModel):
    status_id: str
    original_id: str
    apply_permille: int
    diminished: bool


class TargetOut(_ApiModel):
    unit_id: UnitId
    hit_permille: int
    crit_permille: int
    damage: DamageOut | None
    ally: bool
    knock_permille: int | None
    status_chances: tuple[StatusChanceOut, ...]


class CoverOut(_ApiModel):
    penalty: int
    object_id: ObjectId
    kind: str
    name_zh: str
    pos: XY


class HealOut(_ApiModel):
    unit_id: UnitId
    minimum: int
    maximum: int


class CollisionOut(_ApiModel):
    """撞擊傷害預覽（Phase 3C-3a）：某單位受到的撞擊傷害總和（最少、最多後果）。"""

    unit_id: UnitId
    minimum: int
    maximum: int


class PierceObjectOut(_ApiModel):
    object_id: ObjectId
    pos: XY


class PierceOut(_ApiModel):
    """穿透技能的射線預覽（Phase 3C-5b）：路線、穿過的物件與後方受打折傷害的單位。"""

    route: tuple[XY, ...]
    """施放者與目標之間的格子（不含兩端；直線為影響範圍）。"""
    objects: tuple[PierceObjectOut, ...]
    """穿過的 ``penetrable`` 物件（受全額傷害）。"""
    behind: tuple[UnitId, ...]
    """位於這些物件後方的單位。"""
    behind_permille: int
    """後方單位受到的傷害（‰）。"""


class ToppleOut(_ApiModel):
    """預覽中的推倒（Phase 3C-5b）：物件、倒下的方向、壓住的格子與單位、倒塌物的位置。"""

    object_id: ObjectId
    pos: XY
    direction: XY
    tiles: tuple[XY, ...]
    units: tuple[UnitId, ...]
    rubble: XY | None


class HurlOut(_ApiModel):
    """預覽中的物件投擲（Phase 3C-5b）：``outcome`` 為 exploded／shattered／placed／lost。"""

    object_id: ObjectId
    kind: str
    from_pos: XY
    to_pos: XY
    outcome: str
    placed_pos: XY | None


class SummonOut(_ApiModel):
    """預覽中會出現的召喚物（Phase 3D-4b）：``expires_round`` 是在召喚者第幾輪的回合結束時消失，
    ``totem_radius`` 是圖騰的光環半徑（不是圖騰為 ``None``），``replaces`` 是因超過同時存在的上限
    而消失的舊召喚物。"""

    unit_id: UnitId
    template_id: str
    name_zh: str
    pos: XY
    expires_round: int
    max_hp: int
    totem_radius: int | None
    replaces: tuple[UnitId, ...]


class BombPreviewOut(_ApiModel):
    """預覽中會綁上的定時炸彈（Phase 3D-8b）：``rounds`` 次環境回合後爆炸，``tiles`` 是以攜帶者
    目前位置展開的波及格子。"""

    unit_id: UnitId
    rounds: int
    radius: int
    tiles: tuple[XY, ...]


class ReviveOut(_ApiModel):
    """預覽中的復活（Phase 3D-8b）：站起來的單位、HP 與站的格子（``from_pos`` 是倒下的位置）。"""

    unit_id: UnitId
    hp: int
    pos: XY
    from_pos: XY


class GrantPreviewOut(_ApiModel):
    """預覽中暫時獲得的技能（Phase 3D-8c）：``unit_id`` 暫時獲得 ``skill_id``（``name_zh``）
    ``duration`` 輪；``refreshed``：已經暫時擁有，只刷新輪數。"""

    unit_id: UnitId
    skill_id: str
    name_zh: str
    duration: int
    refreshed: bool


class MoveOut(_ApiModel):
    """預覽中的自身位移（Phase 3D-2）：``kind`` 為 dash（路線，``other_id`` 是衝鋒的目標）／
    leap（起點與落點）／swap（``unit_id`` 與 ``other_id`` 交換，``path`` 是 ``unit_id`` 的起點與
    終點）。"""

    kind: str
    unit_id: UnitId
    other_id: UnitId | None
    path: tuple[XY, ...]


class DisplaceCheckOut(_ApiModel):
    """預覽中的位移抵抗判定（Phase 3D-2b）：敵方 ``unit_id`` 被移動的成功率（千分比）；
    ``resist_bonus`` 是目標的抵抗加成，``lethal`` 為落點是致命地形。"""

    unit_id: UnitId
    success_permille: int
    resist_bonus: int
    lethal: bool


class GambleBranchOut(_ApiModel):
    """賭注一個分支的預覽（Phase 3D-7a）：``kind`` 為 ``win``／``lose``，``permille`` 是這個分支
    發生的機率（命中之後）。``multiplier_permille`` 是本次傷害的倍率；``targets`` 是強制這個分支時
    各目標的命中率與傷害範圍（已含倍率）；``self_damage_*`` 是施放者自己受到的傷害（最少與最多）、
    ``self_statuses`` 是他獲得的狀態、``self_healed_*`` 是他回復的 HP。"""

    kind: Literal["win", "lose"]
    permille: int
    multiplier_permille: int
    targets: tuple[TargetOut, ...]
    self_damage_min: int
    self_damage_max: int
    self_statuses: tuple[str, ...]
    self_healed_min: int
    self_healed_max: int


class GambleOut(_ApiModel):
    """賭注技能的預覽（Phase 3D-7a）：成功率與兩個分支（依序 ``win``、``lose``）。玩家是在知情下
    下注：網頁依它列出「60%：傷害 ×2｜40%：你受 15 傷害」。"""

    chance_permille: int
    branches: tuple[GambleBranchOut, GambleBranchOut]


class PreviewOut(_ApiModel):
    """:class:`trpg.engine.preview.Preview` 的公開版本：不含模擬後的完整狀態與原始事件。"""

    action: Action
    hit_permille: int | None
    crit_permille: int | None
    damage: DamageOut | None
    affected_tiles: tuple[XY, ...]
    affected_units: tuple[UnitId, ...]
    certain: tuple[OutcomeOut, ...]
    """確定會發生的連鎖（最少後果的模擬）。"""
    possible: tuple[OutcomeOut, ...]
    """可能發生的連鎖（最多後果的模擬減去確定的部分）。"""
    cover: CoverOut | None
    notes: tuple[str, ...]
    targets: tuple[TargetOut, ...]
    healed: tuple[HealOut, ...]
    min_events: tuple[dict[str, Any], ...]
    """最少後果的模擬事件（我方視角過濾，附中文 ``text``）；連鎖預覽用。"""
    max_events: tuple[dict[str, Any], ...]
    """最多後果的模擬事件。"""
    ap_cost: int | None = None
    """這個動作花的 AP（含修正規則，Phase 3C-2）；不花 AP 的動作為 ``None``。"""
    reach: int | None = None
    """射程（普攻與有射程的技能，含修正規則）；其他動作為 ``None``。"""
    collisions: tuple[CollisionOut, ...] = ()
    """撞擊傷害（Phase 3C-3a）：每個單位的最少與最多。"""
    pierce: PierceOut | None = None
    """穿透技能的射線（Phase 3C-5b）；不是穿透的動作為 ``None``。"""
    topples: tuple[ToppleOut, ...] = ()
    """動作會造成的推倒（Phase 3C-5b）。"""
    hurls: tuple[HurlOut, ...] = ()
    """動作會造成的物件投擲（Phase 3C-5b）。"""
    moves: tuple[MoveOut, ...] = ()
    """動作的自身位移：衝鋒路線、跳躍落點、交換位置（Phase 3D-2）；位移他人另有 ``teleport``
    （``unit_id`` 被傳送到 ``path`` 的終點，Phase 3D-2b）。"""
    displace_checks: tuple[DisplaceCheckOut, ...] = ()
    """位移的抵抗判定（Phase 3D-2b：``swap``、``swap_any``、``teleport_target`` 的敵方目標）。"""
    summons: tuple[SummonOut, ...] = ()
    """動作會召喚的單位（Phase 3D-4b）。"""
    bombs: tuple[BombPreviewOut, ...] = ()
    """動作會綁上的定時炸彈：倒數與爆炸範圍（Phase 3D-8b）。"""
    revives: tuple[ReviveOut, ...] = ()
    """動作會復活的單位（Phase 3D-8b）。"""
    grants: tuple[GrantPreviewOut, ...] = ()
    """動作會讓誰暫時獲得哪個技能（Phase 3D-8c）。"""
    run_range: tuple[XY, ...] = ()
    """跑步（Phase 3-20）：跑完之後本回合能走到的格子（依 (y, x)）；其他動作為空。"""
    displace_permille: int | None = None
    """位移成功的總機率（千分比；所有敵方目標都沒抵抗成功）；沒有檢定（全是友方）為 ``None``。"""
    gamble: GambleOut | None = None
    """技能有賭注時（Phase 3D-7a）：成功率與兩個分支各自的結果；其他欄位（傷害範圍、連鎖）只算
    賭注以外的效果。"""
    miss_notes: tuple[str, ...] = ()
    """失手反噬 ``cost.on_miss`` 的說明（Phase 3D-7a，例「失手時：你獲得「倒地」」）。"""
    backstab: tuple[UnitId, ...] = ()
    """行動者會從背後攻擊的單位（Phase 3D-8d；命中率已含背刺加成，說明在 ``notes``）。"""
    landing: XY | None = None
    """複合技能（Phase 3F-3a）：位移段的落點＝動作段的原點；其他動作為 ``None``。"""
    followup_tiles: tuple[XY, ...] = ()
    """複合技能：動作段的影響格（``affected_tiles`` 已含兩段的範圍）。"""
    followup_when: str | None = None
    """複合技能第二段的種類（``followup.when``，Phase 3F-4b）；其他動作為 ``None``。"""


def _damage(d: DamageRange | None) -> DamageOut | None:
    if d is None:
        return None
    return DamageOut(
        minimum=d.minimum,
        maximum=d.maximum,
        expected_milli=_milli(d.expected),
        expected_if_hit_milli=_milli(d.expected_if_hit),
    )


def _outcome(o: Outcome) -> OutcomeOut:
    return OutcomeOut(
        kind=o.kind, unit_id=o.unit_id, object_id=o.object_id, pos=o.pos, detail=o.detail
    )


def _status_chance(c: StatusChance) -> StatusChanceOut:
    return StatusChanceOut(
        status_id=c.status_id,
        original_id=c.original_id,
        apply_permille=_milli(c.apply_chance),
        diminished=c.diminished,
    )


def _target(t: TargetPreview) -> TargetOut:
    return TargetOut(
        unit_id=t.unit_id,
        hit_permille=_milli(t.hit_chance),
        crit_permille=_milli(t.crit_chance),
        damage=_damage(t.damage),
        ally=t.ally,
        knock_permille=permille(t.knock_chance),
        status_chances=tuple(_status_chance(c) for c in t.status_chances),
    )


def _pierce(p: PierceInfo | None) -> PierceOut | None:
    if p is None:
        return None
    return PierceOut(
        route=p.route,
        objects=tuple(PierceObjectOut(object_id=o, pos=xy) for o, xy in p.objects),
        behind=p.behind,
        behind_permille=p.behind_permille,
    )


def _topple(t: ToppleInfo) -> ToppleOut:
    return ToppleOut(
        object_id=t.object_id,
        pos=t.pos,
        direction=t.direction,
        tiles=t.tiles,
        units=t.units,
        rubble=t.rubble,
    )


def _summon(s: SummonInfo) -> SummonOut:
    return SummonOut(
        unit_id=s.unit_id,
        template_id=s.template_id,
        name_zh=s.name_zh,
        pos=s.pos,
        expires_round=s.expires_round,
        max_hp=s.max_hp,
        totem_radius=s.totem_radius,
        replaces=s.replaces,
    )


def _grant(g: GrantInfo) -> GrantPreviewOut:
    return GrantPreviewOut(
        unit_id=g.unit_id,
        skill_id=g.skill_id,
        name_zh=g.name_zh,
        duration=g.duration,
        refreshed=g.refreshed,
    )


def _revive(r: ReviveInfo) -> ReviveOut:
    return ReviveOut(unit_id=r.unit_id, hp=r.hp, pos=r.pos, from_pos=r.from_pos)


def _hurl(h: HurlInfo) -> HurlOut:
    return HurlOut(
        object_id=h.object_id,
        kind=h.kind,
        from_pos=h.from_pos,
        to_pos=h.to_pos,
        outcome=h.outcome,
        placed_pos=h.placed_pos,
    )


def _gamble(p: Preview) -> GambleOut | None:
    info = p.gamble
    if info is None:
        return None
    win, lose = info.branches
    return GambleOut(
        chance_permille=info.chance_permille,
        branches=(_gamble_branch(win), _gamble_branch(lose)),
    )


def _gamble_branch(b: GambleOutcome) -> GambleBranchOut:
    return GambleBranchOut(
        kind=b.kind,
        permille=_milli(b.chance),
        multiplier_permille=b.multiplier_permille,
        targets=tuple(_target(t) for t in b.preview.targets),
        self_damage_min=b.self_damage[0],
        self_damage_max=b.self_damage[1],
        self_statuses=b.self_statuses,
        self_healed_min=b.self_healed[0],
        self_healed_max=b.self_healed[1],
    )


def preview_out(
    p: Preview,
    min_events: tuple[dict[str, Any], ...],
    max_events: tuple[dict[str, Any], ...],
) -> PreviewOut:
    cover = p.cover
    return PreviewOut(
        action=p.action,
        hit_permille=permille(p.hit_chance),
        crit_permille=permille(p.crit_chance),
        damage=_damage(p.damage),
        affected_tiles=p.affected_tiles,
        affected_units=p.affected_units,
        certain=tuple(_outcome(o) for o in p.certain),
        possible=tuple(_outcome(o) for o in p.possible),
        cover=(
            None
            if cover is None
            else CoverOut(
                penalty=cover.penalty,
                object_id=cover.object_id,
                kind=cover.kind,
                name_zh=cover.name_zh,
                pos=cover.pos,
            )
        ),
        notes=p.notes,
        targets=tuple(_target(t) for t in p.targets),
        healed=tuple(HealOut(unit_id=u, minimum=lo, maximum=hi) for u, lo, hi in p.healed),
        min_events=min_events,
        max_events=max_events,
        ap_cost=p.ap_cost,
        reach=p.reach,
        collisions=tuple(
            CollisionOut(unit_id=u, minimum=lo, maximum=hi) for u, lo, hi in p.collisions
        ),
        pierce=_pierce(p.pierce),
        topples=tuple(_topple(t) for t in p.topples),
        hurls=tuple(_hurl(h) for h in p.hurls),
        summons=tuple(_summon(x) for x in p.summons),
        bombs=tuple(
            BombPreviewOut(unit_id=b.unit_id, rounds=b.rounds, radius=b.radius, tiles=b.tiles)
            for b in p.bombs
        ),
        revives=tuple(_revive(r) for r in p.revives),
        grants=tuple(_grant(g) for g in p.grants),
        run_range=p.run_range,
        moves=tuple(
            MoveOut(kind=m.kind, unit_id=m.unit_id, other_id=m.other_id, path=m.path)
            for m in p.moves
        ),
        displace_checks=tuple(
            DisplaceCheckOut(
                unit_id=c.unit_id,
                success_permille=_milli(c.chance),
                resist_bonus=c.resist_bonus,
                lethal=c.lethal,
            )
            for c in p.displace_checks
        ),
        displace_permille=permille(p.displace_chance),
        gamble=_gamble(p),
        miss_notes=p.miss_notes,
        backstab=p.backstab,
        landing=p.landing,
        followup_tiles=p.followup_tiles,
        followup_when=p.followup_when,
    )
