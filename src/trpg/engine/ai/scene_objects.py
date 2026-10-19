"""場景物件技能的 AI 估計（Phase 3C-5b）：投擲物件 ``hurl_object`` 與推倒 ``topple``。

這兩種技能的選取是（物件 × 落點）或（可推倒的物件）的組合，數量多、而且影響範圍（落點、物件所在
格）看不出效果：落點的油桶爆炸會波及周圍、推倒會壓住物件後方的格子。:func:`scene_estimate` 以
便宜的幾何估計（不跑引擎）給每個選取一個分數，讓 :class:`~trpg.engine.ai.utility.UtilityAI` 只對最
有希望的前幾個組合跑完整 ``preview``（每個技能的候選數有上限，所以列舉再多也不會變慢）。

估計只決定「誰值得完整預覽」；值不值得施放仍由預覽的收益決定。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.skills import HURL_OBJECT, TOPPLE, SkillDef
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.effects.world import topple_line
from trpg.engine.rules.geometry import XY, axis_direction, chebyshev, manhattan
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface

__all__ = ["SCENE_PRIMITIVES", "has_fire_follow_up", "scene_estimate"]

SCENE_PRIMITIVES = (HURL_OBJECT, TOPPLE)
"""需要 :func:`scene_estimate` 的效果原語。"""

_ENEMY_VALUE = 3
_FRIEND_PENALTY = 3


def scene_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, action: UseSkill, area: SkillArea
) -> Fraction | None:
    """投擲物件或推倒選取的便宜估計；沒有任何敵人會受到影響時為 ``None``（不納入候選）。

    - 投擲：落點的單位（敵 ＋3、友 −3）；爆炸物（油桶）只有在技能帶火元素或落點有火焰時才爆炸
      （Phase 3D-3），這時再加爆炸範圍（切比雪夫距離不超過爆炸半徑）內的每個單位；不爆炸而漏油
      時，行動者有火焰技能（:func:`has_fire_follow_up`）就把油（落點與上下左右）上的單位也算進去
      （評分同上：鋪油再點火的兩步連招，最簡單的近似）；
    - 推倒：物件往遠離施放者的方向倒下壓住的單位（:func:`~trpg.engine.effects.world.topple_line`）。

    平手以與施放者的距離判定（近者優先，保持確定）。
    """
    if any(e.type == TOPPLE for e in skill.effects):
        score = _topple_value(state, unit, action)
    else:
        score = _hurl_value(state, unit, skill, action, area)
    if score is None:
        return None
    return score - Fraction(manhattan(unit.xy, area.origin), 1000)


def _value(unit: UnitState, hit: list[UnitState]) -> int:
    return sum(_ENEMY_VALUE if other.team is not unit.team else -_FRIEND_PENALTY for other in hit)


def has_fire_follow_up(state: BattleState, unit: UnitState) -> bool:
    """行動者有可以點燃油的火焰技能（裝備的主動技能中，標籤或效果帶火，且不是投擲技能自己）。"""
    rules = state.ruleset
    for skill_id in sorted(unit.skills):
        skill = rules.skill_def(skill_id)
        if skill.kind != "active" or any(e.type == HURL_OBJECT for e in skill.effects):
            continue
        if modifiers.skill_has_fire(skill):
            return True
    return False


def _hurl_value(
    state: BattleState, unit: UnitState, skill: SkillDef, action: UseSkill, area: SkillArea
) -> Fraction | None:
    assert action.target_object_id is not None
    obj = state.objects[action.target_object_id]
    dest: XY = area.origin
    hit: list[UnitState] = []
    landing = state.unit_at(*dest)
    if landing is not None:
        hit.append(landing)
    definition = state.ruleset.object_def(obj.kind)
    lit = modifiers.skill_is_fiery(state, unit, skill) or state.tile(*dest).surface is Surface.FIRE
    if definition.explosion is not None and "explosive" in definition.tags:
        if lit:
            hit += [
                u
                for u in state.living_units()
                if u is not landing and chebyshev(dest, u.xy) <= definition.explosion.radius
            ]
        elif definition.spill is not None and has_fire_follow_up(state, unit):
            hit += [
                u for u in state.living_units() if u is not landing and manhattan(dest, u.xy) <= 1
            ]
    if not any(u.team is not unit.team for u in hit):
        return None
    return Fraction(_value(unit, hit))


def _topple_value(state: BattleState, unit: UnitState, action: UseSkill) -> Fraction | None:
    assert action.target_object_id is not None
    obj = state.objects[action.target_object_id]
    direction = axis_direction(obj.pos.x - unit.pos.x, obj.pos.y - unit.pos.y)
    if direction is None:
        return None
    crushed = [state.units[uid] for uid in topple_line(state, obj, direction).units]
    if not any(u.team is not unit.team for u in crushed):
        return None
    return Fraction(_value(unit, crushed))
