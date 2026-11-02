# ruff: noqa: E501
"""BAL-15a：資源消耗與上限（B11 法力換耐力是否合理）——讀 ``bal15a_resources.py measure`` 的輸出。

每個 build：法力／耐力上限、一般戰與 Boss 戰每場實際花費、花費占上限的比例、每回合花費；
另算「等價法力」＝ 法力花費 ＋ 耐力花費 ÷ 2（預算換算 ``stamina_per_mana: 2``），看兩類 build 一場戰鬥
實際用掉的資源在同一把尺上差多少。用法::

    uv run python scripts/bal15a_pool.py --inp .scratch_15a/base.json [--variant base] [--out x.md]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inp", required=True)
    p.add_argument("--variant", default="base")
    p.add_argument("--out", default="")
    args = p.parse_args(argv)
    rows: list[dict[str, Any]] = [
        r
        for r in json.loads(Path(args.inp).read_text(encoding="utf-8"))
        if r["variant"] == args.variant and r["ok"]
    ]
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by[(r["build"], r["kind"])].append(r)
    builds = list(dict.fromkeys(r["build"] for r in rows))
    out = [
        f"## 資源消耗與上限（覆寫：{args.variant}）",
        "",
        "| build | 法力上限 | 耐力上限 | 一般戰 法力花費（占上限）| 一般戰 耐力花費（占上限）| Boss 法力花費（占上限）| Boss 耐力花費（占上限）| Boss 每回合 法力／耐力 | Boss 等價法力花費 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for b in builds:
        n, bo = by[(b, "normal")], by[(b, "boss")]
        if not n or not bo:
            continue
        mmax, smax = _mean([r["mana_max"] for r in n]), _mean([r["stam_max"] for r in n])
        nm, ns = _mean([r["mana_spent"] for r in n]), _mean([r["stam_spent"] for r in n])
        bm, bs = _mean([r["mana_spent"] for r in bo]), _mean([r["stam_spent"] for r in bo])
        turns = _mean([r["turns"] for r in bo]) or 1
        out.append(
            f"| {b} | {mmax:.0f} | {smax:.0f} | {nm:.1f}（{100 * nm / max(1, mmax):.0f}%）| {ns:.1f}（{100 * ns / max(1, smax):.0f}%）"
            f"| {bm:.1f}（{100 * bm / max(1, mmax):.0f}%）| {bs:.1f}（{100 * bs / max(1, smax):.0f}%）"
            f"| {bm / turns:.1f}／{bs / turns:.1f} | {bm + bs / 2:.1f} |"
        )
    text = "\n".join(out)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
