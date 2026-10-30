"""BAL-9b：分析 ``bal9b_boss.py --dump`` 的逐場記錄（輸場死因、援軍時機、AI 目標）。

用法::

    uv run python scripts/bal9b_analyze.py <recs.json> > docs/phases/BAL-9b/boss_loss_analysis.md
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

Rec = dict[str, Any]
REINFORCE_ROUND = 3


def m(xs: list[float]) -> float:
    return statistics.mean(xs) if xs else float("nan")


def _cell(recs: list[Rec], mult: int, summon: bool) -> list[Rec]:
    return [r for r in recs if r["mult"] == mult and r["summon"] == summon]


def _outcome_table(recs: list[Rec], mults: list[int], summon: bool) -> list[str]:
    out = [
        "| 頭目HP | n | 勝率 | 輸場數 | 輸場平均輪數 | 輸場頭目殘血% | 輸場頭目已死 "
        "| 輸場第3輪頭目血% | 全場第3輪頭目血% | 打到第3輪% | 勝場輪數 | 輸場英雄倒下輪（場數） |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mult in mults:
        rs = _cell(recs, mult, summon)
        lost = [r for r in rs if not r["win"]]
        won = [r for r in rs if r["win"]]
        r3 = [r["boss_frac_r3"] for r in rs if r["boss_frac_r3"] is not None]
        r3l = [r["boss_frac_r3"] for r in lost if r["boss_frac_r3"] is not None]
        dead = [r for r in lost if r["boss_dead_round"] is not None]
        hd = [r["hero_down_round"] for r in lost if r["hero_down_round"] is not None]
        out.append(
            f"| {mult}‰ | {len(rs)} | {100 * len(won) / len(rs):.1f}% | {len(lost)} "
            f"| {m([r['rounds'] for r in lost]):.1f} "
            f"| {100 * m([r['boss_frac_end'] for r in lost]):.0f} "
            f"| {len(dead)}/{len(lost)} | {100 * m(r3l):.0f} | {100 * m(r3):.0f} "
            f"| {100 * len(r3) / len(rs):.0f} | {m([r['rounds'] for r in won]):.1f} "
            f"| {m(hd):.1f}（{len(hd)}） |"
        )
    return out


def _target_table(recs: list[Rec], mults: list[int], summon: bool) -> list[str]:
    out = [
        "| 頭目HP | hi:英雄 | hi:隊友 | hi:召喚物 | lo:英雄 | lo:隊友 | lo:召喚物 "
        "| 英雄占比(lo) | 頭目距離hi | 頭目距離lo | 輸場我方存活(末) | 輸場敵方存活(末) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mult in mults:
        rs = _cell(recs, mult, summon)
        lost = [r for r in rs if not r["win"]]

        def d(k: str, rs: list[Rec] = rs) -> float:
            return m([r["dmg"].get(k, 0) for r in rs])

        lo = [d("lo:hero"), d("lo:comp"), d("lo:summon")]
        dist_hi = [x for r in rs for x in r["dist"].get("hi", [])]
        dist_lo = [x for r in rs for x in r["dist"].get("lo", [])]
        share = lo[0] / sum(lo) if sum(lo) else float("nan")
        out.append(
            f"| {mult}‰ | {d('hi:hero'):.1f} | {d('hi:comp'):.1f} | {d('hi:summon'):.1f} "
            f"| {lo[0]:.1f} | {lo[1]:.1f} | {lo[2]:.1f} | {100 * share:.0f}% "
            f"| {m(dist_hi):.1f} | {m(dist_lo):.1f} "
            f"| {m([r['allies_alive_end'] for r in lost]):.1f} "
            f"| {m([r['enemies_alive_end'] for r in lost]):.1f} |"
        )
    return out


def main() -> int:
    recs: list[Rec] = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    mults = sorted({r["mult"] for r in recs}, reverse=True)
    out: list[str] = []
    for summon in (False, True):
        out += [f"\n## {'有召喚' if summon else '無召喚'}\n", *_outcome_table(recs, mults, summon)]
        out += ["\n敵方對我方的傷害（每場平均）與頭目回合距最近我方（格）\n"]
        out += _target_table(recs, mults, summon)
        out.append("\n輸場類型：")
        for mult in mults:
            lost = [r for r in _cell(recs, mult, summon) if not r["win"]]
            c = Counter("我方全倒" if r["allies_alive_end"] == 0 else "其他" for r in lost)
            fr = Counter(
                "第3輪前" if (r["hero_down_round"] or 99) < REINFORCE_ROUND else "之後"
                for r in lost
            )
            out.append(f"- {mult}‰：{dict(c)}；英雄倒下 {dict(fr)}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
