"""完整技能的強度（Phase 3W-5b，``docs/design/06-技能.md`` 6.34.6）。

完整技能視為「已閃 3 次」，預算上限 +``complete.budget_permille``‰（``flash_templates.yaml``），而且
這 +120‰ 要 **實際加上去**：預算分數（:func:`complete_power`）至少是原本的 ×（1000 ＋ 它）÷ 1000。

做法是從原本的數值 **只往上加**，一次一格，直到達到目標（數字不會變小，卡片上看得出變強）：

1. **數值旋鈕**：預算器的強度旋鈕（傷害、治療、護盾的骰子或倍率、推拉距離、修正幅度、接續段的
   傷害）；召喚再加召喚物 HP 與傷害的倍率（``summon_power_steps``，乘在 ``power_permille`` 上）；
   姿態再加姿態幅度（``stance_magnitude_steps``，``apply_status.magnitude_permille``）。
2. 上一組都加不動時，效果參數的旋鈕（狀態、表面的持續回合等，``skill_primitives.yaml`` 的
   ``knob``，同升階重配）。
3. 仍然沒有可加的數值時，依 ``cost_cuts`` 的順序減一格代價（維持費、冷卻、法力、耐力、AP）；
   只減不拿掉（每項最少留 1）。

每一步都要通過驗證（不超過預算上限、骨架占比等；「過弱」除外，見 :data:`_WEAK`）。同一組裡有能
一步達標的，取超出最少的；否則取分數加最多的（同分取資料順序在前的）。都加不動、還沒達標時停在
目前最強的版本（例如沒有代價的修正型被動），由呼叫者記錄。旋鈕的階梯與減代價的順序都在資料檔；
這裡不認技能 ID，沒有亂數。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.flash_templates import CompleteSkillRules, CostCut
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.evolution import effect_strength_knobs
from trpg.skillgen.flash import with_budget_bonus
from trpg.skillgen.flash_ops import base_draft, tuning_extras
from trpg.skillgen.skill_tier import param_knobs
from trpg.skillgen.validate import validate_skill

__all__ = ["complete_gain_permille", "complete_power", "complete_strength"]

_PERMILLE = 1000
_MAX_STEPS = 40
"""最多加幾步（每一步一格；防止資料寫錯時無窮迴圈）。"""
_DICE = re.compile(r"^(\d+)d(\d+)$")

type _Draft = tuple[dict[str, Any], list[dict[str, Any]]]
type _Trial = tuple[SkillDef, Fraction]


def complete_power(skill: SkillDef, library: ContentLibrary) -> Fraction:
    """完整技能比較用的預算分數：預算總點數 ÷（AP 或觸發係數 ×（1000 ＋ 代價折抵）÷ 1000）。

    同 :func:`~trpg.skillgen.evolution.budget_power`，但把代價折抵也換算掉（姿態本來就這樣算），
    所以減冷卻、法力、維持費這類「代價變便宜」也算變強；只改效果數值時兩者的比例相同。"""
    report = skill_budget(skill, library)
    cost = report.ap_coefficient * Fraction(_PERMILLE + report.allowance_permille, _PERMILLE)
    return report.total / cost


def complete_gain_permille(before: SkillDef, after: SkillDef, library: ContentLibrary) -> int:
    """``after`` 比 ``before`` 的預算分數多幾 ‰（無條件捨去）。"""
    ratio = complete_power(after, library) / complete_power(before, library)
    return int((ratio - 1) * _PERMILLE)


def complete_strength(library: ContentLibrary, skill: SkillDef) -> SkillDef:
    """``skill`` 照完整技能的強度重做（結構不變、帶上 ``budget_bonus_permille``）；見模組說明。
    ID 不變（換 ID 是呼叫者的事）。"""
    rules = library.flash.rules.complete
    scale = Fraction(_PERMILLE + rules.budget_permille, _PERMILLE)
    base = complete_power(skill, library)
    target = base * scale
    cap = base * Fraction(_PERMILLE + rules.cap_permille, _PERMILLE)
    start = with_budget_bonus(skill, rules.budget_permille)
    # 先只走不超過上限的步子（較細的旋鈕補上）；這樣達不到 +120‰ 才接受超過上限（06 6.34.6）
    capped, power = _climb(library, rules, start, target, cap)
    if power >= target:
        return capped
    return _climb(library, rules, start, target, None)[0]


def _climb(
    library: ContentLibrary,
    rules: CompleteSkillRules,
    current: SkillDef,
    target: Fraction,
    cap: Fraction | None,
) -> _Trial:
    power = complete_power(current, library)
    for _ in range(_MAX_STEPS):
        if power >= target:
            break
        step = _next_step(library, rules, current, target, cap)
        if step is None:
            break
        current, power = step
    return current, power


# ---------------------------------------------------------------------------
# 一步
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Move:
    """一個可以往上加的旋鈕：草稿裡第 ``index`` 個字典的 ``field``，下一格是 ``value``。"""

    index: int
    field: str
    value: Any


type _Group = Callable[[ContentLibrary, CompleteSkillRules, SkillDef, _Draft], list[Knob]]


def _next_step(
    library: ContentLibrary,
    rules: CompleteSkillRules,
    skill: SkillDef,
    target: Fraction,
    cap: Fraction | None = None,
) -> _Trial | None:
    """往上加一格後的（技能, 分數）；三組依序，前一組都加不動才看下一組。``cap`` 不是 ``None`` 時
    只考慮不超過它的步子。"""
    groups: tuple[_Group, ...] = (_strength_knobs, _param_knobs)
    trial_sets: list[Iterator[_Trial | None]] = [
        _raised(library, rules, skill, group) for group in groups
    ]
    trial_sets += [iter([_cut(library, skill, cut)]) for cut in rules.cost_cuts]
    for trials in trial_sets:
        kept = trials if cap is None else (t for t in trials if t is not None and t[1] <= cap)
        found = _best(kept, target)
        if found is not None:
            return found
    return None


def _best(trials: Iterator[_Trial | None], target: Fraction) -> _Trial | None:
    """能一步達標的取分數最低者；否則取分數最高者（同分取先出現的）。"""
    reached: _Trial | None = None
    best: _Trial | None = None
    for trial in trials:
        if trial is None:
            continue
        if trial[1] >= target and (reached is None or trial[1] < reached[1]):
            reached = trial
        if best is None or trial[1] > best[1]:
            best = trial
    return reached or best


def _raised(
    library: ContentLibrary, rules: CompleteSkillRules, skill: SkillDef, group: _Group
) -> Iterator[_Trial | None]:
    """這一組旋鈕各往上加一格的結果（不合法的為 ``None``）。"""
    draft = base_draft(skill)
    knobs = group(library, rules, skill, draft)
    for move in _moves(knobs, _targets(skill, draft)):
        base, effects = base_draft(skill)
        _targets(skill, (base, effects))[move.index][move.field] = move.value
        yield _checked(library, {**base, "effects": effects})


def _targets(skill: SkillDef, draft: _Draft) -> list[dict[str, Any]]:
    """旋鈕的 ``index`` 指向的字典：效果，之後接修正規則的 change 或接續段的效果（同一批物件）。"""
    base, effects = draft
    if base.get("kind") == "modifier":
        return [*effects, *(m["change"] for m in base["modifiers"])]
    if skill.followup is not None and base.get("followup"):
        return [*effects, *base["followup"]["effects"]]
    return list(effects)


def _moves(knobs: Sequence[Knob], targets: Sequence[dict[str, Any]]) -> Iterator[_Move]:
    """每個旋鈕（同一欄位只算一次）從目前的值往上的下一格。"""
    seen: set[tuple[int, str]] = set()
    for knob in knobs:
        if (knob.index, knob.field) in seen or knob.index >= len(targets):
            continue
        seen.add((knob.index, knob.field))
        current = _order(targets[knob.index].get(knob.field))
        if current is None:
            continue
        ups = [(o, v) for v in knob.values if (o := _order(v)) is not None and o > current]
        if ups:
            yield _Move(knob.index, knob.field, min(ups, key=lambda pair: pair[0])[1])


def _order(value: Any) -> int | None:
    """旋鈕值的大小：整數照原值、骰子 ``NdM`` 用 ``N × (M + 1)``（平均值 ×2）；其他無法比較。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and (m := _DICE.match(value)) is not None:
        return int(m.group(1)) * (int(m.group(2)) + 1)
    return None


