"""物件、表面、地形與陷阱事件。"""

from __future__ import annotations

from typing import Literal

from trpg.engine.events.base import DamageCause, EventBase, ObjectDestroyCause
from trpg.shared.types import Attribute, Element, ObjectId, Pos, Surface, Team, UnitId

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


class SurfaceBlown(EventBase):
    """吹送（Phase 3-54a ``blow_surface``，06 6.33）：``from_pos`` 的表面被風往 ``direction`` 吹到
    ``to_pos``（被擋住時可能少於技能的距離，甚至留在原地）。落點的表面改變另有 ``surface_changed``
    （原因 ``blow``；落點查互動表後可能不是 ``surface``）。"""

    type: Literal["surface_blown"] = "surface_blown"
    source_id: UnitId | None = None
    from_pos: Pos
    to_pos: Pos
    surface: Surface
    direction: tuple[int, int]
    lost: bool = False
    """被推進致命地形（深淵、岩漿；上面不能有表面）：``to_pos`` 是消失的那一格，沒有落點。"""


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
    """檢定失敗時獲得的狀態（由觸發表套用；``slide`` 時在滑行結束後套用）。"""
    slide: bool = False
    """自己走進冰面的檢定（#123，Phase 6E-2）：失敗時先滑行（``unit_slid``），停下後才倒地，
    不經觸發表。"""


class EffectFizzled(EventBase):
    """效果沒有發生（例如障礙物無處可放）。"""

    type: Literal["effect_fizzled"] = "effect_fizzled"
    effect_kind: str
    pos: Pos | None
    reason: str


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


class TrapTraced(EventBase):
    """玩家方看到敵方陷阱的「可疑痕跡」（RG-2，#162，05 5.7）：``unit_id`` 走到（或回合開始時站在）
    ``trap_trace_radius`` 格內。只帶格子，不帶技能與種類；只給 ``team`` 看（``event_filter``）。"""

    type: Literal["trap_traced"] = "trap_traced"
    unit_id: UnitId
    team: Team
    pos: Pos


class TrapGlance(EventBase):
    """敵人放陷阱時「看那一格一眼」（RG-2，#162，05 5.7）：所有人可見的演出事件，只帶放置者與格子；
    不改面向、不讓那一格變成痕跡。"""

    type: Literal["trap_glance"] = "trap_glance"
    owner_id: UnitId
    pos: Pos


class TrapExpired(EventBase):
    """陷阱消失而沒有觸發：``timeout`` 為 ``enter`` 陷阱輪數到了，``source_lost`` 為放置者離場。"""

    type: Literal["trap_expired"] = "trap_expired"
    owner_id: UnitId
    pos: Pos
    skill_id: str
    reason: Literal["timeout", "source_lost"]
