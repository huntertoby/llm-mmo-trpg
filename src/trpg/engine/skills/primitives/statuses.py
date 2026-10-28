"""狀態與層數原語：施加、消耗狀態、奪取與驅散增益、揭露、定時炸彈、累積層數。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.battle import Dice
from trpg.content.skills import (
    TIME_BOMB,
    EffectSpec,
)
from trpg.engine import modifiers
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    RemoveStatusEffect,
    ShieldEffect,
)
from trpg.engine.events import (
    EffectFizzled,
)
from trpg.engine.forms import enter_form as enter_unit_form
from trpg.engine.ids import CONCEALED, REVEALED
from trpg.engine.resources import (
    dispelled_buffs,
    pick_stolen_buff,
)
from trpg.engine.rules.combat import PERMILLE
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.primitives.base import Handler
from trpg.engine.skills.targeting import (
    ResolvedEffect,
    damage_parameters,
)
from trpg.engine.stacks import add_stacks, consume_stacks
from trpg.engine.state import UnitState
from trpg.engine.traps import reveal_traps

if TYPE_CHECKING:
    from trpg.engine.skills.cast import Cast


def apply_status(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """施加狀態：對敵方先轉換（Boss）、再擲抵抗判定（:mod:`trpg.engine.control`）；
    對友方與自己不擲。"""
    batch: list[EffectBase] = []
    for unit in cast.targets(effect.affects, spec.condition):
        batch += cast.status_effects(spec, unit)
    return batch


def consume_status(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``consume_status``：每個有該狀態的對象先移除狀態（立刻結算），再對它（與 ``splash``
    範圍內的敵方單位）結算 ``then``。沒有任何對象有該狀態時發出 ``effect_fizzled``。"""
    assert spec.status is not None and spec.then
    ctx = cast.ctx
    batch: list[EffectBase] = []
    consumed = False
    for unit in cast.targets(effect.affects, spec.condition):
        instance = unit.get_status(spec.status)
        if instance is None:
            continue
        consumed = True
        scale = _consume_scale(cast, unit, spec, instance.remaining)
        execute(
            ctx,
            [
                RemoveStatusEffect(
                    source_id=cast.caster.id,
                    target_id=unit.id,
                    status_id=spec.status,
                    reason="consumed",
                )
            ],
        )
        batch += _consume_then(cast, unit, spec, scale)
    if not consumed:
        ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_status")
    return batch


def _consume_scale(cast: Cast, unit: UnitState, spec: EffectSpec, remaining: int | None) -> int:
    """``then`` 的骰數倍率：``remaining_rounds``（永久狀態為 1）或同時消耗的目標型層數；
    至少 1、至多 ``consume_status_max_scale``。"""
    cap = cast.ctx.core.consume_status_max_scale
    if spec.scale == "remaining_rounds":
        return max(1, min(cap, remaining or 1))
    if spec.scale == "stacks":
        assert spec.stack is not None
        spent = consume_stacks(cast.ctx, unit, spec.stack, source_id=cast.caster.id)
        return max(1, min(cap, spent))
    return 1


def _consume_then(cast: Cast, unit: UnitState, spec: EffectSpec, scale: int) -> list[EffectBase]:
    recipients = [unit]
    if spec.splash is not None:
        near = [
            u
            for u in cast.ctx.state.units_sorted()
            if u.alive
            and u.id != unit.id
            and u.team is not cast.caster.team
            and manhattan(u.xy, unit.xy) <= spec.splash
        ]
        recipients += near
    batch: list[EffectBase] = []
    for sub in spec.then or ():
        scaled = sub
        if sub.dice is not None and scale > 1:
            dice = sub.dice
            scaled = sub.model_copy(
                update={"dice": Dice(count=dice.count * scale, sides=dice.sides)}
            )
        for target in recipients:
            batch += _then_effect(cast, scaled, target)
    return batch


def _then_effect(cast: Cast, spec: EffectSpec, target: UnitState) -> list[EffectBase]:
    """``then`` 的一個效果對 ``target`` 的結算（自動命中、不暴擊、沒有格擋）。"""
    caster = cast.caster
    if spec.type == "damage":
        dice, flat, scaled, multiplier, element = damage_parameters(
            cast.ctx.state, caster, cast.skill, spec, modified=cast.modified
        )
        bonus = cast.modifier(modifiers.damage_permille, target)
        return [
            DamageEffect(
                target_id=target.id,
                source_id=caster.id,
                cause="attack",
                element=element,
                dice=dice,
                flat=flat,
                scaled_permille=scaled,
                min_damage=cast.ctx.core.min_damage_on_hit,
                multiplier_permille=multiplier * bonus // PERMILLE,
            )
        ]
    if spec.type == "heal":
        return [
            HealEffect(
                target_id=target.id,
                source_id=caster.id,
                dice=spec.dice,
                scaled_permille=cast.spell_scaled(),
                multiplier_permille=cast.level_permille(),
            )
        ]
    if spec.type == "shield":
        return [
            ShieldEffect(
                target_id=target.id,
                source_id=caster.id,
                dice=spec.dice,
                scaled_permille=cast.spell_scaled(),
                multiplier_permille=cast.level_permille(),
                duration=spec.duration,
            )
        ]
    return cast.status_effects(spec, target)


