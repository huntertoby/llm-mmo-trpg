"""持續區域與符文事件。"""

from __future__ import annotations

from typing import Literal

from trpg.engine.events.base import EventBase
from trpg.shared.types import Element, Pos, Surface, UnitId

# ---------------------------------------------------------------------------
# Phase 3D-5：持續區域、符文
# ---------------------------------------------------------------------------


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


class ZoneExpanded(EventBase):
    """元素擴散（Phase 3-54a，06 6.33）：風元素的技能吹到區域，區域往風向多出 ``added`` 這些格子；
    ``cells`` 是擴大後的全部格子。"""

    type: Literal["zone_expanded"] = "zone_expanded"
    zone_id: int
    owner_id: UnitId
    skill_id: str
    source_id: UnitId | None = None
    added: tuple[Pos, ...]
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
