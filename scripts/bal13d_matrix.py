# ruff: noqa: E501
"""BAL-13d：全矩陣重量（第 6、9 項）與「沒有價值的技能」量測（第 5 項，只量不改）。

用法::

    # 全矩陣（可分批）：寫出 MatrixReport JSON，另寫 ``<OUT>.skills.json``（每個 build 英雄技能的使用率與每次效果）
    uv run python scripts/bal13d_matrix.py run OUT.json --builds a,b,... --jobs 6
    # 合併各批（以 BAL-12d 全矩陣為底，各批的格子全部取代）並重算前段判定：用 bal13c_matrix.py merge
    uv run python scripts/bal13c_matrix.py merge docs/phases/BAL-12/12d_matrix.json A.json B.json
    # 拿掉一招後的勝率（同種子；對照 run 的格子）
    uv run python scripts/bal13d_matrix.py ablate --base A.json --base B.json --pair build_seer:skill_flare_sight ... --jobs 6
    # 技能表：使用率、每次傷害／治療、每 AP 傷害對普攻的比
    uv run python scripts/bal13d_matrix.py skills A.skills.json B.skills.json

技能列（``trpg.sim.batch.SkillRow``）是同一批戰鬥裡所有用到該技能的單位合計（我方標準隊友若帶同一招會算進去；
``teams`` 欄會標出）。``每 AP 傷害`` ＝ 每次傷害 ÷ 技能 AP（含未命中）；批次報表沒有普攻的列，
普攻每 AP 的對照見 ``bal13d_backstab.py``（assassin）與 BAL-13b 報告。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path
from typing import Any

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.sim.batch import run_batches
from trpg.sim.matrix import (
    MATRIX_ADAPTER,
    MapInfo,
    MatrixReport,
    _raw_cell,
    assemble_matrix,
    matrix_specs,
)

ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(30))


def _hero_skills(library: ContentLibrary, build: str) -> tuple[str, ...]:
    return tuple(library.builds.by_id()[build].hero.skills)


def _skill_rows(
    library: ContentLibrary, builds: list[str], specs: Any, reports: Any
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for (build, _map_id, _), report in zip(specs, reports, strict=True):
        skills = _hero_skills(library, build)
        rows = out.setdefault(
            build,
            {
                s: {"battles": 0, "uses": 0.0, "dmg": 0.0, "heal": 0.0, "hits": 0.0, "teams": []}
                for s in skills
            },
        )
        for s in skills:
            rows[s]["battles"] += report.battles
        for row in report.skills:
            if row.skill_id not in rows:
                continue
            r = rows[row.skill_id]
            uses = row.uses_per_battle * report.battles
            r["uses"] += uses
            r["dmg"] += (row.avg_damage or 0.0) * uses
            r["heal"] += (row.avg_healed or 0.0) * uses
            r["hits"] += (row.hit_rate or 0.0) * uses
            r["teams"] = sorted(set(r["teams"]) | set(row.teams))
    return out


def cmd_run(args: argparse.Namespace) -> int:
    library = load_library(ROOT / "content")
    builds = args.builds.split(",")
    maps = default_sim_maps(library)
    started = time.perf_counter()
    specs = matrix_specs(library, builds, maps, SEEDS)
    reports = run_batches([spec for _, _, spec in specs], jobs=args.jobs)
    raw = [
        _raw_cell(build, map_id, library.map(map_id).archetype, report)
        for (build, map_id, _), report in zip(specs, reports, strict=True)
    ]
    infos = [MapInfo(map_id=m, archetype=library.map(m).archetype) for m in maps]
    report = assemble_matrix(builds, infos, raw, SEEDS)
    out = Path(args.out)
    out.write_bytes(MATRIX_ADAPTER.dump_json(report, indent=1))
    skills = _skill_rows(library, builds, specs, reports)
    out.with_suffix(".skills.json").write_text(
        json.dumps(skills, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    print(f"[{time.perf_counter() - started:7.1f}s] {len(builds)} builds × {len(maps)} maps")
    return 0


def _without(library: ContentLibrary, build: str, skill: str) -> ContentLibrary:
    builds = []
    for item in library.builds.builds:
        if item.id == build:
            hero = item.hero.model_copy(
                update={"skills": tuple(s for s in item.hero.skills if s != skill)}
            )
            builds.append(item.model_copy(update={"hero": hero}))
        else:
            builds.append(item)
    return dataclasses.replace(
        library, builds=library.builds.model_copy(update={"builds": tuple(builds)})
    )


def _win(report: MatrixReport, build: str) -> float:
    cs = [c for c in report.cells if c.build_id == build]
    return sum(c.ally_wins for c in cs) * 100 / max(1, sum(c.completed for c in cs))


def cmd_ablate(args: argparse.Namespace) -> int:
    library = load_library(ROOT / "content")
    maps = default_sim_maps(library)
    bases = [MATRIX_ADAPTER.validate_json(Path(p).read_bytes()) for p in args.base]
    started = time.perf_counter()
    pairs = [p.split(":") for p in args.pair]
    all_specs: list[Any] = []
    for build, skill in pairs:
        lib = _without(library, build, skill)
        all_specs += [
            (build, skill, spec) for _, _, spec in matrix_specs(lib, [build], maps, SEEDS)
        ]
    reports = run_batches([spec for _, _, spec in all_specs], jobs=args.jobs)
    agg: dict[tuple[str, str], list[int]] = {}
    for (build, skill, _), rep in zip(all_specs, reports, strict=True):
        a = agg.setdefault((build, skill), [0, 0])
        a[0] += rep.ally_wins
        a[1] += rep.completed
    print("| build | 拿掉的技能 | 基準勝率 | 拿掉後 | 差 |")
    print("|---|---|---|---|---|")
    for (build, skill), (wins, done) in agg.items():
        base = next((_win(b, build) for b in bases if build in b.builds), float("nan"))
        win = wins * 100 / max(1, done)
        print(f"| {build} | {skill} | {base:.1f} | {win:.1f} | {win - base:+.1f} |", flush=True)
    print(f"[{time.perf_counter() - started:7.1f}s] {len(pairs)} 組", file=sys.stderr)
    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    library = load_library(ROOT / "content")
    data: dict[str, Any] = {}
    for path in args.inputs:
        data.update(json.loads(Path(path).read_text(encoding="utf-8")))
    print(
        "| build | 技能 | 種類 | AP | 每場施放 | 命中率 | 每次傷害 | 每 AP 傷害 | 每次治療 | 也有誰用 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for build in sorted(data):
        for sid, r in data[build].items():
            skill = library.skills[sid]
            uses = r["uses"]
            per_battle = uses / max(1, r["battles"])
            ap = skill.ap_cost or 0
            dmg = r["dmg"] / uses if uses else 0.0
            heal = r["heal"] / uses if uses else 0.0
            hit = f"{r['hits'] / uses * 100:.0f}%" if uses and r["hits"] else "-"
            per_ap = f"{dmg / ap:.1f}" if ap and dmg else "-"
            teams = ",".join(t for t in r["teams"] if t != "ally") or "-"
            print(
                f"| {build} | {sid} | {skill.kind} | {ap or '-'} | {per_battle:.2f} | {hit} | {dmg:.1f} | {per_ap} | {heal:.1f} | {teams} |"
            )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("out")
    run.add_argument("--builds", required=True)
    run.add_argument("--jobs", type=int, default=6)
    run.set_defaults(func=cmd_run)
    abl = sub.add_parser("ablate")
    abl.add_argument("--base", action="append", required=True)
    abl.add_argument("--pair", action="append", required=True)
    abl.add_argument("--jobs", type=int, default=6)
    abl.set_defaults(func=cmd_ablate)
    sk = sub.add_parser("skills")
    sk.add_argument("inputs", nargs="+")
    sk.set_defaults(func=cmd_skills)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
