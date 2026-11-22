"""內容庫全部技能的預算與結構檢查（``trpg content check`` 與數值工坊共用）。

原本在 ``trpg.cli.budget``（NW-1a 搬來：``trpg.api`` 不能匯入 ``trpg.cli``）；``trpg.cli.budget``
照舊 re-export，行為不變。"""

from __future__ import annotations

from trpg.content.equipment import ActionAffix
from trpg.content.library import ContentLibrary
from trpg.shared.fmt import ratio_pct
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.validate import GEAR_TAG, Violation, validate_skill

__all__ = ["BUDGET_RANGE_RULES", "gear_grant_violations", "library_violations"]

BUDGET_RANGE_RULES = frozenset({"budget.over", "budget.weak"})


def library_violations(library: ContentLibrary) -> list[Violation]:
    """全部技能的違規（依技能 ID 排序），再加裝備授予技能的預算窗（:func:`gear_grant_violations`）。"""
    out: list[Violation] = []
    for skill_id in sorted(library.skills):
        found = validate_skill(library.skills[skill_id], library)
        if skill_id in library.budget.known_budget_exceptions:  # 3-49 已知例外：不計預算範圍
            found = [v for v in found if v.rule not in BUDGET_RANGE_RULES]
        out += found
    return out + gear_grant_violations(library)


def gear_grant_violations(library: ContentLibrary) -> list[Violation]:
    """裝備授予的技能（第 9 類詞條，E1，08 8.28）照 ``gear_skill_tier`` 那一階的預算窗檢查
    （玩法交接 4.1.36 待決答覆 1），不看技能本身標的階級；依技能 ID 排序、同一招只列一次。

    超出上限就是錯；過弱照技能本身的規則（帶 ``gear`` 標籤的不算過弱，同 :func:`validate_skill`）。
    技能本身的階級等於這一階時，結果和 :func:`validate_skill` 的預算檢查相同，所以不重複列。
    已知例外（``known_budget_exceptions``）不列。"""
    tier = library.budget.gear_skill_tier
    granted = sorted(
        {a.skill for a in library.affixes.values() if isinstance(a, ActionAffix)}
        & set(library.skills)
    )
    out: list[Violation] = []
    for skill_id in granted:
        skill = library.skills[skill_id]
        if skill.tier == tier or skill_id in library.budget.known_budget_exceptions:
            continue
        try:
            report = skill_budget(skill.model_copy(update={"tier": tier}), library)
        except BudgetError:
            continue  # 算不出來的照 validate_skill 的 budget.unavailable
        weak = report.too_weak and GEAR_TAG not in skill.tags
        if report.over_budget or weak:
            limit = report.max_ratio if report.over_budget else report.min_ratio
            word = "超出" if report.over_budget else "過弱"
            out.append(
                Violation(
                    skill_id,
                    "budget.gear_tier",
                    f"裝備授予的技能照 {tier} 階的預算窗{word}：{ratio_pct(report.ratio)}"
                    f"（{'上限' if report.over_budget else '下限'} {ratio_pct(limit)}）",
                )
            )
    return out
