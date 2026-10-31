# ruff: noqa: E501, PLR2004
"""BAL-13d 第 4 項：找「瞬步背刺每 AP 傷害 ≥ 普攻 1.2 倍」所需的最小預算係數改動（只在記憶體內覆寫）。

用法::

    # 預算：每組（瞬步點數 s, 背刺條件倍率 c‰）下，瞬步背刺背後加成取預算上限內的最大值，
    # 並列出所有內建技能的預算比例變動與掉出 70～100% 的技能
    uv run python scripts/bal13d_backstab.py budget --cand 4:850 --cand 3:550 --cand 2:650 ...
    # 實測：assassin（10 圖 × 種子）的每 AP 傷害（含未命中），普攻＝英雄普攻傷害 ÷ 擲骰數
    uv run python scripts/bal13d_backstab.py measure --cand 3:550 --seeds 30 --jobs 6

``--cand s:c[:m1:m2]``：``s`` 是 ``shadowstep`` 的 ``base_points``，``c`` 是 ``from_behind`` 的預算倍率
（‰），``m1``／``m2`` 是瞬步背刺兩段傷害的倍率（‰；省略時 m1 維持 content、m2 取預算上限內 50‰ 一格的最大值）。
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import sys
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.sim.matrix import matrix_specs
from trpg.sim.parallel import run_tasks
from trpg.skillgen.budget import BudgetError, skill_budget

ROOT = Path(__file__).resolve().parents[1]
SKILL = "skill_shadow_backstab"
BUILD = "build_assassin"
TARGET = Fraction(12, 10)
_spec = importlib.util.spec_from_file_location(
    "weak_build_audit", ROOT / "scripts" / "weak_build_audit.py"
)
assert _spec is not None and _spec.loader is not None
audit = importlib.util.module_from_spec(_spec)
sys.modules["weak_build_audit"] = audit
_spec.loader.exec_module(audit)


def _with_skill(lib: ContentLibrary, skill_id: str, **fields: Any) -> ContentLibrary:
    out: ContentLibrary = audit._skill_edit(lib, skill_id, **fields)
    return out


def with_coefficients(lib: ContentLibrary, s: int, c: int) -> ContentLibrary:
    """``shadowstep`` 的 ``base_points`` ＝ s、``from_behind`` 的預算倍率 ＝ c‰（記憶體內）。"""
    rs = lib.ruleset
    prims = tuple(
        p.model_copy(update={"base_points": s}) if p.id == "shadowstep" else p
        for p in rs.primitives.primitives
    )
    conds = tuple(
        x.model_copy(update={"budget_permille": c}) if x.id == "from_behind" else x
        for x in rs.conditions.conditions
    )
    ruleset = rs.model_copy(
        update={
            "primitives": rs.primitives.model_copy(update={"primitives": prims}),
            "conditions": rs.conditions.model_copy(update={"conditions": conds}),
        }
    )
    return dataclasses.replace(lib, ruleset=ruleset)


def with_multipliers(lib: ContentLibrary, m1: int, m2: int) -> ContentLibrary:
    skill = lib.skills[SKILL]
    effects = list(skill.effects)
    effects[1] = effects[1].model_copy(update={"multiplier_permille": m1})
    effects[2] = effects[2].model_copy(update={"multiplier_permille": m2})
    return _with_skill(lib, SKILL, effects=tuple(effects))


def ratio(lib: ContentLibrary, skill_id: str) -> Fraction | None:
    try:
        return skill_budget(lib.skills[skill_id], lib).ratio
    except BudgetError:
        return None


def candidate(base: ContentLibrary, text: str) -> tuple[ContentLibrary, tuple[int, int, int, int]]:
    parts = [int(x) for x in text.split(":")]
    s, c = parts[0], parts[1]
    lib = with_coefficients(base, s, c)
    effects = base.skills[SKILL].effects
    m1 = parts[2] if len(parts) > 2 else (effects[1].multiplier_permille or 1000)
    if len(parts) > 3:
        m2 = parts[3]
    else:
        m2 = 500
        while True:
            trial = with_multipliers(lib, m1, m2 + 50)
            r = ratio(trial, SKILL)
            if r is None or r > 1:
                break
            m2 += 50
    return with_multipliers(lib, m1, m2), (s, c, m1, m2)


def cmd_budget(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    lo = Fraction(base.budget.min_ratio_permille, 1000)
    hi = Fraction(base.budget.max_ratio_permille, 1000)
    before = {sid: ratio(base, sid) for sid in sorted(base.skills)}
    for text in args.cand:
        lib, (s, c, m1, m2) = candidate(base, text)
        r = ratio(lib, SKILL)
        assert r is not None
        print(f"\n## s={s} c={c}‰：瞬步背刺 m1={m1} m2={m2}，比例 {float(r) * 100:.1f}%")
        print(f"背後命中時的總倍率 {(m1 + m2) / 1000:.2f}（原 1.50）")
        changed = []
        for sid, old in before.items():
            new = ratio(lib, sid) if sid != SKILL else r
            if old != new:
                changed.append((sid, old, new))
        for sid, old, new in changed:
            flag = "" if new is not None and lo <= new <= hi else " **掉出區間**"
            o = "-" if old is None else f"{float(old) * 100:.1f}%"
            n = "-" if new is None else f"{float(new) * 100:.1f}%"
            print(f"- {sid}：{o} → {n}{flag}")
    return 0


def _row_stats(rows: list[dict[str, Any]]) -> tuple[float, float, float, float, float]:
    agg: Counter[str] = Counter()
    basic: Counter[str] = Counter()
    for r in rows:
        agg.update(r["skills"].get(SKILL, {}))
        basic.update(r["skills"].get("basic", {}))
    uses = max(1, agg["uses"])
    ap = agg["ap"] / uses
    per_ap = agg["dmg"] / uses / ap
    basic_ap = basic["dmg"] / max(1, basic["rolls"])
    win = sum(r["win"] for r in rows) * 100 / len(rows)
    return per_ap, basic_ap, agg["uses"] / len(rows), win, agg["hits"] / max(1, agg["rolls"])


def cmd_measure(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    maps = default_sim_maps(base)
    seeds = list(range(args.seeds))
    started = time.perf_counter()
    print(
        "| 候選 | 背後總倍率 | 比例 | 瞬步背刺每 AP | 普攻每 AP | 倍數 | 每場施放 | 命中率 | 勝率 |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for text in args.cand:
        lib, (s, c, m1, m2) = (
            (base, (4, 850, 1000, 500)) if text == "base" else candidate(base, text)
        )
        r = ratio(lib, SKILL)
        specs = matrix_specs(lib, [BUILD], maps, seeds)
        pairs = tuple((b, sp) for b, _, sp in specs)
        tasks = [(i, seed) for i in range(len(pairs)) for seed in seeds]
        rows = [
            x for x in run_tasks(audit._worker, (pairs,), tasks, jobs=args.jobs) if "error" not in x
        ]
        per_ap, basic_ap, uses, win, hit = _row_stats(rows)
        print(
            f"| s={s} c={c} m={m1}/{m2} | {(m1 + m2) / 1000:.2f} | {float(r or 0) * 100:.1f}% | {per_ap:.2f} | {basic_ap:.2f} "
            f"| {per_ap / basic_ap:.2f} | {uses:.2f} | {hit * 100:.0f}% | {win:.1f} |",
            flush=True,
        )
        print(f"[{text} {time.perf_counter() - started:.0f}s]", file=sys.stderr, flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("budget")
    p.add_argument("--cand", action="append", required=True)
    p.set_defaults(fn=cmd_budget)
    p = sub.add_parser("measure")
    p.add_argument("--cand", action="append", required=True)
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--jobs", type=int, default=6)
    p.set_defaults(fn=cmd_measure)
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
