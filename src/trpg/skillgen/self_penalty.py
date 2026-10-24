"""LLM 提議的「自己付的代價」（Phase 3-50，06 6.5 共通規則 7）：只能從允許的代價中挑一個。

提議格式沒有 ``cost``（數值由引擎補），所以這裡多一個可省略的欄位 ``cost_penalty``：值是
``allowance.self_status.allowed`` 裡的一個狀態 ID（依稀有度篩選，和驗證器的 ``rarity.status`` 同一
規則）；另一個可省略的 ``cost_overdraft: true`` 是透支（3-50b：透支不算自身狀態，可以和
``cost_penalty`` 同時使用，仍受整體 50% 上限）。引擎把它們換成 ``cost.self_status`` 與
``cost.overdraft``；持續時間不給 LLM 選（固定狀態用規則的固定值，其他取最短的 2）。範圍與上限
（沉默限法術技、一招最多一個自身狀態）由驗證器檢查。
"""

from __future__ import annotations

from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillRarity, rarity_rank

__all__ = ["penalty_choices", "penalty_cost", "penalty_of_cost"]

_MIN_DURATION = 2


def penalty_choices(library: ContentLibrary, rarity: SkillRarity | None = None) -> tuple[str, ...]:
    """提議可以挑的自身狀態代價（排序；透支另外用 ``cost_overdraft``）。"""
    statuses = library.ruleset.statuses.by_id()
    rule = library.budget.allowance.self_status
    found = sorted(
        s
        for s in rule.allowed
        if s in statuses
        and statuses[s].budget_points is not None
        and (rarity is None or rarity_rank(statuses[s].min_rarity) <= rarity_rank(rarity))
    )
    return tuple(found)


def penalty_cost(library: ContentLibrary | None, choice: str) -> dict[str, Any]:
    """自身狀態選擇 → ``cost`` 裡要加的欄位。"""
    fixed = {} if library is None else library.budget.allowance.self_status.fixed_duration
    return {"self_status": {"status": choice, "duration": fixed.get(choice, _MIN_DURATION)}}


def penalty_of_cost(cost: dict[str, Any]) -> tuple[str | None, bool]:
    """``cost`` 字典 → （自身狀態選擇或 ``None``，是否透支）；會把 ``cost`` 裡的這些欄位移除。"""
    status = cost.pop("self_status", None)
    overdraft = bool(cost.pop("overdraft", None))
    return (str(status.get("status")) if isinstance(status, dict) else None), overdraft
