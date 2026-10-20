"""賭博型技能的 AI（Phase 3D-7a，最簡單的近似；係數在 ai_profiles.yaml 的 ``gamble:``）。

- **期望值**：賭注（``gamble``）的技能，預覽附上兩個分支各自的完整預覽（
  :attr:`trpg.engine.preview.Preview.gamble`），AI 對每個分支各自評分，再依分支的機率加權平均。
- **失手反噬**（``cost.on_miss``）：預覽只算命中的情形，所以另外扣「未命中的機率 × 反噬的價值」。
- **不在快死時亂賭**（:func:`cautious`）：施放者的 HP 低於 ``hp_floor_permille`` 時，反噬可能造成
  傷害的賭博技能，正分乘上 ``low_hp_permille``（大幅降低）。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import AiProfile
from trpg.content.skills import SELF_DAMAGE_OF_HIT, EffectSpec, SkillDef
from trpg.engine.preview import Preview
from trpg.engine.state import BattleState, UnitState

__all__ = ["can_hurt_caster", "cautious", "on_miss_cost", "overloads"]

_PERMILLE = 1000


def can_hurt_caster(skill: SkillDef) -> bool:
    """反噬可能對施放者造成傷害：失手反噬有傷害，或賭注的分支有對自己的傷害或
    ``self_damage_of_hit``。"""
    if any(sub.type == "damage" for sub in skill.cost.on_miss):
        return True
    for effect in skill.effects:
        for sub in (*(effect.win or ()), *(effect.lose or ())):
            if sub.type == SELF_DAMAGE_OF_HIT or (sub.type == "damage" and sub.affects == "self"):
                return True
    return False


def overloads(state: BattleState, actor: UnitState, skill: SkillDef) -> bool:
    """這次施放會把超載層數（``content/stacks.yaml`` 的 ``overload``）累積到門檻，使施放者吃到會
    造成傷害的反噬（Phase 3C-6a：低血量規則也套用到會超載的技能）。"""
    for effect in skill.effects:
        if effect.type != "add_stack" or effect.stack is None:
            continue
        overload = state.ruleset.stack_def(effect.stack).overload
        if overload is None or not any(sub.type == "damage" for sub in overload.backlash):
            continue
        if actor.stacks.get(effect.stack, 0) + (effect.amount or 1) >= overload.threshold:
            return True
    return False


def cautious(
    state: BattleState, actor: UnitState, skill: SkillDef, score: Fraction, profile: AiProfile
) -> Fraction:
    """施放者 HP 太低時，降低會自傷的賭博技能（含這次會超載的技能）的分數（正分乘
    ``low_hp_permille``；負分不變）。"""
    rules = profile.gamble
    if not (can_hurt_caster(skill) or overloads(state, actor, skill)) or score <= 0:
        return score
    if actor.hp * _PERMILLE >= actor.max_hp * rules.hp_floor_permille:
        return score
    return score * Fraction(rules.low_hp_permille, _PERMILLE)


def _self_damage_estimate(actor: UnitState, skill: SkillDef, sub: EffectSpec) -> Fraction:
    """失手反噬傷害的粗估：法術技為效果自己的骰子平均，武器技為武器骰平均（含固定值）× 倍率。"""
    if skill.category == "spell" and sub.dice is not None:
        dice, flat, mult = sub.dice, 0, Fraction(1)
    else:
        dice, flat = actor.weapon.dice, actor.weapon.flat
        mult = Fraction(sub.multiplier_permille or _PERMILLE, _PERMILLE)
    return (Fraction(dice.count * (dice.sides + 1), 2) + flat) * mult


def on_miss_cost(actor: UnitState, skill: SkillDef, p: Preview, profile: AiProfile) -> Fraction:
    """失手反噬的期望成本：未命中任何敵人的機率 × 反噬的價值（傷害用 ``friendly_fire`` 權重、
    狀態用 ``status_values``，沒列出的狀態用 ``status`` 權重）。"""
    if not skill.cost.on_miss:
        return Fraction(0)
    miss = Fraction(1)
    enemies = [t for t in p.targets if not t.ally]
    if not enemies:
        return Fraction(0)
    for t in enemies:
        miss *= 1 - t.hit_chance
    w = profile.weights
    cost = Fraction(0)
    for sub in skill.cost.on_miss:
        if sub.type == "damage":
            cost += w.friendly_fire * _self_damage_estimate(actor, skill, sub)
        elif sub.status is not None:
            points = profile.status_values.get(sub.status)
            cost += w.status if points is None else w.damage * points
    return miss * cost
