"""被動題目的關鍵字寫法：放不進被動預算的「產生效果」不列（Phase LB-2b，玩法 PM 4.1.17 第 1 點）。

LB-1、LB-2 的 Q12（1 階史詩被動、關鍵字高處）所有模型都退回：關鍵字的 ``ways`` 先列 ``makes``
（``raise_terrain``、``lower_terrain``），模型照著把升降地形當被動效果，而它固定 7 點，單這一個
效果就超過被動的可用預算。規則與數值都不改；這裡只決定 prompt 列哪些寫法。

判定（:func:`unfit_effect_rules`，照預算實算、不寫死清單）：對關鍵字每一條專屬「效果」規則，
組一個最省的被動技能去算預算（:func:`trpg.skillgen.budget.skill_budget`）：

- 觸發時機取子集裡係數最高的（``max_per_round`` 1、``every_n_hits`` 取係數最高的 ``n``）；
- 效果本身是骨架核心原語時單獨一個效果，否則配一個最省的核心效果（子集裡骨架核心原語各試一次）；
- 數值一律用 :func:`~trpg.skillgen.proposal_numbers.minimal_filler` 的最小值，``affects: self``；
- 不加條件（技能或效果的條件倍率可以再壓低點數，但那是另一種寫法，這裡不假設）。

所有組合都超過 ``max_ratio`` 才算「放不進」；組不出合法技能（缺參數、驗證不過、算不出點數）時
**照列**（保守：不確定就不藏）。純函式、確定性（只依子集與內容庫，順序照 YAML）。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordRule
from trpg.content.skills import SkillDef, SkillRarity
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.proposal_numbers import minimal_filler

__all__ = ["PASSIVE_KIND", "best_trigger", "rule_key", "unfit_effect_rules"]

PASSIVE_KIND = "passive"
_PERMILLE = 1000
_PROBE_ID = "skill_passive_probe"
_EFFECT_PARAM_KEYS = ("status", "surface", "element", "object", "stack", "tag")
"""規則參數中直接對應到效果欄位的（其他參數如 ``unit``、``infusion`` 的規則本來就不列）。"""


def best_trigger(library: ContentLibrary, triggers: Iterable[str]) -> dict[str, Any] | None:
    """子集裡預算係數最高的觸發（``trigger`` 欄位的字典；同係數取 ID 排序第一個）；
    沒有時 ``None``。"""
    table = {t.id: t for t in library.ruleset.skill_triggers.triggers}
    best: tuple[int, str, dict[str, Any]] | None = None
    for trigger_id in sorted(triggers):
        found = table.get(trigger_id)
        if found is None or found.params.keys() - {"n"}:
            continue  # 需要 tag／status／surface 的時機另有參數，最省的組合不用它
        options: list[int | None] = (
            [*sorted(found.budget_by_n_permille)] if found.budget_by_n_permille else [None]
        )
        for n in options:
            coefficient = found.coefficient_permille(n)
            spec: dict[str, Any] = {"event": trigger_id, "target": "self", "max_per_round": 1}
            if n is not None:
                spec["n"] = n
            if best is None or coefficient > best[0]:
                best = (coefficient, trigger_id, spec)
    return None if best is None else best[2]


def rule_key(rule: KeywordRule) -> str:
    """規則的比對鍵（來源種類、ID 與排序後的參數；同一條寫法同一把鍵）。"""
    params = "，".join(f"{k}＝{v}" for k, v in sorted(rule.params().items()))
    return f"{rule.source}:{rule.source_id}（{params}）"


def _effect(rule: KeywordRule) -> dict[str, Any]:
    params = rule.params()
    out: dict[str, Any] = {"type": rule.source_id, "affects": "self"}
    out.update({k: params[k] for k in _EFFECT_PARAM_KEYS if k in params})
    return out


def _probe(
    library: ContentLibrary,
    effects: list[dict[str, Any]],
    trigger: Mapping[str, Any],
    *,
    tier: int,
    rarity: SkillRarity,
) -> Fraction | None:
    """這組效果做成最省的被動技能時的預算比例（total ÷ 可用預算）；組不出合法技能時 ``None``。"""
    data: dict[str, Any] = {
        "id": _PROBE_ID,
        "schema_version": 1,
        "name_zh": "預算探測",
        "tier": tier,
        "rank": 1,
        "rarity": rarity,
        "kind": PASSIVE_KIND,
        "skeleton": PASSIVE_KIND,
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": "int",
        "shape": {"type": "self"},
        "effects": effects,
        "trigger": dict(trigger),
        "tags": [PASSIVE_KIND],
        "narrative": {"concept": "預算探測", "cast_flavor": "預算探測"},
        "provenance": {"origin": "builtin"},
    }
    try:
        skill = SkillDef.model_validate(minimal_filler(library)(data))
        report = skill_budget(skill, library)
    except (ValidationError, BudgetError, ValueError, KeyError):
        return None
    return report.ratio


def unfit_effect_rules(
    library: ContentLibrary,
    rules: Iterable[KeywordRule],
    *,
    tier: int,
    rarity: SkillRarity,
    primitives: Iterable[str],
    triggers: Iterable[str],
    skeletons: Iterable[str] = (PASSIVE_KIND,),
) -> frozenset[str]:
    """``rules`` 中做成被動技能一定超預算的「效果」規則的 :func:`rule_key`（見模組說明）。"""
    allowed = set(primitives)
    trigger = best_trigger(library, triggers)
    if trigger is None:
        return frozenset()
    cores = [
        p
        for s in sorted(set(skeletons))
        if (skeleton := library.skeletons.get(s)) is not None
        for p in skeleton.core.primitives
        if p in allowed
    ]
    limit = Fraction(library.budget.max_ratio_permille, _PERMILLE)
    unfit: set[str] = set()
    for rule in rules:
        if rule.source != "effect" or rule.source_id not in allowed:
            continue
        effect = _effect(rule)
        groups = [[effect]] if rule.source_id in cores else []
        groups += [[{"type": c, "affects": "self"}, effect] for c in cores if c != rule.source_id]
        ratios = [
            r
            for group in groups
            if (r := _probe(library, group, trigger, tier=tier, rarity=rarity)) is not None
        ]
        if ratios and min(ratios) > limit:
            unfit.add(rule_key(rule))
    return frozenset(unfit)
