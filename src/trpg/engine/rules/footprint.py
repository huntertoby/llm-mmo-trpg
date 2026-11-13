"""多格單位的佔格與距離（GB-1a，``docs/design/05-戰鬥.md`` 5.12.4、``PhaseGB計畫.md`` T1、T2）。

- 單位的 ``pos`` 一律是佔格的**中心格**；佔格邊長 :attr:`UnitState.footprint`（1 或奇數，第一版只有
  3）。「這個單位佔哪些格」「離它多遠」「和它相不相鄰」一律走這裡。
- 一格的單位時，每個函式都退化成原本的 ``manhattan(unit.xy, …)``（逐值相同、不取亂數）；
  ``tests/engine/test_footprint_gb1a.py`` 以 hypothesis 檢查。
- 距離是曼哈頓：方塊內離某格最近的格子＝把那格夾進方塊（唯一，所以不需要同距離的排序）。
"""

from __future__ import annotations

from collections.abc import Collection

from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "adjacent",
    "chebyshev_to",
    "dist_to",
    "face_tile",
    "giant_at",
    "is_giant",
    "nearest_tile",
    "occupies",
    "strike_tiles",
    "tiles_of",
    "touches",
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


def strike_tiles(a: UnitState, b: UnitState) -> tuple[XY, XY]:
    """``a`` 對 ``b`` 出手時兩邊用的格子（GB-1b，05 5.12.4 第 2 點）：``a`` 離 ``b`` 最近的佔格
    （出招起點）與 ``b`` 離那一格最近的佔格（打中的那一格）；兩格的曼哈頓距離＝:func:`unit_dist`。
    射程、視線、掩護都以這兩格算。都是一格時＝``(a.xy, b.xy)``。"""
    if a.footprint == 1 and b.footprint == 1:
        return a.xy, b.xy
    aim = nearest_tile(b, nearest_tile(a, b.xy))
    return nearest_tile(a, aim), aim


def touches(unit: UnitState, cells: Collection[XY]) -> bool:
    """``unit`` 有任一佔格在 ``cells`` 裡（區域、爆炸範圍「在不在裡面」；巨型單位整個只算一次，
    GB-1b）。一格的單位＝``unit.xy in cells``。"""
    if unit.footprint == 1:
        return unit.xy in cells
    return any(xy in cells for xy in tiles_of(unit))


def chebyshev_to(unit: UnitState, xy: XY) -> int:
    """``xy`` 到 ``unit`` 佔格的切比雪夫距離（環形、方陣以整個佔格為中心時用；佔格內為 0）。"""
    near = nearest_tile(unit, xy)
    return max(abs(near[0] - xy[0]), abs(near[1] - xy[1]))


def face_tile(unit: UnitState, step: XY) -> XY:
    """佔格朝 ``step``（單位方向向量）那一面的中間格（錐形、直線的起點，R2；一格時是自己）。"""
    half = unit.footprint // 2
    x, y = unit.xy
    return (x + step[0] * half, y + step[1] * half)


def giant_at(state: BattleState, xy: XY) -> UnitState | None:
    """佔著 ``xy`` 的存活巨型單位。存活單位的佔格不重疊，所以最多一個、不必排序；這個查詢在
    造表面等常走的路徑上，沒有巨型單位時只掃一遍 ``footprint``。"""
    for unit in state.units.values():
        if unit.footprint > 1 and unit.alive and unit.covers(*xy):
            return unit
    return None
