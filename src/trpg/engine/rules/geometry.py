"""距離與視線（``docs/phases/Phase1計畫.md`` 4.1、4.2）。"""

from __future__ import annotations

from trpg.engine.state import BattleState

__all__ = ["XY", "bresenham", "has_line_of_sight", "manhattan", "neighbors4"]

type XY = tuple[int, int]

# 固定方向順序：上、右、下、左（與 Pos.neighbors4 一致）
_DIRECTIONS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def manhattan(a: XY, b: XY) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors4(state: BattleState, xy: XY) -> list[XY]:
    """地圖內的上下左右四格，固定順序：上、右、下、左。"""
    x, y = xy
    return [(x + dx, y + dy) for dx, dy in _DIRECTIONS if state.in_bounds(x + dx, y + dy)]


def bresenham(a: XY, b: XY) -> list[XY]:
    """``a`` 到 ``b`` 的 Bresenham 直線（含兩端，從 ``a`` 開始；整數運算，結果確定）。"""
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    cells = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
        cells.append((x0, y0))
    return cells


def has_line_of_sight(state: BattleState, a: XY, b: XY) -> bool:
    """攻擊者 ``a`` 到目標 ``b`` 的視線。

    取 Bresenham 直線經過的格子（不含兩端）；任一格高度 ``≥ max(兩端高度) + 1`` 即被阻擋。
    （Phase 1B 加入：物件 ``blocks_sight``、``darkness`` 表面、濃霧。）
    """
    limit = max(state.tile(*a).height, state.tile(*b).height) + 1
    return all(state.tile(*cell).height < limit for cell in bresenham(a, b)[1:-1])
