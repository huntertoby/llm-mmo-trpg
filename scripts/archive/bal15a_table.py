"""BAL-15a：把 ``bal15a_resources.py measure`` 的多個輸出併成「build × 覆寫」對照表。

用法::

    uv run python scripts/archive/bal15a_table.py --inp base.json,mana.json --builds build_fire,build_tank \\
        --variants mcap=1000,base,mcap=1800 --chain-max 16 [--metrics short,win] [--out x.md]

每個 build 列出 Boss 戰與連戰各場的法力短缺回合（%）、Boss 勝率、三連勝；最後一段是這些 build 的合計。
``--metrics`` 可選 ``short``（短缺）、``win``（勝率）、``rounds``（輪數）、``eskill``（敵方技能次數／場）。
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

Rows = list[dict[str, Any]]


def _beyond(r: dict[str, Any], limit: int) -> bool:
    kind = r["kind"]
    if kind == "chain":
        return bool(r["seed"] >= limit)
    if kind.startswith("chain"):
        return bool(r["seed"] - 1000 - (int(kind[5:]) - 1) >= limit)
    return False


def _short(rs: Rows) -> float:
    t = sum(r["turns"] for r in rs)
    return 100 * sum(r["mana_short"] for r in rs) / t if t else float("nan")


def _stam(rs: Rows) -> float:
    t = sum(r["turns"] for r in rs)
    return 100 * sum(r["stam_short"] for r in rs) / t if t else float("nan")


def _win(rs: Rows) -> float:
    return 100 * sum(r["won"] for r in rs) / len(rs) if rs else float("nan")


def _rounds(rs: Rows) -> float:
    return sum(r["rounds"] for r in rs) / len(rs) if rs else float("nan")


def _eskill(rs: Rows) -> float:
    return sum(r["enemy_skill_uses"] for r in rs) / len(rs) if rs else float("nan")


METRICS: dict[str, tuple[str, str, Callable[[Rows], float]]] = {
    "short:normal": ("一般戰 法力短缺%", "normal", _short),
    "short:boss": ("Boss 法力短缺%", "boss", _short),
    "short:chain2": ("連戰第2場 法力短缺%", "chain2", _short),
    "short:chain3": ("連戰第3場 法力短缺%", "chain3", _short),
    "stam:normal": ("一般戰 耐力短缺%", "normal", _stam),
    "stam:boss": ("Boss 耐力短缺%", "boss", _stam),
    "win:normal": ("一般戰 勝率%", "normal", _win),
    "win:boss": ("Boss 勝率%", "boss", _win),
    "win:chain": ("連戰 3 連勝%", "chain", _win),
    "rounds:normal": ("一般戰 輪數", "normal", _rounds),
    "rounds:boss": ("Boss 輪數", "boss", _rounds),
    "eskill:boss": ("Boss 敵方技能次數/場", "boss", _eskill),
    "eskill:normal": ("一般戰 敵方技能次數/場", "normal", _eskill),
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inp", required=True)
    p.add_argument("--builds", required=True)
    p.add_argument("--variants", required=True)
    p.add_argument("--chain-max", type=int, default=0)
    p.add_argument(
        "--metrics",
        default="short:boss,short:chain2,short:chain3,win:boss,win:chain",
        help=f"逗號分隔：{','.join(METRICS)}",
    )
    p.add_argument("--out", default="")
    args = p.parse_args(argv)
    rows: Rows = []
    for inp in args.inp.split(","):
        rows += json.loads(Path(inp).read_text(encoding="utf-8"))
    builds = args.builds.split(",")
    variants = args.variants.split(",")
    rows = [
        r
        for r in rows
        if r["build"] in builds and r["ok"] and not (args.chain_max and _beyond(r, args.chain_max))
    ]
    by: dict[tuple[str, str, str], Rows] = defaultdict(list)
    for r in rows:
        by[(r["variant"], r["build"], r["kind"])].append(r)
    metrics = args.metrics.split(",")
    out = [
        "| build | 指標 | " + " | ".join(variants) + " |",
        "|---|---|" + "---|" * len(variants),
    ]
    for b in builds:
        for m in metrics:
            label, kind, fn = METRICS[m]
            cells = " | ".join(f"{fn(by[(v, b, kind)]):.1f}" for v in variants)
            out.append(f"| {b.removeprefix('build_')} | {label} | {cells} |")
    out += ["", "| 合計指標 | " + " | ".join(variants) + " |", "|---|" + "---|" * len(variants)]
    for m in metrics + [x for x in ("rounds:normal", "rounds:boss") if x not in metrics]:
        label, kind, fn = METRICS[m]
        cells = " | ".join(
            f"{fn([r for b in builds for r in by[(v, b, kind)]]):.1f}" for v in variants
        )
        out.append(f"| {label} | {cells} |")
    text = "\n".join(out)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
