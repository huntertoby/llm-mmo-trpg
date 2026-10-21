"""勝利條件（撤離、守點）的 AI 評分（Phase 3-22；權重在 ``content/ai_profiles.yaml`` 的
``objective_ai:``，填入每個行為模式的 ``weights``，初值未經模擬）。

- 撤離戰：我方朝最近的出口格（``objective`` ＋ ``rush_exit``）；敵方去攔截出口路線（``intercept``：
  離最近出口格越近越好）。
- 守點戰：敵方去搶點（``objective`` ＋ ``contest``）；我方守在點附近（離守點超過 ``hold_radius`` 格
  才扣 ``hold_point``），且在點附近、敵人逼近時優先守護（``hold_guard``）。

非撤離／守點的戰鬥，或所有相關權重為 0 時，全部回傳 0（行為不變）。
"""

from __future__ import annotations

from trpg.content.environment import AiWeights
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Team

__all__ = ["hold_guard_bonus", "objective_cost"]

_THREAT_RADIUS = 6


def _nearest(unit: UnitState, tiles: tuple[tuple[int, int], ...]) -> int:
    return min(manhattan(unit.xy, t) for t in tiles)


def objective_cost(state: BattleState, unit: UnitState, w: AiWeights) -> int:
    """位置價值中與勝利條件有關的扣分（越小越好；``unit`` 可以是虛擬複本）。"""
    objective = state.objective
    if objective.kind == "eliminate" or not objective.tiles:
        return 0
    dist = _nearest(unit, objective.tiles)
    cost = 0
    if objective.kind == "escape":
        weight = w.objective + w.rush_exit if unit.team is Team.ALLY else w.intercept
        cost = weight * dist
    elif unit.team is Team.ENEMY:
        cost = (w.objective + w.contest) * dist
    else:
        cost = w.objective * dist + w.hold_point * max(0, dist - w.hold_radius)
    return cost


def hold_guard_bonus(state: BattleState, unit: UnitState, w: AiWeights) -> int:
    """守點戰中，我方單位在守點附近且敵人逼近時，守護（防禦）動作多加的分數。"""
    objective = state.objective
    if objective.kind != "defend" or unit.team is not Team.ALLY or not w.hold_guard:
        return 0
    if _nearest(unit, objective.tiles) > w.hold_radius:
        return 0
    threatened = any(
        manhattan(unit.xy, e.xy) <= _THREAT_RADIUS
        for e in state.living_units()
        if e.team is Team.ENEMY and not e.is_summon
    )
    return w.hold_guard if threatened else 0
