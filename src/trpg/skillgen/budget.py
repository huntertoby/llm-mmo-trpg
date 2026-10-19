"""技能預算計算（``docs/phases/Phase2B計畫.md`` 4.2、``docs/design/06-技能.md`` 6.5）。

::

    效果點數  ＝ base_points × 強度係數 × 形狀倍率 × 對象係數 × 效果條件倍率
    raw       ＝ Σ 效果點數
    total     ＝ raw × 技能條件倍率 × Π 協同係數
    可用預算  ＝ tier_budget[tier] × AP係數 × (1000 ＋ 代價折抵‰) ÷ 1000
               （被動技能以觸發時機的係數取代 AP 係數，見 :func:`_passive_coefficient`）

修正技能（``kind: modifier``，Phase 3C-2）沒有效果原語，改以每條修正規則為一列「效果點數」：
``每場預估使用次數 ×（命中後才生效的再 × 命中率）× 每次的價值 × 條件倍率``，可用預算的係數為
``skill_budget.yaml`` 的 ``modifier.coefficient_permille``（見 :func:`_modifier_budgets`）。
    合格      ＝ 0.7 × 可用預算 ≤ total ≤ 1.0 × 可用預算

「強度係數」已併入各原語的點數算法（骰子平均值、武器倍率、距離、持續 ÷ 預設持續，見
``skill_primitives.yaml`` 的 ``budget_basis``）。全部以 :class:`fractions.Fraction` 計算，
不使用浮點數；顯示時才四捨五入。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.battle import Dice, StatusDef
from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import BudgetRules, ModifierBudget
from trpg.content.skills import (
    EXTRA_REACTION,
    GRANT_AP,
    ConditionDef,
    EffectSpec,
    ModifierChange,
    ModifierSpec,
    PrimitiveDef,
    SelfStatusCost,
    SkillDef,
    on_hit_carrier,
)
from trpg.content.summons import summon_dpr
from trpg.skillgen.mechanics import mechanic_tags, resolved_affects

__all__ = ["BudgetError", "BudgetReport", "EffectBudget", "skill_budget"]

_PERMILLE = 1000
_SHAPED_AFFECTS = frozenset({"enemies", "allies", "all", "tiles"})
_HIT_GATED = frozenset(
    {"damage_permille", "cooldown_delta", "push_distance_delta", "add_element", "on_hit_effects"}
)
"""命中後才生效的修正（使用次數再 × 命中率）。"""
_SHAPE_GATED = frozenset({"area_delta", "shape_to", "allow_self_target"})
"""技能變形（3D-3）：使用次數再 × ``shape_benefit_permille``（站位剛好受益的比例）。"""
_ACTION_NAMES = {"attack": "普攻", "shove": "推擊", "trip": "絆倒", "interact": "互動"}


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
        points = Fraction(primitive.base_points * distance)
        note = f"{primitive.base_points}×{distance} 格"
        if effect.collision_dice is not None:
            extra = effect.collision_dice.count * library.budget.collision_die_points
            points += extra
            note += f" ＋ 撞擊 {effect.collision_dice}（{extra} 點）"
        return points, note
    if basis == "per_amount":
        assert primitive.base_points is not None
        amount = effect.amount or 1
        unit = {GRANT_AP: "AP", EXTRA_REACTION: "次"}.get(primitive.id, "層")
        return Fraction(primitive.base_points * amount), f"{primitive.base_points}×{amount} {unit}"
    special = _SPECIAL_BASES.get(basis)
    if special is not None:
        return special(skill, effect, library)
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


def _restore_resource_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``restore_resource`` 的點數（3D-1）：法力 ＝ 點數 × ``restore_mana_point_permille``‰；
    冷卻 ＝ 回合數 × ``restore_cooldown_points``。"""
    amount = effect.amount or 1
    rules = library.budget
    if effect.resource == "cooldown":
        return (
            Fraction(rules.restore_cooldown_points * amount),
            f"冷卻 −{amount} × {rules.restore_cooldown_points} 點",
        )
    permille = rules.restore_mana_point_permille
    return Fraction(permille * amount, _PERMILLE), f"法力 {amount} × {permille}‰"


