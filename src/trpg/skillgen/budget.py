"""技能預算計算（``docs/phases/Phase2B計畫.md`` 4.2、``docs/design/06-技能.md`` 6.5）。

::

    效果點數  ＝ base_points × 強度係數 × 形狀倍率 × 對象係數 × 效果條件倍率
    raw       ＝ Σ 效果點數
    total     ＝ raw × 技能條件倍率 × Π 協同係數
    可用預算  ＝ tier_budget[tier] × AP係數 × (1000 ＋ 代價折抵‰) ÷ 1000
               （被動技能以觸發時機的係數取代 AP 係數，見 :func:`_passive_coefficient`）
    合格      ＝ 0.7 × 可用預算 ≤ total ≤ 1.0 × 可用預算

「強度係數」已併入各原語的點數算法（骰子平均值、武器倍率、距離、持續 ÷ 預設持續，見
``skill_primitives.yaml`` 的 ``budget_basis``）。全部以 :class:`fractions.Fraction` 計算，
不使用浮點數；顯示時才四捨五入。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from trpg.content.battle import Dice, StatusDef
from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import BudgetRules
from trpg.content.skills import ConditionDef, EffectSpec, PrimitiveDef, SkillDef
from trpg.skillgen.mechanics import mechanic_tags, resolved_affects

__all__ = ["BudgetError", "BudgetReport", "EffectBudget", "skill_budget"]

_PERMILLE = 1000
_SHAPED_AFFECTS = frozenset({"enemies", "allies", "all", "tiles"})


class BudgetError(ValueError):
    """技能無法計算預算（缺少點數資料、尚無算法的技能種類……）。"""


@dataclass(frozen=True, slots=True)
class EffectBudget:
    """一個效果的點數明細。``base`` 為基礎點數（含強度），其餘為各倍率。"""

    index: int
    type: str
    note: str
    base: Fraction
    shape: Fraction
    target: Fraction
    condition: Fraction
    points: Fraction


@dataclass(frozen=True, slots=True)
class BudgetReport:
    """:func:`skill_budget` 的結果：全部中間值，供 CLI 與驗證器使用。"""

    skill_id: str
    tier: int
    effects: tuple[EffectBudget, ...]
    raw: Fraction
    condition_multiplier: Fraction
    tags: tuple[str, ...]
    synergies: tuple[tuple[tuple[str, ...], Fraction], ...]
    total: Fraction
    tier_budget: int
    ap_coefficient: Fraction
    allowance_parts: tuple[tuple[str, int], ...]
    allowance_cap: int
    """折抵加總的上限（‰）。"""
    min_ratio: Fraction
    max_ratio: Fraction
    coefficient_label: str = "AP 係數"
    """可用預算公式中係數的名稱：主動技能為 AP 係數、被動為觸發係數（2E-1）。"""

    @property
    def allowance_raw_permille(self) -> int:
        """各項（已套用各自上限）加總，尚未套用總上限。"""
        return sum(value for _, value in self.allowance_parts)

    @property
    def allowance_permille(self) -> int:
        """實際採用的折抵（‰）：加總後以 ``allowance_cap`` 截斷。"""
        return min(self.allowance_raw_permille, self.allowance_cap)

    @property
    def allowance_capped(self) -> bool:
        return self.allowance_raw_permille > self.allowance_cap

    @property
    def usable(self) -> Fraction:
        """可用預算。"""
        return (
            self.tier_budget
            * self.ap_coefficient
            * Fraction(_PERMILLE + self.allowance_permille, _PERMILLE)
        )

    @property
    def ratio(self) -> Fraction:
        """total ÷ 可用預算。"""
        return self.total / self.usable

    @property
    def too_weak(self) -> bool:
        return self.ratio < self.min_ratio

    @property
    def over_budget(self) -> bool:
        return self.ratio > self.max_ratio

    @property
    def ok(self) -> bool:
        return not (self.too_weak or self.over_budget)


def _dice_average(dice: Dice) -> Fraction:
    return Fraction(dice.count * (dice.sides + 1), 2)


def _duration_ratio(duration: int | None, default: int | None) -> Fraction:
    if duration is None or default is None:
        return Fraction(1)
    return Fraction(duration, default)


def _fmt(value: Fraction) -> str:
    return f"{float(value):g}"


def _base_points(  # noqa: PLR0911
    skill: SkillDef, effect: EffectSpec, primitive: PrimitiveDef, library: ContentLibrary
) -> tuple[Fraction, str]:
    """基礎點數（含強度）與一句說明。"""
    rules = library.ruleset
    basis = primitive.budget_basis
    if basis is None:
        raise BudgetError(f"原語 {primitive.id} 沒有預算算法（budget_basis）")
    if basis == "fixed":
        assert primitive.base_points is not None
        return Fraction(primitive.base_points), "固定"
    if basis == "per_distance":
        assert primitive.base_points is not None
        distance = effect.distance or 1
        return Fraction(primitive.base_points * distance), f"{primitive.base_points}×{distance} 格"
    if basis == "per_amount":
        assert primitive.base_points is not None
        amount = effect.amount or 1
        return Fraction(primitive.base_points * amount), f"{primitive.base_points}×{amount} 層"
    if basis == "consume_stack":
        return _consume_stack_points(skill, effect, library)
    if basis == "dice_average" or (basis == "damage" and skill.category == "spell"):
        if effect.dice is None:
            raise BudgetError(f"效果 {primitive.id} 缺少 dice，無法計算點數")
        return _dice_average(effect.dice), f"{effect.dice} 平均"
    if basis == "damage":
        permille = effect.multiplier_permille or _PERMILLE
        reference = rules.core.budget_reference_weapon_damage
        return Fraction(permille * reference, _PERMILLE), f"武器 ×{permille / _PERMILLE:g}"
    if basis == "status":
        return _status_points(effect, rules.statuses.by_id())
    return _surface_points(effect, library)


def _consume_stack_points(
    skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``consume_stack`` 的加成點數：同技能傷害效果（含形狀與對象倍率）× 期望消耗層數 ×
    ``per_stack_permille``；期望消耗＝層數上限 × ``consume_stack_expected_permille``。"""
    rules, budget = library.ruleset, library.budget
    if effect.stack is None or effect.per_stack_permille is None:
        raise BudgetError("consume_stack 缺少 stack 或 per_stack_permille")
    expected = Fraction(
        rules.stack_def(effect.stack).max * budget.consume_stack_expected_permille, _PERMILLE
    )
    primitives = rules.primitives.by_id()
    damage = Fraction(0)
    for other in skill.effects:
        if other.type == "damage":
            base, _ = _base_points(skill, other, primitives["damage"], library)
            damage += base * _shape_multiplier(skill, other, primitives["damage"], library)
    bonus = damage * expected * Fraction(effect.per_stack_permille, _PERMILLE)
    return bonus, f"傷害 {_fmt(damage)} × 期望 {_fmt(expected)} 層 × {effect.per_stack_permille}‰"


