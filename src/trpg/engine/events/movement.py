"""移動事件（步行、衝鋒、滑行、跳躍、碰撞、墜落等）。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from trpg.content.battle import Dice
from trpg.engine.events.base import EventBase, MoveMode, SlideStopReason
from trpg.shared.types import ObjectId, Pos, UnitId

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


class UnitSlid(EventBase):
    """冰面滑倒後的滑行（#123，Phase 6E-2）：``path`` 含起點（滑倒的那一格）與停點，只有起點時表示
    一格都沒滑（下一格就擋住）；每滑一格另有 ``unit_moved``（``mode: slide``）。之後移動者倒地
    （``status_applied``）、這次移動剩下的點數作廢。"""

    type: Literal["unit_slid"] = "unit_slid"
    unit_id: UnitId
    path: tuple[Pos, ...]
    stop_reason: SlideStopReason


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


class RaceSkillUsed(EventBase):
    """使用種族技（Phase 3R-2）：``skill_id`` 是種族技 ID（``races.yaml``）。

    選取欄位依種族技的形狀填入（沒用到的為 ``None``），``uses_left`` 是本場剩餘次數。
    之後是效果自己的事件（推擊、表面、狀態……）。"""

    type: Literal["race_skill_used"] = "race_skill_used"
    unit_id: UnitId
    race_id: str
    skill_id: str
    target_id: UnitId | None = None
    target_object_id: ObjectId | None = None
    target_pos: Pos | None = None
    direction: Literal["north", "east", "south", "west"] | None = None
    choice: Literal["stamina", "mana"] | None = None
    uses_left: int


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
    damage_permille: int = Field(default=1000, ge=0)
    """撞擊傷害倍率（‰）：風壓撞擊（Phase 3-54a）時為 ``core.wind.collision_permille``。"""


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
