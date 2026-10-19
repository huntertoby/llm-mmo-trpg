"""召喚技能的 AI（Phase 3D-4a，最簡單的近似）。

- **選位置**（:func:`summon_estimate`，不跑引擎）：召喚位置越靠近最近的敵人越好；沒有敵人時不納入
  候選。只決定「哪幾個位置值得完整預覽」。
- **評分**（:func:`summon_gains`，預覽收益的一部分）：新召喚物的預估每輪傷害
  （:func:`~trpg.content.summons.summon_dpr`）× 持續輪數 × ``damage`` 權重 × 命中折合
  :data:`SUMMON_HIT`，再扣掉召喚位置與最近敵人的距離 × :data:`SUMMON_DISTANCE_COST`（讓完整評分
  也偏好靠近敵人的格子）；因超過上限而消失的舊召喚物，扣掉它剩餘輪數的同樣價值。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from trpg.content.environment import AiWeights
from trpg.content.skills import SUMMON, SkillDef
from trpg.content.summons import summon_dpr
from trpg.engine.events import EventBase, SummonExpired, UnitSummoned
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "SUMMON_DISTANCE_COST",
    "SUMMON_HIT",
    "has_summon",
    "summon_estimate",
    "summon_gains",
]

SUMMON_HIT = Fraction(1, 2)
"""召喚物預估傷害的命中與走位折合（初值，未經模擬）。"""

SUMMON_DISTANCE_COST = Fraction(1, 10)
"""召喚位置與最近敵人每差一格扣的分數（只用來在同一技能的位置之間排序）。"""

_ESTIMATE_BASE = 20


def has_summon(skill: SkillDef) -> bool:
    return any(e.type == SUMMON for e in skill.effects)


def _nearest_enemy(state: BattleState, team: object, xy: XY) -> int | None:
    distances = [manhattan(xy, u.xy) for u in state.living_units() if u.team is not team]
    return min(distances) if distances else None


def summon_estimate(state: BattleState, unit: UnitState, xy: XY) -> Fraction | None:
    """召喚位置 ``xy`` 的便宜估計：越靠近最近的敵人越高（同距離時離施放者近者優先）；沒有敵人時
    ``None``。"""
    nearest = _nearest_enemy(state, unit.team, xy)
    if nearest is None:
        return None
    return Fraction(_ESTIMATE_BASE - nearest) - Fraction(manhattan(unit.xy, xy), 1000)


def _value(state: BattleState, template_id: str, rounds: int, w: AiWeights) -> Fraction:
    try:
        summon = state.ruleset.summon_def(template_id)
    except KeyError:
        return Fraction(0)
    return w.damage * summon_dpr(summon) * max(rounds, 0) * SUMMON_HIT


def summon_gains(
    state: BattleState, actor: UnitState, events: Sequence[EventBase], w: AiWeights
) -> Fraction:
    """預覽事件中召喚與因上限消失的收益（``state`` 為動作前的狀態）。"""
    gains = Fraction(0)
    for e in events:
        if isinstance(e, UnitSummoned) and e.team is actor.team:
            gains += _value(state, e.template_id, e.expires_round - state.round, w)
            nearest = _nearest_enemy(state, actor.team, (e.pos.x, e.pos.y))
            if nearest is not None:
                gains -= SUMMON_DISTANCE_COST * nearest
        elif isinstance(e, SummonExpired) and e.reason == "limit":
            old = state.units.get(e.unit_id)
            if old is not None and old.team is actor.team and old.summon_expires_round is not None:
                gains -= _value(state, old.template_id, old.summon_expires_round - state.round, w)
    return gains
