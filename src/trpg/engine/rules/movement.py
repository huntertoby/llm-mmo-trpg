"""移動規則、可達格與路徑（``docs/phases/Phase1計畫.md`` 4.1）。

- 四方向移動。同高度或往下一步成本 1；往上 1 層成本 ``1 + move_climb_extra_cost``；
  往上超過 ``max_climb_height`` 層不可通行。
- 不可穿過敵方單位；可穿過友方但不能停在同一格；不可主動進入不可站立的地形（深淵、岩漿）。
- 路徑以 Dijkstra 計算；同成本時依固定方向順序（上、右、下、左）與發現順序打破平手。
"""

from __future__ import annotations

import heapq

from trpg.content.maps import standable
from trpg.engine.rules.geometry import XY, manhattan, neighbors4
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, UnitId

__all__ = [
    "PathMap",
    "available_move_budget",
    "find_path",
    "is_deadly",
    "is_standable",
    "nearest_safe_tile",
    "path_map",
    "reachable_tiles",
    "stand_up_cost",
    "step_cost",
]

PRONE = "prone"


def is_standable(state: BattleState, xy: XY) -> bool:
    """地形可站立（可主動進入且非致命）。Phase 1B 會再考慮 ``blocks_move`` 物件與木橋。"""
    return standable(state.ruleset.terrain_def(state.tile(*xy).terrain))


def is_deadly(state: BattleState, xy: XY) -> bool:
    """致命地形（Phase 1B：``over_chasm`` 物件會讓深淵格變安全）。"""
    return state.ruleset.terrain_def(state.tile(*xy).terrain).deadly


def step_cost(state: BattleState, a: XY, b: XY) -> int | None:
    """從 ``a`` 主動走到相鄰格 ``b`` 的成本；不可通行時回傳 ``None``（不考慮單位）。"""
    if not is_standable(state, b):
        return None
    core = state.ruleset.core
    rise = state.tile(*b).height - state.tile(*a).height
    if rise > core.max_climb_height:
        return None
    if rise > 0:
        return 1 + core.move_climb_extra_cost * rise
    return 1


def stand_up_cost(state: BattleState, unit: UnitState) -> int:
    """倒地者站起的移動點數消耗：速度 × ``prone_stand_up_move_permille``，無條件進位。"""
    permille = state.ruleset.core.prone_stand_up_move_permille
    return (unit.speed * permille + 999) // 1000


def available_move_budget(state: BattleState, unit: UnitState) -> int | None:
    """本回合還能用於走路的點數（倒地時扣掉站起的消耗）；站不起來時回傳 ``None``。"""
    if not unit.has_status(PRONE):
        return unit.move_points
    cost = stand_up_cost(state, unit)
    return None if cost > unit.move_points else unit.move_points - cost


class PathMap:
    """單位出發的 Dijkstra 結果：``cost[xy]`` 與 ``prev[xy]``（只含能經過的格子）。"""

    __slots__ = ("cost", "occupied", "prev", "start")

    def __init__(
        self,
        start: XY,
        cost: dict[XY, int],
        prev: dict[XY, XY],
        occupied: dict[XY, UnitState],
    ) -> None:
        self.start = start
        self.cost = cost
        self.prev = prev
        self.occupied = occupied

    def can_end_at(self, xy: XY) -> bool:
        return xy in self.cost and xy != self.start and xy not in self.occupied

    def path_to(self, xy: XY) -> list[XY]:
        path = [xy]
        while path[-1] != self.start:
            path.append(self.prev[path[-1]])
        path.reverse()
        return path


def path_map(state: BattleState, unit: UnitState, budget: int | None) -> PathMap:
    """從 ``unit`` 目前位置出發的 Dijkstra；``budget`` 為 ``None`` 表示不限成本。"""
    start = unit.xy
    occupied = {xy: u for xy, u in state.occupancy().items() if u.id != unit.id}
    cost: dict[XY, int] = {start: 0}
    prev: dict[XY, XY] = {}
    heap: list[tuple[int, int, XY]] = [(0, 0, start)]
    counter = 1
    while heap:
        d, _, cur = heapq.heappop(heap)
        if d > cost[cur]:
            continue
        for nxt in neighbors4(state, cur):
            other = occupied.get(nxt)
            if other is not None and other.team is not unit.team:
                continue
            c = step_cost(state, cur, nxt)
            if c is None:
                continue
            nd = d + c
            if budget is not None and nd > budget:
                continue
            if nd < cost.get(nxt, nd + 1):
                cost[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(heap, (nd, counter, nxt))
                counter += 1
    return PathMap(start, cost, prev, occupied)


def reachable_tiles(state: BattleState, unit_id: UnitId) -> dict[Pos, int]:
    """本回合可以停下的格子與成本（不含目前位置；倒地時已扣除站起消耗）。

    回傳的字典依 ``(y, x)`` 排序。
    """
    unit = state.unit(unit_id)
    budget = available_move_budget(state, unit)
    if budget is None or unit.downed:
        return {}
    pm = path_map(state, unit, budget)
    ends = sorted((xy for xy in pm.cost if pm.can_end_at(xy)), key=lambda p: (p[1], p[0]))
    return {Pos(x=x, y=y): pm.cost[(x, y)] for x, y in ends}


def find_path(
    state: BattleState, unit_id: UnitId, dest: Pos, *, unlimited: bool = False
) -> list[Pos] | None:
    """到 ``dest`` 的最短路徑（含起點）；無法抵達或無法停在那裡時回傳 ``None``。

    預設只考慮本回合剩餘的移動點數；``unlimited=True`` 時不限成本（AI 規劃用）。
    """
    unit = state.unit(unit_id)
    budget = None if unlimited else available_move_budget(state, unit)
    if not unlimited and budget is None:
        return None
    pm = path_map(state, unit, budget)
    target = (dest.x, dest.y)
    if not pm.can_end_at(target):
        return None
    return [Pos(x=x, y=y) for x, y in pm.path_to(target)]


def nearest_safe_tile(state: BattleState, origin: XY, unit: UnitState) -> XY | None:
    """離 ``origin`` 最近的安全格（曼哈頓距離；同距離依 ``y`` 再依 ``x`` 由小到大）。

    安全格：地形可站立、沒有其他存活單位。找不到時回傳 ``None``。
    """
    occupied = {xy for xy, u in state.occupancy().items() if u.id != unit.id}
    best: tuple[int, int, int] | None = None
    for y in range(state.height):
        for x in range(state.width):
            if (x, y) in occupied or not is_standable(state, (x, y)):
                continue
            key = (manhattan(origin, (x, y)), y, x)
            if best is None or key < best:
                best = key
    return None if best is None else (best[2], best[1])
