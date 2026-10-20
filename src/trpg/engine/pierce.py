"""穿透（Phase 3C-5b，``docs/design/06-技能.md`` 6.15）：射線穿過 ``penetrable`` 物件。

穿透的技能（``SkillDef.pierce``，或修正規則的 ``grant_pierce``）只能是遠程的單體或直線：

- 無視半掩護（命中判定，見 :class:`~trpg.engine.rules.combat.AttackProfile` 的 ``pierce``）。
- 射線遇到 ``penetrable`` 物件時不停下：物件受全額傷害，位於物件後方的目標只受
  ``core.pierce_behind_permille``‰ 的傷害。石柱、土牆等非 ``penetrable`` 的物件照樣擋住
  （直線遇到阻擋視線的物件會停下；單體技要看得到目標）。

這個模組只讀狀態：:func:`pierce_trace` 算出射線經過的格子、穿過的物件與位於後方的單位，解譯器、
預覽與 AI 共用。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.engine.ids import PENETRABLE
from trpg.engine.rules.geometry import XY, bresenham, manhattan
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import ObjectId, UnitId

__all__ = ["NO_PIERCE", "PierceTrace", "pierce_trace"]


@dataclass(frozen=True, slots=True)
class PierceTrace:
    """一次穿透施放的射線：``route``（施放者與目標之間的格子，不含兩端；直線為影響範圍）、
    穿過的 ``objects``（依路線順序，含所在格 ``object_tiles``）與位於它們後方的 ``behind`` 單位。"""

    route: tuple[XY, ...] = ()
    objects: tuple[ObjectId, ...] = ()
    object_tiles: tuple[XY, ...] = ()
    behind: tuple[UnitId, ...] = ()


NO_PIERCE = PierceTrace()


def pierce_trace(
    state: BattleState, caster: UnitState, shape_type: str, area: SkillArea
) -> PierceTrace:
    """``area`` 這次施放的射線。單體：施放者到目標的 Bresenham 直線（只畫一個方向）；直線：影響
    範圍依距離排序。目標是物件、或單體技的目標格沒有單位時沒有「後方」（``behind`` 為空）。"""
    if shape_type == "single":
        target = area.tiles[0]
        route = tuple(bresenham(caster.xy, target)[1:-1])
        objects = _penetrable(state, route)
        unit = state.unit_at(*target)
        behind = (unit.id,) if objects and unit is not None else ()
        return PierceTrace(
            route, tuple(o for o, _ in objects), tuple(xy for _, xy in objects), behind
        )
    route = tuple(sorted(area.tiles, key=lambda p: (manhattan(caster.xy, p), p[1], p[0])))
    objects = _penetrable(state, route)
    if not objects:
        return PierceTrace(route)
    first = route.index(objects[0][1])
    units = [u for xy in route[first + 1 :] if (u := state.unit_at(*xy)) is not None]
    return PierceTrace(
        route,
        tuple(o for o, _ in objects),
        tuple(xy for _, xy in objects),
        tuple(u.id for u in units),
    )


def _penetrable(state: BattleState, route: tuple[XY, ...]) -> list[tuple[ObjectId, XY]]:
    found: list[tuple[ObjectId, XY]] = []
    for xy in route:
        obj = state.object_at(*xy)
        if obj is not None and PENETRABLE in state.object_def(obj).tags:
            found.append((obj.id, xy))
    return found
