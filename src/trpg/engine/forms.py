"""形態的狀態轉換（Phase 3J-1a，``docs/design/06-技能.md`` 6.30）。

形態是姿態的擴充（:class:`~trpg.engine.state.FormState`）：

- **進入**（``enter_form`` 原語）：先移除一般姿態（``replaced``）、離開目前的形態（``switched``）；
  把普攻武器換成天生武器（手上的武器與進入前的裝備狀態存進 ``FormState``，主手的普攻詞條與武器
  特性強化詞條在形態中不生效）、最大 HP 依 ``max_hp_permille`` 加減（目前 HP 不變但不超過上限）；
  發出 ``form_entered``，回傳進入獎勵的效果（護盾、治療、範圍傷害、隱蔽…）給呼叫端結算；
  命中／暴擊與本回合移動的獎勵直接寫進單位。
- **離開**（:func:`leave_form`）：換回手上的武器與裝備狀態、最大 HP 減回（目前 HP 不超過上限）、
  清掉「下一次攻擊」的獎勵、該形態冷卻 ``forms.yaml`` 的 ``cooldown`` 回合，發出 ``form_left``。
  原因見 :data:`~trpg.engine.events.FormLeaveReason`。
- **維持費**（:func:`pay_upkeep`）：自己的回合開始時扣耐力（物理）或法力（心智）；不夠付就自動
  解除（``upkeep``）。
- **冷卻**（:func:`tick_form_cooldowns`）：自己的回合開始時每個形態的冷卻 −1（同技能冷卻）。

移動加減在回合開始計算移動點數時套用（同狀態的 ``move_delta``），進入或離開當回合不重算。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.content.forms import CHOSEN, FormEntry
from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    ShieldEffect,
)
from trpg.engine.events import (
    EventBase,
    FormEntered,
    FormLeaveReason,
    FormLeft,
    FormUpkeepPaid,
    StatusRemoved,
)
from trpg.engine.gear_state import GearState
from trpg.engine.ids import CONCEALED
from trpg.engine.rules.forms import form_heal_permille
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.statuses import effective_attribute, stance_status_ids
from trpg.engine.state import FormState, UnitState
from trpg.shared.types import Element

__all__ = [
    "enter_form",
    "leave_all_forms",
    "leave_form",
    "pay_upkeep",
    "tick_form_cooldowns",
]

PERMILLE = 1000
_MAIN_HAND = "main_hand"
_HAND_CATEGORIES = ("attack", "weapon_trait")
"""形態中不生效的主手詞條類別：普攻附加與武器特性強化（6.30：手上武器的普攻詞條不生效）。"""


def _strip_hand_affixes(gear: GearState) -> GearState:
    """形態中的裝備狀態：拿掉主手的普攻附加與武器特性強化詞條（其餘不變）。"""
    kept = tuple(
        a
        for a in gear.affixes
        if not (a.slot == _MAIN_HAND and a.affix.category in _HAND_CATEGORIES)
    )
    return gear if len(kept) == len(gear.affixes) else replace(gear, affixes=kept)


def enter_form(
    ctx: Ctx, unit: UnitState, form_id: str, element: Element | None, skill_id: str | None
) -> list[EffectBase]:
    """``unit`` 進入 ``form_id``（合法性由呼叫端先檢查）：回傳進入獎勵中要交給效果佇列結算的
    效果。"""
    rules = ctx.rules
    form = rules.form_def(form_id)
    for old in stance_status_ids(rules, unit):  # 和姿態互斥：進入形態取代一般姿態
        unit.statuses = [s for s in unit.statuses if s.status_id != old]
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=old, reason="replaced")
    if unit.form is not None:
        leave_form(ctx, unit, "switched")
    chosen = (element or form.element_choices[0]) if form.element_choices else None
    permille = form.effects.max_hp_permille  # 加減的量無條件捨去（−10% 的 999 是 −99）
    delta = unit.max_hp * abs(permille) // PERMILLE * (1 if permille >= 0 else -1)
    unit.form = FormState(
        form_id=form.id,
        hand_weapon=unit.weapon,
        hand_gear=unit.gear,
        element=chosen,
        max_hp_delta=delta,
        skill_id=skill_id,
    )
    unit.weapon = form.natural_weapon.weapon_def(form.id, chosen)
    unit.gear = _strip_hand_affixes(unit.gear)
    unit.max_hp += delta
    unit.hp = min(unit.hp, unit.max_hp)
    ctx.emit(
        FormEntered,
        unit_id=unit.id,
        form_id=form.id,
        skill_id=skill_id,
        element=chosen,
        max_hp=unit.max_hp,
        hp=unit.hp,
    )
    return _entry_effects(ctx, unit, form.entry, chosen)


def _entry_effects(
    ctx: Ctx, unit: UnitState, entry: FormEntry, chosen: Element | None
) -> list[EffectBase]:
    """進入獎勵：命中／暴擊與本回合移動直接寫進單位；其餘回傳效果（依固定順序）。"""
    unit.next_attack_hit = max(unit.next_attack_hit, entry.next_attack_hit)
    unit.next_attack_crit = max(unit.next_attack_crit, entry.next_attack_crit)
    unit.move_points += entry.move
    effects: list[EffectBase] = []
    if entry.shield_max_hp_permille is not None:
        amount = unit.max_hp * entry.shield_max_hp_permille // PERMILLE
        if amount > 0:
            effects.append(
                ShieldEffect(
                    target_id=unit.id,
                    source_id=unit.id,
                    flat=amount,
                    duration=entry.shield_duration,
                )
            )
    if entry.heal_max_hp_permille is not None:
        amount = unit.max_hp * entry.heal_max_hp_permille // PERMILLE
        if amount > 0:
            effects.append(HealEffect(target_id=unit.id, source_id=unit.id, flat=amount))
    if entry.conceal is not None:
        effects.append(
            ApplyStatusEffect(
                target_id=unit.id, source_id=unit.id, status_id=CONCEALED, duration=entry.conceal
            )
        )
    effects += _burst_effects(ctx, unit, entry, chosen)
    effects += _heal_adjacent_effects(ctx, unit, entry)
    return effects


def _burst_effects(
    ctx: Ctx, unit: UnitState, entry: FormEntry, chosen: Element | None
) -> list[EffectBase]:
    burst = entry.burst
    if burst is None:
        return []
    element = chosen if burst.element == CHOSEN else burst.element
    assert isinstance(element, Element)
    return [
        DamageEffect(target_id=other.id, source_id=unit.id, element=element, dice=burst.dice)
        for other in ctx.state.units_sorted()
        if other.alive
        and other.team is not unit.team
        and manhattan(other.xy, unit.xy) <= burst.radius
    ]


def _heal_adjacent_effects(ctx: Ctx, unit: UnitState, entry: FormEntry) -> list[EffectBase]:
    heal = entry.heal_adjacent
    if heal is None:
        return []
    attr = effective_attribute(ctx.rules, unit, heal.attr)
    multiplier = PERMILLE + form_heal_permille(ctx.rules, unit)
    return [
        HealEffect(
            target_id=other.id,
            source_id=unit.id,
            dice=heal.dice,
            scaled_permille=attr * heal.attr_permille,
            multiplier_permille=multiplier,
        )
        for other in ctx.state.units_sorted()
        if other.alive
        and other.id != unit.id
        and other.team is unit.team
        and manhattan(other.xy, unit.xy) == 1
    ]


def leave_form(ctx: Ctx, unit: UnitState, reason: FormLeaveReason) -> list[EventBase]:
    """``unit`` 離開目前的形態（不在形態中時沒有效果）：換回武器與裝備、最大 HP 減回、該形態
    冷卻。回傳發出的事件。"""
    current = unit.form
    if current is None:
        return []
    cooldown = ctx.rules.forms.cooldown
    unit.form = None
    unit.weapon = current.hand_weapon
    unit.gear = current.hand_gear
    unit.max_hp = max(1, unit.max_hp - current.max_hp_delta)
    unit.hp = min(unit.hp, unit.max_hp)
    unit.next_attack_hit = 0
    unit.next_attack_crit = 0
    unit.form_cooldowns[current.form_id] = cooldown
    return [
        ctx.emit(
            FormLeft,
            unit_id=unit.id,
            form_id=current.form_id,
            reason=reason,
            cooldown=cooldown,
            max_hp=unit.max_hp,
            hp=unit.hp,
        )
    ]


def leave_all_forms(ctx: Ctx, reason: FormLeaveReason) -> None:
    """所有單位離開形態（戰鬥結束；依單位 ID）。"""
    for unit in ctx.state.units_sorted():
        if unit.form is not None:
            leave_form(ctx, unit, reason)


def tick_form_cooldowns(unit: UnitState) -> None:
    """自己的回合開始：每個冷卻中的形態 −1（歸零移除；依形態 ID）。"""
    for form_id in sorted(unit.form_cooldowns):
        remaining = unit.form_cooldowns[form_id] - 1
        if remaining <= 0:
            del unit.form_cooldowns[form_id]
        else:
            unit.form_cooldowns[form_id] = remaining


def pay_upkeep(ctx: Ctx, unit: UnitState) -> bool:
    """自己的回合開始付形態的維持費；付不起就自動解除。回傳是否因此離開形態。"""
    if unit.form is None:
        return False
    form = ctx.rules.form_def(unit.form.form_id)
    resource, amount = ctx.rules.forms.upkeep(form)
    have = unit.stamina if resource == "stamina" else unit.mana
    if have < amount:
        leave_form(ctx, unit, "upkeep")
        return True
    if amount == 0:
        return False
    if resource == "stamina":
        unit.stamina -= amount
    else:
        unit.mana -= amount
    ctx.emit(
        FormUpkeepPaid,
        unit_id=unit.id,
        form_id=form.id,
        resource=resource,
        amount=amount,
        remaining=have - amount,
    )
    return False