_WEAK = "budget.weak"
"""「過弱」不擋中間步驟：上限加了 +120‰，原本的數值換算成新的比例一定偏低；加到目標時比例就回到
原本的水準（不低於原本），所以只有還沒加到目標的中間版本會過弱。"""


def _checked(library: ContentLibrary, data: dict[str, Any]) -> _Trial | None:
    """草稿通過驗證（過弱除外，見 :data:`_WEAK`）時的（技能, 分數）。"""
    try:
        skill = SkillDef.model_validate(data)
        if any(not v.rule.endswith(_WEAK) for v in validate_skill(skill, library)):
            return None
        return skill, complete_power(skill, library)
    except (ValidationError, BudgetError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 旋鈕的兩組
# ---------------------------------------------------------------------------


def _strength_knobs(
    library: ContentLibrary, rules: CompleteSkillRules, skill: SkillDef, draft: _Draft
) -> list[Knob]:
    """預算器的強度旋鈕（傷害、治療、護盾、推拉、修正幅度、接續段），加上召喚與姿態的旋鈕。"""
    base, effects = draft
    knobs = list(effect_strength_knobs(skill.category, effects, library))
    _, extra = tuning_extras("followup" if skill.followup else "", base, library)
    knobs += [Knob(len(effects) + k.index, k.field, k.values) for k in extra]
    statuses = library.ruleset.statuses.by_id()
    for index, effect in enumerate(effects):
        if effect["type"] == "summon" and (effect.get("count") or 1) == 1:
            field, steps = "power_permille", rules.summon_power_steps
        elif (
            skill.kind == "stance"
            and effect["type"] == "apply_status"
            and (status := statuses.get(str(effect.get("status")))) is not None
            and status.stance
        ):
            field, steps = "magnitude_permille", rules.stance_magnitude_steps
        else:
            continue
        start = int(effect.get(field) or _PERMILLE)
        effect[field] = start  # 比較大小用（只在這份草稿上）
        knobs.append(Knob(index, field, tuple(start * s // _PERMILLE for s in steps)))
    return knobs


def _param_knobs(
    library: ContentLibrary, _rules: CompleteSkillRules, skill: SkillDef, draft: _Draft
) -> list[Knob]:
    """效果參數的旋鈕（狀態、表面的持續回合、累積層數……；同升階重配的 ``param_knobs``）。"""
    return param_knobs(draft[1], skill.category, library)


# ---------------------------------------------------------------------------
# 減代價
# ---------------------------------------------------------------------------


def _cut(library: ContentLibrary, skill: SkillDef, cut: CostCut) -> _Trial | None:
    """``skill`` 的 ``cut.field`` 減一格並驗證；減完會低於 1（等於把這項代價拿掉）或不合法時
    ``None``——只減不拿掉，例如冷卻最少留 1 回合。"""
    data = skill.model_dump(mode="json")
    holder = data if cut.field in ("stance_upkeep", "ap_cost") else data["cost"]
    value = holder.get(cut.field)
    if not value or value - cut.step < 1:
        return None
    holder[cut.field] = value - cut.step
    return _checked(library, data)
