"""自身位移（Phase 3D-2，``docs/design/06-技能.md`` 6.16 A）的選取檢查：``dash``（衝鋒）、
``leap``（跳躍）、``swap``（交換位置），以及 ``shadowstep``（瞬步，Phase 3D-8d）的落點。

只讀取狀態，不修改；實際的移動由解譯器（``_Cast``）與效果處理器結算。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.engine.ids import PRONE
from trpg.engine.rules.facing import back_xy
from trpg.engine.rules.geometry import XY, bresenham, chebyshev, manhattan
from trpg.engine.rules.movement import is_deadly, is_standable, path_map, step_cost
from trpg.engine.rules.statuses import is_rooted
from trpg.engine.skills.shapes import is_wall
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "ChargeRoute",
    "charge_candidates",
    "charge_route",
    "dash_route",
    "leap_candidates",
    "leap_problem",
    "self_move_problem",
    "shadowstep_behind",
    "shadowstep_choices",
    "shadowstep_spot_problem",
    "swap_pair_problem",
    "swap_problem",
]

LEAP_MAX_HEIGHT_DIFF = 1
"""跳躍落點與起點的最大高度差（層）；同時也是「可以無視的低矮地形」的高度。"""


def self_move_problem(state: BattleState, caster: UnitState) -> str | None:
    """衝鋒與跳躍的施放者不能行動的原因：定身（腳被困住）或倒地（要先站起來）。"""
    if is_rooted(state.ruleset, caster):
        return f"{caster.name_zh} 被定身，不能衝鋒、跳躍或瞬步"
    if caster.has_status(PRONE):
        return f"{caster.name_zh} 倒地中，不能衝鋒、跳躍或瞬步"
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


@dataclass(frozen=True, slots=True)
class ChargeRoute:
    """直線衝撞（Phase 3D-2c）的路線：``cells`` 是施放者依序經過的格子（不含起點，含有單位的格子；
    施放者不會停在有單位的格子，所以最後一格一定是空的），``stop`` 是停下的格子（＝``cells`` 的
    最後一格）。"""

    cells: tuple[XY, ...]
    stop: XY


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _charge_line_problem(state: BattleState, caster: UnitState, dest: XY, reach: int) -> str | None:
    """衝撞終點的方向問題：在地圖內、與施放者同一列或同一行、在射程內。"""
    if not state.in_bounds(*dest):
        return f"超出地圖範圍：{dest}"
    dx, dy = dest[0] - caster.xy[0], dest[1] - caster.xy[1]
    if dx == 0 and dy == 0:
        return "不能衝撞到原地"
    if dx != 0 and dy != 0:
        return f"衝撞只能走直線：{dest} 與施放者不在同一列或同一行"
    if abs(dx) + abs(dy) > reach:
        return f"目標超出射程：距離 {abs(dx) + abs(dy)}，射程 {reach}"
    return None


def _charge_dest_problem(state: BattleState, caster: UnitState, dest: XY, reach: int) -> str | None:
    """衝撞終點本身的問題：方向、射程，以及要可站立、沒有單位。"""
    problem = _charge_line_problem(state, caster, dest, reach)
    if problem is not None:
        return problem
    if not is_standable(state, dest):
        return f"無法衝撞到不可站立的格子：{dest}"
    other = state.unit_at(*dest)
    if other is not None:
        return f"終點必須是空格：{dest}（{other.name_zh}）"
    return None


def charge_route(state: BattleState, caster: UnitState, dest: XY, reach: int) -> ChargeRoute | str:
    """衝撞到終點格 ``dest`` 的路線；不合法時回傳原因（繁體中文）。

    終點要與施放者同一列或同一行、距離在 ``reach`` 內、可站立且沒有單位。沿直線一格一格走（步行
    規則：不可站立的格子與爬升過高的格子擋住），被擋住時停在擋住前的格子；單位（敵我）不擋，但
    不能停在有單位的格子，所以停點往回退到最後一個空格；退到起點就停不下來，不能施放。
    """
    problem = _charge_dest_problem(state, caster, dest, reach)
    if problem is not None:
        return problem
    x0, y0 = caster.xy
    step = (_sign(dest[0] - x0), _sign(dest[1] - y0))
    cells: list[XY] = []
    prev = caster.xy
    for i in range(1, manhattan(caster.xy, dest) + 1):
        cell = (x0 + step[0] * i, y0 + step[1] * i)
        if step_cost(state, prev, cell) is None:
            break
        cells.append(cell)
        prev = cell
    while cells and state.unit_at(*cells[-1]) is not None:
        cells.pop()
    if not cells:
        return f"衝撞被擋住，停不下來：{dest} 方向的第一個空格就過不去"
    return ChargeRoute(cells=tuple(cells), stop=cells[-1])


def charge_candidates(state: BattleState, caster: UnitState, reach: int) -> list[XY]:
    """射程內四個方向所有合法的衝撞終點（依 ``(y, x)`` 排序）。"""
    x0, y0 = caster.xy
    cells = [
        (x0 + dx * i, y0 + dy * i)
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
        for i in range(1, reach + 1)
    ]
    legal = [c for c in cells if isinstance(charge_route(state, caster, c, reach), ChargeRoute)]
    return sorted(legal, key=lambda p: (p[1], p[0]))


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


def swap_pair_problem(state: BattleState, first: UnitState, second: UnitState) -> str | None:
    """任意兩者互換（Phase 3D-2b）：``first`` 與 ``second`` 互換位置，兩格都要能讓對方站上去。"""
    for unit, other in ((first, second), (second, first)):
        if not is_standable(state, other.xy):
            return f"{unit.name_zh} 無法站上 {other.xy}：不能交換位置"
    return None


def swap_problem(state: BattleState, caster: UnitState, target: UnitState) -> str | None:
    """與 ``target`` 交換位置不合法的原因：不能和自己交換，兩格都要能讓對方站上去。"""
    if target.id == caster.id:
        return "不能和自己交換位置"
    for unit, other in ((caster, target), (target, caster)):
        if not is_standable(state, other.xy):
            return f"{unit.name_zh} 無法站上 {other.xy}：不能交換位置"
    return None


# ---------------------------------------------------------------------------
# 瞬步（Phase 3D-8d，6.21）
# ---------------------------------------------------------------------------


def shadowstep_spot_problem(
    state: BattleState, caster: UnitState, target: UnitState, xy: XY
) -> str | None:
    """瞬步落在 ``xy`` 不合法的原因：要與目標相鄰、在地圖內、可站立、不是致命地形、沒有其他單位
    （施放者自己所在的格子可以），與目標的高度差不超過近戰上限（落地後要打得到）。"""
    if manhattan(xy, target.xy) != 1:
        return f"瞬步的落點必須在 {target.name_zh} 的相鄰格：{xy}"
    if not state.in_bounds(*xy):
        return f"超出地圖範圍：{xy}"
    if not is_standable(state, xy) or is_deadly(state, xy):
        return f"無法瞬步到不可站立的格子：{xy}"
    other = state.unit_at(*xy)
    if other is not None and other.id != caster.id:
        return f"無法瞬步到已有單位的格子：{xy}（{other.name_zh}）"
    limit = state.ruleset.core.melee_height_limit
    diff = abs(state.tile(*xy).height - state.tile(*target.xy).height)
    if diff > limit:
        return f"高度差過大，無法瞬步到 {xy}：與目標相差 {diff} 層（上限 {limit} 層）"
    return None


def _adjacent(target: UnitState) -> list[XY]:
    """目標的相鄰格，固定順序：上、右、下、左。"""
    x, y = target.xy
    return [(x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]


def shadowstep_choices(state: BattleState, caster: UnitState, target: UnitState) -> list[XY]:
    """一般瞬步（``landing: choose``）可選的落點：目標相鄰的合法格（上、右、下、左的順序）。"""
    return [
        xy for xy in _adjacent(target) if shadowstep_spot_problem(state, caster, target, xy) is None
    ]


def shadowstep_behind(state: BattleState, caster: UnitState, target: UnitState) -> XY | None:
    """瞬步背刺類（``landing: behind``）的落點：目標的背後格；被占住或不可站立時改為目標相鄰的
    其他合法格中離背後格最近的（左右兩側先於正面；同距離依上、右、下、左的順序）；都沒有時為
    ``None``（不能施放）。"""
    back = back_xy(target)
    spots = shadowstep_choices(state, caster, target)
    if not spots:
        return None
    return min(spots, key=lambda xy: (chebyshev(xy, back), _adjacent(target).index(xy)))
