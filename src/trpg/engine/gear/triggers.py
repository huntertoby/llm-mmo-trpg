"""裝備的觸發（第 6 類）與充能（第 7 類）詞條的結算（Phase 3G-G3a，``docs/design/08-裝備.md``
8.21.2.6、8.21.2.7、8.21.5.3）。

沿用被動技能的觸發機制（:mod:`trpg.engine.skill_triggers`）：收集時記一筆 ``Fired``
（``event`` 為 ``gear:<時機>``、``skill_id`` 為詞條 ID），等效果佇列清空後依事件順序結算。

- **觸發**（:class:`~trpg.content.equipment.TriggerAffix`）：持有者在場、沒有 ``skip_turn``、
  這條詞條
  本回合（``limit: per_turn``，自己回合開始時清除）或本輪（``per_round``）還沒觸發過，深度在
  ``max_trigger_depth`` 內，才發出 ``gear_triggered`` 並結算效果（自動命中、歸給持有者）。**每條
  每回合最多 1 次**；深度超過時發出 ``trigger_limit_reached``（不計次數）。同 id 兩件只算 1 條
  （G1 的非數值類遞減：:meth:`~trpg.engine.gear.state.GearState.active_affixes` 只回傳生效的）。
- **充能累積**（:class:`~trpg.content.equipment.ChargeAffix`）：``gain_trigger`` 時持有者累積 1 層
  （裝備版上限 ``max_stacks``，沒有每回合限制）。啟動見 :mod:`trpg.engine.gear.charge`。

效果的包裝：詞條的 ``effects`` 包成一個被動技能（:func:`gear_carrier`），沒有寫 ``affects`` 的效果
依 ``effect_target`` 補上（``self`` → 持有者自己，其餘 → 敵方）。
"""

from __future__ import annotations

from trpg.content.equipment import AttackAffix, ChargeAffix, TriggerAffix
from trpg.content.library import Ruleset
from trpg.content.skills import (
    DETONATE_RUNES,
    INSCRIBE,
    ON_SUMMON_DOWNED,
    EffectSpec,
    ShapeSpec,
    SkillDef,
)
from trpg.engine.context import Ctx
from trpg.engine.events import GearTriggered
from trpg.engine.rules.statuses import effective_attribute, skip_turn_status
from trpg.engine.skill_triggers import (
    GEAR_ATTACK_RUNE,
    GEAR_PREFIX,
    Fired,
    check_trigger_depth,
)
from trpg.engine.skills.casting import use_gear_effects
from trpg.engine.stacks import add_stacks
from trpg.engine.state import UnitState
from trpg.shared.types import Attribute, Element

DEFAULT_RUNE_ROUNDS = 2
"""普攻刻下的符文預設持續輪數（6.25 普攻與符文）。"""

__all__ = ["gear_carrier", "resolve_gear_fired"]

_DEAD_TARGET_TIMINGS = ("on_kill", ON_SUMMON_DOWNED)
"""另一方已經倒下仍然結算的觸發時機（擊倒時：地面效果；召喚物倒下時：以牠的位置為中心結算）。"""


def gear_carrier(
    rules: Ruleset, unit: UnitState, affix: TriggerAffix | ChargeAffix | AttackAffix
) -> SkillDef:
    """詞條的效果包成的被動技能（不經過 schema 驗證）：縮放屬性取持有者最高的屬性（同分取字母序
    在前者），形狀是 ``self``。"""
    effects: tuple[EffectSpec, ...]
    if isinstance(affix, AttackAffix):  # 普攻符文（3-31）：沿用原語的預設對象
        effects = (_rune_effect(affix),)
    else:
        affects = "self" if affix.effect_target == "self" else "enemies"
        effects = tuple(
            e if e.affects is not None else e.model_copy(update={"affects": affects})
            for e in affix.effects
        )
    best = max(sorted(Attribute), key=lambda a: effective_attribute(rules, unit, a))
    return SkillDef.model_construct(
        id=f"skill_gear_{affix.id.removeprefix('affix_')}",
        name_zh=affix.name_zh,
        tier=1,
        rank=1,
        rarity="common",
        kind="passive",
        skeleton="passive",
        category="spell",
        weapon_req="any",
        scaling_attr=best,
        shape=ShapeSpec(type="self"),
        effects=effects,
    )


