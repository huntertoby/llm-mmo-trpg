"""直線衝撞（Phase 3D-2c ``charge_through``）的輔助：被撞到的敵人推到路徑旁的方向。"""

from __future__ import annotations

from trpg.engine.effects.world import unit_push_block
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import is_deadly
from trpg.engine.state import BattleState, UnitState

__all__ = ["aside_direction"]


def _free_side(state: BattleState, unit: UnitState, side: XY) -> bool:
    """``unit`` 往 ``side`` 推一格不會撞到東西：在地圖內、可站立、沒有單位、不比目前高。

    推擊規則（:func:`~trpg.engine.effects.world.unit_push_block`）允許把單位推進致命地形，但
    「推到旁邊」要避開它，所以致命地形額外排除。"""
    nxt = (unit.xy[0] + side[0], unit.xy[1] + side[1])
    return unit_push_block(state, unit.xy, nxt, unit.id) is None and not is_deadly(state, nxt)


def aside_direction(state: BattleState, unit: UnitState, travel: XY) -> XY:
    """衝撞方向 ``travel`` 的左右兩側（先左後右；左＝行進方向的左手邊，座標 y 向下）中第一個
    推得動的一側；兩側都撞得到東西就取左側（照常觸發撞擊）。"""
    left = (travel[1], -travel[0])
    right = (-left[0], -left[1])
    for side in (left, right):
        if _free_side(state, unit, side):
            return side
    return left
