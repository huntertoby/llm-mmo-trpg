"""技能內的擊殺時效果（``on_kill``，Phase 3D-8b，``docs/design/06-技能.md`` 6.18 F）的專用效果。

``refund_ap`` 與 ``refund_cooldown`` 只能出現在傷害效果的 ``on_kill`` 裡，不是改寫規則型原語
（不佔 ``max_rule_rewrite``、不受「每輪最多被給一次 AP」與傳說門檻限制）：

- ``refund_ap``：施放者獲得 ``amount`` AP，超過本回合上限（:func:`~trpg.engine.rewrites.ap_cap`）的
  部分不保留；
- ``refund_cooldown``：本技能的冷卻歸零（``skill_cooldown_changed``，``remaining: 0``）。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import ApRefunded, SkillCooldownChanged
from trpg.engine.rewrites import ap_cap
from trpg.engine.state import UnitState

__all__ = ["refund_ap", "refund_cooldown"]


def refund_ap(ctx: Ctx, caster: UnitState, skill_id: str, amount: int) -> None:
    """施放者獲得 ``amount`` AP（不超過上限）；實際沒有增加時不產生事件。"""
    before = caster.ap
    caster.ap = max(before, min(before + amount, ap_cap(ctx.core)))
    if caster.ap > before:
        caster.ap_gain_turn += caster.ap - before
        ctx.emit(
            ApRefunded,
            unit_id=caster.id,
            skill_id=skill_id,
            amount=caster.ap - before,
            ap_after=caster.ap,
        )


def refund_cooldown(ctx: Ctx, caster: UnitState, skill_id: str) -> None:
    """本技能的冷卻歸零；沒有在冷卻中時不產生事件。"""
    if caster.cooldowns.pop(skill_id, 0) > 0:
        ctx.emit(SkillCooldownChanged, unit_id=caster.id, skill_id=skill_id, remaining=0)
