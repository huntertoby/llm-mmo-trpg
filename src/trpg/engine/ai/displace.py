"""位移他人技能的 AI 估計（Phase 3D-2b）：傳送他人 ``teleport_target`` 與任意兩者互換
``swap_any``。

這兩種技能的選取是（單位 × 落點）或（單位 × 單位）的組合，數量多、而且影響範圍（兩格）看不出
效果：好用的組合是「把敵人丟進致命地形或有害表面」與「把站在有害表面或快倒下的隊友換出來」。
:func:`displace_estimate` 以便宜的幾何估計（不跑引擎）給每個選取一個分數，讓
:class:`~trpg.engine.ai.utility.UtilityAI` 只對最有希望的前幾個組合跑完整 ``preview``（每個技能的
候選數有上限，所以列舉再多也不會變慢）。

估計只決定「誰值得完整預覽」；值不值得施放由預覽的收益決定（``utility._displace_gains``）。
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

from trpg.content.skills import SWAP_ANY, TELEPORT_TARGET, SkillDef
from trpg.engine.actions import UseSkill
from trpg.engine.rules.geometry import XY, chebyshev, manhattan
from trpg.engine.rules.movement import is_deadly
from trpg.engine.state import BattleState, UnitState
from trpg.engine.traps import own_traps
from trpg.shared.types import Team

__all__ = ["DISPLACE_PRIMITIVES", "displace_estimate", "exposure", "is_hurt", "tile_harm"]

DISPLACE_PRIMITIVES = (TELEPORT_TARGET, SWAP_ANY)
"""需要 :func:`displace_estimate` 的效果原語。"""

_DEADLY_HARM = 10
_SURFACE_HARM = 4
_TRAP_HARM = 3
_LOW_HP_PERMILLE = 400
_EXPOSURE_RADIUS = 2

type Harmful = Callable[[BattleState, XY], bool]


def tile_harm(state: BattleState, xy: XY, trap_team: Team, harmful: Harmful) -> int:
    """格子對站在上面的單位有多危險（便宜的估計）：致命地形 10、有害表面 4、``trap_team`` 陣營
    放的陷阱 3、其他 0。"""
    if is_deadly(state, xy):
        return _DEADLY_HARM
    if harmful(state, xy):
        return _SURFACE_HARM
    traps = own_traps(state, trap_team)
    return _TRAP_HARM if any(t.xy == xy for t in traps) else 0


def exposure(state: BattleState, unit: UnitState, xy: XY) -> int:
    """``unit`` 站在 ``xy`` 時，兩格內有幾個敵人。"""
    return sum(
        1
        for other in state.living_units()
        if other.team is not unit.team and chebyshev(xy, other.xy) <= _EXPOSURE_RADIUS
    )


def is_hurt(unit: UnitState) -> bool:
    """快倒下的單位（HP 不超過 40%）。"""
    return unit.hp * 1000 <= unit.max_hp * _LOW_HP_PERMILLE


def _moved_value(
    state: BattleState,
    caster: UnitState,
    unit: UnitState,
    to: XY,
    harmful: Harmful,
) -> int:
    """``unit`` 被移到 ``to`` 的收益（施放者的立場）：敵人走向危險、友方離開危險或受傷的友方
    離開敵人都是正的；反過來是負的。"""
    here = tile_harm(state, unit.xy, caster.team, harmful)
    there = tile_harm(state, to, caster.team, harmful)
    if unit.team is not caster.team:
        return there - here
    value = here - there
    if is_hurt(unit):
        value += exposure(state, unit, unit.xy) - exposure(state, unit, to)
    return value


def displace_estimate(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    action: UseSkill,
    harmful: Harmful,
) -> Fraction | None:
    """傳送他人或任意兩者互換選取的便宜估計；沒有任何收益（分數不為正）時為 ``None``。

    - 傳送：被傳送的單位走到落點的收益（:func:`_moved_value`）；
    - 互換：兩個單位各自走到對方所在格的收益總和。

    平手以與施放者的距離判定（近者優先，保持確定）。
    """
    assert action.target_id is not None
    first = state.units[action.target_id]
    if any(e.type == TELEPORT_TARGET for e in skill.effects):
        assert action.target_pos is not None
        landing = (action.target_pos.x, action.target_pos.y)
        value = _moved_value(state, caster, first, landing, harmful)
    else:
        assert action.second_target_id is not None
        second = state.units[action.second_target_id]
        value = _moved_value(state, caster, first, second.xy, harmful) + _moved_value(
            state, caster, second, first.xy, harmful
        )
    if value <= 0:
        return None
    return Fraction(value) - Fraction(manhattan(caster.xy, first.xy), 1000)
