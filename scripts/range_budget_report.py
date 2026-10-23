"""內建技能的射程係數重算報表（Phase 3-49，玩法決定 #53）。

安靜模式：只列出射程係數 ≠ 1 的技能（技能、射程、改前／改後比例），以及改後超出 70～100% 的技能。
不修改任何技能數值。用法：``uv run python scripts/range_budget_report.py``。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path

import trpg.skillgen.budget as budget_module
from trpg.content.library import ContentLibrary, load_library
from trpg.skillgen.budget import BudgetError, skill_budget


@contextmanager
def _no_range() -> Iterator[None]:
    original = budget_module.range_coefficient
    budget_module.range_coefficient = lambda shape, budget: (None, Fraction(1))  # type: ignore[assignment]
    try:
        yield
    finally:
        budget_module.range_coefficient = original  # type: ignore[assignment]


def _ratio(skill_id: str, library: ContentLibrary) -> Fraction | None:
    try:
        return skill_budget(library.skills[skill_id], library).ratio
    except BudgetError:
        return None


def main() -> None:
    library = load_library(Path(__file__).resolve().parents[1] / "content")
    ids = sorted(library.skills)
    after = {i: _ratio(i, library) for i in ids}
    with _no_range():
        before = {i: _ratio(i, library) for i in ids}
    low = library.budget.min_ratio_permille
    high = library.budget.max_ratio_permille

    def pct(value: Fraction | None) -> str:
        return "—" if value is None else f"{float(value) * 100:.1f}%"

    print("| 技能 | 射程 | 係數 | 改前 | 改後 | 狀態 |")
    print("|---|---|---|---|---|---|")
    out_of_range = 0
    changed = 0
    for i in ids:
        report = skill_budget(library.skills[i], library) if after[i] is not None else None
        if report is None or report.range_coefficient == 1:
            continue
        changed += 1
        b, a = before[i], after[i]
        assert a is not None
        status = "ok"
        if a * 1000 > high:
            status = "超出上限"
        elif a * 1000 < low:
            status = "過弱"
        if status != "ok":
            out_of_range += 1
        print(
            f"| {i} | {report.range_value} | ×{float(report.range_coefficient):g} "
            f"| {pct(b)} | {pct(a)} | {status} |"
        )
    total_bad = sum(1 for v in after.values() if v is not None and not (low <= v * 1000 <= high))
    total_bad_before = sum(
        1 for v in before.values() if v is not None and not (low <= v * 1000 <= high)
    )
    print(
        f"\n技能 {len(ids)} 個；射程係數 ≠ 1 的 {changed} 個；"
        f"其中超出 70～100% 的 {out_of_range} 個；"
        f"全部技能超出範圍：改前 {total_bad_before} 個、改後 {total_bad} 個。"
    )


if __name__ == "__main__":
    main()
