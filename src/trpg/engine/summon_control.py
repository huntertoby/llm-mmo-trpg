"""召喚物的操控（Phase 3-33c，``docs/design/06-技能.md`` 6.29.2）。

- **模式**（0 AP，:class:`~trpg.engine.actions.SetSummonMode`）：集火（打指定的敵人，目標離場後退回
  跟隨，見 :func:`trpg.engine.lifecycle.retire_focus`）／守護我／跟隨／待命。模式存在召喚物狀態
  （``UnitState.summon_mode``），由效用 AI 在牠自己的回合依模式行動
  （:mod:`trpg.engine.ai.summon`）。
- **指揮**（``summon_command_ap_cost`` AP，:class:`~trpg.engine.actions.CommandSummon`）：召喚者立刻
  讓一隻召喚物執行指定的移動（用牠的移動力）與普攻，不佔牠自己的回合；每隻每輪最多一次。
- 兩者都 **不列入** ``legal_actions``（同 ``set_reaction_mode``；指揮的組合太多），合法性由這裡的
  ``*_problem`` 判斷；介面用 :func:`command_options` 取得可選的終點與目標。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.content.battle import SummonMode
from trpg.engine.actions import SetSummonMode
from trpg.engine.rules.combat import attack_problem
from trpg.engine.rules.movement import available_move_budget, path_map
from trpg.engine.rules.statuses import move_points_for_turn, skip_turn_status
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons import summon_inert
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, UnitId

__all__ = [
    "MODE_NAMES_ZH",
    "CommandOption",
    "command_options",
    "command_problem",
    "mode_problem",
    "summon_problem",
]

MODE_NAMES_ZH: dict[SummonMode, str] = {
    "focus": "集火",
    "guard": "守護我",
    "follow": "跟隨",
    "hold": "待命",
}


@dataclass(frozen=True, slots=True)
class CommandOption:
    """指揮的一個終點：``path`` 從召喚物目前位置開始（原地不動時只有起點），``targets`` 是從那裡
    普攻打得到的敵方單位（依單位 ID）。"""

    dest: Pos
    path: tuple[Pos, ...]
    targets: tuple[UnitId, ...]


def summon_problem(state: BattleState, owner: UnitState, summon_id: UnitId) -> str | None:
    """``summon_id`` 不能由 ``owner`` 操控的原因（不是自己的、已不在場上、圖騰）；可以時
    ``None``。"""
    summon = state.units.get(summon_id)
    if summon is None:
        return f"找不到召喚物：{summon_id}"
    if summon.owner_id != owner.id:
        return f"不是你的召喚物：{summon.name_zh}"
    if not summon.alive:
        return f"{summon.name_zh}已不在戰場上"
    if summon_inert(state, summon):
        return f"{summon.name_zh}不會行動，不能操控"
    return None


def mode_problem(state: BattleState, owner: UnitState, action: SetSummonMode) -> str | None:
    """切換模式不合法的原因：召喚物不能操控、集火目標不是場上的敵人、與目前完全相同。"""
    problem = summon_problem(state, owner, action.summon_id)
    if problem is not None:
        return problem
    summon = state.units[action.summon_id]
    if action.mode == "focus":
        assert action.target_id is not None
        target = state.units.get(action.target_id)
        if target is None:
            return f"找不到集火目標：{action.target_id}"
        if not target.alive:
            return f"集火目標已不在戰場上：{target.name_zh}"
        if target.team is owner.team:
            return f"只能集火敵方單位：{target.name_zh}"
    if summon.summon_mode == action.mode and summon.summon_target_id == action.target_id:
        return f"{summon.name_zh}已經是「{MODE_NAMES_ZH[action.mode]}」"
    return None


def command_problem(state: BattleState, owner: UnitState, summon_id: UnitId) -> str | None:
    """指揮不合法的原因（路徑與攻擊本身的檢查在結算時，用召喚物的移動力與射程）：召喚物不能操控、
    本輪已指揮過、被暈眩、AP 不足。"""
    problem = summon_problem(state, owner, summon_id)
    if problem is not None:
        return problem
    summon = state.units[summon_id]
    if summon.commanded_round == state.round:
        return f"{summon.name_zh}本輪已經被指揮過了"
    if skip_turn_status(state.ruleset, summon) is not None:
        return f"{summon.name_zh}無法行動（暈眩）"
    cost = state.ruleset.core.summon_command_ap_cost
    if owner.ap < cost:
        return f"AP 不足：指揮需要 {cost}，剩餘 {owner.ap}"
    return None


def command_options(
    state: BattleState, owner_id: UnitId, summon_id: UnitId
) -> tuple[CommandOption, ...]:
    """``summon_id`` 被指揮時可選的終點（含原地）與各終點打得到的敵人，依 ``(y, x)``（原地在最前）。

    用召喚物完整的移動力（不佔牠自己的回合）計算；不能指揮時拋出
    :class:`~trpg.shared.errors.IllegalActionError`。"""
    owner = state.units[owner_id]
    problem = command_problem(state, owner, summon_id)
    if problem is not None:
        raise IllegalActionError(problem)
    sim = state.clone()
    summon = sim.units[summon_id]
    summon.move_points = move_points_for_turn(sim.ruleset, summon)
    origin = summon.pos
    options = [CommandOption(origin, (origin,), _targets_from(sim, summon))]
    budget = available_move_budget(sim, summon)
    if budget is not None:
        pm = path_map(sim, summon, budget)
        ends = sorted((xy for xy in pm.cost if pm.can_end_at(xy)), key=lambda p: (p[1], p[0]))
        for xy in ends:
            path = tuple(Pos(x=x, y=y) for x, y in pm.path_to(xy))
            summon.pos = Pos(x=xy[0], y=xy[1])
            options.append(CommandOption(summon.pos, path, _targets_from(sim, summon)))
    return tuple(options)


def _targets_from(sim: BattleState, summon: UnitState) -> tuple[UnitId, ...]:
    return tuple(
        e.id
        for e in sim.living_units()
        if e.team is not summon.team and attack_problem(sim, summon, e) is None
    )
