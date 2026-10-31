"""BAL-12a：讀 ``skill_diagnosis.py matrix`` 存的 JSON，列各類型第 7 名門檻與指定 build 的差距。

用法：``uv run python scripts/matrix_ranks.py docs/phases/BAL-12/12a_matrix.json build_a,build_b``
"""

from __future__ import annotations

import sys
from pathlib import Path

from trpg.sim.matrix import MATRIX_ADAPTER, MatrixReport


def build_stats(report: MatrixReport) -> None:
    """每個 build 的平均：勝率、英雄 DPR、存活率、承傷、治療、護盾、隊友存活率、輪數。"""
    print("build              勝率   DPR  存活%  承傷  治療  護盾  隊友%  輪數")
    rows = []
    for b in report.builds:
        cs = [c for c in report.cells if c.build_id == b]
        n = len(cs)
        done = sum(c.completed for c in cs)
        rows.append(
            (
                b,
                sum(c.ally_wins for c in cs) * 100 / done,
                sum(c.hero_dpr for c in cs) / n,
                sum(c.hero_survival for c in cs) * 100 / n,
                sum(c.hero_taken for c in cs) / n,
                sum(c.hero_healing for c in cs) / n,
                sum(c.hero_shield for c in cs) / n,
                sum(c.teammate_survival for c in cs) * 100 / n,
                sum(c.rounds_mean for c in cs) / n,
            )
        )
    for x in sorted(rows, key=lambda r: -r[1]):
        print(f"{x[0]:18s}" + " ".join(f"{v:5.1f}" for v in x[1:]))


def main(argv: list[str]) -> int:
    report = MATRIX_ADAPTER.validate_json(Path(argv[1]).read_bytes())
    arg = "".join(argv[2:3])
    if arg == "--stats":
        build_stats(report)
        return 0
    builds = arg.split(",") if arg else list(report.builds)
    k = report.standards.top_count
    print(f"seeds={len(report.seeds)} top_count={k} never_top={list(report.standards.never_top)}")
    cut: dict[str, float] = {}
    for a in report.archetypes:
        cells = sorted(
            (c for c in report.archetype_cells if c.archetype == a), key=lambda c: c.rank
        )
        cut[a] = cells[k - 1].win_rate
        top1 = cells[0]
        print(
            f"{a}: 第{k}名 {cut[a] * 100:.0f}%（第1名 {top1.build_id} {top1.win_rate * 100:.0f}%）"
        )
    for b in builds:
        print(f"\n{b}")
        for a in report.archetypes:
            c = next(x for x in report.archetype_cells if x.build_id == b and x.archetype == a)
            gap = (c.win_rate - cut[a]) * 100
            print(
                f"  {a:14s} 勝率{c.win_rate * 100:5.1f}% 名次{c.rank:2d} "
                f"與第{k}名差{gap:+5.1f}pt DPR{c.hero_dpr:5.1f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
