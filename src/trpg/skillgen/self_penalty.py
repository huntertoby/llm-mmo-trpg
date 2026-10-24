"""LLM 提議的「自己付的代價」（Phase 3-50，06 6.5 共通規則 7）：只能從允許的代價中挑一個。

提議格式沒有 ``cost``（數值由引擎補），所以這裡多一個可省略的欄位 ``cost_penalty``：值是
``allowance.self_status.allowed`` 裡的一個狀態 ID（依稀有度篩選，和驗證器的 ``rarity.status`` 同一
規則），或 ``overdraft``（透支）。引擎把它換成 ``cost.self_status`` 或 ``cost.overdraft``；持續
時間不給 LLM 選（固定狀態用規則的固定值，其他取最短的 2）。範圍與上限（沉默限法術技、一招最多一個）
由驗證器檢查。
"""

from __future__ import annotations

from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillRarity, rarity_rank

__all__ = ["OVERDRAFT_CHOICE", "penalty_choices", "penalty_cost", "penalty_of_cost"]

OVERDRAFT_CHOICE = "overdraft"
_MIN_DURATION = 2


def penalty_choices(library: ContentLibrary, rarity: SkillRarity | None = None) -> tuple[str, ...]:
    """提議可以挑的代價（排序）：稀有度夠的自身狀態，加上透支。"""
    statuses = library.ruleset.statuses.by_id()
    rule = library.budget.allowance.self_status
    found = sorted(
        s
        for s in rule.allowed
        if s in statuses
        and statuses[s].budget_points is not None
        and (rarity is None or rarity_rank(statuses[s].min_rarity) <= rarity_rank(rarity))
    )
    return (*found, OVERDRAFT_CHOICE)


def penalty_cost(library: ContentLibrary | None, choice: str) -> dict[str, Any]:
    """代價選擇 → ``cost`` 裡要加的欄位。"""
    if choice == OVERDRAFT_CHOICE:
        return {"overdraft": 1}
    fixed = {} if library is None else library.budget.allowance.self_status.fixed_duration
    return {"self_status": {"status": choice, "duration": fixed.get(choice, _MIN_DURATION)}}


def penalty_of_cost(cost: dict[str, Any]) -> str | None:
    """``cost`` 字典 → 代價選擇（沒有時為 ``None``）；會把 ``cost`` 裡的這些欄位移除。"""
    status = cost.pop("self_status", None)
    overdraft = cost.pop("overdraft", None)
    if isinstance(status, dict):
        return str(status.get("status"))
    return OVERDRAFT_CHOICE if overdraft else None
