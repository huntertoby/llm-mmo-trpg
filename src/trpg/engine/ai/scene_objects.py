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
from trpg.engine.actions import UseSkill
from trpg.engine.effects.world import topple_line
from trpg.engine.rules.geometry import XY, axis_direction, chebyshev, manhattan
from trpg.engine.skills.targeting import SkillArea
from trpg.engine.state import BattleState, UnitState

__all__ = ["SCENE_PRIMITIVES", "scene_estimate"]

SCENE_PRIMITIVES = (HURL_OBJECT, TOPPLE)
"""需要 :func:`scene_estimate` 的效果原語。"""

_ENEMY_VALUE = 3
_FRIEND_PENALTY = 3


def scene_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, action: UseSkill, area: SkillArea
) -> Fraction | None:
    """投擲物件或推倒選取的便宜估計；沒有任何敵人會受到影響時為 ``None``（不納入候選）。

    - 投擲：落點的單位（敵 ＋3、友 −3），物件是 ``explosive`` 時再加爆炸範圍（切比雪夫距離不超過
      爆炸半徑）內的每個單位；
    - 推倒：物件往遠離施放者的方向倒下壓住的單位（:func:`~trpg.engine.effects.world.topple_line`）。

    平手以與施放者的距離判定（近者優先，保持確定）。
    """
    if any(e.type == TOPPLE for e in skill.effects):
        score = _topple_value(state, unit, action)
    else:
        score = _hurl_value(state, unit, action, area)
    if score is None:
        return None
    return score - Fraction(manhattan(unit.xy, area.origin), 1000)


def _value(unit: UnitState, hit: list[UnitState]) -> int:
    return sum(_ENEMY_VALUE if other.team is not unit.team else -_FRIEND_PENALTY for other in hit)


def _hurl_value(
    state: BattleState, unit: UnitState, action: UseSkill, area: SkillArea
) -> Fraction | None:
    assert action.target_object_id is not None
    obj = state.objects[action.target_object_id]
    dest: XY = area.origin
    hit: list[UnitState] = []
    landing = state.unit_at(*dest)
    if landing is not None:
        hit.append(landing)
    explosion = state.ruleset.object_def(obj.kind).explosion
    if explosion is not None:
        hit += [
            u
            for u in state.living_units()
            if u is not landing and chebyshev(dest, u.xy) <= explosion.radius
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
