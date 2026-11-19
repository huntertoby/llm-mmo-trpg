"""技能內的擊殺時效果（``on_kill``，Phase 3D-8b，``docs/design/06-技能.md`` 6.18 F）的專用效果。

``refund_ap`` 與 ``refund_cooldown`` 只能出現在傷害效果的 ``on_kill`` 裡，不是改寫規則型原語
（不佔 ``max_rule_rewrite``、不受「每輪最多被給一次 AP」與傳說門檻限制）：

- ``refund_ap``：施放者獲得 ``amount`` AP，超過本回合上限（:func:`~trpg.engine.rewrites.ap_cap`）的
  部分不保留；
- ``refund_cooldown``：本技能的冷卻歸零（``skill_cooldown_changed``，``remaining: 0``）。

另有 **失手返還**（AP-1，#168，05 5.2「⚠ AP 改版」）：實際花了至少 ``miss_refund_min_cost`` AP 的
技能施放，所有敵方目標都沒命中時返還 ``miss_refund_ap`` AP（:func:`refund_on_miss`）。一個目標
「沒命中」＝擲了命中而每一下都失手；或命中（或不擲命中）之後，對它的抵抗判定（狀態、位移與擊倒的對抗）全部被
抵抗、而且沒有受到這次施放的傷害（被豁免擋下）。不擲命中也沒有抵抗判定的目標（自動生效）算命中。範圍技命中
一個就不返還；敵我都適用，每個單位每回合最多 1 次（``UnitState.miss_refunded``）；不算進裝備的
每回合 AP 回復上限（``ap_gain_turn``）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from trpg.engine.context import Ctx
from trpg.engine.events import (
    ApRefunded,
    AttackRolled,
    DamageDealt,
    ManeuverRolled,
    SkillCooldownChanged,
    StatusSaveRolled,
)
from trpg.engine.events.base import EventBase
from trpg.engine.rewrites import ap_cap
from trpg.engine.state import UnitState

__all__ = ["all_targets_missed", "refund_ap", "refund_cooldown", "refund_on_miss"]


def refund_ap(ctx: Ctx, caster: UnitState, skill_id: str, amount: int) -> None:
    """施放者獲得 ``amount`` AP（不超過上限）；實際沒有增加時不產生事件。"""
    before = caster.ap
    caster.ap = max(before, min(before + amount, ap_cap(ctx.core, caster)))
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


def all_targets_missed(
    events: Sequence[EventBase], caster_id: str, rolls: Mapping[str, Sequence[bool]]
) -> bool:
    """``rolls``（敵方目標 ID → 這次施放對它擲命中的結果，沒擲為空）裡每個目標都沒命中；沒有目標時
    為 ``False``（沒有可失手的對象）。``events`` 是這次施放產生的事件。"""
    return bool(rolls) and all(
        _target_missed(events, caster_id, uid, rolls[uid]) for uid in sorted(rolls)
    )


def _target_missed(
    events: Sequence[EventBase], caster_id: str, uid: str, rolled: Sequence[bool]
) -> bool:
    attacks = [
        e.hit
        for e in events
        if isinstance(e, AttackRolled) and e.attacker_id == caster_id and e.target_id == uid
    ]
    hits = [*rolled, *attacks]
    if hits and not any(hits):
        return True  # 擲了命中，每一下都失手
    saves = [
        e.applied if isinstance(e, StatusSaveRolled) else e.success
        for e in events
        if isinstance(e, StatusSaveRolled | ManeuverRolled)
        and e.attacker_id == caster_id
        and e.target_id == uid
    ]
    if not saves or any(saves):
        return False  # 自動生效，或至少一個狀態上身
    damaged = any(
        isinstance(e, DamageDealt) and e.target_id == uid and e.source_id == caster_id
        for e in events
    )
    return not damaged  # 被豁免擋下：狀態全被抵抗、也沒受到傷害


def refund_on_miss(
    ctx: Ctx,
    caster: UnitState,
    skill_id: str,
    paid_ap: int,
    *,
    rolls: Mapping[str, Sequence[bool]],
    start: int,
) -> None:
    """失手返還（見模組說明）。``start``：這次施放開始時 ``ctx.events`` 的長度。"""
    core = ctx.core
    if core.miss_refund_ap <= 0 or paid_ap < core.miss_refund_min_cost:
        return
    if caster.miss_refunded or not caster.alive:
        return
    if not all_targets_missed(ctx.events[start:], caster.id, rolls):
        return
    before = caster.ap
    caster.ap = max(before, min(before + core.miss_refund_ap, ap_cap(core, caster)))
    if caster.ap <= before:
        return
    caster.miss_refunded = True
    ctx.emit(
        ApRefunded,
        unit_id=caster.id,
        skill_id=skill_id,
        amount=caster.ap - before,
        ap_after=caster.ap,
        on_miss=True,
    )
