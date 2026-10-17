"""技能的目標形狀：影響格子的計算（純函式，``docs/phases/Phase2A計畫.md`` 3.3）。

這個模組只做幾何：給定狀態、施放者位置與選取（中心格或方向），回傳影響的格子。
``preview``、AI 與之後的前端共用。規則：

- 方向只有東南西北（:data:`DIRECTIONS`）；「射程」一律為曼哈頓距離。
- 影響範圍不含地圖外的格子與牆壁格（:func:`is_wall`）。
- 回傳的格子依 ``(y, x)`` 排序（確定性）。
- 中心格型（十字、方陣、指定格）只要求 **中心格** 在射程與視線內（:func:`center_problem`），
  其餘格子不需要視線；錐形只含施放者看得到的格子；直線遇到牆壁停在它之前，遇到阻擋視線的
  物件則包含該格後停止。
"""

from __future__ import annotations

from trpg.engine.rules.geometry import XY, chebyshev, has_line_of_sight, manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "DIRECTIONS",
    "DIRECTION_ORDER",
    "center_candidates",
    "center_problem",
    "chain_units",
    "cone_tiles",
    "cross_tiles",
    "in_play",
    "is_wall",
    "line_tiles",
    "radius_tiles",
    "ring_tiles",
    "square3_tiles",
]

DIRECTIONS: dict[str, XY] = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
"""方向名稱 → 單位向量（座標系：``x`` 向右、``y`` 向下，``north`` 是 ``y − 1``）。"""

DIRECTION_ORDER: tuple[str, ...] = ("north", "east", "south", "west")


def _sorted(cells: set[XY] | list[XY]) -> tuple[XY, ...]:
    return tuple(sorted(set(cells), key=lambda p: (p[1], p[0])))


def is_wall(state: BattleState, xy: XY) -> bool:
    """牆壁：不可通行、不可站立、阻擋視線，也不是致命地形（深淵、岩漿不算）。"""
    terrain = state.ruleset.terrain_def(state.tile(*xy).terrain)
    return terrain.blocks_sight and not terrain.walkable and not terrain.deadly


def in_play(state: BattleState, xy: XY) -> bool:
    """在地圖內且不是牆壁（技能的影響範圍可以包含的格子）。"""
    return state.in_bounds(*xy) and not is_wall(state, xy)


def line_tiles(state: BattleState, origin: XY, direction: str, size: int) -> tuple[XY, ...]:
    """直線：正前方第 1…``size`` 格；遇到牆壁（或地圖邊緣）停在它之前，遇到阻擋視線的物件時
    包含該格後停止。"""
    dx, dy = DIRECTIONS[direction]
    cells: list[XY] = []
    for k in range(1, size + 1):
        cell = (origin[0] + dx * k, origin[1] + dy * k)
        if not in_play(state, cell):
            break
        cells.append(cell)
        if state.object_has_tag(*cell, "blocks_sight"):
            break
    return _sorted(cells)


def cone_tiles(state: BattleState, origin: XY, direction: str, size: int) -> tuple[XY, ...]:
    """錐形：第 k 排（k＝1…``size``）為正前方第 k 格及其左右各 k−1 格；只含施放者看得到的格子。"""
    dx, dy = DIRECTIONS[direction]
    px, py = -dy, dx  # 垂直於前進方向的單位向量
    cells: list[XY] = []
    for k in range(1, size + 1):
        for off in range(-(k - 1), k):
            cell = (origin[0] + dx * k + px * off, origin[1] + dy * k + py * off)
            if in_play(state, cell) and has_line_of_sight(state, origin, cell):
                cells.append(cell)
    return _sorted(cells)


def cross_tiles(state: BattleState, center: XY) -> tuple[XY, ...]:
    """十字：中心與四方向相鄰格。"""
    x, y = center
    cells = [(x, y), (x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]
    return _sorted([c for c in cells if in_play(state, c)])


def square3_tiles(state: BattleState, center: XY) -> tuple[XY, ...]:
    """方陣：以中心為準的 3×3。"""
    x, y = center
    cells = [(x + i, y + j) for j in (-1, 0, 1) for i in (-1, 0, 1)]
    return _sorted([c for c in cells if in_play(state, c)])


def ring_tiles(state: BattleState, origin: XY, radius: int) -> tuple[XY, ...]:
    """環形：與 ``origin`` 切比雪夫距離恰為 ``radius`` 的格子。"""
    cells = [
        (x, y)
        for y in range(origin[1] - radius, origin[1] + radius + 1)
        for x in range(origin[0] - radius, origin[0] + radius + 1)
        if chebyshev(origin, (x, y)) == radius and in_play(state, (x, y))
    ]
    return _sorted(cells)


def radius_tiles(state: BattleState, origin: XY, radius: int) -> tuple[XY, ...]:
    """範圍光環：與 ``origin`` 曼哈頓距離不超過 ``radius`` 的格子（含 ``origin``）。"""
    cells = [
        (x, y)
        for y in range(origin[1] - radius, origin[1] + radius + 1)
        for x in range(origin[0] - radius, origin[0] + radius + 1)
        if manhattan(origin, (x, y)) <= radius and in_play(state, (x, y))
    ]
    return _sorted(cells)


def center_problem(state: BattleState, origin: XY, center: XY, reach: int) -> str | None:
    """中心格型的選取問題（繁體中文）：在地圖內、不是牆壁、在射程內、看得到。"""
    if not state.in_bounds(*center):
        return f"超出地圖範圍：{center}"
    if is_wall(state, center):
        return f"不能以牆壁為目標：{center}"
    distance = manhattan(origin, center)
    if distance > reach:
        return f"目標超出射程：距離 {distance}，射程 {reach}"
    if not has_line_of_sight(state, origin, center):
        return f"視線被阻擋：看不到 {center}"
    return None


def center_candidates(state: BattleState, origin: XY, reach: int) -> list[XY]:
    """射程內所有合法的中心格（依 ``(y, x)`` 排序）。"""
    cells = [
        (x, y)
        for y in range(max(0, origin[1] - reach), min(state.height, origin[1] + reach + 1))
        for x in range(max(0, origin[0] - reach), min(state.width, origin[0] + reach + 1))
        if center_problem(state, origin, (x, y), reach) is None
    ]
    return cells


def chain_units(
    state: BattleState, caster: UnitState, first: UnitState, jumps: int, jump_range: int
) -> list[UnitState]:
    """連鎖：第一個目標，之後每跳選「距上一個目標 ≤ ``jump_range``、看得到、尚未被擊中」的最近
    同陣營單位（與第一個目標同一邊；同距離依單位 ID），沒有可跳的就停止。

    「同一邊」：第一個目標是施放者的敵人時跳敵人，否則跳友方（連鎖治療）。
    """
    enemy_side = first.team is not caster.team
    chain = [first]
    seen = {first.id}
    for _ in range(jumps):
        last = chain[-1]
        candidates = [
            u
            for u in state.living_units()
            if u.id not in seen
            and (u.team is not caster.team) == enemy_side
            and manhattan(last.xy, u.xy) <= jump_range
            and has_line_of_sight(state, last.xy, u.xy)
        ]
        if not candidates:
            break
        nxt = min(candidates, key=lambda u: (manhattan(last.xy, u.xy), u.id))
        chain.append(nxt)
        seen.add(nxt.id)
    return chain
