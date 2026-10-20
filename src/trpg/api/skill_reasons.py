"""灰掉的技能按鈕的原因（Phase 3-5c-2）：主角現在不能用的技能 → 引擎的拒絕理由（繁體中文）。

只讀取狀態、不改變工作階段。先問 :func:`~trpg.engine.skills.targeting.skill_problem`（AP、法力、
冷卻、沉默……）；資源都夠但沒有合法選取時，依距離由近到遠試敵方單位當目標，取最近一個的拒絕理由
（例如「視線被阻擋」「目標超出射程」）；都試不出理由時給通用說明。
"""

from __future__ import annotations

from trpg.api.schemas import SkillReasons
from trpg.content.skills import SkillDef
from trpg.engine import modifiers
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.skills.targeting import checked_area, skill_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, UnitId

__all__ = ["NO_TARGET_REASON", "PASSIVE_REASON", "skill_reasons"]

NO_TARGET_REASON = "目前沒有合法目標"
PASSIVE_REASON = "被動技能：條件成立時自動生效，不能主動施放"


def _target_reason(state: BattleState, unit: UnitState, skill: SkillDef) -> str:
    foes = sorted(
        (u for u in state.living_units() if u.team is not unit.team),
        key=lambda u: (abs(u.xy[0] - unit.xy[0]) + abs(u.xy[1] - unit.xy[1]), u.id),
    )
    targeting = state.ruleset.shape_def(skill.shape.type).targeting
    for foe in foes:
        if targeting == "unit":
            action = UseSkill(unit_id=unit.id, skill_id=skill.id, target_id=foe.id)
        elif targeting == "tile":
            action = UseSkill(
                unit_id=unit.id, skill_id=skill.id, target_pos=Pos(x=foe.xy[0], y=foe.xy[1])
            )
        else:
            break
        try:
            checked_area(state, unit, skill, action)
        except IllegalActionError as exc:
            return str(exc)
    return NO_TARGET_REASON


def skill_reasons(state: BattleState, hero_id: UnitId) -> SkillReasons:
    """主角每個沒有合法動作的技能 → 原因。不是主角的回合（或暫停中）時為空。"""
    unit = state.active
    if state.ended or unit is None or unit.id != hero_id or state.pending is not None:
        return SkillReasons(reasons={})
    usable = {a.skill_id for a in legal_actions(state) if isinstance(a, UseSkill)}
    reasons: dict[str, str] = {}
    for skill_id in sorted(unit.all_skills):
        if skill_id in usable:
            continue
        skill = modifiers.acting_skill(state, unit, skill_id)
        if not skill.is_actionable:
            reasons[skill_id] = PASSIVE_REASON
            continue
        reasons[skill_id] = skill_problem(state, unit, skill) or _target_reason(state, unit, skill)
    return SkillReasons(reasons=reasons)
