"""LLM 提議的數值補齊與「引擎可修的錯誤」（Phase 4-L5；使用者決定 #3：數值一律由預算器補）。

- :func:`budget_filler`：取代 :func:`~trpg.skillgen.proposal_numbers.minimal_filler` 在正式流程
  的角色。先補必填的最小值（沿用 ``minimal_filler``），再依提議的效果建立強度旋鈕（與隨機組合器
  共用 :func:`~trpg.skillgen.composer_parts.effect_knobs`），以
  :func:`~trpg.skillgen.composer_tuning.tune` 把預算比例調進 ``[low, high]``。LLM 選的形狀參數
  （``range`` 等）不調；確定性：同一份提議＋同一個 ``seed`` 必得相同數值。
- :data:`REPAIRABLE_CODES` 與 :func:`cooldown_repairs`：補數值後仍出現、但屬於「數值問題」的驗證
  代碼——由引擎修一次再驗，不回給 LLM（:func:`evaluate_with_repair`）。Phase 4-L5b 起「先修可修的、
  再回報其餘」：錯誤裡只要有可修的代碼就先修，修補後剩下的錯誤才回給 LLM。

旋鈕建在頂層效果與複合技能第二段的效果上（Phase 4-L8；組合器只有頂層）；巢狀效果（``then``、
``win``／``lose``、``effects`` 等）的數值維持最小值。AP 與冷卻不是旋鈕（4-L3 待決 #2，4-L8 仍
未開放）：AP 補 2、沒有冷卻；例外是修「補冷卻即可」的互斥規則（``exclusion.*``，由
``skill_exclusions.yaml`` 推導）時補到規則要求的冷卻，以及修 ``budget.weak`` 時的過弱補強
（Phase 4-L10b，:func:`lift_weak`）：先把巢狀效果（``then``、``on_kill``）的數值也當旋鈕重調，
仍過弱就依 ``skill_composer.yaml`` ``llm_cost.weak_steps`` 降 AP（必要時補回冷卻／法力）。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from fnmatch import fnmatchcase
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.composer_rules import CostStep
from trpg.content.library import ContentLibrary
from trpg.content.skills import EffectSpec, SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob, effect_knobs
from trpg.skillgen.composer_tuning import base_ratio, tune, tuning_bounds
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalError,
    ProposalModels,
    ProposalResult,
    evaluate_proposal,
)
from trpg.skillgen.proposal_numbers import NumberFiller, minimal_filler
from trpg.skillgen.validate import is_core_effect, share_violations

__all__ = [
    "REPAIRABLE_CODES",
    "RepairedEvaluation",
    "budget_filler",
    "cap_cooldown",
    "cooldown_repairs",
    "evaluate_with_repair",
    "is_repairable",
    "lift_weak",
    "repairable_codes",
    "repairable_errors",
    "segment_code",
]

REPAIRABLE_CODES: tuple[str, ...] = (
    "budget.over",
    "budget.weak",
    "skeleton.core_share",
    "skeleton.secondary_share",
    "cap.revive_cost",
    "cap.rule_rewrite_cost",
)
"""引擎可修的驗證代碼（``fnmatch`` 樣式）。``budget.over``／``budget.weak``：換一條亂數串流重調
旋鈕（核心優先、全部旋鈕交替）；``skeleton.core_share``、``skeleton.secondary_share``：先只調核心效果的旋鈕（附帶效果停在最小值）。
互斥規則（``exclusion.*``）中「補冷卻即可」的由 :func:`cooldown_repairs` 從 YAML 推導。
``cap.revive_cost``／``cap.rule_rewrite_cost``（Phase 4-L10b，4-L9 建議 B2）：補到
``skill_budget.yaml`` 要求的最低冷卻（:func:`cap_cooldown`；和互斥規則同法）。
``budget.unavailable``（預算無法計算）是結構問題，不在清單內。"""

REPAIR_COOLDOWN = 1
"""「有冷卻就不適用」的互斥規則（例：沒有冷卻的大範圍）補的冷卻回合（預算折抵照
``skill_budget.yaml``）。"""
EXCLUSION_PREFIX = "exclusion."
FOLLOWUP_PREFIX = "followup."
REPAIR_TUNES = 4
"""修補時最多重調幾次（每次換一條亂數串流，核心優先與全部旋鈕交替）。"""
_PROBE_ID = "skill_llm_probe"
_PROBE_NAME = "試算"
_CORE_FIRST = frozenset({"skeleton.core_share", "skeleton.secondary_share"})
WEAK = "budget.weak"
SECONDARY_SHARE = "skeleton.secondary_share"
NESTED_KNOB_KEYS = ("then", "on_kill")
"""過弱補強（4-L10b）時也當旋鈕調的巢狀效果欄位：消耗狀態後的追加效果、擊殺時效果（都是施放者
這一方得利的效果；失手反噬、賭注的輸方不調）。"""


def cooldown_repairs(library: ContentLibrary) -> dict[str, int]:
    """「補冷卻即可」的互斥規則代碼 → 要補到的冷卻回合（由 ``skill_exclusions.yaml`` 推導，唯一
    來源）：``when: {has_cooldown: false}`` 的規則補 :data:`REPAIR_COOLDOWN`（有冷卻就不適用）；
    ``require`` 有 ``min_cooldown``（或 ``has_cooldown: true``）的規則補到該值。規則若還要求別的
    （例：形狀），補冷卻後仍可能違反，剩下的錯誤照常回給 LLM。"""
    out: dict[str, int] = {}
    for rule in library.exclusions.rules:
        need = 0
        if rule.when is not None and rule.when.has_cooldown is False:
            need = REPAIR_COOLDOWN
        if rule.require is not None:
            if rule.require.min_cooldown is not None:
                need = max(need, rule.require.min_cooldown)
            elif rule.require.has_cooldown:
                need = max(need, REPAIR_COOLDOWN)
        if need:
            out[EXCLUSION_PREFIX + rule.id] = need
    return out


REVIVE_COST = "cap.revive_cost"
RULE_REWRITE_COST = "cap.rule_rewrite_cost"


def cap_cooldown(library: ContentLibrary, code: str, data: Mapping[str, Any]) -> int:
    """「每場一次或冷卻至少 N 回合」的上限規則（復活、改寫規則型原語）要補到的冷卻；不是這兩條規則
    時為 0。門檻取自 ``skill_budget.yaml``：``rule_rewrite_min_cooldown``，改寫規則型且花源力時用
    ``rule_rewrite_min_cooldown_with_source``（與驗證器同一個來源）。引擎選「補冷卻」而不是「每場
    一次」：和 ``exclusion.*`` 的修法一致，也不會多出每場一次的大額折抵。"""
    budget = library.budget
    if code == RULE_REWRITE_COST:
        cost = data.get("cost")
        paid = isinstance(cost, Mapping) and cost.get("source") is not None
        return (
            budget.rule_rewrite_min_cooldown_with_source
            if paid
            else budget.rule_rewrite_min_cooldown
        )
    if code == REVIVE_COST:
        return budget.rule_rewrite_min_cooldown
    return 0


def segment_code(code: str) -> str:
    """去掉複合技能第二段的前綴（``followup.``，驗證器對第二段的規則代碼；Phase 4-L8）：第二段的
    預算、占比與「補冷卻即可」的互斥規則和第一段一樣由引擎修（冷卻是整招共用的）。"""
    return code.removeprefix(FOLLOWUP_PREFIX)


def is_repairable(code: str, library: ContentLibrary) -> bool:
    """``code`` 是否可由引擎修（:data:`REPAIRABLE_CODES` 或 :func:`cooldown_repairs`；第二段的
    ``followup.`` 代碼同樣適用）。"""
    code = segment_code(code)
    if code.startswith(EXCLUSION_PREFIX):
        return code in cooldown_repairs(library)
    return any(fnmatchcase(code, pattern) for pattern in REPAIRABLE_CODES)


def repairable_codes(errors: Iterable[ProposalError], library: ContentLibrary) -> tuple[str, ...]:
    """錯誤中規則層、可由引擎修的代碼（排序、去重）。"""
    found = {e.code for e in errors if e.stage == "rules" and is_repairable(e.code, library)}
    return tuple(sorted(found))


def repairable_errors(errors: Iterable[ProposalError], library: ContentLibrary) -> bool:
    """錯誤全部是規則層、且全部可由引擎修（空的不算）。"""
    items = list(errors)
    return bool(items) and all(e.stage == "rules" and is_repairable(e.code, library) for e in items)


# ---------------------------------------------------------------------------
# 旋鈕
# ---------------------------------------------------------------------------


def _segment_knobs(
    library: ContentLibrary,
    skeleton_id: str,
    raws: list[dict[str, Any]],
    effects: Iterable[EffectSpec],
    *,
    category: str,
    offset: int,
    core_only: bool,
) -> list[Knob] | None:
    """一段（技能本身或複合技能第二段）的旋鈕；核心依該段的骨架判斷，索引從 ``offset`` 起算。"""
    skeleton = library.skeletons.get(skeleton_id)
    if skeleton is None:
        return None
    structure = library.composer.structure
    knobs: list[Knob] = []
    for index, (raw, effect) in enumerate(zip(raws, effects, strict=True)):
        core = is_core_effect(library, skeleton, effect)
        if core_only and not core:
            continue
        weight = structure.knob_weight_core if core else structure.knob_weight_other
        for name, values, knob_weight in effect_knobs(
            library, raw, category=category, weight=weight
        ):
            knobs.append(Knob(offset + index, name, values, knob_weight))
    return knobs


def _knobs(library: ContentLibrary, data: dict[str, Any], *, core_only: bool) -> list[Knob] | None:
    """頂層效果與複合技能第二段效果（Phase 4-L8；索引接在頂層效果之後）的旋鈕；結構不合法
    （無法判斷核心）時為 ``None``。"""
    try:
        skill = SkillDef.model_validate({"name_zh": _PROBE_NAME, **data, "id": _PROBE_ID})
    except ValidationError:
        return None
    category = str(data.get("category", "spell"))
    knobs = _segment_knobs(
        library,
        str(data.get("skeleton")),
        data["effects"],
        skill.effects,
        category=category,
        offset=0,
        core_only=core_only,
    )
    if knobs is None or skill.followup is None:
        return knobs
    second = _segment_knobs(
        library,
        skill.followup.skeleton,
        data["followup"]["effects"],
        skill.followup.effects,
        category=category,
        offset=len(data["effects"]),
        core_only=core_only,
    )
    return None if second is None else knobs + second


def _nested_of(effects: Iterable[Any]) -> Iterator[dict[str, Any]]:
    """``effects`` 裡（遞迴）:data:`NESTED_KNOB_KEYS` 底下的效果字典（就是資料裡的同一批物件）。"""
    for effect in effects:
        if not isinstance(effect, dict):
            continue
        for key in NESTED_KNOB_KEYS:
            items = effect.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        yield item
                yield from _nested_of(items)


def _nested_knobs(
    library: ContentLibrary, nested: list[dict[str, Any]], *, category: str, offset: int
) -> list[Knob]:
    weight = library.composer.structure.knob_weight_other
    return [
        Knob(offset + index, name, values, knob_weight)
        for index, raw in enumerate(nested)
        for name, values, knob_weight in effect_knobs(
            library, raw, category=category, weight=weight
        )
    ]


def _tune_once(library: ContentLibrary, data: dict[str, Any], rng: Rng, *, core_only: bool) -> bool:
    knobs = _knobs(library, data, core_only=core_only)
    if knobs is None:
        return False
    extra = _extra_of(data)  # 與 base 裡的是同一批物件
    return tune(rng, library, _base_of(data), data["effects"], knobs, extra=extra)


def _base_of(data: dict[str, Any]) -> dict[str, Any]:
    base = {k: v for k, v in data.items() if k != "effects"}
    base["id"] = _PROBE_ID
    base.setdefault("name_zh", _PROBE_NAME)
    return base


def _with_step(library: ContentLibrary, data: dict[str, Any], step: CostStep) -> dict[str, Any]:
    """``data`` 套上費用階梯的一階（各欄位取較大者）；``data`` 本身不變。"""
    out = dict(data)
    cost = dict(out.get("cost") or {})
    if step.ap is not None:
        out["ap_cost"] = max(int(out.get("ap_cost") or 0), step.ap)
    if step.cooldown is not None:
        cost["cooldown"] = max(int(cost.get("cooldown") or 0), step.cooldown)
    if step.mana is not None:
        category = str(out.get("category"))
        resource = library.budget.resource_of(category)  # type: ignore[arg-type]
        amount = step.mana if resource == "mana" else library.budget.stamina_for_mana(step.mana)
        cost[resource] = max(int(cost.get(resource) or 0), amount)
    out["cost"] = cost
    return out


def raise_costs(library: ContentLibrary, data: dict[str, Any]) -> dict[str, Any]:
    """費用旋鈕（Phase 4-L8b）：旋鈕全在最弱時預算比例仍高於上限，就依 ``skill_composer.yaml``
    ``llm_cost.steps`` 由輕到重往上試，取第一個讓比例回到上限以內的階（回傳套用後的新資料）。
    沒有超出、不是主動技能、沒有階能解決（維持原狀交給驗證器報錯）、結構不合法時原樣回傳。"""
    rules = library.composer.llm_cost
    if data.get("kind") != "active" or not rules.steps or not data.get("effects"):
        return data
    high = tuning_bounds(library)[1]
    for step in (None, *rules.steps):
        trial = data if step is None else _with_step(library, data, step)
        knobs = _knobs(library, trial, core_only=False)
        if knobs is None:
            return data
        extra = _extra_of(trial)
        ratio = base_ratio(library, _base_of(trial), trial["effects"], knobs, extra=extra)
        if ratio is None:
            return data
        if ratio <= high:
            return trial
    return data


def _extra_of(data: dict[str, Any]) -> list[dict[str, Any]]:
    follow = data.get("followup")
    return follow["effects"] if isinstance(follow, dict) else []


def _tune(
    library: ContentLibrary, data: dict[str, Any], seed: int, repairs: frozenset[str]
) -> None:
    """就地調整 ``data["effects"]`` 的旋鈕。沒有修補時調一次；有修補時換串流重調到成功為止。"""
    root = Rng(seed).fork("proposal.budget")
    if not repairs:
        _tune_once(library, data, root, core_only=False)
        return
    core_first = bool(_CORE_FIRST & repairs)
    for attempt in range(REPAIR_TUNES):
        core_only = (attempt % 2 == 0) == core_first
        if _tune_once(library, data, root.fork(f"repair.{attempt}"), core_only=core_only):
            return
    if SECONDARY_SHARE in repairs and _floor_secondary(library, data):
        # 4-L10b B3：最後一次重調可能把附帶傷害調高了——降回最低值，只調核心
        _tune_once(library, data, root.fork("repair.floor"), core_only=True)


def _limited_types(library: ContentLibrary, data: dict[str, Any]) -> list[frozenset[str]]:
    """每個旋鈕目標（頂層效果、第二段效果）所屬骨架有占比上限的原語。"""
    out: list[frozenset[str]] = []
    segments = [(data.get("skeleton"), data.get("effects") or [])]
    follow = data.get("followup")
    if isinstance(follow, dict):
        segments.append((follow.get("skeleton"), follow.get("effects") or []))
    for skeleton_id, effects in segments:
        skeleton = library.skeletons.get(str(skeleton_id))
        limited = frozenset(skeleton.secondary.max_share_permille) if skeleton else frozenset()
        out += [limited] * len(effects)
    return out


def _floor_secondary(library: ContentLibrary, data: dict[str, Any]) -> bool:
    """附帶效果中有占比上限的原語（骨架 ``secondary.max_share_permille``，例如控制骨架的傷害）的旋鈕
    全部降到最低值（就地修改）；有任何旋鈕被降回 ``True``。"""
    knobs = _knobs(library, data, core_only=False)
    core = _knobs(library, data, core_only=True)
    if knobs is None or core is None:
        return False
    core_keys = {(k.index, k.field) for k in core}
    targets = [*data["effects"], *_extra_of(data)]
    limited = _limited_types(library, data)
    lowered = False
    for knob in knobs:
        effect = targets[knob.index]
        if (knob.index, knob.field) in core_keys or str(effect.get("type")) not in limited[
            knob.index
        ]:
            continue
        if effect.get(knob.field) != knob.values[0]:
            effect[knob.field] = knob.values[0]
            lowered = True
    return lowered


def _window_ok(library: ContentLibrary, data: dict[str, Any]) -> bool | None:
    """``data`` 的預算比例是否落在驗證器的窗（``min_ratio``～``max_ratio``）且骨架占比合格；結構不
    合法時為 ``None``。"""
    try:
        skill = SkillDef.model_validate(_base_of(data) | {"effects": data["effects"]})
        report = skill_budget(skill, library)
    except (ValidationError, BudgetError):
        return None
    return report.ok and not share_violations(skill, library, report)


def _with_weak_step(
    library: ContentLibrary, data: dict[str, Any], step: CostStep
) -> dict[str, Any]:
    """過弱階梯的一階（``data`` 本身不變，回傳深拷貝）：AP 取較小者，冷卻與法力取較大者。"""
    out = deepcopy(data)
    if step.ap is not None:
        out["ap_cost"] = min(int(out.get("ap_cost") or step.ap), step.ap)
    return _with_step(library, out, step.model_copy(update={"ap": None}))


def lift_weak(library: ContentLibrary, data: dict[str, Any], seed: int) -> dict[str, Any]:
    """過弱補強（Phase 4-L10b，4-L9 建議 B1）：一般旋鈕調完仍不在驗證器的窗內時，

    1. 連同巢狀效果（:data:`NESTED_KNOB_KEYS`）的數值一起重調；
    2. 仍不行（主動技能）就依 ``llm_cost.weak_steps`` 由輕到重：降 AP（必要時補冷卻／法力把過頭的
       部分拉回），每一階都重調旋鈕；

    取第一個落進窗且占比合格的結果。全部不行時原樣回傳（交給驗證器照舊報 ``budget.weak``）。
    不降預算下限；確定性：同一份資料＋同一個 ``seed`` 必得相同結果。"""
    if _window_ok(library, data) is not False:
        return data
    steps: tuple[CostStep | None, ...] = (None,)
    if data.get("kind") == "active" and data.get("ap_cost") is not None:
        steps += library.composer.llm_cost.weak_steps
    low = Fraction(library.budget.min_ratio_permille, 1000)
    root = Rng(seed).fork("proposal.weak")
    category = str(data.get("category", "spell"))
    for attempt, step in enumerate(steps):
        trial = deepcopy(data) if step is None else _with_weak_step(library, data, step)
        knobs = _knobs(library, trial, core_only=False)
        if knobs is None:
            return data
        nested = list(_nested_of([*trial["effects"], *_extra_of(trial)]))
        extra = _extra_of(trial)
        offset = len(trial["effects"]) + len(extra)
        knobs += _nested_knobs(library, nested, category=category, offset=offset)
        rng = root.fork(f"weak.{attempt}")
        tune(
            rng,
            library,
            _base_of(trial),
            trial["effects"],
            knobs,
            extra=[*extra, *nested],
            min_ratio=low,
        )
        if _window_ok(library, trial):
            return trial
    return data


def budget_filler(
    library: ContentLibrary, *, seed: int, repairs: Iterable[str] = ()
) -> NumberFiller:
    """預算補值器：必填最小值 → 旋鈕 → ``tune``。``repairs`` 是要修的驗證代碼（見
    :data:`REPAIRABLE_CODES`）；調不進區間時照樣回傳（交給驗證器報錯）。"""
    minimal = minimal_filler(library)
    wanted = frozenset(segment_code(c) for c in repairs)
    needs = cooldown_repairs(library)
    cooldown = max((needs[c] for c in wanted if c in needs), default=0)

    def fill(data: dict[str, Any]) -> dict[str, Any]:
        out = minimal(data)
        if not isinstance(out.get("effects"), list) or not out["effects"]:
            return out
        need = max([cooldown, *(cap_cooldown(library, c, out) for c in wanted)])
        if need:
            cost = dict(out.get("cost") or {})
            cost["cooldown"] = max(int(cost.get("cooldown") or 0), need)
            out["cost"] = cost
        out = raise_costs(library, out)
        _tune(library, out, seed, wanted)
        if WEAK in wanted:
            out = lift_weak(library, out, seed)
        return out

    return fill


# ---------------------------------------------------------------------------
# 驗證＋修補
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RepairedEvaluation:
    """:func:`evaluate_with_repair` 的結果。``result``：最終結果（有修補時是修補後的結果：剩下的
    錯誤才回給 LLM，Phase 4-L5b）；``repaired``：引擎修好的代碼（修補前有、修補後沒有；排序）。"""

    result: ProposalResult
    repaired: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.result.ok


def evaluate_with_repair(
    raw: str | Mapping[str, Any],
    models: ProposalModels,
    library: ContentLibrary,
    ctx: ProposalContext,
    *,
    seed: int,
) -> RepairedEvaluation:
    """``evaluate_proposal``（數值由 :func:`budget_filler` 補）；錯誤中有可修的代碼時，
    **先修可修的**（一次），再回報修補後剩下的錯誤（Phase 4-L5b，4-L5 待決 #5）。"""
    first = evaluate_proposal(raw, models, library, ctx, fill=budget_filler(library, seed=seed))
    codes = () if first.ok else repairable_codes(first.errors, library)
    if not codes:
        return RepairedEvaluation(first)
    fill = budget_filler(library, seed=seed, repairs=codes)
    second = evaluate_proposal(raw, models, library, ctx, fill=fill)
    left = {e.code for e in second.errors}
    if SECONDARY_SHARE in left:
        second = _explain_secondary(raw, library, second)
    return RepairedEvaluation(second, tuple(c for c in codes if c not in left))