def _shape_multiplier(
    skill: SkillDef, effect: EffectSpec, primitive: PrimitiveDef, library: ContentLibrary
) -> Fraction:
    """形狀倍率（只對作用在單位的效果）；陷阱技能取 ``trap.shape`` 的倍率（觸發時的影響範圍）。"""
    rules = library.ruleset
    affects = resolved_affects(rules, effect)
    if not (affects in _SHAPED_AFFECTS and primitive.acts_on != "caster"):
        return Fraction(1)
    if skill.trap is not None:
        shape = rules.shapes.by_id()[skill.trap.shape]
        return Fraction(shape.budget.permille_for({}), _PERMILLE)
    shape = rules.shapes.by_id()[skill.shape.type]
    return Fraction(shape.budget.permille_for(skill.shape.param_values()), _PERMILLE)


def _status_points(effect: EffectSpec, statuses: dict[str, StatusDef]) -> tuple[Fraction, str]:
    status = statuses.get(effect.status or "")
    if status is None:
        raise BudgetError(f"未知的狀態 {effect.status!r}")
    if status.budget_points is None:
        raise BudgetError(f"狀態 {status.id}（{status.name_zh}）沒有預算點數，不能由技能施加")
    ratio = _duration_ratio(effect.duration, status.duration)
    return status.budget_points * ratio, f"{status.id} {status.budget_points}×{_fmt(ratio)}"


