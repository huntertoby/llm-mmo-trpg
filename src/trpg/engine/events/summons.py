"""召喚、灌注、圖騰等召喚物事件。"""

from __future__ import annotations

from typing import Literal

from trpg.content.battle import SummonMode
from trpg.engine.events.base import EventBase
from trpg.shared.types import ObjectId, Pos, Team, UnitId

# ---------------------------------------------------------------------------
# Phase 3D-4：召喚物
# ---------------------------------------------------------------------------


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
    "expired", "owner_gone", "limit", "sacrificed", "detonated", "toppled", "decoy_hit"
]
"""召喚物消失的原因：``expired`` 到期、``owner_gone`` 召喚者倒下或撤離、``limit`` 超過同時存在的
上限（最舊的消失）、``sacrificed`` 被召喚者獻祭（``sacrifice_summon``，Phase 3-24c）、
``detonated`` 自爆（爆裂傀儡，Phase 3-33e2a）、``toppled`` 土牆被推倒、``decoy_hit`` 狐火誘餌
攔下了一次單體攻擊（Phase 3R-2）。"""


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
