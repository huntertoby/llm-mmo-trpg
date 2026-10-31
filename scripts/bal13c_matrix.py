"""BAL-13c：重量用 chain／雷的 build，與其他 build 的既有全矩陣合併後重算前段判定。

用法::

    uv run python scripts/bal13c_matrix.py run OUT.json --builds a,b --jobs 4 [--conduct 1000]
    uv run python scripts/bal13c_matrix.py merge BASE.json PART.json [PART2.json ...]

- ``run``：只跑指定 build（全部有 encounter 的地圖、種子 0～29），寫出 :class:`MatrixReport` JSON。
  ``--conduct`` 在記憶體內把互動表兩條 ``lightning_conducts_*`` 的 ``damage_permille`` 改成該值
  （規格第 4 點：storm 低於 70% 時用 1000‰ 再量一次）。
- ``merge``：以 ``PART`` 的格子取代 ``BASE``（例如 ``docs/phases/BAL-12/12d_matrix.json``）中
  同 build 的格子，用 :func:`trpg.sim.matrix.assemble_matrix` 重算名次與 06 6.8 的兩條標準，
  印出每個 build
  的勝率、無前段名單與指定 build 的各類型名次。

本段只改了 chain 形狀、雷電擴散與 ``chain_lightning``，沒有 chain／雷的 build 的戰鬥結算不變（同種子
同結果），所以只重跑受影響的 build（全矩陣 16 核約 19 分鐘，平行上限 4 時超過時間預算）。
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.sim.matrix import (
    MATRIX_ADAPTER,
    MatrixCell,
    MatrixReport,
    RawCell,
    assemble_matrix,
    run_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(30))
CONDUCT_RULES = ("lightning_conducts_water", "lightning_conducts_object")


def _with_conduct(library: ContentLibrary, permille: int) -> ContentLibrary:
    rs = library.ruleset
    rules = []
    for rule in rs.interactions.rules:
        if rule.id in CONDUCT_RULES:
            then = tuple(o.model_copy(update={"damage_permille": permille}) for o in rule.then)
            rules.append(rule.model_copy(update={"then": then}))
        else:
            rules.append(rule)
    table = rs.interactions.model_copy(update={"rules": tuple(rules)})
    return replace(library, ruleset=rs.model_copy(update={"interactions": table}))


def cmd_run(args: argparse.Namespace) -> int:
    library = load_library(ROOT / "content")
    if args.conduct is not None:
        library = _with_conduct(library, args.conduct)
    builds = args.builds.split(",")
    start = time.perf_counter()
    maps = args.maps.split(",") if args.maps else default_sim_maps(library)
    report = run_matrix(library, builds, maps, SEEDS, jobs=args.jobs)
    Path(args.out).write_bytes(MATRIX_ADAPTER.dump_json(report, indent=1))
    print(f"[{time.perf_counter() - start:7.1f}s] {len(builds)} builds × {len(report.maps)} maps")
    return 0


def _raw(cell: MatrixCell) -> RawCell:
    return RawCell(
        build_id=cell.build_id,
        map_id=cell.map_id,
        archetype=cell.archetype,
        battles=cell.battles,
        completed=cell.completed,
        ally_wins=cell.ally_wins,
        draws=cell.draws,
        hero_dpr=cell.hero_dpr,
        hero_survival=cell.hero_survival,
        rounds_mean=cell.rounds_mean,
        errors=cell.errors,
        hero_healing=cell.hero_healing,
        hero_shield=cell.hero_shield,
        hero_taken=cell.hero_taken,
        teammate_survival=cell.teammate_survival,
        team_hp_ratio=cell.team_hp_ratio,
    )


def merge(base: MatrixReport, parts: list[MatrixReport]) -> MatrixReport:
    replaced = {c.build_id: c for p in parts for c in p.cells}
    keep = [c for c in base.cells if c.build_id not in replaced]
    cells = keep + [c for p in parts for c in p.cells]
    return assemble_matrix(base.builds, base.maps, [_raw(c) for c in cells], base.seeds)


def _win(report: MatrixReport, build: str) -> float:
    cs = [c for c in report.cells if c.build_id == build]
    return sum(c.ally_wins for c in cs) * 100 / sum(c.completed for c in cs)


def cmd_merge(args: argparse.Namespace) -> int:
    base = MATRIX_ADAPTER.validate_json(Path(args.base).read_bytes())
    parts = [MATRIX_ADAPTER.validate_json(Path(p).read_bytes()) for p in args.parts]
    merged = merge(base, parts)
    changed = sorted({c.build_id for p in parts for c in p.cells})
    print("build              基準勝率  新勝率   差")
    for b in sorted(merged.builds, key=lambda b: -_win(merged, b)):
        mark = " *" if b in changed else ""
        old, new = _win(base, b), _win(merged, b)
        print(f"{b:18s} {old:7.1f} {new:7.1f} {new - old:+6.1f}{mark}")
    print(f"\ntop_count={merged.standards.top_count}")
    print(f"全類型前段：{list(merged.standards.always_top)}")
    print(f"無前段：{list(merged.standards.never_top)}")
    print(f"（基準）全類型前段：{list(base.standards.always_top)}")
    print(f"（基準）無前段：{list(base.standards.never_top)}")
    for b in changed:
        ranks = [
            f"{a}:{merged.archetype_cell(b, a).rank}"
            + ("*" if merged.archetype_cell(b, a).top else "")
            for a in merged.archetypes
        ]
        print(f"{b}：{'  '.join(ranks)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("out")
    run.add_argument("--builds", required=True)
    run.add_argument("--jobs", type=int, default=4)
    run.add_argument("--conduct", type=int, default=None)
    run.add_argument("--maps", default="", help="只跑這些地圖（對照用；merge 需要全部地圖）")
    run.set_defaults(func=cmd_run)
    mer = sub.add_parser("merge")
    mer.add_argument("base")
    mer.add_argument("parts", nargs="+")
    mer.set_defaults(func=cmd_merge)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
