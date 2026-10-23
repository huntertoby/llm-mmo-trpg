"""內建技能的預算範圍已知例外（Phase 3-49，玩法決定 #53）。

射程係數（06 6.5）上線後，下列內建技能的 total ÷ 可用預算掉到 70～100% 之外。依規格**不改任何技能
數值**，先標記為已知，交玩法 PM 決定怎麼調（見 ``docs/phases/Phase3-49報告.md``）；調整完成後，
把對應的技能從這份清單移除，測試會自動恢復嚴格檢查。重算報表：``scripts/range_budget_report.py``。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.skillgen.draft_check import DraftCheck
from trpg.skillgen.validate import Violation, validate_skill

__all__ = ["RANGE_BUDGET_EXCEPTIONS", "legal_or_known", "shipped_violations"]

RANGE_BUDGET_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "skill_arc_follow_up",  # 射程 5：98.9% -> 103.8%（超出）
        "skill_armor_break_combo",  # 射程 1：74.5% -> 66.3%（過弱）
        "skill_deep_freeze",  # 射程 5：97.9% -> 102.8%（超出）
        "skill_flare_sight",  # 射程 6：97.7% -> 107.4%（超出）
        "skill_quake_topple",  # 射程 2：76.9% -> 69.2%（過弱）
    }
)
"""交玩法 PM 重新調整的內建技能 ID。"""

_BUDGET_RULES = frozenset({"budget.over", "budget.weak"})


def legal_or_known(skill_id: str, check: DraftCheck) -> bool:
    """工坊檢查合格；或內建技能是已知例外，且問題只有預算範圍（over／weak）。"""
    if check.legal:
        return True
    return skill_id in RANGE_BUDGET_EXCEPTIONS and all(
        p.rule in _BUDGET_RULES for p in check.problems
    )


def shipped_violations(skill_id: str, library: ContentLibrary) -> list[Violation]:
    """內建技能的驗證結果；已知例外的技能不計預算範圍（over／weak）的違規，其他違規照舊。"""
    found = validate_skill(library.skills[skill_id], library)
    if skill_id not in RANGE_BUDGET_EXCEPTIONS:
        return found
    return [v for v in found if v.rule not in _BUDGET_RULES]