def _surface_points(effect: EffectSpec, library: ContentLibrary) -> tuple[Fraction, str]:
    if effect.surface is None:
        raise BudgetError("create_surface 缺少 surface")
    surface = library.ruleset.surfaces.get(effect.surface)
    if surface.budget_points is None:
        raise BudgetError(f"表面 {surface.id.value}（{surface.name_zh}）沒有預算點數")
    ratio = _duration_ratio(effect.duration, surface.duration)
    return (
        surface.budget_points * ratio,
        f"{surface.id.value} {surface.budget_points}×{_fmt(ratio)}",
    )


def _condition_multiplier(
    condition_type: str, conditions: dict[str, ConditionDef], budget: BudgetRules
) -> Fraction:
    definition = conditions.get(condition_type)
    if definition is None:
        raise BudgetError(f"未知的條件 {condition_type!r}")
    return Fraction(budget.condition_permille[definition.harshness], _PERMILLE)


def _effect_budget(
    skill: SkillDef, index: int, effect: EffectSpec, library: ContentLibrary
) -> EffectBudget:
    rules, budget = library.ruleset, library.budget
    primitive = rules.primitives.by_id().get(effect.type)
    if primitive is None:
        raise BudgetError(f"未知的效果原語 {effect.type!r}")
    base, note = _base_points(skill, effect, primitive, library)
    affects = resolved_affects(rules, effect)
    # consume_stack 的加成點數已含傷害效果的形狀倍率
    shape = (
        Fraction(1)
        if primitive.budget_basis == "consume_stack"
        else _shape_multiplier(skill, effect, primitive, library)
    )
    target = Fraction(budget.all_target_permille, _PERMILLE) if affects == "all" else Fraction(1)
    condition = Fraction(1)
    if effect.condition is not None:
        condition = _condition_multiplier(effect.condition.type, rules.conditions.by_id(), budget)
    return EffectBudget(
        index=index,
        type=effect.type,
        note=note,
        base=base,
        shape=shape,
        target=target,
        condition=condition,
        points=base * shape * target * condition,
    )


def _allowance_parts(skill: SkillDef, budget: BudgetRules) -> tuple[tuple[str, int], ...]:
    """代價折抵（‰）的各項；沒有該代價的項目不列出。"""
    allowance, cost = budget.allowance, skill.cost
    parts: list[tuple[str, int]] = []
    if cost.cooldown is not None:
        parts.append(
            (
                f"冷卻 {cost.cooldown} 回合",
                min(cost.cooldown * allowance.cooldown_per_turn, allowance.cooldown_cap),
            )
        )
    if cost.uses_per_battle is not None:
        value = allowance.uses_per_battle.get(cost.uses_per_battle, allowance.uses_default)
        parts.append((f"每場 {cost.uses_per_battle} 次", value))
    if cost.mana:
        parts.append(
            (f"法力 {cost.mana}", min(cost.mana * allowance.mana_per_point, allowance.mana_cap))
        )
    if cost.hp_percent is not None:
        parts.append(
            (
                f"HP {cost.hp_percent / 10:g}%",
                min(cost.hp_percent * allowance.hp_per_permille, allowance.hp_cap),
            )
        )
    return tuple(parts)


