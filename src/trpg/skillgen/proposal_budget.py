"""LLM 提議的數值補齊與「引擎可修的錯誤」（Phase 4-L5；使用者決定 #3：數值一律由預算器補）。

- :func:`budget_filler`：取代 :func:`~trpg.skillgen.proposal_numbers.minimal_filler` 在正式流程
  的角色。先補必填的最小值（沿用 ``minimal_filler``），再依提議的效果建立強度旋鈕（與隨機組合器
  共用 :func:`~trpg.skillgen.composer_parts.effect_knobs`），以
  :func:`~trpg.skillgen.composer_tuning.tune` 把預算比例調進 ``[low, high]``。LLM 選的形狀參數
  （``range`` 等）不調；確定性：同一份提議＋同一個 ``seed`` 必得相同數值。
- :data:`REPAIRABLE_CODES` 與 :func:`cooldown_repairs`：補數值後仍出現、但屬於「數值問題」的驗證
  代碼——由引擎修一次再驗，不回給 LLM（:func:`evaluate_with_repair`）。Phase 4-L5b 起「先修可修的、
  再回報其餘」：錯誤裡只要有可修的代碼就先修，修補後剩下的錯誤才回給 LLM。

旋鈕只建在頂層效果上（與組合器相同）；巢狀效果（``then``、``win``／``lose``、``effects`` 等）的
數值維持最小值。AP 與冷卻不是旋鈕（4-L3 待決 #2，留給 4-L8）：AP 補 2、沒有冷卻；唯一的例外是
修「補冷卻即可」的互斥規則（``exclusion.*``，由 ``skill_exclusions.yaml`` 推導）時補到規則要求的
冷卻。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.composer_parts import Knob, effect_knobs
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalError,
    ProposalModels,
    ProposalResult,
    evaluate_proposal,
)
from trpg.skillgen.proposal_numbers import NumberFiller, minimal_filler
from trpg.skillgen.validate import is_core_effect

__all__ = [
    "REPAIRABLE_CODES",
    "RepairedEvaluation",
    "budget_filler",
    "cooldown_repairs",
    "evaluate_with_repair",
    "is_repairable",
    "repairable_codes",
    "repairable_errors",
]

REPAIRABLE_CODES: tuple[str, ...] = (
    "budget.over",
    "budget.weak",
    "skeleton.core_share",
    "skeleton.secondary_share",
)
"""引擎可修的驗證代碼（``fnmatch`` 樣式）。``budget.over``／``budget.weak``：換一條亂數串流重調
旋鈕（核心優先、全部旋鈕交替）；``skeleton.core_share``、``skeleton.secondary_share``：先只調核心效果的旋鈕（附帶效果停在最小值）。
互斥規則（``exclusion.*``）中「補冷卻即可」的由 :func:`cooldown_repairs` 從 YAML 推導。
``budget.unavailable``（預算無法計算）是結構問題，不在清單內。"""

REPAIR_COOLDOWN = 1
"""「有冷卻就不適用」的互斥規則（例：沒有冷卻的大範圍）補的冷卻回合（預算折抵照
``skill_budget.yaml``）。"""
EXCLUSION_PREFIX = "exclusion."
REPAIR_TUNES = 4
"""修補時最多重調幾次（每次換一條亂數串流，核心優先與全部旋鈕交替）。"""
_PROBE_ID = "skill_llm_probe"
_PROBE_NAME = "試算"
_CORE_FIRST = frozenset({"skeleton.core_share", "skeleton.secondary_share"})


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


def is_repairable(code: str, library: ContentLibrary) -> bool:
    """``code`` 是否可由引擎修（:data:`REPAIRABLE_CODES` 或 :func:`cooldown_repairs`）。"""
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


def _knobs(library: ContentLibrary, data: dict[str, Any], *, core_only: bool) -> list[Knob] | None:
    """頂層效果的旋鈕；結構不合法（無法判斷核心）時為 ``None``。"""
    skeleton = library.skeletons.get(str(data.get("skeleton")))
    if skeleton is None:
        return None
    try:
        skill = SkillDef.model_validate({"name_zh": _PROBE_NAME, **data, "id": _PROBE_ID})
    except ValidationError:
        return None
    structure = library.composer.structure
    category = str(data.get("category", "spell"))
    knobs: list[Knob] = []
    for index, (raw, effect) in enumerate(zip(data["effects"], skill.effects, strict=True)):
        core = is_core_effect(library, skeleton, effect)
        if core_only and not core:
            continue
        weight = structure.knob_weight_core if core else structure.knob_weight_other
        for name, values, knob_weight in effect_knobs(
            library, raw, category=category, weight=weight
        ):
            knobs.append(Knob(index, name, values, knob_weight))
    return knobs


def _tune_once(library: ContentLibrary, data: dict[str, Any], rng: Rng, *, core_only: bool) -> bool:
    knobs = _knobs(library, data, core_only=core_only)
    if knobs is None:
        return False
    base = {k: v for k, v in data.items() if k != "effects"}
    base["id"] = _PROBE_ID
    base.setdefault("name_zh", _PROBE_NAME)
    return tune(rng, library, base, data["effects"], knobs)


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


def budget_filler(
    library: ContentLibrary, *, seed: int, repairs: Iterable[str] = ()
) -> NumberFiller:
    """預算補值器：必填最小值 → 旋鈕 → ``tune``。``repairs`` 是要修的驗證代碼（見
    :data:`REPAIRABLE_CODES`）；調不進區間時照樣回傳（交給驗證器報錯）。"""
    minimal = minimal_filler(library)
    wanted = frozenset(repairs)
    needs = cooldown_repairs(library)
    cooldown = max((needs[c] for c in wanted if c in needs), default=0)

    def fill(data: dict[str, Any]) -> dict[str, Any]:
        out = minimal(data)
        if not isinstance(out.get("effects"), list) or not out["effects"]:
            return out
        if cooldown:
            cost = dict(out.get("cost") or {})
            cost["cooldown"] = max(int(cost.get("cooldown") or 0), cooldown)
            out["cost"] = cost
        _tune(library, out, seed, wanted)
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
    return RepairedEvaluation(second, tuple(c for c in codes if c not in left))
