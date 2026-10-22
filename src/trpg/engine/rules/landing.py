"""落點與最近空格（Phase 3E-2f）：「單位能不能站在這一格」「離某格最近的空格」的唯一實作。

傳送、跳躍、瞬步、復活、召喚、援軍、陷阱、投擲物件等原本各自判斷一遍（可站立、不是致命地形、
沒有單位、地圖範圍），這裡集中成 :func:`landing_problem`（回傳阻擋原因碼，由呼叫端自己組中文訊息，
各處的訊息措辭維持不變）與 :func:`nearest_free`（曼哈頓距離最近，同距離依 ``y`` 再依 ``x``）。

可站立（:func:`~trpg.engine.rules.movement.is_standable`）已排除致命地形（沒有木橋時深淵、岩漿不可
站立；有木橋時不致命），所以不另外檢查致命。
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.movement import is_standable
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

__all__ = ["LandingBlock", "landing_problem", "nearest_free"]


class LandingBlock(StrEnum):
    """單位站不上某一格的原因（檢查順序即宣告順序）。"""

    OUT_OF_BOUNDS = "out_of_bounds"
    NOT_STANDABLE = "not_standable"
    OCCUPIED = "occupied"
    OBJECT = "object"


def landing_problem(
    state: BattleState,
    xy: XY,
    *,
    mover: UnitId | None = None,
    clear_of_objects: bool = False,
    occupancy: Mapping[XY, UnitState] | None = None,
) -> LandingBlock | None:
    """``xy`` 不能放單位的原因；可以時回傳 ``None``。

    依序檢查：地圖範圍、可站立、有沒有（別的）存活單位、（``clear_of_objects`` 時）有沒有物件。
    ``mover`` 是要站上去的單位，它自己所在的格子不算被占用。``occupancy`` 是呼叫端已建好的
    :meth:`~trpg.engine.state.BattleState.occupancy`（掃描很多格時避免重複建表）。
    """
    if not state.in_bounds(*xy):
        return LandingBlock.OUT_OF_BOUNDS
    if not is_standable(state, xy):
        return LandingBlock.NOT_STANDABLE
    other = state.unit_at(*xy) if occupancy is None else occupancy.get(xy)
    if other is not None and other.id != mover:
        return LandingBlock.OCCUPIED
    if clear_of_objects and state.tile(*xy).object_id is not None:
        return LandingBlock.OBJECT
    return None


def nearest_free(
    state: BattleState,
    origin: XY,
    *,
    radius: int | None = None,
    mover: UnitId | None = None,
    clear_of_objects: bool = False,
) -> XY | None:
    """離 ``origin`` 最近的空格（:func:`landing_problem` 為 ``None``）；曼哈頓距離相同依 ``y`` 再依
    ``x`` 由小到大。``radius`` 限制搜尋的曼哈頓半徑（``None`` 為整張地圖）；找不到時為 ``None``。"""
    occupancy = state.occupancy()
    if radius is None:
        xs, ys = range(state.width), range(state.height)
    else:
        xs = range(max(0, origin[0] - radius), min(state.width, origin[0] + radius + 1))
        ys = range(max(0, origin[1] - radius), min(state.height, origin[1] + radius + 1))
    best: tuple[int, int, int] | None = None
    for y in ys:
        for x in xs:
            distance = manhattan(origin, (x, y))
            if radius is not None and distance > radius:
                continue
            key = (distance, y, x)
            if best is not None and key >= best:
                continue
            problem = landing_problem(
                state, (x, y), mover=mover, clear_of_objects=clear_of_objects, occupancy=occupancy
            )
            if problem is None:
                best = key
    return None if best is None else (best[2], best[1])
