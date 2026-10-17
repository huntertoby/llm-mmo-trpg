"""技巧動作與技能的對抗判定（推擊、絆倒、技能的擊倒）。"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import ManeuverRolled
from trpg.engine.rules.combat import is_hit
from trpg.engine.state import UnitState
from trpg.shared.types import Attribute

__all__ = ["contest"]


def contest(
    ctx: Ctx,
    kind: str,
    unit: UnitState,
    target: UnitState,
    attr: Attribute,
    *,
    skill_id: str | None = None,
    primary: bool = True,
) -> bool:
    """對抗判定：``d20 + 比例修正（攻方屬性 vs 守方屬性）+ 熟練 ≥ hit_target``。

    預覽：``primary``（動作本身的技巧動作，推擊、絆倒）視為成功（成功率另以 ``preview`` 計算）；
    次要的對抗（技能附帶的擊倒）是分歧點——``min`` 視為失敗、``max`` 視為成功。
    """
    rules = ctx.rules
    modifier = rules.hit_table.modifier(unit.attributes[attr], max(1, target.attributes[attr]))
    proficiency = rules.core.proficiency
    if ctx.preview is None:
        natural = ctx.rng.d20()
    elif primary:
        natural = 20
    else:
        ctx.mark_branch()
        natural = 20 if ctx.preview == "max" else 1
    total = natural + modifier + proficiency
    success = is_hit(natural, total, rules.core.hit_target)
    ctx.emit(
        ManeuverRolled,
        maneuver=kind,
        attacker_id=unit.id,
        target_id=target.id,
        natural=natural,
        modifier=modifier,
        proficiency=proficiency,
        total=total,
        target_number=rules.core.hit_target,
        success=success,
        skill_id=skill_id,
    )
    return success