def _hurl_object_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``hurl_object`` 的點數（3C-5a）：骰子平均 × 「需要附近有物件」折扣；``knock_prone`` 另加
    擊倒原語的點數。"""
    if effect.dice is None:
        raise BudgetError("hurl_object 缺少 dice，無法計算點數")
    discount = library.budget.hurl_object_discount_permille
    points = _dice_average(effect.dice) * Fraction(discount, _PERMILLE)
    note = f"{effect.dice} 平均 × 需有物件 {discount}‰"
    if effect.knock_prone:
        prone = library.ruleset.primitives.by_id()["knock_prone"].base_points or 0
        points += prone
        note += f" ＋ 擊倒 {prone}"
    return points, note


def _charge_through_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``charge_through`` 的點數（3D-2c）：（骰子平均 ＋ ``on_hit`` 的點數）× 預期被撞到的敵人數。
    ``on_hit`` 的點數：``knock_prone`` 為擊倒原語的 ``base_points``、``push_aside`` 為推擊 1 格。"""
    if effect.dice is None or effect.on_hit is None:
        raise BudgetError("charge_through 缺少 dice 或 on_hit，無法計算點數")
    primitives = library.ruleset.primitives.by_id()
    follow = (
        primitives["knock_prone" if effect.on_hit == "knock_prone" else "push"].base_points or 0
    )
    expected = library.budget.charge_through_expected_targets_permille
    points = (_dice_average(effect.dice) + follow) * Fraction(expected, _PERMILLE)
    return points, f"（{effect.dice} 平均 ＋ {effect.on_hit} {follow}）× 預期 {expected}‰ 個敵人"


def _summon_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``summon`` 的點數（3D-4a）：召喚物每輪預估傷害 × 持續輪數 ×
    ``summon_round_value_permille``；圖騰（3D-4b）改用光環狀態的點數 × 預期受惠的友方數。"""
    if effect.unit is None or effect.duration is None:
        raise BudgetError("summon 缺少 unit 或 duration，無法計算點數")
    try:
        summon = library.ruleset.summon_def(effect.unit)
    except KeyError:
        raise BudgetError(f"未知的召喚物範本：{effect.unit}") from None
    permille = library.budget.summon_round_value_permille
    totem = summon.template.totem
    if totem is not None:  # 圖騰（3D-4b）：光環狀態的點數 × 預期受惠的友方數 × 持續輪數
        status = library.ruleset.status_def(totem.status)
        allies = library.budget.totem_expected_allies_permille
        value = Fraction(status.budget_points or 0) * Fraction(allies, _PERMILLE)
        points = value * effect.duration * Fraction(permille, _PERMILLE)
        return points, (
            f"{status.id} {status.budget_points} × 預期 {allies}‰ 個友方 × {effect.duration} 輪"
            f" × {permille}‰"
        )
    dpr = summon_dpr(summon)
    points = dpr * effect.duration * Fraction(permille, _PERMILLE)
    return points, f"每輪 {_fmt(dpr)} × {effect.duration} 輪 × {permille}‰"


def zone_cell_count(skill: SkillDef) -> int:
    """持續區域（3D-5）的形狀格數（純幾何，不看地圖上的牆壁）。"""
    shape = skill.shape
    size = shape.size or 1
    radius = shape.radius or 1
    counts = {
        "cross": 5,
        "square3": 9,
        "line": size,
        "cone": size * size,
        "ring": 8 * radius,
        "allies_in_radius": 2 * radius * radius + 2 * radius + 1,
    }
    return counts.get(shape.type, 1)


def _zone_points(
    skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``zone`` 的點數（3D-5）：``effects`` 的基礎點數合計 × 格數 × 輪數 × 每格每輪的觸發率
    （× ``both`` 倍率、× ``moving`` 倍率）＋ 表面點數 × 新覆蓋的格數 × 表面折合。"""
    rules = library.budget
    primitives = library.ruleset.primitives.by_id()
    if effect.duration is None:
        raise BudgetError("zone 缺少 duration，無法計算點數")
    per_trigger = Fraction(0)
    for sub in effect.effects or ():
        points, _ = _base_points(skill, sub, primitives[sub.type], library)
        per_trigger += points
    cells = zone_cell_count(skill)
    rate = rules.zone_cell_round_permille
    total = per_trigger * cells * effect.duration * Fraction(rate, _PERMILLE)
    notes = [f"每次 {_fmt(per_trigger)} × {cells} 格 × {effect.duration} 輪 × {rate}‰"]
    if effect.when == "both":
        total *= Fraction(rules.zone_both_permille, _PERMILLE)
        notes.append(f"× 兩種時機 {rules.zone_both_permille}‰")
    if effect.anchor == "moving":
        total *= Fraction(rules.zone_moving_permille, _PERMILLE)
        notes.append(f"× 移動 {rules.zone_moving_permille}‰")
    if effect.surface is not None:
        surface, _ = _surface_points(effect.model_copy(update={"duration": None}), library)
        covered = (
            cells * (1 + effect.duration * (effect.speed or 1))
            if effect.anchor == "moving"
            else cells
        )
        extra = surface * covered * Fraction(rules.zone_surface_permille, _PERMILLE)
        total += extra
        notes.append(f"＋ 表面 {_fmt(surface)} × {covered} 格 × {rules.zone_surface_permille}‰")
    return total, " ".join(notes)


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


