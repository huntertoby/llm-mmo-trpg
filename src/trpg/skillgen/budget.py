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
from dataclasses import dataclass, replace
from fractions import Fraction

from trpg.content.battle import Dice, StatusDef
from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import BudgetRules, ModifierBudget
from trpg.content.skills import (
    ADD_STACK,
    DAMAGE_MULTIPLIER,
    EXTRA_REACTION,
    GRANT_AP,
    REFUND_AP,
    REFUND_COOLDOWN,
    SELF_DAMAGE_OF_HIT,
    ConditionDef,
    EffectSpec,
    ModifierChange,
    ModifierSpec,
    PrimitiveDef,
    SelfStatusCost,
    ShapeSpec,
    SkillDef,
    on_hit_carrier,
)
from trpg.content.summons import SummonDef, summon_dpr
from trpg.skillgen.combo import self_combo_reasons
from trpg.skillgen.mechanics import mechanic_tags, resolved_affects

__all__ = [
    "BUDGET_BASES",
    "BudgetError",
    "BudgetReport",
    "EffectBudget",
    "SegmentBudget",
    "VariantBudget",
    "self_status_allowance_permille",
    "skill_budget",
]

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
    range: Fraction = Fraction(1)
    """射程係數（Phase 3-49）：只對有形狀倍率的效果生效，其他為 1；``points`` 已乘上它。"""


@dataclass(frozen=True, slots=True)
class SegmentBudget:
    """複合技能（Phase 3F-3a）一段的預算：該段依自己的骨架與形狀倍率計算的效果點數、條件與協同。"""

    label: str
    """段名：``位移段``／``動作段``（位移 → 動作）、``動作段``／``位移段``（動作 → 位移）、
    ``聚集段``／``打擊段``、``第一段``／``擊殺後的第二段``、``第一段``／``命中後的第二段``。"""
    skeleton: str
    shape: str
    effects: tuple[EffectBudget, ...]
    raw: Fraction
    condition_multiplier: Fraction
    synergies: tuple[tuple[tuple[str, ...], Fraction], ...]
    total: Fraction
    chance_permille: int = 1000
    """有條件的第二段（``on_kill``／``on_hit``，Phase 3F-4a）的觸發機率（‰）：加總時這段點數 ×
    它；其他段為 1000。"""
    range_value: int | None = None
    """這一段形狀的固定射程（沒有或武器射程為 ``None``）。"""
    range_coefficient: Fraction = Fraction(1)
    """這一段的射程係數（Phase 3-49）。"""


@dataclass(frozen=True, slots=True)
class VariantBudget:
    """戰場變奏（Phase 3-25a）一個型態的預算：變奏 ID、型態名與型態自己的預算明細。"""

    id: str
    name_zh: str
    report: BudgetReport


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
    segments: tuple[SegmentBudget, ...] = ()
    """複合技能（Phase 3F-3a）：位移段與動作段各自的明細（依序）；一般技能為空。"""
    composite_tax_permille: int = 0
    """複合技能的加成（‰）：``total`` ＝（第一段 ＋ 第二段 × 觸發機率）×（1000 ＋ 它）÷ 1000
    ×（1000 ＋ ``self_combo_permille``）÷ 1000。"""
    self_combo_permille: int = 0
    """複合技能兩段之間有元素／表面連鎖（Phase 3F-4a，:mod:`trpg.skillgen.combo`）時的加價（‰）；
    沒有連鎖時為 0。"""
    self_combo_reasons: tuple[str, ...] = ()
    """連鎖的說明（:func:`~trpg.skillgen.combo.self_combo_reasons`）。"""
    variant_surcharge_permille: int = 0
    """戰場變奏（Phase 3-25a）的加價合計（‰）：``variant_surcharge_permille`` × 變奏數；``total``
    已乘上 ×（1000 ＋ 它）÷ 1000。沒有變奏時為 0。"""
    variants: tuple[VariantBudget, ...] = ()
    range_value: int | None = None
    """技能形狀的固定射程（Phase 3-49）；射程寫「武器射程」或形狀沒有射程時為 ``None``。"""
    range_coefficient: Fraction = Fraction(1)
    """射程係數（Phase 3-49，#53）：``1 ＋ (射程 − 4) × 5%``；已乘在作用於單位的各效果點數上。"""
    """各變奏型態自己的預算（依資料順序；型態本身照一般技能計算，不含加價）。"""

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


def _base_points(
    skill: SkillDef, effect: EffectSpec, primitive: PrimitiveDef, library: ContentLibrary
) -> tuple[Fraction, str]:
    """基礎點數（含強度）與一句說明；傷害效果再乘高變異、縮放與超載的期望值係數（3D-7b）。"""
    points, note = _plain_base_points(skill, effect, primitive, library)
    if effect.type != "damage":
        return points, note
    factor, extra = _variance_factor(skill, effect, library)
    if effect.split_heal and effect.dice is not None:  # 聖光雙效（3D-8a）：傷害與治療兩邊都計
        heal = _dice_average(effect.dice)
        return points * factor + heal, f"{note}{extra}＋ 友方治療 {_fmt(heal)}"
    return (points * factor, f"{note}{extra}") if extra else (points, note)


def _explode_ratio(sides: int, rerolls: int) -> Fraction:
    """爆骰的期望值倍率：每顆骰平均 ``E_k = (s+1)/2 + E_(k-1)/s`` 除以 ``E_0``（k 為再擲上限）。"""
    base = Fraction(sides + 1, 2)
    value = base
    for _ in range(rerolls):
        value = base + value / sides
    return value / base


