"""校準 ``tier_budget``（Phase 2B-2 4.2）。

用法::

    uv run python scripts/calibrate_tier_budget.py [--min 4] [--max 40]

對每個有示範技能的階級，列出每個技能「不修改就合格」的 ``tier_budget`` 區間
``[total ÷ (AP係數 × 折抵), 該值 ÷ 0.7]``，以及每個候選值下合格的技能數。最後依下列順序挑出
各階級的最佳值（階級間必須嚴格遞增）：①全部階級合格的技能總數最多 ②相鄰階級的差距總和最大
③較小的值。沒有示範技能的階級不在此校準，由報告說明外推方式。
"""

from __future__ import annotations

import argparse
import itertools
import sys
from fractions import Fraction

from trpg.content.library import ContentLibrary, load_library
from trpg.skillgen.budget import skill_budget


def implied_windows(library: ContentLibrary) -> dict[int, list[tuple[str, Fraction, Fraction]]]:
    """階級 → [(技能 ID, 合格的 tier_budget 下限, 上限)]（只看預算比例，不看結構規則）。"""
    out: dict[int, list[tuple[str, Fraction, Fraction]]] = {}
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        report = skill_budget(skill, library)
        factor = report.ap_coefficient * Fraction(1000 + report.allowance_permille, 1000)
        low = report.total / (factor * report.max_ratio)
        high = report.total / (factor * report.min_ratio)
        out.setdefault(skill.tier, []).append((skill_id, low, high))
    return out


def count_ok(windows: list[tuple[str, Fraction, Fraction]], value: int) -> int:
    return sum(1 for _, low, high in windows if low <= value <= high)


def best_values(
    windows: dict[int, list[tuple[str, Fraction, Fraction]]], lo: int, hi: int
) -> dict[int, int]:
    """各階級的最佳 tier_budget（嚴格遞增；排序規則見模組說明）。"""
    tiers = sorted(windows)
    best: tuple[tuple[int, int, int], dict[int, int]] | None = None
    for combo in itertools.product(range(lo, hi + 1), repeat=len(tiers)):
        if any(a >= b for a, b in itertools.pairwise(combo)):
            continue
        total = sum(count_ok(windows[t], v) for t, v in zip(tiers, combo, strict=True))
        spread = combo[-1] - combo[0]
        key = (total, spread, -combo[0])
        if best is None or key > best[0]:
            best = (key, dict(zip(tiers, combo, strict=True)))
    assert best is not None
    return best[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校準 tier_budget")
    parser.add_argument("--min", type=int, default=4, dest="lo")
    parser.add_argument("--max", type=int, default=40, dest="hi")
    args = parser.parse_args(argv)
    library = load_library()
    windows = implied_windows(library)
    for tier in sorted(windows):
        print(f"階級 {tier}（{len(windows[tier])} 個示範技能）：不修改就合格的 tier_budget 區間")
        for skill_id, low, high in windows[tier]:
            print(f"  {skill_id:26} {float(low):6.2f} – {float(high):6.2f}")
    print("\n候選值 → 合格技能數")
    header = "  T    " + "  ".join(f"階級{t}" for t in sorted(windows))
    print(header)
    for value in range(args.lo, args.hi + 1):
        counts = "  ".join(f"{count_ok(windows[t], value):>4}" for t in sorted(windows))
        print(f"  {value:<4} {counts}")
    best = best_values(windows, args.lo, args.hi)
    print("\n最佳（嚴格遞增）：" + "、".join(f"T{t}={v}" for t, v in best.items()))
    for tier, value in best.items():
        print(f"  階級 {tier}：{count_ok(windows[tier], value)} / {len(windows[tier])} 個合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
