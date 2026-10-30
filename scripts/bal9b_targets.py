"""BAL-9b：無召喚 Boss 戰的火力分配（我方打誰、誰打我方、各敵人何時倒下）。

用法::

    uv run python scripts/bal9b_targets.py <recs.json> > docs/phases/BAL-9b/boss_plain_targets.md
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

TPL = ("bandit_warlord", "bandit_guard", "bandit_archer_guard", "bandit_shieldbearer_guard")


def m(xs: list[float]) -> float:
    return statistics.mean(xs) if xs else float("nan")


def main() -> int:
    recs: list[dict[str, Any]] = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    mults = sorted({r["mult"] for r in recs}, reverse=True)
    out = ["## 我方打出的傷害（每場平均，依目標）\n"]
    out.append("| 頭目HP | 場數 | 勝率 | " + " | ".join(TPL) + " | 頭目占比 |")
    out.append("|---|---|---|" + "---|" * (len(TPL) + 1))
    for mult in mults:
        rs = [r for r in recs if r["mult"] == mult]
        vals = [m([r["out_by_target"].get(t, 0) for r in rs]) for t in TPL]
        w = 100 * sum(r["win"] for r in rs) / len(rs)
        out.append(
            f"| {mult}‰ | {len(rs)} | {w:.1f}% | "
            + " | ".join(f"{v:.1f}" for v in vals)
            + f" | {100 * vals[0] / sum(vals):.0f}% |"
        )
    out.append("\n## 敵方打出的傷害（每場平均，依來源）\n")
    out.append("| 頭目HP | " + " | ".join(TPL) + " |")
    out.append("|---|" + "---|" * len(TPL))
    for mult in mults:
        rs = [r for r in recs if r["mult"] == mult]
        out.append(
            f"| {mult}‰ | "
            + " | ".join(f"{m([r['in_by_source'].get(t, 0) for r in rs]):.1f}" for t in TPL)
            + " |"
        )
    out.append("\n## 敵人被擊倒（場數比例與平均輪數）\n")
    out.append("| 頭目HP | " + " | ".join(TPL) + " |")
    out.append("|---|" + "---|" * len(TPL))
    for mult in mults:
        rs = [r for r in recs if r["mult"] == mult]
        cells = []
        for t in TPL:
            rounds = [min(r["enemy_down"][t]) for r in rs if t in r["enemy_down"]]
            cells.append(f"{100 * len(rounds) / len(rs):.0f}%／第 {m(rounds):.1f} 輪")
        out.append(f"| {mult}‰ | " + " | ".join(cells) + " |")
    out.append("\n## 勝／敗分開（頭目血量被打到 <= 50% 的場次比例；頭目死亡後的結果）\n")
    out.append("| 頭目HP | 頭目被擊倒場數 | 其中勝 | 其中仍輸 | 頭目沒死場數 | 其中勝 |")
    out.append("|---|---|---|---|---|---|")
    for mult in mults:
        rs = [r for r in recs if r["mult"] == mult]
        dead = [r for r in rs if r["boss_dead_round"] is not None]
        alive = [r for r in rs if r["boss_dead_round"] is None]
        out.append(
            f"| {mult}‰ | {len(dead)} | {sum(r['win'] for r in dead)} "
            f"| {sum(not r['win'] for r in dead)} | {len(alive)} | {sum(r['win'] for r in alive)} |"
        )
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