def _raw_mapping(raw: str | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, Mapping) else {}


def _explain_secondary(
    raw: str | Mapping[str, Any], library: ContentLibrary, result: ProposalResult
) -> ProposalResult:
    """修補後仍有 ``skeleton.secondary_share``（4-L10b B3）：引擎已把附帶效果降到最低值仍超標，
    改寫成明確的建議——移除那個附帶效果（路徑指到它），讓模型重試時知道要改哪裡。"""
    data = _raw_mapping(raw)
    skeleton = library.skeletons.get(str(data.get("skeleton")))
    effects = data.get("effects")
    if skeleton is None or not isinstance(effects, list):
        return result
    limited = skeleton.secondary.max_share_permille
    errors = tuple(
        _secondary_advice(e, effects, limited, library) if e.code == SECONDARY_SHARE else e
        for e in result.errors
    )
    return replace(result, errors=errors)


def _secondary_advice(
    error: ProposalError,
    effects: list[Any],
    limited: Mapping[str, int],
    library: ContentLibrary,
) -> ProposalError:
    for index, effect in enumerate(effects):
        kind = str(effect.get("type")) if isinstance(effect, dict) else ""
        if kind not in limited or f"：{kind} 占" not in error.message:
            continue
        name = library.ruleset.primitives.by_id()[kind].name_zh
        advice = (
            f"{error.message}。引擎已把這個{name}（{kind}）降到最低值仍超過上限："
            f"請移除 effects[{index}] 的 {kind}，只保留骨架的核心效果"
            f"（或改用允許 {kind} 當主軸的骨架）"
        )
        return replace(error, path=f"effects[{index}]", message=advice)
    return error