def _consume_status_points(
    skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``consume_status`` 的點數（3C-3b）：``then`` 各效果的基礎點數合計 × 期望倍率（有 ``scale``）
    × 濺射加成 × 「需要先有狀態」折扣。"""
    budget = library.ruleset.primitives.by_id()
    rules = library.budget
    total = Fraction(0)
    for sub in effect.then or ():
        points, _ = _base_points(skill, sub, budget[sub.type], library)
        total += points
    notes = [f"then {_fmt(total)}"]
    if effect.scale is not None:
        total *= rules.consume_status_scale_expected
        notes.append(f"× 倍率 {rules.consume_status_scale_expected}")
    if effect.splash is not None:
        total *= Fraction(_PERMILLE + rules.consume_status_splash_permille, _PERMILLE)
        notes.append(f"× 濺射 {rules.consume_status_splash_permille}‰")
    total *= Fraction(rules.consume_status_discount_permille, _PERMILLE)
    notes.append(f"× 需先有狀態 {rules.consume_status_discount_permille}‰")
    return total, " ".join(notes)


def _rule_change_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``rule_change`` 的點數（3D-6）：該類規則改變的點數（``rule_changes.yaml`` 的 ``kinds``；
    參數不影響點數）。"""
    try:
        rule = library.ruleset.rule_change_def(effect.rule or "")
    except KeyError:
        raise BudgetError(f"未知的規則改變 {effect.rule!r}") from None
    points = library.ruleset.rule_changes.points(rule.kind)
    return Fraction(points), f"規則改變 {rule.kind} {points} 點"


_SPECIAL_BASES: dict[
    str, Callable[[SkillDef, EffectSpec, ContentLibrary], tuple[Fraction, str]]
] = {
    "consume_stack": _consume_stack_points,
    "consume_status": _consume_status_points,
    "hurl_object": _hurl_object_points,
    "charge_through": _charge_through_points,
    "summon": _summon_points,
    "zone": _zone_points,
    "restore_resource": _restore_resource_points,
    "rule_change": _rule_change_points,
}
"""需要整個技能或特殊規則的 ``budget_basis`` → 點數算法。"""


def _shape_multiplier(
    skill: SkillDef, effect: EffectSpec, primitive: PrimitiveDef, library: ContentLibrary
) -> Fraction:
    """形狀倍率（只對作用在單位的效果）；陷阱技能取 ``trap.shape`` 的倍率（觸發時的影響範圍）。"""
    rules = library.ruleset
    affects = resolved_affects(rules, effect)
    if primitive.budget_basis == "zone":  # 持續區域（3D-5）：格數已算進觸發次數
        return Fraction(1)
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


def _allowance_parts(
    skill: SkillDef, budget: BudgetRules, statuses: dict[str, StatusDef]
) -> tuple[tuple[str, int], ...]:
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
    if cost.self_status is not None:
        parts.append(_self_status_allowance(cost.self_status, budget, statuses))
    if cost.source is not None:
        parts.append(
            (
                f"源力 {cost.source}",
                min(cost.source * allowance.source_per_point, allowance.source_cap),
            )
        )
    return tuple(parts)


def _self_status_allowance(
    cost: SelfStatusCost, budget: BudgetRules, statuses: dict[str, StatusDef]
) -> tuple[str, int]:
    """自身狀態代價的折抵：狀態點數 × 有效回合（duration − 1）× 每點折抵，先套用自己的上限。"""
    rule = budget.allowance.self_status
    status = statuses.get(cost.status)
    if status is None or status.budget_points is None:
        raise BudgetError(f"自身狀態代價 {cost.status!r} 沒有預算點數")
    value = status.budget_points * (cost.duration - 1) * rule.per_point_permille
    return (f"自身{status.name_zh} {cost.duration} 回合", min(value, rule.cap))


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


def _modifier_uses(rule: ModifierSpec, budget: ModifierBudget) -> tuple[int, str]:
    """一條修正規則每場的預估使用次數（``applies_to`` 各項加總，上限 ``uses_cap``）與說明。"""
    target, uses = rule.applies_to, budget.uses
    total = 0
    parts: list[str] = []
    if target.all_attacks:
        total += uses["all_attacks"]
        parts.append("所有攻擊")
    if target.all_skills:
        total += uses["all_skills"]
        parts.append("所有技能")
    for action in target.actions:
        if not (action == "attack" and target.all_attacks):
            total += uses[action]
            parts.append(_ACTION_NAMES[action])
    if target.skill_tags and not target.all_skills:
        total += uses["skill_tag"] * len(target.skill_tags)
        parts.append(f"標籤 {'／'.join(target.skill_tags)}")
    return min(total, budget.uses_cap), "＋".join(parts)


def _structured_value(
    skill: SkillDef, change: ModifierChange, library: ContentLibrary
) -> tuple[Fraction, str] | None:
    """價值由其他資料算出的改變（傷害‰、推擊距離、命中後效果、形狀轉換）；其他為 ``None``。"""
    core = library.ruleset.core
    if change.damage_permille is not None:
        value = Fraction(core.budget_reference_weapon_damage * change.damage_permille, _PERMILLE)
        return value, f"傷害 {change.damage_permille:+d}‰"
    if change.push_distance_delta is not None:
        base = library.ruleset.primitive_def("push").base_points or 0
        return Fraction(base * change.push_distance_delta), f"推擊 +{change.push_distance_delta} 格"
    if change.on_hit_effects is not None:
        carrier = on_hit_carrier(skill, change.on_hit_effects)
        value = sum(
            (_effect_budget(carrier, i, e, library).points for i, e in enumerate(carrier.effects)),
            Fraction(0),
        )
        return value, f"命中後 {len(carrier.effects)} 個效果"
    if change.shape_to is not None:
        return _shape_to_value(library, change.shape_to)
    return None


def _modifier_value(
    skill: SkillDef, rule: ModifierSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """一條修正規則每次使用增加的價值（點數）與說明。"""
    change = rule.change
    points = library.budget.modifier.points_milli
    kind = change.kind
    milli = Fraction(1, _PERMILLE)
    structured = _structured_value(skill, change, library)
    if structured is not None:
        return structured
    if kind == "ap_delta":
        assert change.ap_delta is not None
        per = points.ap_decrease if change.ap_delta < 0 else points.ap_increase
        return per * milli, f"AP {change.ap_delta:+d}"
    if kind == "add_tags":
        assert change.add_tags is not None
        return points.add_tag * len(change.add_tags) * milli, f"標籤 +{len(change.add_tags)}"
    flags = (
        "add_element",
        "grant_pierce",
        "area_delta",
        "allow_self_target",
    )  # 沒有數值：每次 1 份
    magnitude = abs(int(getattr(change, kind) or 0)) if kind not in flags else 1
    per = {
        "hit_bonus": points.hit_bonus,
        "cooldown_delta": points.cooldown_delta,
        "range_delta": points.range_delta,
        "add_element": points.add_element,
        "grant_pierce": points.grant_pierce,
        "area_delta": points.area_delta,
        "allow_self_target": points.allow_self_target,
    }[kind]
    sign = -1 if kind == "hit_bonus" and (change.hit_bonus or 0) < 0 else 1
    sign = -1 if kind == "range_delta" and (change.range_delta or 0) < 0 else sign
    return sign * per * magnitude * milli, kind


_REFERENCE_PARAM = 3
"""``shape_to`` 預算計算時，保留自原形狀的大小參數（``keep``）取的代表值。"""


def _shape_to_value(library: ContentLibrary, target: str) -> tuple[Fraction, str]:
    """``shape_to`` 每次使用的價值（3D-3）：基準武器傷害 ×（轉換後的形狀倍率 − 轉換前的形狀倍率），
    倍率取自 ``skill_shapes.yaml``（6.5）；保留自原形狀的大小參數以 :data:`_REFERENCE_PARAM` 計。"""
    shapes = library.ruleset.shapes
    by_id = shapes.by_id()
    gains: list[tuple[Fraction, str]] = []
    for conv in shapes.conversions:
        if conv.to != target:
            continue
        before_params: dict[str, int | str] = {
            name: _REFERENCE_PARAM for name in conv.keep if name in ("size", "radius")
        }
        after_params: dict[str, int | str] = {**conv.params, **before_params}
        before = by_id[conv.from_shape].budget.permille_for(before_params)
        after = by_id[conv.to].budget.permille_for(after_params)
        damage = library.ruleset.core.budget_reference_weapon_damage
        gains.append(
            (
                Fraction(damage * (after - before), _PERMILLE),
                f"形狀 {conv.from_shape}→{conv.to} 倍率 {before}‰→{after}‰",
            )
        )
    if not gains:
        raise BudgetError(f"shape_to {target!r} 不在 skill_shapes.yaml 的轉換表")
    return max(gains, key=lambda g: g[0])


def _modifier_budgets(skill: SkillDef, library: ContentLibrary) -> tuple[EffectBudget, ...]:
    """修正技能每條規則的點數（當成 :class:`EffectBudget` 的一列；形狀與對象倍率為 1）。"""
    rules, budget = library.ruleset, library.budget
    out: list[EffectBudget] = []
    for index, rule in enumerate(skill.modifiers):
        uses, where = _modifier_uses(rule, budget.modifier)
        value, what = _modifier_value(skill, rule, library)
        count = Fraction(uses)
        if rule.change.kind in _HIT_GATED:
            count *= Fraction(budget.modifier.hit_rate_permille, _PERMILLE)
        if rule.change.kind in _SHAPE_GATED:
            count *= Fraction(budget.modifier.shape_benefit_permille, _PERMILLE)
        condition = Fraction(1)
        if rule.condition is not None:
            condition = _condition_multiplier(rule.condition.type, rules.conditions.by_id(), budget)
        base = count * value
        out.append(
            EffectBudget(
                index=index,
                type=f"modifier.{rule.change.kind}",
                note=f"{where} {uses} 次 × {what}",
                base=base,
                shape=Fraction(1),
                target=Fraction(1),
                condition=condition,
                points=base * condition,
            )
        )
    return tuple(out)


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


def _activation_coefficient(skill: SkillDef, library: ContentLibrary) -> tuple[Fraction, str]:
    """常駐類傳說（3D-6，``activation``）的係數：啟動 AP（``legendary_activation_ap``）的 AP 係數；
    整場型再 × ``legendary_battle_budget_permille``。"""
    budget = library.budget
    ap = library.ruleset.core.legendary_activation_ap
    coefficient = budget.ap_coefficient_permille.get(ap)
    if coefficient is None:
        raise BudgetError(f"沒有 AP {ap} 的預算係數")
    if skill.activation == "battle":
        permille = budget.legendary_battle_budget_permille
        return (
            Fraction(coefficient * permille, _PERMILLE * _PERMILLE),
            f"啟動 AP {ap} 係數 × 整場 {permille}‰",
        )
    return Fraction(coefficient, _PERMILLE), f"啟動 AP {ap} 係數（限時）"


def skill_budget(skill: SkillDef, library: ContentLibrary) -> BudgetReport:
    """計算 ``skill`` 的預算明細；缺少點數資料時拋出 :class:`BudgetError`。"""
    rules, budget = library.ruleset, library.budget
    if skill.is_modifier:
        effects = _modifier_budgets(skill, library)
    else:
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
    if skill.pierce:  # 穿透加成（3C-5b）：列成一個「pierce」協同
        synergies = (
            *synergies,
            (("pierce",), Fraction(_PERMILLE + budget.pierce_bonus_permille, _PERMILLE)),
        )
    for _, coefficient in synergies:
        total *= coefficient
    tier_budget = rules.core.tier_budget.get(skill.tier)
    if tier_budget is None:
        raise BudgetError(f"沒有階級 {skill.tier} 的預算（tier_budget）")
    if skill.is_activatable:
        coefficient, label = _activation_coefficient(skill, library)
    elif skill.kind == "passive":
        coefficient, label = _passive_coefficient(skill, library)
    elif skill.is_modifier:
        coefficient = Fraction(budget.modifier.coefficient_permille, _PERMILLE)
        label = "修正係數"
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
        allowance_parts=_allowance_parts(skill, budget, rules.statuses.by_id()),
        allowance_cap=budget.allowance.total_cap,
        min_ratio=Fraction(budget.min_ratio_permille, _PERMILLE),
        max_ratio=Fraction(budget.max_ratio_permille, _PERMILLE),
        coefficient_label=label,
    )
