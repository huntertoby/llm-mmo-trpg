"""自身位移（Phase 3D-2，``docs/design/06-技能.md`` 6.16 A）的選取檢查：``dash``（衝鋒）、
``leap``（跳躍）、``swap``（交換位置）。

只讀取狀態，不修改；實際的移動由解譯器（``_Cast``）與效果處理器結算。
"""

from __future__ import annotations

from trpg.engine.rules.geometry import XY, bresenham, manhattan
from trpg.engine.rules.movement import is_deadly, is_standable, path_map
from trpg.engine.rules.statuses import is_rooted
from trpg.engine.skills.shapes import is_wall
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "dash_route",
    "leap_candidates",
    "leap_problem",
    "self_move_problem",
    "swap_problem",
]

PRONE = "prone"
LEAP_MAX_HEIGHT_DIFF = 1
"""跳躍落點與起點的最大高度差（層）；同時也是「可以無視的低矮地形」的高度。"""


def self_move_problem(state: BattleState, caster: UnitState) -> str | None:
    """衝鋒與跳躍的施放者不能行動的原因：定身（腳被困住）或倒地（要先站起來）。"""
    if is_rooted(state.ruleset, caster):
        return f"{caster.name_zh} 被定身，不能衝鋒或跳躍"
    if caster.has_status(PRONE):
        return f"{caster.name_zh} 倒地中，不能衝鋒或跳躍"
    return None


def dash_route(state: BattleState, caster: UnitState, target: XY, reach: int) -> list[XY] | None:
    """衝鋒的路徑：從施放者所在格到 ``target`` 的相鄰格（含起點與終點）；施放者已經相鄰時只有
    起點。步行規則（高度、地形、恐懼）、不經過任何單位，路徑成本不超過 ``reach``。

    有多個相鄰格可到達時取成本最小者，同成本依 ``(y, x)`` 由小到大；沒有可抵達的相鄰格時回傳
    ``None``。
    """
    if manhattan(caster.xy, target) == 1:
        return [caster.xy]
    pm = path_map(state, caster, reach, through_allies=False)
    goals = [
        xy
        for xy in (
            (target[0] + dx, target[1] + dy) for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
        )
        if state.in_bounds(*xy) and pm.can_end_at(xy)
    ]
    if not goals:
        return None
    best = min(goals, key=lambda xy: (pm.cost[xy], xy[1], xy[0]))
    return pm.path_to(best)


def _leap_blocked(state: BattleState, start: XY, dest: XY) -> XY | None:
    """起點到落點的直線上擋住跳躍的第一格（牆壁、同時擋行動與視線的物件、比兩端都高出超過
    1 層的地形）；沒有時為 ``None``。單位與低矮的地形不擋。"""
    limit = max(state.tile(*start).height, state.tile(*dest).height) + LEAP_MAX_HEIGHT_DIFF
    for cell in bresenham(start, dest)[1:-1]:
        if is_wall(state, cell) or state.tile(*cell).height > limit:
            return cell
        if state.object_has_tag(*cell, "blocks_move") and state.object_has_tag(
            *cell, "blocks_sight"
        ):
            return cell
    return None


def _landing_problem(state: BattleState, caster: UnitState, dest: XY) -> str | None:
    """落點本身的問題：可站立、不是致命地形、沒有單位、與起點的高度差不超過 1 層。"""
    if not is_standable(state, dest) or is_deadly(state, dest):
        return f"無法跳到不可站立的格子：{dest}"
    other = state.unit_at(*dest)
    if other is not None and other.id != caster.id:
        return f"無法跳到已有單位的格子：{dest}（{other.name_zh}）"
    diff = abs(state.tile(*caster.xy).height - state.tile(*dest).height)
    if diff > LEAP_MAX_HEIGHT_DIFF:
        return f"高度差過大，跳不過去：相差 {diff} 層（上限 {LEAP_MAX_HEIGHT_DIFF} 層）"
    return None


def leap_problem(state: BattleState, caster: UnitState, dest: XY, reach: int) -> str | None:
    """跳到 ``dest`` 不合法的原因（繁體中文）；合法時為 ``None``。"""
    if not state.in_bounds(*dest):
        return f"超出地圖範圍：{dest}"
    distance = manhattan(caster.xy, dest)
    if distance == 0:
        return "不能跳到原地"
    if distance > reach:
        return f"目標超出射程：距離 {distance}，射程 {reach}"
    problem = _landing_problem(state, caster, dest)
    if problem is not None:
        return problem
    blocker = _leap_blocked(state, caster.xy, dest)
    if blocker is not None:
        return f"路徑被擋住，跳不過去：{blocker}"
    return None


def leap_candidates(state: BattleState, caster: UnitState, reach: int) -> list[XY]:
    """射程內所有可以跳到的格子（依 ``(y, x)`` 排序）。"""
    x0, y0 = caster.xy
    cells = [
        (x, y)
        for y in range(max(0, y0 - reach), min(state.height, y0 + reach + 1))
        for x in range(max(0, x0 - reach), min(state.width, x0 + reach + 1))
        if leap_problem(state, caster, (x, y), reach) is None
    ]
    return cells


def swap_problem(state: BattleState, caster: UnitState, target: UnitState) -> str | None:
    """與 ``target`` 交換位置不合法的原因：不能和自己交換，兩格都要能讓對方站上去。"""
    if target.id == caster.id:
        return "不能和自己交換位置"
    for unit, other in ((caster, target), (target, caster)):
        if not is_standable(state, other.xy):
            return f"{unit.name_zh} 無法站上 {other.xy}：不能交換位置"
    return None
