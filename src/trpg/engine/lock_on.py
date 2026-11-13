"""瞄準預告（RG-1，#162，``docs/design/05-戰鬥.md`` 5.7「遠程瞄準預告」）的純查詢。

``lock_on: true`` 的技能（遠程敵人的「強力一擊」）施放＝瞄準：付代價、不擲命中，施放者身上帶
``charging``（``StatusInstance.lock_target``＝目標）。施放者下一個自己的回合開始時射出（結算在
:mod:`trpg.engine.delayed`）；射出前依序檢查，第一個不成立的就落空（:func:`lock_problem`）：

1. 目標還站著（``lock_on_lost``）；
2. 目標沒有隱蔽——**不論距離**（施放者看穿隱蔽時不算；``lock_on_concealed``）；
3. 照一般施放的選取仍然合法：射程、視線（``lock_on_lost``）；
4. 施放者到目標的直線上（兩個方向的 Bresenham，不含兩端）沒有**目標陣營**的存活單位
   （隊友擋在中間；``lock_on_blocked``）。施放者自己陣營的單位（例如盾兵）不擋。

瞄準中的施放者被近戰攻擊命中時取消（``interrupted``，:func:`lock_interrupted`，由
:func:`trpg.engine.reactions.hit_reactions` 呼叫）。
"""

from __future__ import annotations

from trpg.content.skills import CHARGING, SkillDef
from trpg.engine.actions import UseSkill
from trpg.engine.rules.combat import is_concealed, sees_hidden
from trpg.engine.rules.geometry import bresenham
from trpg.engine.skills.targeting import SkillArea, checked_area
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import UnitId

__all__ = [
    "LOCK_BLOCKED",
    "LOCK_CONCEALED",
    "LOCK_LOST",
    "lock_blocker",
    "lock_pick",
    "lock_problem",
    "lock_target_of",
]

LOCK_LOST = "lock_on_lost"
"""落空：目標倒下、走出射程或被掩護物斷了視線（一般施放的選取不合法）。"""
LOCK_CONCEALED = "lock_on_concealed"
"""落空：目標進入隱蔽（不論距離）。"""
LOCK_BLOCKED = "lock_on_blocked"
"""落空：目標的隊友擋在施放者與目標之間。"""


def lock_target_of(unit: UnitState) -> UnitId | None:
    """``unit`` 正在瞄準的單位（沒有在瞄準時為 ``None``）。"""
    status = unit.get_status(CHARGING)
    return None if status is None else status.lock_target


def lock_pick(
    state: BattleState, caster: UnitState, skill: SkillDef, target: UnitState
) -> tuple[UseSkill, SkillArea] | None:
    """以一般施放的選取對 ``target`` 射出（射程、視線、隱蔽距離、技能條件）；不合法時為
    ``None``。"""
    pick = UseSkill(unit_id=caster.id, skill_id=skill.id, target_id=target.id)
    try:
        return pick, checked_area(state, caster, skill, pick)
    except IllegalActionError:
        return None


def lock_blocker(state: BattleState, caster: UnitState, target: UnitState) -> UnitState | None:
    """施放者到目標之間擋住的目標隊友（兩個方向的 Bresenham 經過的格子，不含兩端；依直線上的
    順序取第一個，同格不會有兩名單位）；沒有時為 ``None``。"""
    cells = [*bresenham(caster.xy, target.xy)[1:-1], *bresenham(target.xy, caster.xy)[1:-1]]
    seen: set[tuple[int, int]] = set()
    for xy in cells:
        if xy in seen:
            continue
        seen.add(xy)
        other = state.unit_at(*xy)
        if other is not None and other.alive and other.team is target.team:
            return other
    return None


def lock_problem(
    state: BattleState, caster: UnitState, skill: SkillDef, target: UnitState | None
) -> str | None:
    """射出前的檢查：落空的原因（``effect_fizzled.reason``），可以射出時為 ``None``。"""
    if target is None or not target.alive:
        return LOCK_LOST
    if is_concealed(state, target) and not sees_hidden(state, caster, target):
        return LOCK_CONCEALED
    if lock_pick(state, caster, skill, target) is None:
        return LOCK_LOST
    if lock_blocker(state, caster, target) is not None:
        return LOCK_BLOCKED
    return None