def _passive_coefficient(skill: SkillDef, library: ContentLibrary) -> tuple[Fraction, str]:
    """被動技能的係數：觸發時機的係數（``every_n_hits`` 依 n），``max_per_round`` 每多 1 次再乘
    ``passive_extra_trigger_permille``。"""
    trigger = skill.trigger
    if trigger is None:
        raise BudgetError(f"被動技能 {skill.id} 沒有 trigger，無法計算預算")
    definition = library.ruleset.skill_triggers.by_id().get(trigger.event)
    if definition is None:
        raise BudgetError(f"未知的觸發時機 {trigger.event!r}")
    if (
        definition.budget_by_n_permille is not None
        and trigger.n not in definition.budget_by_n_permille
    ):
        raise BudgetError(f"觸發時機 {trigger.event} 的 n 必須是 2 或 3，收到 {trigger.n}")
    coefficient = Fraction(definition.coefficient_permille(trigger.n), _PERMILLE)
    extra = Fraction(library.budget.passive_extra_trigger_permille, _PERMILLE)
    coefficient *= extra ** (trigger.max_per_round - 1)
    return coefficient, f"觸發係數（{definition.id}）"


def _ap_coefficient(skill: SkillDef, budget: BudgetRules) -> Fraction:
    if skill.kind == "reaction":
        return Fraction(budget.reaction_coefficient_permille, _PERMILLE)
    if skill.kind == "stance":
        return Fraction(budget.stance_coefficient_permille, _PERMILLE)
    if skill.kind == "active" and skill.ap_cost is not None:
        coefficient = budget.ap_coefficient_permille.get(skill.ap_cost)
        if coefficient is None:
            raise BudgetError(f"沒有 AP {skill.ap_cost} 的預算係數")
        return Fraction(coefficient, _PERMILLE)
    raise BudgetError(f"{skill.kind} 技能尚無預算算法")


def skill_budget(skill: SkillDef, library: ContentLibrary) -> BudgetReport:
    """計算 ``skill`` 的預算明細；缺少點數資料時拋出 :class:`BudgetError`。"""
    rules, budget = library.ruleset, library.budget
    effects = tuple(_effect_budget(skill, i, e, library) for i, e in enumerate(skill.effects))
    raw = sum((e.points for e in effects), Fraction(0))
    condition_multiplier = Fraction(1)
    if skill.condition is not None:
        condition_multiplier = _condition_multiplier(
            skill.condition.type, rules.conditions.by_id(), budget
        )
    tags = mechanic_tags(skill, rules)
    synergies = tuple(
        (rule.tags, Fraction(rule.coefficient_permille, _PERMILLE))
        for rule in library.synergies.synergies
        if set(rule.tags) <= set(tags)
    )
    total = raw * condition_multiplier
    for _, coefficient in synergies:
        total *= coefficient
    tier_budget = rules.core.tier_budget.get(skill.tier)
    if tier_budget is None:
        raise BudgetError(f"沒有階級 {skill.tier} 的預算（tier_budget）")
    if skill.kind == "passive":
        coefficient, label = _passive_coefficient(skill, library)
    else:
        coefficient = _ap_coefficient(skill, budget)
        label = {"reaction": "反應係數", "stance": "姿態係數"}.get(skill.kind, "AP 係數")
        if skill.trap is not None:
            coefficient *= Fraction(budget.trap_coefficient_permille, _PERMILLE)
            label = "AP 係數 × 陷阱係數"
    return BudgetReport(
        skill_id=skill.id,
        tier=skill.tier,
        effects=effects,
        raw=raw,
        condition_multiplier=condition_multiplier,
        tags=tags,
        synergies=synergies,
        total=total,
        tier_budget=tier_budget,
        ap_coefficient=coefficient,
        allowance_parts=_allowance_parts(skill, budget),
        allowance_cap=budget.allowance.total_cap,
        min_ratio=Fraction(budget.min_ratio_permille, _PERMILLE),
        max_ratio=Fraction(budget.max_ratio_permille, _PERMILLE),
        coefficient_label=label,
    )