def steal_buff(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``steal_buff``：每個有增益的對象先失去一個增益（原因 ``stolen``），再把同一個狀態以相同
    的剩餘回合與數值施加到施放者身上。沒有任何對象有增益時發出 ``effect_fizzled``。"""
    removals: list[EffectBase] = []
    batch: list[EffectBase] = []
    for unit in cast.targets(effect.affects, spec.condition):
        buff = pick_stolen_buff(cast.ctx, unit)
        if buff is None:
            continue
        removals.append(
            RemoveStatusEffect(
                source_id=cast.caster.id,
                target_id=unit.id,
                status_id=buff.status_id,
                reason="stolen",
            )
        )
        batch.append(
            ApplyStatusEffect(
                source_id=cast.caster.id,
                target_id=cast.caster.id,
                status_id=buff.status_id,
                duration=buff.remaining,
                amount=buff.amount,
            )
        )
    if not batch:
        cast.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_buff")
    execute(cast.ctx, removals)  # 先「被奪走」再「獲得」（效果排序會把施加排在移除之前；3C-6a）
    return batch


def dispel(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``dispel``（Phase 3D-8a）：每個對象失去 ``count`` 個增益（剩餘回合最長者先，永久最長；
    ``all`` 為全部；原因 ``dispelled``）。沒有任何對象有增益時發出 ``effect_fizzled``。"""
    batch: list[EffectBase] = [
        RemoveStatusEffect(
            source_id=cast.caster.id,
            target_id=unit.id,
            status_id=buff.status_id,
            reason="dispelled",
        )
        for unit in cast.targets(effect.affects, spec.condition)
        for buff in dispelled_buffs(cast.ctx, unit, spec.count or 1)
    ]
    if not batch:
        cast.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="no_buff")
    return batch


def reveal(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``reveal``（Phase 3D-8a）：範圍內的敵人不擲命中就失去 ``concealed`` 狀態（原因
    ``revealed``）並獲得 ``revealed`` 狀態 ``duration`` 回合（期間不算隱蔽、不能再隱蔽）；
    範圍內的敵方陷阱對施放者的陣營顯示。範圍內沒有敵人也沒有敵方陷阱時發出
    ``effect_fizzled``。"""
    batch: list[EffectBase] = []
    for unit in sorted((u for u in cast.enemies if u.alive), key=lambda u: u.id):
        if unit.has_status(CONCEALED):
            batch.append(
                RemoveStatusEffect(
                    source_id=cast.caster.id,
                    target_id=unit.id,
                    status_id=CONCEALED,
                    reason="revealed",
                )
            )
        batch.append(
            ApplyStatusEffect(
                source_id=cast.caster.id,
                target_id=unit.id,
                status_id=REVEALED,
                duration=spec.duration,
            )
        )
    before = len(cast.ctx.events)
    reveal_traps(cast.ctx, cast.caster, cast.area.tiles)
    if not batch and len(cast.ctx.events) == before:
        cast.ctx.emit(EffectFizzled, effect_kind=spec.type, pos=None, reason="nothing_hidden")
    return batch


def delayed_damage(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``delayed_damage``（Phase 3D-8b）：命中的敵人身上附加定時炸彈（狀態 ``time_bomb``，剩餘
    回合 ＝ 倒數；已經有炸彈的目標不再附加）。爆炸見 :mod:`trpg.engine.bombs`。"""
    batch: list[EffectBase] = []
    for unit in cast.targets(effect.affects, spec.condition):
        if unit.has_status(TIME_BOMB):
            cast.ctx.emit(
                EffectFizzled, effect_kind=spec.type, pos=unit.pos, reason="already_bombed"
            )
            continue
        batch.append(
            ApplyStatusEffect(
                source_id=cast.caster.id,
                target_id=unit.id,
                status_id=TIME_BOMB,
                duration=spec.rounds,
                skill_id=cast.skill.id,
            )
        )
    return batch


def _add_stack(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> None:
    """``add_stack``：``owner: self`` 的層數加在施放者身上（技能有對敵方的效果時，至少命中一名
    敵人才累積）；``owner: target`` 的加在每個被命中的目標身上。"""
    assert spec.stack is not None
    amount = spec.amount or 1
    if cast.ctx.rules.stack_def(spec.stack).owner == "self":
        # 命中的敵人即使被這一擊擊倒也算（命中判定在效果結算之前就決定了）
        connected = not any(e.hostile for e in cast.effects) or any(
            cast.is_hit(u) for u in cast.enemies
        )
        subject = Subject(cast.caster, cast.caster.xy)
        if connected and cast.caster.alive and cast.holds(spec.condition, subject):
            add_stacks(cast.ctx, cast.caster, spec.stack, amount, source_id=cast.caster.id)
        return
    for unit in cast.targets(effect.affects, spec.condition):
        add_stacks(cast.ctx, unit, spec.stack, amount, source_id=cast.caster.id)


def add_stack(cast: Cast, effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    _add_stack(cast, effect, spec)
    return []


def enter_form(cast: Cast, _effect: ResolvedEffect, spec: EffectSpec) -> list[EffectBase]:
    """``enter_form``（Phase 3J-1a，6.30）：施放者進入 ``form``（元素取動作的 ``form_element``，
    省略為清單第一個）；回傳進入獎勵中要結算的效果（見 :mod:`trpg.engine.forms`）。"""
    assert spec.form is not None
    action = cast.action
    element = None if action is None else action.form_element
    return enter_unit_form(cast.ctx, cast.caster, spec.form, element, cast.skill.id)


HANDLERS: dict[str, Handler] = {
    "apply_status": apply_status,
    "enter_form": enter_form,
    "consume_status": consume_status,
    "steal_buff": steal_buff,
    "dispel": dispel,
    "reveal": reveal,
    "delayed_damage": delayed_damage,
    "add_stack": add_stack,
}
