"""自己付的代價（Phase 3-50，``docs/design/06-技能.md`` 6.5）：自身負面狀態與透支。

施放結算完之後，施放者自己獲得 ``cost.self_status`` 的狀態與 ``cost.overdraft`` 的透支狀態
（不擲抵抗、不觸發控制遞減、不受 Boss 硬控轉換影響——見 ``ApplyStatusEffect.self_paid``）。
"""

from __future__ import annotations

from trpg.content.skills import SkillDef
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, EffectBase
from trpg.engine.ids import OVERDRAWN
from trpg.engine.state import UnitState
from trpg.shared.types import UnitId

__all__ = ["OVERDRAFT_DURATION", "pay_self_costs", "self_cost_effects"]

OVERDRAFT_DURATION = 2
"""透支狀態的持續回合：施放當回合結束 −1，剩下的 1 在下一個回合開始時扣 AP、該回合結束移除。"""


def self_cost_effects(caster_id: UnitId, skill: SkillDef) -> list[EffectBase]:
    """技能施放後施放者要承受的狀態（自身狀態代價、透支）；沒有時為空串列。"""
    out: list[EffectBase] = []
    cost = skill.cost
    if cost.self_status is not None:
        out.append(
            ApplyStatusEffect(
                source_id=caster_id,
                target_id=caster_id,
                status_id=cost.self_status.status,
                duration=cost.self_status.duration,
                self_paid=True,
            )
        )
    if cost.overdraft is not None:
        out.append(
            ApplyStatusEffect(
                source_id=caster_id,
                target_id=caster_id,
                status_id=OVERDRAWN,
                duration=OVERDRAFT_DURATION,
                self_paid=True,
            )
        )
    return out


def pay_self_costs(ctx: Ctx, unit: UnitState, skill: SkillDef) -> None:
    """施放結算完之後，施放者承受自己付的代價。自暈（``skip_turn`` 狀態）不影響本回合（3-50b）：
    狀態帶 ``dormant``，回合結束才生效，下一個回合被跳過、再下一個回合恢復。"""
    effects = self_cost_effects(unit.id, skill)
    if effects:
        execute(ctx, effects)
