"""簡易 AI：走向最近的敵人並攻擊（Phase 1B 會換成效用 AI）。

每次呼叫決定一個動作：

1. 有 AP 且有可攻擊的敵人 → 攻擊（距離最近 → HP 最低 → ID 最小）。
2. 有 AP、還能移動 → 走向「能攻擊到敵人的格子」中路徑成本最低者（不限本回合點數規劃，
   沿路徑走到點數用完為止）；沒有這種格子時，走向離最近敵人曼哈頓距離最小的格子。
3. 還有防禦所需的 AP 且尚未防禦 → 防禦。
4. 否則結束回合。

完全確定：所有平手都以座標與 ID 決定。
"""

from __future__ import annotations

from trpg.engine.actions import Action, Attack, Defend, EndTurn, Move, Reload
from trpg.engine.basics import reload_problem
from trpg.engine.ids import DEFENDING
from trpg.engine.rules.combat import attack_problem, is_height_limited
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.rules.movement import PathMap, available_move_budget, path_map
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos

__all__ = ["choose_action"]


def _enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    return [u for u in state.living_units() if u.team is not unit.team]


def _can_hit_from(state: BattleState, unit: UnitState, xy: XY, enemy: UnitState) -> bool:
    if manhattan(xy, enemy.xy) > unit.weapon.range:
        return False
    if is_height_limited(state, unit):
        diff = abs(state.tile(*xy).height - state.tile(*enemy.xy).height)
        if diff > state.ruleset.core.melee_height_limit:
            return False
    return has_line_of_sight(state, xy, enemy.xy, lob=unit.weapon.lob)


def _pick_target(unit: UnitState, targets: list[UnitState]) -> UnitState:
    return min(targets, key=lambda t: (manhattan(unit.xy, t.xy), t.hp, t.id))


def _goal(state: BattleState, unit: UnitState, pm: PathMap, enemies: list[UnitState]) -> XY | None:
    candidates = [xy for xy in pm.cost if xy == pm.start or pm.can_end_at(xy)]
    attack_spots = [
        xy for xy in candidates if any(_can_hit_from(state, unit, xy, e) for e in enemies)
    ]
    if attack_spots:
        return min(attack_spots, key=lambda xy: (pm.cost[xy], xy[1], xy[0]))
    if not candidates:
        return None

    def closeness(xy: XY) -> tuple[int, int, int, int]:
        return (min(manhattan(xy, e.xy) for e in enemies), pm.cost[xy], xy[1], xy[0])

    return min(candidates, key=closeness)


def _approach(state: BattleState, unit: UnitState, enemies: list[UnitState]) -> Move | None:
    budget = available_move_budget(state, unit)
    if budget is None or budget <= 0:
        return None
    pm = path_map(state, unit, None)
    goal = _goal(state, unit, pm, enemies)
    if goal is None or goal == pm.start:
        return None
    full = pm.path_to(goal)
    # 沿路徑走到點數用完；停下的格子不能有其他單位（可以穿過友方）
    stop = 0
    for i, xy in enumerate(full):
        if pm.cost[xy] > budget:
            break
        if i == 0 or xy not in pm.occupied:
            stop = i
    if stop == 0:
        return None
    path = tuple(Pos(x=x, y=y) for x, y in full[: stop + 1])
    return Move(unit_id=unit.id, path=path)


def choose_action(state: BattleState) -> Action:
    unit = state.active
    if unit is None:
        raise ValueError("目前沒有行動中的單位")
    core = state.ruleset.core
    enemies = _enemies(state, unit)
    if reload_problem(state, unit) is None:
        return Reload(unit_id=unit.id)  # 空膛先裝填（3-24a2）
    if unit.ap >= core.basic_attack_ap_cost:
        targets = [e for e in enemies if attack_problem(state, unit, e) is None]
        if targets:
            return Attack(unit_id=unit.id, target_id=_pick_target(unit, targets).id)
        move = _approach(state, unit, enemies)
        if move is not None:
            return move
    if unit.ap >= core.defend_ap_cost and not unit.has_status(DEFENDING):
        return Defend(unit_id=unit.id)
    return EndTurn(unit_id=unit.id)
