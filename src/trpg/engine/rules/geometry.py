"""距離與視線（``docs/phases/Phase1計畫.md`` 4.1、4.2）。"""

from __future__ import annotations

from trpg.engine.ids import BLOCKS_SIGHT_TAG
from trpg.engine.rules.race import sight_range_for
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface

__all__ = [
    "XY",
    "axis_direction",
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


def axis_direction(dx: int, dy: int) -> XY | None:
    """向量的主要軸向（四方向）；兩軸相同時取水平；零向量為 ``None``。"""
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)


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


def sight_range(state: BattleState, viewer: UnitState | None = None) -> int:
    """視線距離（曼哈頓）：``base_sight_range`` × 天氣倍率（濃霧減半）。給了 ``viewer`` 時再套用
    種族的環境被動（人類的明視、精靈的林間視野，見 :mod:`trpg.engine.rules.race`）。"""
    return sight_range_for(state, viewer)


def blocks_sight_at(state: BattleState, xy: XY) -> bool:
    """地形 ``blocks_sight``（牆壁）、物件 ``blocks_sight`` 或表面 ``blocks_sight``（黑暗）
    阻擋穿越這一格的視線。"""
    tile = state.tile(*xy)
    if state.ruleset.terrain_def(tile.terrain).blocks_sight:
        return True
    if tile.object_id is not None and state.object_has_tag(*xy, "blocks_sight"):
        return True
    return tile.surface is not Surface.NONE and state.ruleset.surface_def(tile.surface).blocks_sight


def _sight_walls(state: BattleState) -> frozenset[XY]:
    """擋視線的單位（帶 ``blocks_sight`` 標籤，例如土牆召喚物，Phase 3-33e2a）所在的格子。"""
    return frozenset(u.xy for u in state.units.values() if u.alive and u.has_tag(BLOCKS_SIGHT_TAG))


def _blocks_line(state: BattleState, cell: XY, limit: int, lob: int, walls: frozenset[XY]) -> bool:
    """``cell`` 是否擋住視線。``lob``（拋射，Phase 3-24a1）> 0 時：高度差不超過 ``lob`` 層的地形
    高度與物件（物件視為 1 層高）可以越過；牆壁（地形 ``blocks_sight``）與黑暗表面照擋。"""
    tile = state.tile(*cell)
    if tile.height >= limit + lob:
        return True
    if lob <= 0:
        return state.tile(*cell).height >= limit or blocks_sight_at(state, cell) or cell in walls
    if state.ruleset.terrain_def(tile.terrain).blocks_sight:
        return True
    if tile.surface is not Surface.NONE and state.ruleset.surface_def(tile.surface).blocks_sight:
        return True
    if (tile.object_id is not None and state.object_has_tag(*cell, "blocks_sight")) or (
        cell in walls
    ):
        return tile.height + 1 > limit - 1 + lob  # 物件頂端高過（兩端最高 ＋ lob）才擋
    return False


def _line_clear(
    state: BattleState, line: tuple[XY, XY], limit: int, lob: int, walls: frozenset[XY]
) -> bool:
    a, b = line
    return not any(_blocks_line(state, cell, limit, lob, walls) for cell in bresenham(a, b)[1:-1])


def has_line_of_sight(
    state: BattleState, a: XY, b: XY, *, lob: int = 0, viewer: UnitState | None = None
) -> bool:
    """``a`` 與 ``b`` 之間的視線（對稱：``has_line_of_sight(a, b) == has_line_of_sight(b, a)``）。

    - 距離超過 :func:`sight_range`（濃霧）時看不到。
    - Bresenham 直線在兩個方向畫出的格子可能不同，因此 **兩個方向都畫線**，兩條線經過的格子
      （不含兩端）都沒有阻擋才算可見。
    - 阻擋條件：格子高度 ``≥ max(兩端高度) + 1``、地形 ``blocks_sight``（牆壁，不論高度）、
      物件帶 ``blocks_sight``、表面 ``blocks_sight``（黑暗）。
    - ``lob``（拋射，Phase 3-24a1，弓）：可越過這麼多層高的障礙（高度差與物件；牆壁與黑暗不行）。
      有 ``lob`` 時不再對稱——只看攻擊方向（``a`` 是射擊者）。
    - ``viewer``（Phase 3R-2）：看的人；種族被動讓他的視線距離改變（只影響距離，不影響遮擋）。
    """
    if manhattan(a, b) > sight_range(state, viewer):
        return False
    limit = max(state.tile(*a).height, state.tile(*b).height) + 1
    walls = _sight_walls(state)
    if lob > 0:
        return _line_clear(state, (a, b), limit, lob, walls)
    return _line_clear(state, (a, b), limit, 0, walls) and _line_clear(
        state, (b, a), limit, 0, walls
    )
