"""召喚技能的 AI（Phase 3D-4a，最簡單的近似；係數在 ``content/ai_profiles.yaml`` 的 ``summon:``）。

- **選位置**（:func:`summon_estimate`，不跑引擎）：召喚位置越靠近最近的敵人越好；沒有敵人時不納入
  候選。圖騰（3D-4b）相反：看光環範圍內有幾個友方。只決定「哪幾個位置值得完整預覽」。
- **評分**（:func:`summon_gains`，預覽收益的一部分）：新召喚物的預估每輪傷害
  （:func:`~trpg.content.summons.summon_dpr`）× 持續輪數 × ``damage`` 權重 × 命中折合
  （``hit_permille``），再扣掉召喚位置與最近敵人的距離 × ``distance_cost_permille``（讓完整評分
  也偏好靠近敵人的格子）；因超過上限而消失的舊召喚物，扣掉它剩餘輪數的同樣價值。圖騰的價值是
  光環範圍內的友方數 × 狀態價值 × 持續輪數 × ``support`` 權重 × 折合。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from trpg.content.environment import AiProfile
from trpg.content.skills import SUMMON, SkillDef
from trpg.content.summons import summon_dpr
from trpg.engine.events import EventBase, SummonExpired, UnitSummoned
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons import totem_of

__all__ = [
    "has_summon",
    "summon_estimate",
    "summon_gains",
    "summon_template",
]

_ESTIMATE_BASE = 20
_PERMILLE = 1000


def has_summon(skill: SkillDef) -> bool:
    return any(e.type == SUMMON for e in skill.effects)


def summon_template(skill: SkillDef) -> str | None:
    """技能召喚的範本 ID（沒有召喚效果時 ``None``）。"""
    return next((e.unit for e in skill.effects if e.type == SUMMON), None)


def _nearest_enemy(state: BattleState, team: object, xy: XY) -> int | None:
    distances = [manhattan(xy, u.xy) for u in state.living_units() if u.team is not team]
    return min(distances) if distances else None


def _totem_allies(state: BattleState, team: object, template_id: str, xy: XY) -> int:
    """圖騰放在 ``xy`` 時，光環範圍內的友方數（不含圖騰；不計其他圖騰）。"""
    try:
        spec = state.ruleset.summon_def(template_id).template.totem
    except KeyError:
        return 0
    if spec is None:
        return 0
    return sum(
        1
        for u in state.living_units()
        if u.team is team and totem_of(state, u) is None and manhattan(u.xy, xy) <= spec.radius
    )


def summon_estimate(
    state: BattleState, unit: UnitState, xy: XY, template_id: str | None = None
) -> Fraction | None:
    """召喚位置 ``xy`` 的便宜估計：越靠近最近的敵人越高（同距離時離施放者近者優先）；沒有敵人時
    ``None``。圖騰（``template_id``）看光環範圍內的友方數，沒有友方時 ``None``。"""
    tie = Fraction(manhattan(unit.xy, xy), _PERMILLE)
    if template_id is not None and _is_totem(state, template_id):
        allies = _totem_allies(state, unit.team, template_id, xy)
        return Fraction(allies) - tie if allies else None
    nearest = _nearest_enemy(state, unit.team, xy)
    if nearest is None:
        return None
    return Fraction(_ESTIMATE_BASE - nearest) - tie


def _is_totem(state: BattleState, template_id: str) -> bool:
    try:
        return state.ruleset.summon_def(template_id).template.totem is not None
    except KeyError:
        return False


def _value(
    state: BattleState, template_id: str, rounds: int, *, xy: XY, team: object, profile: AiProfile
) -> Fraction:
    """召喚物在 ``rounds`` 輪內的預估價值（等值傷害點數）。"""
    try:
        summon = state.ruleset.summon_def(template_id)
    except KeyError:
        return Fraction(0)
    rules = profile.summon
    hit = Fraction(rules.hit_permille, _PERMILLE)
    rounds = max(rounds, 0)
    spec = summon.template.totem
    if spec is None:
        return profile.weights.damage * summon_dpr(summon) * rounds * hit
    points = profile.ally_status_values.get(spec.status, rules.totem_ally_points)
    allies = _totem_allies(state, team, template_id, xy)
    return profile.weights.support * points * allies * min(rounds, 99) * hit


def summon_gains(
    state: BattleState, actor: UnitState, events: Sequence[EventBase], profile: AiProfile
) -> Fraction:
    """預覽事件中召喚與因上限消失的收益（``state`` 為動作前的狀態）。"""
    gains = Fraction(0)
    cost = Fraction(profile.summon.distance_cost_permille, _PERMILLE)
    for e in events:
        if isinstance(e, UnitSummoned) and e.team is actor.team:
            xy = (e.pos.x, e.pos.y)
            rounds = e.expires_round - state.round
            gains += _value(state, e.template_id, rounds, xy=xy, team=actor.team, profile=profile)
            nearest = _nearest_enemy(state, actor.team, xy)
            if nearest is not None and not _is_totem(state, e.template_id):
                gains -= cost * nearest
        elif isinstance(e, SummonExpired) and e.reason == "limit":
            old = state.units.get(e.unit_id)
            if old is not None and old.team is actor.team and old.summon_expires_round is not None:
                rounds = old.summon_expires_round - state.round
                gains -= _value(
                    state, old.template_id, rounds, xy=old.xy, team=actor.team, profile=profile
                )
    return gains
