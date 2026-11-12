"""內容庫全部技能的預算與結構檢查（``trpg content check`` 與數值工坊共用）。

原本在 ``trpg.cli.budget``（NW-1a 搬來：``trpg.api`` 不能匯入 ``trpg.cli``）；``trpg.cli.budget``
照舊 re-export，行為不變。"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.skillgen.validate import Violation, validate_skill

__all__ = ["BUDGET_RANGE_RULES", "library_violations"]

BUDGET_RANGE_RULES = frozenset({"budget.over", "budget.weak"})


def library_violations(library: ContentLibrary) -> list[Violation]:
    """全部技能的違規（依技能 ID 排序）。"""
    out: list[Violation] = []
    for skill_id in sorted(library.skills):
        found = validate_skill(library.skills[skill_id], library)
        if skill_id in library.budget.known_budget_exceptions:  # 3-49 已知例外：不計預算範圍
            found = [v for v in found if v.rule not in BUDGET_RANGE_RULES]
        out += found
    return out
