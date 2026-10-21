"""符文的唯讀查詢（Phase 3-23；:mod:`trpg.engine.runes` 的狀態寫入與這裡分開，避免循環匯入）。"""

from __future__ import annotations

from trpg.engine.rules.geometry import XY
from trpg.engine.state import BattleState, RuneState
from trpg.shared.types import Element, UnitId

__all__ = ["has_own_rune", "own_runes", "own_runes_at", "rune_matches", "runes_at"]


def rune_matches(rune: RuneState, element: Element | None, tag: str | None) -> bool:
    """符文是否符合篩選（兩個篩選都省略＝任何符文）。"""
    if element is not None and rune.element is not element:
        return False
    return tag is None or rune.tag == tag


def runes_at(state: BattleState, xy: XY) -> list[RuneState]:
    """``xy`` 上的所有符文（敵我都算；依編號）。"""
    return [r for r in state.runes if r.xy == xy]


def own_runes(state: BattleState, owner_id: UnitId) -> list[RuneState]:
    """``owner_id`` 刻下的符文（依編號）。"""
    return [r for r in state.runes if r.owner_id == owner_id]


def own_runes_at(
    state: BattleState,
    owner_id: UnitId,
    xy: XY,
    *,
    element: Element | None = None,
    tag: str | None = None,
) -> list[RuneState]:
    """``xy`` 上 ``owner_id`` 自己的符文（可用元素與標籤篩選）。"""
    return [
        r
        for r in state.runes
        if r.owner_id == owner_id and r.xy == xy and rune_matches(r, element, tag)
    ]


def has_own_rune(
    state: BattleState,
    owner_id: UnitId,
    xy: XY,
    *,
    element: Element | None = None,
    tag: str | None = None,
) -> bool:
    """``xy`` 上有沒有 ``owner_id`` 自己的符文（條件 ``on_own_rune``）。"""
    return bool(own_runes_at(state, owner_id, xy, element=element, tag=tag))
