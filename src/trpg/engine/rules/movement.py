"""移動規則、可達格與路徑（``docs/phases/Phase1計畫.md`` 4.1）。

- 四方向移動。同高度或往下一步成本 1；往上 1 層成本 ``1 + move_climb_extra_cost``；
  往上超過 ``max_climb_height`` 層不可通行。
- 不可穿過敵方單位；可穿過友方但不能停在同一格；不可主動進入不可站立的地形（深淵、岩漿）。
- **會飛的單位**（Phase 3-33e2b，標籤 ``flying``）：每一步成本 1，無視高度差、不可站立的地形與障礙
  （不穿過單位的規則不變），但只能停在可站立的格子（:func:`is_standable`）。
- 路徑以 Dijkstra 計算；同成本時依固定方向順序（上、右、下、左）與發現順序打破平手。
"""

from __future__ import annotations

import heapq

from trpg.content.maps import standable
from trpg.engine.ids import FLYING, PRONE
from trpg.engine.rules.geometry import XY, manhattan, neighbors4
from trpg.engine.rules.statuses import fear_sources, is_rooted
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, UnitId

__all__ = [
    "PathMap",
    "available_move_budget",
    "can_only_stand_up",
    "fear_blocks_step",
    "fear_origins",
    "find_path",
    "is_deadly",
    "is_flying",
    "is_standable",
    "nearest_safe_tile",
    "path_map",
    "reachable_tiles",
    "stand_up_cost",
    "step_cost",
    "unit_step_cost",
]


def is_standable(state: BattleState, xy: XY) -> bool:
    """單位能否站上（並停在）這一格。

    地形可站立（可主動進入且非致命），或有 ``over_chasm`` 物件（木橋）架在上面；
    且沒有 ``blocks_move`` 物件。
    """
    tile = state.tile(*xy)
    if tile.object_id is not None:
        tags = state.ruleset.object_def(state.objects[tile.object_id].kind).tags
        if "blocks_move" in tags:
            return False
        if "over_chasm" in tags:
            return True
    return standable(state.ruleset.terrain_def(tile.terrain))


def is_deadly(state: BattleState, xy: XY) -> bool:
    """致命地形；有 ``over_chasm`` 物件（木橋）架在上面時不致命。"""
    tile = state.tile(*xy)
    if not state.ruleset.terrain_def(tile.terrain).deadly:
        return False
    return not (tile.object_id is not None and state.object_has_tag(*xy, "over_chasm"))


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


def is_flying(unit: UnitState) -> bool:
    """會飛的單位（標籤 ``flying``，Phase 3-33e2b）。"""
    return unit.has_tag(FLYING)


def unit_step_cost(state: BattleState, unit: UnitState, a: XY, b: XY) -> int | None:
    """``unit`` 從 ``a`` 走到相鄰格 ``b`` 的成本：會飛的單位恆為 1（只要在地圖內），其餘同
    :func:`step_cost`。"""
    if is_flying(unit):
        return 1 if state.in_bounds(*b) else None
    return step_cost(state, a, b)


def stand_up_cost(state: BattleState, unit: UnitState) -> int:
    """倒地者站起的移動點數消耗：速度 × ``prone_stand_up_move_permille``，無條件進位。"""
    permille = state.ruleset.core.prone_stand_up_move_permille
    return (unit.speed * permille + 999) // 1000


def available_move_budget(state: BattleState, unit: UnitState) -> int | None:
    """本回合還能用於走路的點數（倒地時扣掉站起的消耗）；站不起來或被定身時回傳 ``None``。"""
    if is_rooted(state.ruleset, unit):
        return None
    if not unit.has_status(PRONE):
        return unit.move_points
    cost = stand_up_cost(state, unit)
    return None if cost > unit.move_points else unit.move_points - cost


def can_only_stand_up(state: BattleState, unit: UnitState) -> bool:
    """被定身的倒地單位：不能走格子，但付得起站起的消耗時仍可以只站起來。"""
    return (
        is_rooted(state.ruleset, unit)
        and unit.has_status(PRONE)
        and stand_up_cost(state, unit) <= unit.move_points
    )


class PathMap:
    """單位出發的 Dijkstra 結果：``cost[xy]`` 與 ``prev[xy]``（只含能經過的格子）。"""

    __slots__ = ("cost", "no_stop", "occupied", "prev", "start")

    def __init__(
        self,
        start: XY,
        cost: dict[XY, int],
        prev: dict[XY, XY],
        occupied: dict[XY, UnitState],
        no_stop: frozenset[XY] = frozenset(),
    ) -> None:
        self.start = start
        self.cost = cost
        self.prev = prev
        self.occupied = occupied
        self.no_stop = no_stop
        """只能飛越、不能停下的格子（會飛的單位路過的牆、深淵等；Phase 3-33e2b）。"""

    def can_end_at(self, xy: XY) -> bool:
        return (
            xy in self.cost
            and xy != self.start
            and xy not in self.occupied
            and xy not in self.no_stop
        )

    def path_to(self, xy: XY) -> list[XY]:
        path = [xy]
        while path[-1] != self.start:
            path.append(self.prev[path[-1]])
        path.reverse()
        return path


def fear_origins(state: BattleState, unit: UnitState) -> tuple[XY, ...]:
    """恐懼的來源所在格（依單位 ID 排序）；來源已不在場上的不算。"""
    ids = sorted(fear_sources(state.ruleset, unit))
    return tuple(state.units[i].xy for i in ids if i in state.units and state.units[i].alive)


def fear_blocks_step(origins: tuple[XY, ...], cur: XY, nxt: XY) -> bool:
    """恐懼：這一步會讓自己與任一恐懼來源的曼哈頓距離變小。"""
    return any(manhattan(nxt, o) < manhattan(cur, o) for o in origins)


def path_map(
    state: BattleState, unit: UnitState, budget: int | None, *, through_allies: bool = True
) -> PathMap:
    """從 ``unit`` 目前位置出發的 Dijkstra；``budget`` 為 ``None`` 表示不限成本。

    ``through_allies=False`` 時友方單位也擋路（衝鋒不經過任何單位，Phase 3D-2）。"""
    start = unit.xy
    occupied = {xy: u for xy, u in state.occupancy().items() if u.id != unit.id}
    fear = fear_origins(state, unit)
    flying = is_flying(unit)
    no_stop: set[XY] = set()
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
            if other is not None and (other.team is not unit.team or not through_allies):
                continue
            c = unit_step_cost(state, unit, cur, nxt)
            if c is None or (fear and fear_blocks_step(fear, cur, nxt)):
                continue
            if flying and not is_standable(state, nxt):
                no_stop.add(nxt)
            nd = d + c
            if budget is not None and nd > budget:
                continue
            if nd < cost.get(nxt, nd + 1):
                cost[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(heap, (nd, counter, nxt))
                counter += 1
    return PathMap(start, cost, prev, occupied, frozenset(no_stop))


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
