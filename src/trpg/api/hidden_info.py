"""隱蔽中的敵人只藏資訊（05 5.1.2，玩法決定 #144；使用者：「B 只藏資訊」）。

送給瀏覽器之前依觀看者陣營過濾（不是前端隱藏）；引擎、重播與存檔照完整狀態。全部是純函式，
不耗亂數、不改狀態。

- **看不到資訊的單位**（:func:`hidden_unit_ids`）：不是觀看者陣營、還在場上（未倒下、未撤離、
  召喚物未消失）、隱蔽中（:func:`trpg.engine.rules.combat.is_concealed`：``concealed`` 狀態、
  黑暗表面、草叢；被揭露 ``prevents_concealment`` 的不算），而且沒有和觀看者陣營任一在場單位
  （含召喚物）上下左右相鄰。
- **單位**（:func:`mask_view`）：``hp``、``shield`` 為 ``None``，``statuses``、``stacks`` 為空，
  ``hidden_info`` 為 ``True``（其他單位為 ``None``）；位置、外觀、名稱照常。
- **事件**（:func:`event_view`）：剩餘 HP、護盾的欄位改成 ``None``（傷害量、回復量照常，玩家
  自己造成的傷害數字照畫）；這些單位身上的狀態與層數變化，只有來源是觀看者陣營時才給
  （＝自己動作的結果），其他的不給。戰鬥紀錄的文字同樣不寫出剩餘 HP 與護盾
  （:func:`trpg.narrative.events.describe_event` 的 ``hidden``）。
- **預覽**（:func:`mask_outcomes`）：這些單位的「倒下」「護盾」結果不列出（會洩漏剩餘 HP／護盾）。
- **環境預告**（:func:`mask_telegraph_changes`，HID-1b）：這些單位的「將倒下」不列出（會洩漏剩餘
  HP）；其他項目照列（位置與影響的格子是危險預警），但 ``before``、``after``、``amount`` 為
  ``None``，文字不寫數值與狀態名。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from trpg.api.schemas import OutcomeOut
from trpg.engine.environment import TelegraphChange
from trpg.engine.events import (
    BossPhaseChanged,
    DamageDealt,
    DamageRedirected,
    EventBase,
    FormEntered,
    FormLeft,
    GearHpLost,
    Healed,
    ShieldAbsorbed,
    ShieldEnded,
    ShieldGained,
    StacksChanged,
    StatusApplied,
    StatusRemoved,
    StatusSaveRolled,
    UnitRevived,
)
from trpg.engine.rules.combat import is_concealed
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState
from trpg.engine.view import BattleView
from trpg.shared.types import Team, UnitId

__all__ = [
    "event_hidden_fields",
    "event_visible",
    "hidden_unit_ids",
    "mask_event_data",
    "mask_outcomes",
    "mask_telegraph_changes",
    "mask_view",
]

_NUMBER_FIELDS: dict[type[EventBase], tuple[str, tuple[str, ...]]] = {
    DamageDealt: ("target_id", ("hp_before", "hp_after")),
    Healed: ("target_id", ("hp_before", "hp_after")),
    GearHpLost: ("unit_id", ("hp_before", "hp_after")),
    DamageRedirected: ("to_id", ("hp_before", "hp_after")),
    ShieldGained: ("unit_id", ("total",)),
    ShieldAbsorbed: ("unit_id", ("remaining",)),
    FormEntered: ("unit_id", ("hp",)),
    FormLeft: ("unit_id", ("hp",)),
    UnitRevived: ("unit_id", ("hp",)),
    BossPhaseChanged: ("unit_id", ("hp",)),
}
"""事件 → （主角欄位, 主角看不到資訊時改成 ``None`` 的欄位）。"""


def hidden_unit_ids(state: BattleState, team: Team) -> frozenset[UnitId]:
    """對 ``team`` 而言看不到資訊的單位（見模組說明）。"""
    watchers = [u.xy for u in state.units_sorted() if u.team is team and u.alive]
    return frozenset(
        u.id
        for u in state.units_sorted()
        if u.team is not team
        and u.alive
        and is_concealed(state, u)
        and not any(manhattan(u.xy, w) == 1 for w in watchers)
    )


def mask_view(view: BattleView, hidden: frozenset[UnitId]) -> BattleView:
    """``hidden`` 裡的單位只留位置、外觀、名稱等，HP、護盾、狀態、層數改成未知。"""
    if not hidden:
        return view
    units = tuple(
        u.model_copy(
            update={"hp": None, "shield": None, "statuses": (), "stacks": {}, "hidden_info": True}
        )
        if u.id in hidden
        else u
        for u in view.units
    )
    return view.model_copy(update={"units": units})


def _source_team(state: BattleState, source_id: UnitId | None) -> Team | None:
    unit = None if source_id is None else state.units.get(source_id)
    return None if unit is None else unit.team


def event_visible(
    event: EventBase, state: BattleState, team: Team, hidden: frozenset[UnitId]
) -> bool:
    """看不到資訊的單位身上的狀態、層數變化，只有來源是 ``team`` 時才給（自己動作的結果）。"""
    if not hidden:
        return True
    if isinstance(event, StatusApplied | StacksChanged):
        subject = event.target_id if isinstance(event, StatusApplied) else event.unit_id
        return subject not in hidden or _source_team(state, event.source_id) is team
    if isinstance(event, StatusSaveRolled):
        return event.target_id not in hidden or _source_team(state, event.attacker_id) is team
    if isinstance(event, StatusRemoved):
        return event.target_id not in hidden
    if isinstance(event, ShieldEnded):
        return event.unit_id not in hidden or event.broken  # 被打破＝攻擊的結果
    return True


def event_hidden_fields(event: EventBase, hidden: frozenset[UnitId]) -> tuple[str, ...]:
    """``event`` 的 JSON 裡要改成 ``None`` 的欄位（剩餘 HP、護盾）；不用改時為空。"""
    spec = _NUMBER_FIELDS.get(type(event))
    if spec is None or not hidden:
        return ()
    subject, fields = spec
    return fields if getattr(event, subject) in hidden else ()


def mask_event_data(data: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    """把 ``fields`` 改成 ``None``（原地修改並回傳）。"""
    for name in fields:
        data[name] = None
    return data


def mask_outcomes(
    outcomes: tuple[OutcomeOut, ...], hidden: frozenset[UnitId]
) -> tuple[OutcomeOut, ...]:
    """預覽結果去掉看不到資訊的單位的「倒下」與「護盾」（會洩漏剩餘 HP／護盾）。"""
    return tuple(
        o for o in outcomes if not (o.unit_id in hidden and o.kind in ("downed", "shield"))
    )


def mask_telegraph_changes(
    changes: Iterable[TelegraphChange], hidden: frozenset[UnitId]
) -> tuple[TelegraphChange, ...]:
    """預告變化遮掉看不到資訊的單位：「將倒下」不列出，其他項目清掉 ``before``、``after``、
    ``amount``。

    引擎的預告維持完整（這裡回傳新的物件）；文字另由 ``change_text(..., hidden)`` 處理。
    """
    return tuple(
        c.model_copy(update={"before": None, "after": None, "amount": None})
        if c.unit_id in hidden
        else c
        for c in changes
        if not (c.kind == "unit_downed" and c.unit_id in hidden)
    )