def resolve_gear_fired(ctx: Ctx, fired: Fired) -> None:
    """結算一筆裝備詞條的 :class:`~trpg.engine.skill_triggers.Fired`（見模組說明）。"""
    state = ctx.state
    owner = state.units.get(fired.owner_id)
    if state.ended or owner is None or not owner.alive:
        return
    gear = next((g for g in owner.gear.active_affixes() if g.affix.id == fired.skill_id), None)
    if gear is None:
        return
    affix = gear.affix
    if isinstance(affix, AttackAffix):
        _resolve_attack_rune(ctx, owner, affix, fired)
        return
    if isinstance(affix, ChargeAffix):
        add_stacks(ctx, owner, affix.stack, 1, source_id=owner.id, limit=affix.max_stacks)
        return
    assert isinstance(affix, TriggerAffix)
    _resolve_trigger(ctx, owner, affix, fired)


def _rune_effect(affix: AttackAffix) -> EffectSpec:
    """普攻符文詞條的效果：``detonate`` 只引爆目標那 1 格、``inscribe`` 在目標格刻下符文。"""
    if affix.rune == "detonate":
        return EffectSpec(type=DETONATE_RUNES, dice=affix.dice, scope="target_cell")
    return EffectSpec(
        type=INSCRIBE,
        element=affix.rune_element or Element.LIGHTNING,
        duration=affix.rune_rounds or DEFAULT_RUNE_ROUNDS,
    )


def _resolve_attack_rune(ctx: Ctx, owner: UnitState, affix: AttackAffix, fired: Fired) -> None:
    """普攻命中後的符文詞條（Phase 3-31）：目標還活著，這條詞條本回合沒用過（每回合 1 次，自己回合
    開始時清除），深度在上限內；結算在目標所在的那 1 格。"""
    other = None if fired.other_id is None else ctx.state.units.get(fired.other_id)
    if other is None or not other.alive or skip_turn_status(ctx.rules, owner) is not None:
        return
    if owner.gear_turn_counts.get(affix.id, 0) >= 1:
        return
    if not check_trigger_depth(ctx, owner.id, affix.id, fired.depth):
        return
    owner.gear_turn_counts[affix.id] = owner.gear_turn_counts.get(affix.id, 0) + 1
    ctx.emit(
        GearTriggered,
        unit_id=owner.id,
        affix_id=affix.id,
        name_zh=affix.name_zh,
        trigger=GEAR_ATTACK_RUNE,
        other_id=other.id,
        trigger_depth=fired.depth,
    )
    ctx.trigger_depth = fired.depth
    carrier = gear_carrier(ctx.rules, owner, affix)
    use_gear_effects(ctx, owner, carrier, other)


def _resolve_trigger(ctx: Ctx, owner: UnitState, affix: TriggerAffix, fired: Fired) -> None:
    timing = fired.event.removeprefix(GEAR_PREFIX)
    if skip_turn_status(ctx.rules, owner) is not None:
        return
    counts = owner.gear_turn_counts if affix.limit == "per_turn" else owner.gear_round_counts
    if counts.get(affix.id, 0) >= 1:
        return
    other = None if fired.other_id is None else ctx.state.units.get(fired.other_id)
    if affix.effect_target != "self" and (
        other is None or (not other.alive and timing not in _DEAD_TARGET_TIMINGS)
    ):
        return
    if not check_trigger_depth(ctx, owner.id, affix.id, fired.depth):
        return
    counts[affix.id] = counts.get(affix.id, 0) + 1
    ctx.emit(
        GearTriggered,
        unit_id=owner.id,
        affix_id=affix.id,
        name_zh=affix.name_zh,
        trigger=timing,
        other_id=fired.other_id,
        trigger_depth=fired.depth,
    )
    ctx.trigger_depth = fired.depth
    subject = None if affix.effect_target == "self" else other
    use_gear_effects(ctx, owner, gear_carrier(ctx.rules, owner, affix), subject)
