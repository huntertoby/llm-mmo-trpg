"""收回家族的共用做法「放棄一部分 → 換核心數值」（BAL-10d，``docs/design/06-技能.md`` 6.34.4
「收束」「收回家族」；玩法決定 #74、#75）。

一種收回（:class:`Trade`）只需要提供兩個函式：

- ``remove``「拿掉什麼」：同小變化的改法（:data:`~trpg.skillgen.flash_ops.FlashOp`），回傳拿掉之後
  的草稿（只描述結構，不寫強度）；技能身上沒有可拿的就回傳空列表（這個選項不出）。
- ``gain``「換成什麼」：除了效果本身的威力旋鈕以外，重調時要一起調的字典與旋鈕（同
  :func:`~trpg.skillgen.flash_ops.tuning_extras`；收束只換威力，回傳空的）。

另有 ``core``：單發上限要量的「對單一目標的核心數值」（預設 :func:`target_power`：傷害、治療、
護盾各自的期望量）；``knobs``：效果本身威力以外的旋鈕（BAL-10e 合體的召喚物 HP）。

登錄表 :data:`TRADES`：收束（BAL-10d；BAL-10e 補陷阱與地面格）與精煉、合體、專注（BAL-10e，
「拿掉什麼」在 :mod:`trpg.skillgen.flash_reclaim`）。

**流程**（:func:`apply_trade`）：

1. 拿掉之前用預算器算一次總點數；拿掉之後的草稿再算一次可用預算。
2. 目標點數 ＝ 拿掉之前的總點數 ＋ 這一次閃現的 ``budget_step_permille``（佔同階可用預算）：拿掉的
   部分（例：形狀倍率 2000‰ → 1000‰）在總點數不變的前提下全部換成威力，再加這次的 +40‰。
   目標比例 ＝ max(這個點數 ÷ 拿掉之後的可用預算, 一般重調的隨機目標)（BAL-10d2：和其他小變化一樣
   可以吃到之前沒用完的加成），由預算器只用威力旋鈕重調到這個比例（強度下限照 6.34.3）。
3. **單發上限**：對單一目標的期望量 ≤ 同階、同 AP 單體技能預算（``tier_budget`` × AP 係數）×
   ``single_hit_cap_permille``。超過時威力壓回上限，省下的預算依 ``complete.cost_cuts`` 的順序一次減
   一格代價（減費用），直到「每單位可用預算的強度」不低於強度下限；減不動就不出這個選項。

純函式、確定性（亂數一律來自呼叫者的 :class:`~trpg.shared.rng.Rng` 分流）。
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from pydantic import ValidationError

from trpg.content.flash_templates import FlashTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import ShapeSpec, SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError, BudgetReport, skill_budget
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.composer_tuning import tuning_bounds
from trpg.skillgen.evolution import effect_strength_knobs, retune
from trpg.skillgen.flash_ops import FLASH_OPS, Draft, FlashOp, base_draft, cell_count
from trpg.skillgen.flash_reclaim import (
    fuse_knobs,
    modifier_gain,
    op_focus_condition,
    op_focus_mod_condition,
    op_focus_mod_range,
    op_focus_range,
    op_fuse,
    op_refine,
    op_refine_merge,
)
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.mechanics import resolved_affects

__all__ = [
    "MINOR_OPS",
    "POWER_GROUPS",
    "TRADES",
    "CoreFn",
    "GainFn",
    "KnobFn",
    "Trade",
    "apply_trade",
    "cap_points",
    "converge_gain",
    "convergible",
    "has_power",
    "no_gain",
    "no_knobs",
    "target_power",
]

type GainFn = Callable[
    [dict[str, Any], list[dict[str, Any]], ContentLibrary],
    tuple[list[dict[str, Any]], list[Knob]],
]
type CoreFn = Callable[[SkillDef, ContentLibrary], dict[str, Fraction]]
type KnobFn = Callable[[list[dict[str, Any]], ContentLibrary], list[Knob]]

_PERMILLE = 1000
_TUNE_ATTEMPTS = 3
"""同一份草稿最多試幾次不同的調整亂數（同 :data:`trpg.skillgen.flash_derive.TUNE_ATTEMPTS`）。"""
_CAP_SHRINK_STEPS = 6
_CAP_SHRINK_PERMILLE = 30
"""壓回單發上限時，目標比例每次再往下退多少‰（離散的骰子階梯可能一次跳過上限）。"""
_MAX_COST_CUTS = 12

POWER_GROUPS: dict[str, str] = {
    "damage": "damage",
    "delayed_damage": "damage",
    "heal": "heal",
    "shield": "shield",
}
"""算「威力」的效果原語 → 單發上限分開量的組（傷害、治療、護盾）。"""
_TARGETED = frozenset({"enemies", "allies", "all", "tiles"})
"""作用在形狀選到的單位（不是施放者自己）的對象。"""


# ---------------------------------------------------------------------------
# 核心數值與單發上限
# ---------------------------------------------------------------------------


def has_power(skill: SkillDef, library: ContentLibrary) -> bool:
    """技能有作用在目標（不是自己）的傷害、治療或護盾量。"""
    return any(
        effect.type in POWER_GROUPS and resolved_affects(library.ruleset, effect) in _TARGETED
        for effect in skill.effects
    )


def target_power(skill: SkillDef, library: ContentLibrary) -> dict[str, Fraction]:
    """一次施放對單一目標的期望量（預算點數：骰子平均或武器倍率 × 基準，含高變異係數、效果條件與
    技能條件的倍率），依 :data:`POWER_GROUPS` 分組；不含形狀與射程倍率。"""
    report = skill_budget(skill, library)
    out: dict[str, Fraction] = {}
    for item in report.effects:
        if item.index >= len(skill.effects):
            continue
        effect = skill.effects[item.index]
        group = POWER_GROUPS.get(effect.type)
        if (
            group is None
            or effect.type != item.type
            or resolved_affects(library.ruleset, effect) not in _TARGETED
        ):
            continue
        out[group] = out.get(group, Fraction(0)) + item.base * item.condition
    return {k: v * report.condition_multiplier for k, v in sorted(out.items())}


def cap_points(report: BudgetReport, library: ContentLibrary) -> Fraction:
    """單發上限（預算點數）：同階、同 AP 單體技能的預算（``tier_budget`` × AP 係數）×
    ``single_hit_cap_permille``。"""
    permille = library.flash.rules.single_hit_cap_permille
    return report.tier_budget * report.ap_coefficient * Fraction(permille, _PERMILLE)


def _cap_excess(skill: SkillDef, library: ContentLibrary, core: CoreFn) -> Fraction:
    """核心數值最大的那一組 ÷ 單發上限（≤ 1 ＝ 沒超過）。"""
    cap = cap_points(skill_budget(skill, library), library)
    return max(core(skill, library).values(), default=Fraction(0)) / cap


# ---------------------------------------------------------------------------
# 一種收回
# ---------------------------------------------------------------------------


def no_gain(
    _base: dict[str, Any], _effects: list[dict[str, Any]], _library: ContentLibrary
) -> tuple[list[dict[str, Any]], list[Knob]]:
    """只換效果本身的威力（傷害、治療、護盾的骰子或倍率），沒有額外旋鈕。"""
    return [], []


def no_knobs(_effects: list[dict[str, Any]], _library: ContentLibrary) -> list[Knob]:
    """效果本身沒有威力以外的旋鈕。"""
    return []


@dataclass(frozen=True, slots=True)
class Trade:
    """一種收回：``remove`` 拿掉什麼、``gain`` 換成什麼（額外的字典與旋鈕）、``knobs`` 換成什麼
    （效果本身威力以外的旋鈕，``index`` 指向效果；BAL-10e 合體的召喚物 HP）、``core`` 單發上限量
    什麼。"""

    remove: FlashOp
    gain: GainFn = no_gain
    core: CoreFn = target_power
    knobs: KnobFn = no_knobs


def _usable(
    library: ContentLibrary, base: dict[str, Any], effects: list[dict[str, Any]]
) -> BudgetReport | None:
    try:
        return skill_budget(SkillDef.model_validate({**base, "effects": effects}), library)
    except (ValidationError, BudgetError, ValueError):
        return None


def _tuned(
    library: ContentLibrary,
    draft: Draft,
    trade: Trade,
    rng: Rng,
    *,
    ratio: Fraction,
    floor: Fraction | None,
) -> SkillDef | None:
    base, effects = draft
    extra, knobs = trade.gain(base, effects, library)
    for attempt in range(_TUNE_ATTEMPTS):
        done = retune(
            base,
            effects,
            rng.fork(f"r{attempt}"),
            library,
            floor=floor,
            extra=extra,
            extra_knobs=knobs,
            effect_knobs=trade.knobs(effects, library),
            target_ratio=ratio,
            power_only=True,
        )
        if done is not None:
            return done
    return None


def apply_trade(
    library: ContentLibrary,
    current: SkillDef,
    drafts: Sequence[Draft],
    trade: Trade,
    rng: Rng,
    *,
    floor: Fraction | None,
) -> SkillDef | None:
    """把收回的草稿（``trade.remove`` 的結果）換成核心數值並驗證；做不出來時 ``None``（流程見模組
    說明）。``current`` 是收回之前的技能（已設好這一次的預算上限加成），``floor`` 是強度下限
    （:func:`~trpg.skillgen.flash_derive.power_floor`）。"""
    try:
        before = skill_budget(current, library)
    except BudgetError:
        return None
    step = Fraction(library.flash.rules.budget_step_permille, _PERMILLE)
    plain = before.tier_budget * before.ap_coefficient
    wanted = (
        before.total + plain * Fraction(_PERMILLE + before.allowance_permille, _PERMILLE) * step
    )
    top = before.max_ratio
    for index, draft in enumerate(drafts):
        report = _usable(library, *draft)
        if report is None:
            continue
        sub = rng.fork(str(index))
        ratio = min(max(wanted / report.usable, _random_target(library, sub.fork("target"))), top)
        done = _tuned(library, draft, trade, sub, ratio=ratio, floor=floor)
        if done is None:
            continue
        if _cap_excess(done, library, trade.core) <= 1:
            return done
        floor_ratio = (
            report.min_ratio if floor is None else floor * report.ap_coefficient / report.usable
        )
        cut = _cost_cut(library, draft, done, trade, sub.fork("cut"), floor_ratio=floor_ratio)
        if cut is not None:
            return cut
    return None


def _random_target(library: ContentLibrary, rng: Rng) -> Fraction:
    """一般重調（有強度下限時）抽的目標比例：均勻分佈在 ``[low, 1.00 − margin]``（同
    :func:`~trpg.skillgen.composer_tuning.tune`）。"""
    rules = library.composer.tuning
    low, _ = tuning_bounds(library)
    span = 1 - low - Fraction(rules.target_margin_permille, _PERMILLE)
    return low + span * Fraction(rng.randint(0, rules.target_steps), rules.target_steps)


def _cost_cuts(base: dict[str, Any], library: ContentLibrary) -> Iterator[dict[str, Any]]:
    """依 ``complete.cost_cuts`` 的順序一次減一格代價（累計）；只減不拿掉（最少留 1）。"""
    current = copy.deepcopy(base)
    made = 0
    for cut in library.flash.rules.complete.cost_cuts:
        holder = current if cut.field in ("stance_upkeep", "ap_cost") else current.get("cost")
        while isinstance(holder, dict) and made < _MAX_COST_CUTS:
            value = holder.get(cut.field)
            if not value or value - cut.step < 1:
                break
            holder[cut.field] = value - cut.step
            made += 1
            yield copy.deepcopy(current)


def _cost_cut(
    library: ContentLibrary,
    draft: Draft,
    done: SkillDef,
    trade: Trade,
    rng: Rng,
    *,
    floor_ratio: Fraction,
) -> SkillDef | None:
    """超過單發上限：威力壓回上限，省下的預算改成減費用。每減一格代價，可用預算變小；照「上限對應
    的總點數 ÷ 新的可用預算」重調，比例不低於 ``floor_ratio``（減費用之前的強度下限比例）且不超過
    上限的第一個就是結果。"""
    over = _cap_excess(done, library, trade.core)
    cap_total = skill_budget(done, library).total / over
    base, effects = draft
    for index, cheaper in enumerate(_cost_cuts(base, library)):
        report = _usable(library, cheaper, effects)
        if report is None:
            continue
        aim = min(cap_total / report.usable, report.max_ratio)
        for shrink in range(_CAP_SHRINK_STEPS):
            ratio = aim * Fraction(_PERMILLE - shrink * _CAP_SHRINK_PERMILLE, _PERMILLE)
            if ratio < max(floor_ratio, report.min_ratio):
                break
            skill = _tuned(
                library,
                (cheaper, effects),
                trade,
                rng.fork(f"{index}.{shrink}"),
                ratio=ratio,
                floor=None,
            )
            if (
                skill is not None
                and skill_budget(skill, library).ratio >= floor_ratio
                and _cap_excess(skill, library, trade.core) <= 1
            ):
                return skill
    return None


# ---------------------------------------------------------------------------
# 收束（#74）：收成單體、縮小一級；BAL-10e 補陷阱與地面格（持續區域）
# ---------------------------------------------------------------------------

_NOT_AREA_TARGETING = frozenset({"unit_tile", "unit_pair", "object_tile"})
"""選兩個東西的特殊形狀（傳送、投擲）：不算「範圍」，不收束。"""
_STEP_DOWN = {"square3": "cross"}
"""縮小一級換成另一種形狀的（3×3 → 十字，射程沿用）；直線、錐形是長度 −1。陷阱的觸發範圍同樣
3×3 → 十字（十字再小就是單格＝收成單體）。"""
_ZONE = "zone"


def _zone_power(skill: SkillDef) -> bool:
    """地面格（持續區域，6.16 G）裡有傷害、治療或護盾（區域結算的效果）。"""
    return any(
        effect.type == _ZONE and any(e.type in POWER_GROUPS for e in effect.effects or ())
        for effect in skill.effects
    )


def convergible(skill: SkillDef, library: ContentLibrary) -> bool:
    """可以收束：主動技、有威力（作用在目標的傷害／治療／護盾，或地面格裡的），形狀是多格範圍；
    陷阱看觸發範圍（``trap.shape``，BAL-10e）。複合技只看第一段的形狀（接續段不動）。"""
    if skill.kind != "active":
        return False
    if skill.trap is not None:
        return has_power(skill, library) and skill.trap.shape != "single"
    if not (has_power(skill, library) or _zone_power(skill)):
        return False
    definition = library.ruleset.shapes.by_id().get(skill.shape.type)
    if definition is None or definition.targeting in _NOT_AREA_TARGETING:
        return False
    cells = cell_count(skill.shape, library)
    return cells is None or cells > 1


def converge_gain(
    base: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary
) -> tuple[list[dict[str, Any]], list[Knob]]:
    """收束換到的威力：效果本身的威力以外，地面格裡的傷害、治療、護盾也一起調（BAL-10e；區域結算
    的效果字典與 ``effects`` 裡的是同一批物件）。沒有地面格時同 :func:`no_gain`。"""
    extra: list[dict[str, Any]] = []
    knobs: list[Knob] = []
    for effect in effects:
        if effect["type"] != _ZONE:
            continue
        nested = effect.get("effects") or []
        offset = len(extra)
        extra += nested
        knobs += [
            Knob(offset + k.index, k.field, k.values, k.weight)
            for k in effect_strength_knobs(base["category"], nested, library)
            if k.field != "distance"
        ]
    return extra, knobs


def _single_range(shape: ShapeSpec, library: ContentLibrary) -> int | Literal["weapon"]:
    """收成單體的射程：沿用原本的距離（武器射程照舊；直線、錐形是它伸出去的長度）；以自己為中心的
    形狀（射程 0 或沒有射程）改成 1。"""
    if shape.range == "weapon":
        return "weapon"
    top = library.ruleset.shape_def("single").params["range"].max
    if isinstance(shape.range, int) and shape.range >= 1:
        return min(shape.range, top)
    definition = library.ruleset.shape_def(shape.type)
    if definition.targeting == "direction" and shape.size:
        return min(shape.size, top)
    return 1


def _with_shape(
    skill: SkillDef, template: FlashTemplate, shape: ShapeSpec, library: ContentLibrary
) -> list[Draft]:
    """換成 ``shape`` 的草稿：原骨架與模板的 ``skeletons`` 依序，只取允許新形狀的（範圍骨架收成單體
    要換成打擊等單體骨架）。"""
    drafts: list[Draft] = []
    for name in dict.fromkeys((skill.skeleton, *template.skeletons)):
        skeleton = library.skeletons.get(name)
        if (
            skeleton is None
            or skill.kind not in skeleton.kinds
            or shape.type not in skeleton.shapes
        ):
            continue
        base, effects = base_draft(skill)
        base["shape"] = shape.model_dump(mode="json", exclude_none=True)
        base["skeleton"] = name
        drafts.append((base, effects))
    return drafts


def _with_trap_shape(skill: SkillDef, shape: str) -> list[Draft]:
    """陷阱的觸發範圍換成 ``shape``（放置的形狀與骨架不動）。"""
    base, effects = base_draft(skill)
    base["trap"] = {**base["trap"], "shape": shape}
    return [(base, effects)]


def _op_converge_single(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """收成單體：多格形狀 → 單體（射程見 :func:`_single_range`）；範圍造的表面、區域跟著縮。陷阱的
    觸發範圍收成單格。"""
    if not convergible(skill, library):
        return []
    if skill.trap is not None:
        return _with_trap_shape(skill, "single")
    single = ShapeSpec(type="single", range=_single_range(skill.shape, library))
    return _with_shape(skill, template, single, library)


def _op_converge_step(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """縮小一級：直線、錐形長度 −1（不低於形狀的最小值），3×3 → 十字；已是最小一級不出。陷阱的觸發
    範圍 3×3 → 十字。"""
    if not convergible(skill, library):
        return []
    if skill.trap is not None:
        smaller = _STEP_DOWN.get(skill.trap.shape)
        return [] if smaller is None else _with_trap_shape(skill, smaller)
    shape = skill.shape
    smaller = _STEP_DOWN.get(shape.type)
    if smaller is not None:
        return _with_shape(skill, template, ShapeSpec(type=smaller, range=shape.range), library)
    definition = library.ruleset.shape_def(shape.type)
    size = definition.params.get("size")
    if definition.targeting != "direction" or size is None or not shape.size:
        return []
    if shape.size - 1 < size.min:
        return []
    return _with_shape(skill, template, shape.model_copy(update={"size": shape.size - 1}), library)


TRADES: dict[str, Trade] = {
    "converge_single": Trade(remove=_op_converge_single, gain=converge_gain),
    "converge_step": Trade(remove=_op_converge_step, gain=converge_gain),
    # BAL-10e（#75）：精煉、合體、專注（trpg.skillgen.flash_reclaim）
    "refine": Trade(remove=op_refine),
    "refine_merge": Trade(remove=op_refine_merge),
    "fuse": Trade(remove=op_fuse, knobs=fuse_knobs),
    "focus_range": Trade(remove=op_focus_range),
    "focus_condition": Trade(remove=op_focus_condition),
    "focus_mod_range": Trade(remove=op_focus_mod_range, gain=modifier_gain),
    "focus_mod_condition": Trade(remove=op_focus_mod_condition, gain=modifier_gain),
}
"""收回家族的登錄表（``op`` → :class:`Trade`）：收束（BAL-10d）與精煉、合體、專注（BAL-10e）。"""

MINOR_OPS: dict[str, FlashOp] = {**FLASH_OPS, **{op: t.remove for op, t in TRADES.items()}}
"""全部小變化的改法（一般改法 ＋ 收回的「拿掉什麼」）；出題與推出技能用它判斷模板有沒有實作。"""