def _variance_factor(
    skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """傷害效果的期望值係數（3D-7b；爆骰、暴擊範圍、基礎傷害折扣、縮放、超載）與說明（沒有時為空）。

    係數相乘；爆骰與暴擊範圍只影響傷害中「骰子」的部分（法術技整個傷害都是骰子；武器技見
    ``variance_dice_share_permille``）。
    """
    budget, core = library.budget, library.ruleset.core
    share = (
        Fraction(1)
        if skill.category == "spell"
        else Fraction(budget.variance_dice_share_permille, _PERMILLE)
    )
    factor, notes = Fraction(1), []
    if effect.explode:
        sides = effect.dice.sides if effect.dice is not None else budget.explode_weapon_sides
        ratio = 1 + (_explode_ratio(sides, core.explode_max) - 1) * share
        factor *= ratio
        notes.append(f"爆骰 ×{_fmt(ratio)}")
    if skill.crit_range is not None:
        extra_crit = Fraction(20 - skill.crit_range, 20)
        ratio = 1 + extra_crit * share
        factor *= ratio
        notes.append(f"暴擊 {skill.crit_range}–20 ×{_fmt(ratio)}")
    if skill.damage_permille is not None:
        factor *= Fraction(skill.damage_permille, _PERMILLE)
        notes.append(f"基礎傷害 ×{skill.damage_permille / _PERMILLE:g}")
    if effect.scaling is not None:
        steps = Fraction(budget.scale_expected_steps_milli[effect.scaling.by], _PERMILLE)
        bonus = min(steps * effect.scaling.per_step_permille, Fraction(effect.scaling.cap_permille))
        ratio = 1 + bonus / _PERMILLE
        factor *= ratio
        notes.append(f"縮放（預估 {_fmt(steps)} 步）×{_fmt(ratio)}")
    if effect.lifesteal_permille is not None:  # 吸血（3D-8a）：回復的 HP 折合傷害點數
        value = library.budget.lifesteal_value_permille
        ratio = 1 + Fraction(effect.lifesteal_permille * value, _PERMILLE * _PERMILLE)
        factor *= ratio
        notes.append(f"吸血 {effect.lifesteal_permille / 10:g}% ×{_fmt(ratio)}")
    overload = _overload_ratio(skill, library)
    if overload != 1:
        factor *= overload
        notes.append(f"超載 ×{_fmt(overload)}")
    return factor, "".join(f"，{n}" for n in notes)


def _overload_ratio(skill: SkillDef, library: ContentLibrary) -> Fraction:
    """帶超載標籤的技能，傷害的期望值倍率：每個超載層數 ＝ 平均層數 ×（‰ 加成）× 估計比例。"""
    bonus = Fraction(0)
    for stack in library.ruleset.stacks.stacks:
        overload = stack.overload
        if overload is None or overload.tag not in skill.tags:
            continue
        average = Fraction(overload.threshold - 1, 2)
        bonus += (
            average * overload.per_stack_damage_permille * library.budget.overload_expected_permille
        )
    return 1 + bonus / (_PERMILLE * _PERMILLE)


def _overload_stack_cost(
    effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str] | None:
    """累積超載層數的代價（負點數）：反噬點數 × 自傷折合 × 層數 ÷ 門檻；不是超載層數為 ``None``。"""
    stack = library.ruleset.stack_def(effect.stack) if effect.stack else None
    if stack is None or stack.overload is None:
        return None
    rules = library.ruleset
    backlash = Fraction(0)
    for sub in stack.overload.backlash:
        if sub.type == "damage":
            assert sub.dice is not None
            backlash += _dice_average(sub.dice)
        else:
            backlash += _status_points(sub, rules.statuses.by_id())[0]
    harm = Fraction(library.budget.gamble_self_harm_permille, _PERMILLE)
    amount = effect.amount or 1
    cost = backlash * harm * amount / stack.overload.threshold
    return (
        -cost,
        f"超載反噬 {_fmt(backlash)} × 自傷折合 {_fmt(harm)} × {amount} 層"
        f" ÷ 門檻 {stack.overload.threshold}",
    )


def _plain_base_points(  # noqa: PLR0911
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
        if primitive.id == "shield" and effect.duration is not None:  # 護盾持續時間係數（3-50b）
            permille = library.budget.shield_duration_permille[min(max(effect.duration, 2), 3) - 2]
            return (
                _dice_average(effect.dice) * Fraction(permille, _PERMILLE),
                f"{effect.dice} 平均 × 持續 {effect.duration} 回合 {permille}‰",
            )
        return _dice_average(effect.dice), f"{effect.dice} 平均"
    if basis == "damage":
        permille = effect.multiplier_permille or _PERMILLE
        reference = rules.core.budget_reference_weapon_damage
        return Fraction(permille * reference, _PERMILLE), f"武器 ×{permille / _PERMILLE:g}"
    if basis == "status":
        return _status_points(effect, rules.statuses.by_id())
    if basis == "surface":
        return _surface_points(effect, library)
    raise BudgetError(f"原語 {primitive.id} 的預算算法 {basis} 沒有實作")


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


def _dispel_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``dispel`` 的點數（3D-8a）：驅散 1 個 ``dispel_one_points``、全部 ``dispel_all_points``。"""
    rules = library.budget
    if effect.count == "all":
        return Fraction(rules.dispel_all_points), "驅散全部增益"
    return Fraction(rules.dispel_one_points), "驅散 1 個增益"


def _obstacle_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``create_obstacle`` 的點數（3-11）：基礎點數 × 持續時間係數（永久 ＝ 基礎）。"""
    rules = library.budget
    primitive = library.ruleset.primitives.by_id()[effect.type]
    assert primitive.base_points is not None
    if effect.duration is None:
        return Fraction(primitive.base_points), "固定（永久）"
    permille = rules.obstacle_duration_permille[min(effect.duration, 10) - 1]
    return (
        Fraction(primitive.base_points * permille, _PERMILLE),
        f"{primitive.base_points} × {effect.duration} 回合 {permille}‰",
    )


def _inscribe_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``inscribe`` 的點數（3-23）：基礎點數 × 持續時間係數（省略 ``duration`` ＝ 預設輪數）。"""
    rules = library.budget
    primitive = library.ruleset.primitives.by_id()[effect.type]
    assert primitive.base_points is not None
    rounds = effect.duration or library.ruleset.core.rune_default_rounds
    permille = rules.inscribe_duration_permille[min(rounds, 5) - 1]
    return (
        Fraction(primitive.base_points * permille, _PERMILLE),
        f"{primitive.base_points} × {rounds} 輪 {permille}‰",
    )


def _detonate_runes_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``detonate_runes`` 的點數（3-23）：骰子平均 × ``detonate_runes_permille``‰。"""
    if effect.dice is None:
        raise BudgetError("detonate_runes 缺少 dice，無法計算點數")
    permille = library.budget.detonate_runes_permille
    return (
        _dice_average(effect.dice) * Fraction(permille, _PERMILLE),
        f"{effect.dice} 平均 × 引爆折扣 {permille}‰",
    )


def _sacrifice_summon_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``sacrifice_summon`` 的點數（3-24c）：骰子平均 × ``sacrifice_summon_permille``‰。"""
    if effect.dice is None:
        raise BudgetError("sacrifice_summon 缺少 dice，無法計算點數")
    permille = library.budget.sacrifice_summon_permille
    return (
        _dice_average(effect.dice) * Fraction(permille, _PERMILLE),
        f"{effect.dice} 平均 × 獻祭折扣 {permille}‰",
    )


def _reveal_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``reveal`` 的點數（3D-8a）：``reveal_base_points`` ＋ ``reveal_round_points`` × 回合數。"""
    if effect.duration is None:
        raise BudgetError("reveal 缺少 duration，無法計算點數")
    rules = library.budget
    points = rules.reveal_base_points + rules.reveal_round_points * effect.duration
    return (
        Fraction(points),
        f"揭露 {rules.reveal_base_points} ＋ {rules.reveal_round_points}×{effect.duration} 回合",
    )


def _revive_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``revive`` 的點數（3D-8b）：``revive_base_points`` ＋ ``hp_permille`` ×
    ``revive_hp_point_permille`` ÷ 1000。"""
    if effect.hp_permille is None:
        raise BudgetError("revive 缺少 hp_permille，無法計算點數")
    rules = library.budget
    points = rules.revive_base_points + Fraction(
        effect.hp_permille * rules.revive_hp_point_permille, _PERMILLE
    )
    return (
        points,
        f"復活 {rules.revive_base_points} ＋ {effect.hp_permille / 10:g}% × "
        f"{rules.revive_hp_point_permille}‰",
    )


def _delayed_damage_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``delayed_damage`` 的點數（3D-8b）：骰子平均 × 預期波及的人數（基礎 ＋ 半徑 × 每格加成）。"""
    if effect.dice is None or effect.radius is None:
        raise BudgetError("delayed_damage 缺少 dice 或 radius，無法計算點數")
    rules = library.budget
    targets = (
        rules.delayed_damage_base_targets_permille
        + effect.radius * rules.delayed_damage_radius_targets_permille
    )
    points = _dice_average(effect.dice) * Fraction(targets, _PERMILLE)
    return points, f"{effect.dice} 平均 × 預期 {targets}‰ 個目標（半徑 {effect.radius}）"


def _grant_skill_points(
    _skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``grant_skill`` 的點數（3D-8c）：被給技能的總點數 × 預期使用次數（每輪
    ``grant_skill_expected_uses_per_round_permille``‰ × 持續輪數）。"""
    if effect.skill is None or effect.duration is None:
        raise BudgetError("grant_skill 缺少 skill 或 duration，無法計算點數")
    try:
        granted = library.ruleset.skill_def(effect.skill)
    except KeyError:
        raise BudgetError(f"未知的技能 {effect.skill!r}") from None
    if any(e.type == "grant_skill" for e in granted.effects):
        raise BudgetError("grant_skill 不能給出另一個 grant_skill 技能")
    permille = library.budget.grant_skill_expected_uses_per_round_permille
    uses = Fraction(permille * effect.duration, _PERMILLE)
    value = skill_budget(granted, library).total
    return value * uses, f"{granted.id} {_fmt(value)} × 預期 {_fmt(uses)} 次使用"


def _on_kill_budget(
    skill: SkillDef, library: ContentLibrary, index: int, source: EffectSpec
) -> EffectBudget | None:
    """``on_kill`` 的一列（3D-8b）：各效果的點數 × 預估擊殺率（``on_kill_expected_permille``）；
    ``refund_ap`` 每點 AP 折合 ``refund_ap_points``、``refund_cooldown`` ＝ 技能冷卻回合 ×
    ``restore_cooldown_points``，其餘依一般效果的算法（對象是施放者）。"""
    if not source.on_kill:
        return None
    budget = library.budget
    value = Fraction(0)
    for sub in source.on_kill:
        if sub.type == REFUND_AP:
            value += budget.refund_ap_points * (sub.amount or 1)
        elif sub.type == REFUND_COOLDOWN:
            value += budget.restore_cooldown_points * (skill.cost.cooldown or 0)
        else:
            value += _effect_budget(
                skill, 0, sub.model_copy(update={"affects": "self"}), library
            ).points
    rate = Fraction(budget.on_kill_expected_permille, _PERMILLE)
    points = value * rate
    return EffectBudget(
        index=index,
        type="on_kill",
        note=f"擊殺時 {_fmt(value)} × 預估擊殺率 {budget.on_kill_expected_permille}‰",
        base=points,
        shape=Fraction(1),
        target=Fraction(1),
        condition=Fraction(1),
        points=points,
    )


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
    per_round, once, notes = summon_trait_points(summon, library, dpr)
    value = Fraction(permille, _PERMILLE)
    rounds = effect.duration
    if summon.template.detonate is not None:  # 自爆後就消失了：一般攻擊與特性只算幾輪
        rounds = min(rounds, library.budget.summon_detonate_rounds)
    per_round_total, once, variant_note = _summon_variant_points(
        summon, effect, library, dpr, (per_round, once)
    )
    notes += variant_note
    points = per_round_total * rounds * value + once * value
    note = f"每輪 {_fmt(dpr)}"
    if per_round:
        note += f" ＋ 特性 {_fmt(per_round)}"
    note += f" × {rounds} 輪"
    if once:
        note += f" ＋ 一次性 {_fmt(once)}"
    note += f" × {permille}‰"
    if notes:
        note += f"（{'；'.join(notes)}）"
    return points, note


def _summon_variant_points(
    summon: SummonDef,
    effect: EffectSpec,
    library: ContentLibrary,
    dpr: Fraction,
    traits: tuple[Fraction, Fraction],
) -> tuple[Fraction, Fraction, list[str]]:
    """召喚技能分歧進化（Phase 3-33f2）對點數的影響：回傳（每輪總價值, 一次性價值, 說明）。

    - 橋接 ``infusion``：第二個灌注關鍵字的特性點數（同固有灌注的算法）；
    - 加深 ``max_hp_permille``：每輪價值 ×（1 ＋ 多出的 HP 比例 × ``summon_hp_weight_permille``）；
      ``trait``：小特性的一次性點數；
    - 數量型 ``count`` × ``power_permille``：每隻只有一般的比例（HP 與傷害），整體 × 隻數。
    """
    notes: list[str] = []
    core = library.ruleset.core
    per_round, once = traits  # 範本本身的特性點數（每輪, 一次性）
    if effect.infusion is not None:
        extra = summon.model_copy(
            update={
                "template": summon.template.model_copy(update={"innate": effect.infusion}),
            }
        )
        more_round, more_once, more_notes = _infusion_trait_points(extra, library, dpr)
        per_round += more_round
        once += more_once
        notes += [f"第二灌注 {n}" for n in more_notes] or [f"第二灌注 {effect.infusion}"]
    total = dpr + per_round
    if effect.max_hp_permille:
        weight = Fraction(library.budget.summon_hp_weight_permille, _PERMILLE)
        total *= 1 + Fraction(effect.max_hp_permille, _PERMILLE) * weight
        notes.append(f"HP +{effect.max_hp_permille // 10}%")
    trait = None if effect.trait is None else core.summon_traits.get(effect.trait)
    if trait is not None:
        once += trait.budget_points
        notes.append(f"小特性 {trait.name_zh}")
    count = effect.count if isinstance(effect.count, int) else 1
    if count > 1:
        scale = count * Fraction(effect.power_permille or _PERMILLE, _PERMILLE)
        total *= scale
        once *= scale
        notes.append(f"{count} 隻各 {(effect.power_permille or _PERMILLE) // 10}%")
    return total, once, notes


def _status_value(library: ContentLibrary, status_id: str) -> Fraction:
    return Fraction(library.ruleset.status_def(status_id).budget_points or 0)


def _infusion_trait_points(
    summon: SummonDef, library: ContentLibrary, dpr: Fraction
) -> tuple[Fraction, Fraction, list[str]]:
    """固有灌注關鍵字（``innate``）的特性點數：（每輪, 一次性, 說明）。"""
    rules = library.budget
    template = summon.template
    infusion = library.ruleset.core.summon_infusions.get(template.innate or "")
    per_round, once = Fraction(0), Fraction(0)
    notes: list[str] = []
    if infusion is None:
        return per_round, once, notes
    primitives = library.ruleset.primitives.by_id()
    if infusion.status is not None:
        per_round += _status_value(library, infusion.status) * Fraction(
            rules.summon_trait_status_permille, _PERMILLE
        )
        notes.append(f"命中{infusion.status}")
    if infusion.surface is not None:
        surface = library.ruleset.surfaces.get(infusion.surface).budget_points or 0
        per_round += surface * Fraction(rules.summon_trait_surface_permille, _PERMILLE)
        notes.append(f"命中造{infusion.surface.value}")
    if infusion.extra_damage is not None:
        per_round += _dice_average(infusion.extra_damage) * Fraction(
            rules.summon_trait_extra_damage_permille, _PERMILLE
        )
        notes.append(f"額外 {infusion.extra_damage}")
    if infusion.trip:
        prone = primitives["knock_prone"].base_points or 0
        per_round += prone * Fraction(rules.summon_trait_trip_permille, _PERMILLE)
        notes.append("絆倒")
    if infusion.knockback:
        push = primitives["push"].base_points or 0
        per_round += (
            push * infusion.knockback * Fraction(rules.summon_trait_knockback_permille, _PERMILLE)
        )
        notes.append(f"震退{infusion.knockback}")
    if infusion.height_permille:
        per_round += (
            dpr
            * Fraction(infusion.height_permille, _PERMILLE)
            * Fraction(rules.summon_trait_height_permille, _PERMILLE)
        )
        notes.append("高處加傷")
    if infusion.conceal_rounds:
        once += rules.summon_trait_conceal_points
        notes.append("召喚時隱蔽")
    return per_round, once, notes


def _rule_trait_points(
    summon: SummonDef, library: ContentLibrary
) -> tuple[Fraction, Fraction, list[str]]:
    """範本的命中特性、脈動、自爆、被推倒與背刺骰的特性點數（每輪, 一次性, 說明）。"""
    rules = library.budget
    template = summon.template
    weapon = summon.weapon
    per_round, once = Fraction(0), Fraction(0)
    notes: list[str] = []
    for rule in template.hit_rules:
        if rule.status is not None:
            status_points = _status_value(library, rule.status) * Fraction(
                rules.summon_trait_status_permille, _PERMILLE
            )
            if rule.when != "always":
                status_points *= Fraction(rules.summon_trait_conditional_permille, _PERMILLE)
            per_round += status_points
            notes.append(f"命中{rule.status}")
        if rule.chain_targets:
            chain = (
                _dice_average(weapon.dice)
                * rule.chain_targets
                * Fraction(rule.chain_permille, _PERMILLE)
            )
            per_round += chain * Fraction(rules.summon_trait_chain_permille, _PERMILLE)
            notes.append("水面連鎖")
    pulse = template.pulse
    if pulse is not None:
        if pulse.surface is not None:
            surface = library.ruleset.surfaces.get(pulse.surface).budget_points or 0
            per_round += surface * Fraction(rules.summon_trait_surface_permille, _PERMILLE)
        if pulse.heal_dice is not None or pulse.heal_flat:
            heal = (
                _dice_average(pulse.heal_dice) if pulse.heal_dice else Fraction(0)
            ) + pulse.heal_flat
            per_round += heal * Fraction(rules.summon_trait_heal_permille, _PERMILLE)
        notes.append("脈動")
    if weapon.backstab_dice:
        per_round += Fraction(weapon.backstab_dice * (weapon.dice.sides + 1), 2) * Fraction(
            rules.summon_trait_backstab_permille, _PERMILLE
        )
        notes.append("背刺骰")
    if template.detonate is not None:
        blast = template.detonate
        once += (_dice_average(blast.dice) + blast.flat) * Fraction(
            rules.summon_detonate_targets_permille, _PERMILLE
        )
        if blast.surface is not None:
            tiles = 2 * blast.radius * (blast.radius + 1) + 1
            surface = library.ruleset.surfaces.get(blast.surface).budget_points or 0
            once += surface * tiles * Fraction(rules.summon_trait_surface_permille, _PERMILLE)
        notes.append("自爆")
    if "topplable" in template.tags:
        prone = library.ruleset.primitives.by_id()["knock_prone"].base_points or 0
        topple = _dice_average(library.ruleset.core.topple_damage_dice) + prone
        once += topple * Fraction(rules.summon_topple_targets_permille, _PERMILLE)
        notes.append("被推倒壓人")
    return per_round, once, notes


def summon_trait_points(
    summon: SummonDef, library: ContentLibrary, dpr: Fraction
) -> tuple[Fraction, Fraction, list[str]]:
    """召喚物特性的預算點數（Phase 3-33e2a）：（每輪, 一次性, 說明）。每輪的與武器骰平均相加後乘
    持續輪數，一次性的（自爆、被推倒壓人、召喚時隱蔽）只算一次；係數都在 ``skill_budget.yaml``。"""
    per_round, once, notes = _infusion_trait_points(summon, library, dpr)
    more_round, more_once, more_notes = _rule_trait_points(summon, library)
    per_round, once = per_round + more_round, once + more_once
    notes = notes + more_notes
    if summon.template.inert:  # 不行動（土牆）：沒有攻擊，只剩一次性的特性
        per_round = Fraction(0)
        notes = [n for n in notes if n in ("被推倒壓人", "召喚時隱蔽")]
    if "immovable" in summon.template.tags:
        per_round += Fraction(library.budget.summon_trait_immovable_permille, _PERMILLE)
        notes.append("不會被推動")
    pulse = summon.template.pulse
    if pulse is not None and pulse.pull_radius > 0:  # 拉扯（吸引圖騰，3-33e2b）：每輪拉近 1 格
        pull = library.ruleset.primitives.by_id()["pull"].base_points or 0
        per_round += pull * Fraction(library.budget.summon_trait_pull_permille, _PERMILLE)
        notes.append("拉扯")
    platform = summon.template.platform
    if platform is not None:  # 高台（高台圖騰，3-33e2b）：高台在的每一輪都有地形價值
        raised = library.ruleset.primitives.by_id()["raise_terrain"].base_points or 0
        per_round += (
            raised
            * platform.height
            * Fraction(library.budget.summon_trait_platform_permille, _PERMILLE)
        )
        notes.append("高台")
    return per_round, once, notes


def zone_cell_count(skill: SkillDef, library: ContentLibrary) -> int:
    """持續區域（3D-5）的形狀格數（純幾何，不看地圖上的牆壁）；資料在 ``skill_shapes.yaml`` 的
    ``cell_count``，形狀沒有格數（例如連鎖）或參數不在表內時拋出 :class:`BudgetError`。"""
    shape_id = skill.shape.type
    shape = library.ruleset.shapes.by_id().get(shape_id)
    if shape is None:
        raise BudgetError(f"未知的形狀：{shape_id}")
    if shape.cell_count is None:
        raise BudgetError(f"形狀 {shape_id} 沒有 cell_count，無法計算區域格數")
    try:
        return shape.cell_count.count_for(skill.shape.param_values())
    except ValueError as error:
        raise BudgetError(str(error)) from None


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
    cells = zone_cell_count(skill, library)
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


def _damage_points(skill: SkillDef, library: ContentLibrary) -> Fraction:
    """技能傷害效果（含形狀與對象倍率，不含賭注分支）的點數合計：``damage_multiplier`` 與
    ``self_damage_of_hit`` 以它為基礎。"""
    primitives = library.ruleset.primitives.by_id()
    total = Fraction(0)
    for other in skill.effects:
        if other.type == "damage":
            base, _ = _base_points(skill, other, primitives["damage"], library)
            total += base * _shape_multiplier(skill, other, primitives["damage"], library)
    return total


def _self_harm(sub: EffectSpec, library: ContentLibrary) -> bool:
    """分支效果是對施放者自己的有害效果（自傷、非增益的狀態）。"""
    rules = library.ruleset
    if resolved_affects(rules, sub) != "self":
        return False
    if sub.type == "damage":
        return True
    if sub.type == "apply_status":
        return not rules.status_def(sub.status or "").beneficial
    return False


def _branch_points(
    skill: SkillDef, branch: tuple[EffectSpec, ...], library: ContentLibrary
) -> Fraction:
    """賭注一個分支（或失手反噬）的點數：一般效果照一般算法；``damage_multiplier`` ＝ 傷害點數 ×
    （倍率 − 1）；``self_damage_of_hit`` ＝ 傷害點數 × n‰；對自己的有害效果再折合
    ``gamble_self_harm_permille`` 並計為負點數（代價）。"""
    damage = _damage_points(skill, library)
    harm = Fraction(library.budget.gamble_self_harm_permille, _PERMILLE)
    total = Fraction(0)
    for sub in branch:
        if sub.type == DAMAGE_MULTIPLIER:
            assert sub.damage_multiplier_permille is not None
            total += damage * Fraction(sub.damage_multiplier_permille - _PERMILLE, _PERMILLE)
        elif sub.type == SELF_DAMAGE_OF_HIT:
            assert sub.self_damage_permille_of_hit is not None
            total -= damage * Fraction(sub.self_damage_permille_of_hit, _PERMILLE) * harm
        else:
            points = _effect_budget(skill, 0, sub, library).points
            total += -points * harm if _self_harm(sub, library) else points
    return total


def _gamble_points(
    skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``gamble`` 的點數（3D-7a）：期望值 ＝ 成功率 × win ＋ 失敗率 × lose。"""
    if effect.chance_permille is None:
        raise BudgetError("gamble 缺少 chance_permille，無法計算點數")
    chance = effect.chance_permille
    win = _branch_points(skill, effect.win or (), library)
    lose = _branch_points(skill, effect.lose or (), library)
    points = (chance * win + (_PERMILLE - chance) * lose) / _PERMILLE
    lose_chance = (_PERMILLE - chance) / 10
    return points, f"{chance / 10:g}% × win {_fmt(win)} ＋ {lose_chance:g}% × lose {_fmt(lose)}"


def _on_miss_budget(skill: SkillDef, library: ContentLibrary, index: int) -> EffectBudget | None:
    """失手反噬 ``cost.on_miss`` 的一列（3D-7a）：反噬點數 × 自傷折合 × 預估觸發率（負點數）。"""
    if not skill.cost.on_miss:
        return None
    budget = library.budget
    rate = Fraction(budget.gamble_on_miss_rate_permille, _PERMILLE)
    harm = Fraction(budget.gamble_self_harm_permille, _PERMILLE)
    cost = sum(
        (
            _effect_budget(skill, 0, sub.model_copy(update={"affects": "self"}), library).points
            for sub in skill.cost.on_miss
        ),
        Fraction(0),
    )
    points = -cost * harm * rate
    return EffectBudget(
        index=index,
        type="cost.on_miss",
        note=(
            f"失手反噬 {_fmt(cost)} × 自傷折合 {budget.gamble_self_harm_permille}‰"
            f" × 觸發率 {budget.gamble_on_miss_rate_permille}‰"
        ),
        base=points,
        shape=Fraction(1),
        target=Fraction(1),
        condition=Fraction(1),
        points=points,
    )


def _consume_stack_points(
    skill: SkillDef, effect: EffectSpec, library: ContentLibrary
) -> tuple[Fraction, str]:
    """``consume_stack`` 的加成點數：同技能被加成的效果（傷害；層數的 ``consumer.boosts`` 還可以含
    治療、護盾；含形狀與對象倍率）× 期望消耗層數 × ``per_stack_permille``；期望消耗＝層數上限 ×
    ``consume_stack_expected_permille``。"""
    rules, budget = library.ruleset, library.budget
    if effect.stack is None or effect.per_stack_permille is None:
        raise BudgetError("consume_stack 缺少 stack 或 per_stack_permille")
    expected = Fraction(
        rules.stack_def(effect.stack).max * budget.consume_stack_expected_permille, _PERMILLE
    )
    primitives = rules.primitives.by_id()
    stack = rules.stack_def(effect.stack)
    boosted = ("damage",) if stack.consumer is None else stack.consumer.boosts
    damage = Fraction(0)
    for other in skill.effects:
        if other.type in boosted:
            base, _ = _base_points(skill, other, primitives[other.type], library)
            damage += base * _shape_multiplier(skill, other, primitives[other.type], library)
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
    "gamble": _gamble_points,
    "dispel": _dispel_points,
    "reveal": _reveal_points,
    "obstacle": _obstacle_points,
    "inscribe": _inscribe_points,
    "detonate_runes": _detonate_runes_points,
    "sacrifice_summon": _sacrifice_summon_points,
    "revive": _revive_points,
    "delayed_damage": _delayed_damage_points,
    "grant_skill": _grant_skill_points,
}
"""需要整個技能或特殊規則的 ``budget_basis`` → 點數算法。"""

BUDGET_BASES: frozenset[str] = frozenset(
    {"fixed", "per_distance", "per_amount", "dice_average", "damage", "status", "surface"}
) | frozenset(_SPECIAL_BASES)
""":func:`_plain_base_points` 有實作的全部 ``budget_basis``（Phase 3E-2b：載入內容時檢查每個原語的
``budget_basis`` 都在這裡，見 :mod:`trpg.primitive_coverage`）。"""


def range_coefficient(shape: ShapeSpec, budget: BudgetRules) -> tuple[int | None, Fraction]:
    """形狀的射程係數（Phase 3-49，玩法決定 #53）：固定射程 N ≥ 1 時為
    ``1 ＋ (N − range_baseline) × range_step_permille ÷ 1000``；武器射程、射程 0、無射程形狀為 1。
    回傳（採用的射程, 係數）。"""
    value = shape.range
    if not isinstance(value, int) or value < 1:
        return None, Fraction(1)
    permille = _PERMILLE + (value - budget.range_baseline) * budget.range_step_permille
    return value, Fraction(permille, _PERMILLE)


def _shape_parts(
    skill: SkillDef, effect: EffectSpec, primitive: PrimitiveDef, library: ContentLibrary
) -> tuple[Fraction, Fraction]:
    """（形狀倍率, 射程係數）；只對作用在單位的效果，陷阱技能取 ``trap.shape`` 的倍率
    （觸發時的影響範圍，沒有射程）。"""
    rules = library.ruleset
    affects = resolved_affects(rules, effect)
    if primitive.budget_basis in ("zone", "gamble"):  # 持續區域（3D-5）、賭注（3D-7a）：已含倍率
        return Fraction(1), Fraction(1)
    if not (affects in _SHAPED_AFFECTS and primitive.acts_on != "caster"):
        return Fraction(1), Fraction(1)
    if skill.trap is not None:
        shape = rules.shapes.by_id()[skill.trap.shape]
        return Fraction(shape.budget.permille_for({}), _PERMILLE), Fraction(1)
    shape = rules.shapes.by_id()[skill.shape.type]
    multiplier = Fraction(shape.budget.permille_for(skill.shape.param_values()), _PERMILLE)
    return multiplier, range_coefficient(skill.shape, library.budget)[1]


def _shape_multiplier(
    skill: SkillDef, effect: EffectSpec, primitive: PrimitiveDef, library: ContentLibrary
) -> Fraction:
    """形狀倍率 × 射程係數（只對作用在單位的效果）。"""
    shape, reach = _shape_parts(skill, effect, primitive, library)
    return shape * reach


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
    if effect.type == ADD_STACK and (overload_cost := _overload_stack_cost(effect, library)):
        base, note = overload_cost  # 超載層數沒有「消耗」的技能，累積它只有反噬的代價（3D-7b）
    affects = resolved_affects(rules, effect)
    # consume_stack 的加成點數已含傷害效果的形狀倍率
    shape, reach = (
        (Fraction(1), Fraction(1))
        if primitive.budget_basis == "consume_stack"
        else _shape_parts(skill, effect, primitive, library)
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
        points=base * shape * reach * target * condition,
        range=reach,
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
    if cost.stamina:  # 3H-2：耐力與法力預算點數等價（stamina_per_mana 點耐力 ＝ 1 點法力）
        value = cost.stamina * allowance.mana_per_point // allowance.stamina_per_mana
        parts.append((f"耐力 {cost.stamina}", min(value, allowance.mana_cap)))
    if cost.hp_percent is not None:
        parts.append(
            (
                f"HP {cost.hp_percent / 10:g}%",
                min(cost.hp_percent * allowance.hp_per_permille, allowance.hp_cap),
            )
        )
    if cost.self_status is not None:
        parts.append(_self_status_allowance(cost.self_status, budget, statuses))
    if cost.overdraft is not None:  # 透支（3-50）：固定折抵
        parts.append(("透支（下回合少 1 AP）", allowance.overdraft_permille))
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
    return (f"自身{status.name_zh} {cost.duration} 回合", min(value, rule.cap_of(cost.status)))


def self_status_allowance_permille(cost: SelfStatusCost, library: ContentLibrary) -> int:
    """自身狀態代價換到的預算折抵（‰；已套用該狀態的上限，尚未和其他代價加總）。"""
    return _self_status_allowance(cost, library.budget, library.ruleset.statuses.by_id())[1]


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


def _rune_on_hit_factor(effect: EffectSpec, library: ContentLibrary) -> Fraction:
    """命中後效果裡符文原語的點數比例（3-31，``modifier.on_hit_rune_permille``）；其他為 1。"""
    if effect.type not in ("inscribe", "detonate_runes"):
        return Fraction(1)
    return Fraction(library.budget.modifier.on_hit_rune_permille, _PERMILLE)


def _modifier_uses(rule: ModifierSpec, budget: ModifierBudget) -> tuple[int, str]:
    """一條修正規則每場的預估使用次數（``applies_to`` 各項加總，上限 ``uses_cap``）與說明。"""
    target, uses = rule.applies_to, budget.uses
    if rule.per_turn_limit is not None:  # 每回合 1 次（3-31）：以自己的回合數估，不看 uses 表
        return min(budget.per_turn_limit_uses, budget.uses_cap), "每回合 1 次"
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
    if change.heal_permille is not None:
        value = Fraction(core.budget_reference_weapon_damage * change.heal_permille, _PERMILLE)
        return value, f"治療量 {change.heal_permille:+d}‰"
    if change.push_distance_delta is not None:
        base = library.ruleset.primitive_def("push").base_points or 0
        return Fraction(base * change.push_distance_delta), f"推擊 +{change.push_distance_delta} 格"
    if change.on_hit_effects is not None:
        carrier = on_hit_carrier(skill, change.on_hit_effects)
        value = sum(
            (
                _effect_budget(carrier, i, e, library).points * _rune_on_hit_factor(e, library)
                for i, e in enumerate(carrier.effects)
            ),
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
        value, what = structured
        if rule.empty_slots_cap is not None:  # 普攻精通（3-32a）：以滿格（cap 格全空）估，再打折
            ratio = Fraction(library.budget.modifier.empty_slots_permille, _PERMILLE)
            return value * rule.empty_slots_cap * ratio, f"{what}／空格 × {rule.empty_slots_cap}"
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
    magnitude = Fraction(abs(int(getattr(change, kind) or 0))) if kind not in flags else Fraction(1)
    if kind in ("summon_hp_permille", "summon_damage_permille"):
        magnitude /= 100  # 每 +100‰ 一份
    per = {
        "hit_bonus": points.hit_bonus,
        "cooldown_delta": points.cooldown_delta,
        "range_delta": points.range_delta,
        "add_element": points.add_element,
        "grant_pierce": points.grant_pierce,
        "area_delta": points.area_delta,
        "allow_self_target": points.allow_self_target,
        "summon_hp_permille": points.summon_hp_per_100,
        "summon_attack_dice": points.summon_attack_die,
        "summon_limit_delta": points.summon_limit,
        "summon_duration_delta": points.summon_duration,
        "summon_damage_permille": points.summon_damage_per_100,
    }[kind]
    sign = -1 if kind == "hit_bonus" and (change.hit_bonus or 0) < 0 else 1
    sign = -1 if kind == "range_delta" and (change.range_delta or 0) < 0 else sign
    sign = -1 if kind == "summon_limit_delta" and (change.summon_limit_delta or 0) < 0 else sign
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


def _action_coefficient(skill: SkillDef, budget: BudgetRules) -> tuple[Fraction, str]:
    """主動、反應、姿態技能的係數：AP 係數（反應與姿態用各自的係數），陷阱再 × 陷阱係數，
    賭博型（3D-7a）再 × 變異加成。"""
    coefficient = _ap_coefficient(skill, budget)
    label = {"reaction": "反應係數", "stance": "姿態係數"}.get(skill.kind, "AP 係數")
    if skill.trap is not None:
        coefficient *= Fraction(budget.trap_coefficient_permille, _PERMILLE)
        label = "AP 係數 × 陷阱係數"
    if skill.is_gamble:  # 賭博型：期望值計，可用預算 × 變異加成
        coefficient *= Fraction(budget.gamble_variance_bonus_permille, _PERMILLE)
        label += f" × 變異加成 {budget.gamble_variance_bonus_permille}‰"
    return coefficient, label


def _action_budgets(skill: SkillDef, library: ContentLibrary) -> tuple[EffectBudget, ...]:
    """主動、反應、被動等技能的效果點數：各效果，加上失手反噬（3D-7a）與擊殺時效果（3D-8b）的列。"""
    effects = tuple(_effect_budget(skill, i, e, library) for i, e in enumerate(skill.effects))
    miss = _on_miss_budget(skill, library, len(effects))
    if miss is not None:
        effects += (miss,)
    for effect in skill.effects:
        kill = _on_kill_budget(skill, library, len(effects), effect)
        if kill is not None:
            effects += (kill,)
    return effects


def _segment(label: str, report: BudgetReport, skill: SkillDef, offset: int) -> SegmentBudget:
    return SegmentBudget(
        label=label,
        skeleton=skill.skeleton,
        shape=skill.shape.type,
        effects=tuple(replace(e, index=e.index + offset) for e in report.effects),
        raw=report.raw,
        condition_multiplier=report.condition_multiplier,
        synergies=report.synergies,
        total=report.total,
        range_value=report.range_value,
        range_coefficient=report.range_coefficient,
    )


_SEGMENT_LABELS: dict[str, tuple[str, str]] = {
    "after_move": ("位移段", "動作段"),
    "after_action": ("動作段", "位移段"),
    "after_gather": ("聚集段", "打擊段"),
    "on_kill": ("第一段", "擊殺後的第二段"),
    "on_hit": ("第一段", "命中後的第二段"),
    "delayed": ("第一段", "延遲段"),
}


def followup_chance_permille(skill: SkillDef, library: ContentLibrary) -> int:
    """複合技能第二段的觸發機率（‰，Phase 3F-4a）：``on_kill`` 用預估擊殺率
    （``on_kill_expected_permille``）、``on_hit`` 用預估命中率（``modifier.hit_rate_permille``）；
    延遲段（3F-4b）用折扣 ``composite_delayed_discount_permille``；其他種類一定結算（1000）。"""
    assert skill.followup is not None
    budget = library.budget
    if skill.followup.when == "on_kill":
        return budget.on_kill_expected_permille
    if skill.followup.when == "on_hit":
        return budget.modifier.hit_rate_permille
    if skill.followup.when == "delayed":
        return budget.composite_delayed_discount_permille
    return _PERMILLE


def _composite_budget(skill: SkillDef, library: ContentLibrary) -> BudgetReport:
    """複合技能（Phase 3F-3a／3F-4a，6.23）：（第一段點數 ＋ 第二段點數 × 觸發機率）×（1000 ＋
    複合加成）÷ 1000；兩段之間有元素／表面連鎖時再 ×（1000 ＋ ``composite_self_combo_permille``）
    ÷ 1000。兩段各自依自己的骨架與形狀計算（和一般技能相同）；可用預算照技能本身的 AP 與代價。"""
    follow = skill.followup_skill()
    assert follow is not None and skill.followup is not None
    move = skill.move_segment()
    first = skill_budget(move, library)
    second = skill_budget(follow, library)
    tax = library.budget.composite_tax_permille
    chance = followup_chance_permille(skill, library)
    reasons = self_combo_reasons(skill, library)
    combo = library.budget.composite_self_combo_permille if reasons else 0
    first_label, second_label = _SEGMENT_LABELS[skill.followup.when]
    segments = (
        _segment(first_label, first, move, 0),
        replace(_segment(second_label, second, follow, len(first.effects)), chance_permille=chance),
    )
    total = (first.total + second.total * Fraction(chance, _PERMILLE)) * Fraction(
        _PERMILLE + tax, _PERMILLE
    )
    total *= Fraction(_PERMILLE + combo, _PERMILLE)
    return replace(
        first,
        skill_id=skill.id,
        effects=segments[0].effects + segments[1].effects,
        raw=first.raw + second.raw,
        condition_multiplier=Fraction(1),
        tags=tuple(sorted({*first.tags, *second.tags})),
        synergies=(),
        total=total,
        segments=segments,
        composite_tax_permille=tax,
        self_combo_permille=combo,
        self_combo_reasons=reasons,
    )


def _variant_budget(skill: SkillDef, library: ContentLibrary) -> BudgetReport:
    """帶戰場變奏的技能（Phase 3-25a，PM 決定 #6）：基礎型態照一般技能計算，總點數再 ×（1000 ＋
    ``variant_surcharge_permille`` × 變奏數）÷ 1000；各變奏型態另外照一般技能計算（列在
    ``variants``，驗證器要求每個型態都落在預算窗內）。"""
    base = skill_budget(skill.model_copy(update={"variants": ()}), library)
    surcharge = library.budget.variant_surcharge_permille * len(skill.variants)
    forms = tuple(
        VariantBudget(v.id, v.name_zh, skill_budget(skill.variant_form(v.id), library))
        for v in skill.variants
    )
    return replace(
        base,
        total=base.total * Fraction(_PERMILLE + surcharge, _PERMILLE),
        variant_surcharge_permille=surcharge,
        variants=forms,
    )


def skill_budget(skill: SkillDef, library: ContentLibrary) -> BudgetReport:
    """計算 ``skill`` 的預算明細；缺少點數資料時拋出 :class:`BudgetError`。"""
    if skill.variants:
        return _variant_budget(skill, library)
    if skill.followup is not None:
        return _composite_budget(skill, library)
    rules, budget = library.ruleset, library.budget
    if skill.is_modifier:
        effects = _modifier_budgets(skill, library)
    else:
        effects = _action_budgets(skill, library)
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
    range_value, reach = range_coefficient(skill.shape, budget)
    if skill.is_activatable:
        coefficient, label = _activation_coefficient(skill, library)
    elif skill.kind == "passive":
        coefficient, label = _passive_coefficient(skill, library)
    elif skill.is_modifier:
        coefficient = Fraction(budget.modifier.coefficient_permille, _PERMILLE)
        label = "修正係數"
    else:
        coefficient, label = _action_coefficient(skill, budget)
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
        range_value=range_value,
        range_coefficient=reach,
    )
