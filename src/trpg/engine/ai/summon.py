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
from trpg.content.skills import SACRIFICE_SUMMON, SUMMON, SkillDef
from trpg.content.summons import summon_dpr
from trpg.engine.events import DamageDealt, EventBase, SummonExpired, UnitSummoned
from trpg.engine.ids import BOSS_TAG
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons import totem_of

__all__ = [
    "blocker_gains",
    "blocking_summons",
    "has_summon",
    "sacrifice_estimate",
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


def blocking_summons(state: BattleState, boss: UnitState, slack: int) -> frozenset[str]:
    """``boss`` 的敵方召喚物中「擋路」的 ID（Phase 3-33b）：召喚物 ``s`` 與某個敵方非召喚物單位
    ``h`` 滿足 ``距離(boss, s) + 距離(s, h) ≤ 距離(boss, h) + slack``（在 Boss 走向 ``h`` 的
    最短路徑附近）。"""
    foes = [u for u in state.living_units() if u.team is not boss.team]
    heroes = [u for u in foes if not u.is_summon]
    found: set[str] = set()
    for s in foes:
        if not s.is_summon:
            continue
        reach = manhattan(boss.xy, s.xy)
        if any(reach + manhattan(s.xy, h.xy) <= manhattan(boss.xy, h.xy) + slack for h in heroes):
            found.add(s.id)
    return frozenset(found)


def blocker_gains(
    state: BattleState,
    actor: UnitState,
    events: Sequence[EventBase],
    profile: AiProfile,
    hit: Fraction,
) -> Fraction:
    """Boss 優先清擋路的召喚物（Phase 3-33b）：預覽事件中受到傷害的擋路召喚物，每隻加
    ``boss_blocker_points`` × 命中折合（範圍技能順帶打到也算）。不是 Boss 或設定為 0 時 0。"""
    points = profile.summon.boss_blocker_points
    if points == 0 or not actor.has_tag(BOSS_TAG):
        return Fraction(0)
    blockers = blocking_summons(state, actor, profile.summon.boss_blocker_slack)
    hurt = {e.target_id for e in events if isinstance(e, DamageDealt) and e.target_id in blockers}
    return Fraction(points) * hit * len(hurt)


def sacrifice_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, target_xy: XY
) -> Fraction | None:
    """獻祭召喚物（Phase 3-24c）的便宜估計：被獻祭的召喚物所在位置、半徑內的敵人數 × 3（爆炸）或
    受傷的友方數 × 2（治療）；範圍內沒有值得的對象時 ``None``（不納入候選）。"""
    spec = next(e for e in skill.effects if e.type == SACRIFICE_SUMMON)
    radius = spec.radius or 0
    near = [u for u in state.living_units() if manhattan(u.xy, target_xy) <= radius]
    if spec.element is not None:
        score = 3 * sum(1 for u in near if u.team is not unit.team)
    else:
        score = 2 * sum(1 for u in near if u.team is unit.team and u.hp < u.max_hp)
    if score == 0:
        return None
    return Fraction(score) - Fraction(manhattan(unit.xy, target_xy), _PERMILLE)


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
        elif isinstance(e, SummonExpired) and e.reason in ("limit", "sacrificed"):
            old = state.units.get(e.unit_id)
            if old is not None and old.team is actor.team and old.summon_expires_round is not None:
                rounds = old.summon_expires_round - state.round
                gains -= _value(
                    state, old.template_id, rounds, xy=old.xy, team=actor.team, profile=profile
                )
    return gains
