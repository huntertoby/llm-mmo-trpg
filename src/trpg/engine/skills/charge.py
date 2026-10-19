"""直線衝撞（Phase 3D-2c ``charge_through``）的輔助：被撞到的敵人推到路徑旁的方向。"""

from __future__ import annotations

from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import is_standable
from trpg.engine.state import BattleState, UnitState

__all__ = ["aside_direction"]


def _free_side(state: BattleState, unit: UnitState, side: XY) -> bool:
    """``unit`` 往 ``side`` 推一格不會撞到東西：在地圖內、可站立、沒有單位、不比目前高。"""
    x, y = unit.xy[0] + side[0], unit.xy[1] + side[1]
    if not state.in_bounds(x, y) or not is_standable(state, (x, y)):
        return False
    if state.unit_at(x, y) is not None:
        return False
    return state.tile(x, y).height <= state.tile(*unit.xy).height


def aside_direction(state: BattleState, unit: UnitState, travel: XY) -> XY:
    """衝撞方向 ``travel`` 的左右兩側（先左後右；左＝行進方向的左手邊，座標 y 向下）中第一個
    推得動的一側；兩側都撞得到東西就取左側（照常觸發撞擊）。"""
    left = (travel[1], -travel[0])
    right = (-left[0], -left[1])
    for side in (left, right):
        if _free_side(state, unit, side):
            return side
    return left
