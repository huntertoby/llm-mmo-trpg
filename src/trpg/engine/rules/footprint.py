"""多格單位的佔格與距離（GB-1a，``docs/design/05-戰鬥.md`` 5.12.4、``PhaseGB計畫.md`` T1、T2）。

- 單位的 ``pos`` 一律是佔格的**中心格**；佔格邊長 :attr:`UnitState.footprint`（1 或奇數，第一版只有
  3）。「這個單位佔哪些格」「離它多遠」「和它相不相鄰」一律走這裡。
- 一格的單位時，每個函式都退化成原本的 ``manhattan(unit.xy, …)``（逐值相同、不取亂數）；
  ``tests/engine/test_footprint_gb1a.py`` 以 hypothesis 檢查。
- 距離是曼哈頓：方塊內離某格最近的格子＝把那格夾進方塊（唯一，所以不需要同距離的排序）。
"""

from __future__ import annotations

from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "adjacent",
    "dist_to",
    "giant_at",
    "is_giant",
    "nearest_tile",
    "occupies",
    "tiles_of",
    "unit_dist",
]


def is_giant(unit: UnitState) -> bool:
    """佔不只一格的單位（不動巨型頭目）。"""
    return unit.footprint > 1


def _bounds(unit: UnitState) -> tuple[int, int, int, int]:
    """佔格的 ``(x 最小, x 最大, y 最小, y 最大)``（含）。"""
    half = unit.footprint // 2
    x, y = unit.xy
    return (x - half, x + half, y - half, y + half)


def tiles_of(unit: UnitState) -> tuple[XY, ...]:
    """``unit`` 佔的格子，依 ``(y, x)`` 排序（一格的單位就是 ``(unit.xy,)``）。"""
    if unit.footprint == 1:
        return (unit.xy,)
    x0, x1, y0, y1 = _bounds(unit)
    return tuple((x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))


def occupies(unit: UnitState, xy: XY) -> bool:
    """``xy`` 是 ``unit`` 佔的格子（不看存活）。"""
    return unit.covers(*xy)


def nearest_tile(unit: UnitState, xy: XY) -> XY:
    """``unit`` 佔的格子裡離 ``xy`` 最近（曼哈頓）的那一格；``xy`` 在佔格內時就是它自己。"""
    if unit.footprint == 1:
        return unit.xy
    x0, x1, y0, y1 = _bounds(unit)
    return (min(max(xy[0], x0), x1), min(max(xy[1], y0), y1))


def dist_to(unit: UnitState, xy: XY) -> int:
    """``xy`` 到 ``unit`` 最近佔格的曼哈頓距離（一格時＝``manhattan(unit.xy, xy)``）。"""
    return manhattan(nearest_tile(unit, xy), xy)


def unit_dist(a: UnitState, b: UnitState) -> int:
    """兩個單位最近佔格之間的曼哈頓距離（兩邊都取最近格；都是一格時＝``manhattan``）。"""
    if a.footprint == 1:
        return dist_to(b, a.xy)
    if b.footprint == 1:
        return dist_to(a, b.xy)
    ax0, ax1, ay0, ay1 = _bounds(a)
    bx0, bx1, by0, by1 = _bounds(b)
    gap_x = max(0, bx0 - ax1, ax0 - bx1)
    gap_y = max(0, by0 - ay1, ay0 - by1)
    return gap_x + gap_y


def adjacent(a: UnitState, b: UnitState) -> bool:
    """上下左右相鄰（和任何一格相鄰就算；斜角不算）。"""
    return unit_dist(a, b) == 1


def giant_at(state: BattleState, xy: XY) -> UnitState | None:
    """佔著 ``xy`` 的存活巨型單位。存活單位的佔格不重疊，所以最多一個、不必排序；這個查詢在
    造表面等常走的路徑上，沒有巨型單位時只掃一遍 ``footprint``。"""
    for unit in state.units.values():
        if unit.footprint > 1 and unit.alive and unit.covers(*xy):
            return unit
    return None
