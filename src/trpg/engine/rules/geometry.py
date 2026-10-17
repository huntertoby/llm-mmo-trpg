"""距離與視線（``docs/phases/Phase1計畫.md`` 4.1、4.2）。"""

from __future__ import annotations

from trpg.engine.state import BattleState
from trpg.shared.types import Surface

__all__ = [
    "XY",
    "blocks_sight_at",
    "bresenham",
    "chebyshev",
    "has_line_of_sight",
    "manhattan",
    "neighbors4",
    "sight_range",
]

type XY = tuple[int, int]

# 固定方向順序：上、右、下、左（與 Pos.neighbors4 一致）
_DIRECTIONS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def manhattan(a: XY, b: XY) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def chebyshev(a: XY, b: XY) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


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


def sight_range(state: BattleState) -> int:
    """視線距離（曼哈頓）：``base_sight_range`` × 天氣倍率（濃霧減半）。"""
    base = state.ruleset.core.base_sight_range
    permille = 1000 if state.weather is None else state.weather.sight_range_permille
    return base * permille // 1000


def blocks_sight_at(state: BattleState, xy: XY) -> bool:
    """地形 ``blocks_sight``（牆壁）、物件 ``blocks_sight`` 或表面 ``blocks_sight``（黑暗）
    阻擋穿越這一格的視線。"""
    tile = state.tile(*xy)
    if state.ruleset.terrain_def(tile.terrain).blocks_sight:
        return True
    if tile.object_id is not None and state.object_has_tag(*xy, "blocks_sight"):
        return True
    return tile.surface is not Surface.NONE and state.ruleset.surface_def(tile.surface).blocks_sight


def _line_clear(state: BattleState, a: XY, b: XY, limit: int) -> bool:
    for cell in bresenham(a, b)[1:-1]:
        if state.tile(*cell).height >= limit or blocks_sight_at(state, cell):
            return False
    return True


def has_line_of_sight(state: BattleState, a: XY, b: XY) -> bool:
    """``a`` 與 ``b`` 之間的視線（對稱：``has_line_of_sight(a, b) == has_line_of_sight(b, a)``）。

    - 距離超過 :func:`sight_range`（濃霧）時看不到。
    - Bresenham 直線在兩個方向畫出的格子可能不同，因此 **兩個方向都畫線**，兩條線經過的格子
      （不含兩端）都沒有阻擋才算可見。
    - 阻擋條件：格子高度 ``≥ max(兩端高度) + 1``、地形 ``blocks_sight``（牆壁，不論高度）、
      物件帶 ``blocks_sight``、表面 ``blocks_sight``（黑暗）。
    """
    if manhattan(a, b) > sight_range(state):
        return False
    limit = max(state.tile(*a).height, state.tile(*b).height) + 1
    return _line_clear(state, a, b, limit) and _line_clear(state, b, a, limit)
