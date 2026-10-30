"""BAL-9c：弩穿透後方折扣（pierce_permille，pierce_line=5）對勝率與 DPR 的影響（10 圖 × 種子）。

用法::

    uv run python scripts/bal9c_pierce.py --values 1000,800,700,600,500 --seeds 10 --jobs 8 \
        --out docs/phases/BAL-9c/pierce.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from bal8_measure import SWORD, stats, with_weapon  # type: ignore[import-not-found]
from trpg.cli.sim import default_sim_maps
from trpg.content.library import load_library
from trpg.sim.matrix import run_matrix

CROSSBOW = "build_blank_crossbow"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--values", default="1000,800,700,600,500")
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    base = load_library()
    maps = default_sim_maps(base)
    seeds = list(range(args.seeds))
    lines = [
        f"# 弩 pierce_permille 掃描（{len(maps)} 圖 × {args.seeds} 種子；DPR 含穿透）",
        "",
        "| pierce_permille | 弩勝率 | 弩輪數 | 弩 DPR | 單手劍 DPR | DPR 比 |",
        "|---|---|---|---|---|---|",
    ]
    for v in (int(x) for x in args.values.split(",")):
        lib = with_weapon(base, "crossbow", pierce_line=5, pierce_permille=v)
        st = stats(run_matrix(lib, [CROSSBOW, SWORD], maps, seeds, jobs=args.jobs))
        c, s = st[CROSSBOW], st[SWORD]
        lines.append(
            f"| {v} | {c.win:.1f}%（{c.n}） | {c.rounds:.1f} | {c.dpr:.2f} | {s.dpr:.2f} "
            f"| {100 * c.dpr / s.dpr:.1f}% |"
        )
        print(lines[-1], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
