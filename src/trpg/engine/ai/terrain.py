"""純地形技能的 AI（Phase 3T-5；係數在 ``ai_profiles.yaml`` 的 ``terrain:``）。

隆起 ``raise_terrain``、下陷 ``lower_terrain`` 沒有傷害也沒有狀態，預覽事件只有
``terrain_changed``，本來沒有任何評分（單位 AI 不會主動施放）。這裡補兩件事：

- **候選估計**（:func:`terrain_estimate`，不跑引擎）：純地形技能（效果全是隆起或下陷）的影響範圍內
  沒有任何可能的收益就不納入候選；
- **收益**（:func:`terrain_gains`，依預覽事件）：站在被改變的格子上的單位，高度每變一層——敵人被降低
  （或友方被抬高）加分、反過來扣分（單位 × 層數 × ``height_points`` × ``damage`` 權重）；被下陷的
  空格（坑）旁邊站著高出 ``fall_damage_min_drop`` 以上的敵人，而且我方有推擊或拉扯技能時，每名敵人
  加 ``pit_points``（把敵人推進坑才會墜落）。

沒有收益就不施放：技能本身的法力與冷卻成本由 ``skill_cost`` 扣掉，所以總分不為正。行動者自己站的
格子由位置價值的 ``height`` 權重處理，這裡不重複計算。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import AiProfile
from trpg.content.maps import MAX_HEIGHT
from trpg.content.skills import SkillDef
from trpg.engine.events import EventBase, TerrainChanged
from trpg.engine.rules.geometry import XY, manhattan, neighbors4
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState, UnitState

__all__ = ["is_terrain_only", "terrain_estimate", "terrain_gains"]

_RAISE = "raise_terrain"
_LOWER = "lower_terrain"
_PUSHES = frozenset({"push", "pull"})

_ENEMY_VALUE = 3
_ALLY_VALUE = 2
_PIT_VALUE = 2
_PERCH_VALUE = 1
"""候選估計的分數（只用來排序，不是收益）。"""


def is_terrain_only(skill: SkillDef) -> bool:
    """效果全是隆起或下陷（沒有傷害、狀態等其他效果）。"""
    return bool(skill.effects) and all(e.type in (_RAISE, _LOWER) for e in skill.effects)


def _can_push(state: BattleState, unit: UnitState) -> bool:
    """我方（行動者或活著的友方）有沒在冷卻的推擊或拉扯技能。"""
    rules = state.ruleset
    for ally in state.living_units():
        if ally.team is not unit.team:
            continue
        for skill_id in sorted(ally.all_skills):
            if ally.cooldowns.get(skill_id, 0) > 0:
                continue
            skill = rules.skill_def(skill_id)
            if skill.kind == "active" and any(e.type in _PUSHES for e in skill.effects):
                return True
    return False


def _pit_victims(state: BattleState, unit: UnitState, xy: XY, pit_height: int) -> list[UnitState]:
    """坑（高度 ``pit_height``）旁邊、高出墜落門檻的敵人。"""
    min_drop = state.ruleset.core.fall_damage_min_drop
    victims: list[UnitState] = []
    for n in neighbors4(state, xy):
        other = state.unit_at(*n)
        if other is None or other.team is unit.team or not other.alive:
            continue
        if state.tile(*other.xy).height - pit_height >= min_drop:
            victims.append(other)
    return victims


def terrain_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, area: SkillArea, height_weight: int
) -> Fraction | None:
    """純地形技能選取的便宜估計；範圍內沒有可能的收益時為 ``None``（不納入候選）。

    ``height_weight`` 是行為模式的 ``height`` 位置權重（自己站的格子升高，只有偏好高處的模式才算）。
    """
    kinds = {e.type for e in skill.effects}
    lowering, raising = _LOWER in kinds, _RAISE in kinds
    pit = lowering and not raising and _can_push(state, unit)
    score = Fraction(0)
    for xy in area.tiles:
        height = state.tile(*xy).height
        can_lower = lowering and height > 0  # 高度 0 的格子降不下去、頂高的升不上去
        can_raise = raising and height < MAX_HEIGHT
        other = state.unit_at(*xy)
        if other is None or not other.alive:
            if pit and can_lower:
                score += _PIT_VALUE * len(_pit_victims(state, unit, xy, height - 1))
        elif other.id == unit.id:
            score += _PERCH_VALUE if can_raise and height_weight > 0 else 0
        elif other.team is not unit.team:
            score += _ENEMY_VALUE if can_lower else 0
        else:
            score += _ALLY_VALUE if can_raise else 0
    if score <= 0:
        return None
    return score - Fraction(manhattan(unit.xy, area.origin), 1000)


def terrain_gains(
    state: BattleState,
    after: BattleState,
    actor: UnitState,
    events: tuple[EventBase, ...],
    profile: AiProfile,
) -> Fraction:
    """預覽事件中 ``terrain_changed`` 的收益（見模組說明）；``events`` 是施放後的事件，``after`` 是
    施放後的狀態（算坑旁敵人的落差用，敵人自己的格子也可能一起降低）。"""
    rules = profile.terrain
    points = 0
    pusher: bool | None = None
    for e in events:
        if not isinstance(e, TerrainChanged) or e.height_after == e.height_before:
            continue
        xy = (e.pos.x, e.pos.y)
        delta = e.height_after - e.height_before
        other = state.unit_at(*xy)
        if other is not None and other.alive:
            if other.id == actor.id:
                continue  # 自己站的格子：位置價值的 height 權重已經計算
            points += rules.height_points * (-delta if other.team is not actor.team else delta)
        elif delta < 0:
            if pusher is None:
                pusher = _can_push(state, actor)
            if pusher:
                victims = _pit_victims(after, actor, xy, e.height_after)
                points += rules.pit_points * len(victims)
    return Fraction(points * profile.weights.damage)
