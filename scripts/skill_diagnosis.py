"""BAL-12a：build 與資源的診斷與記憶體內覆寫試驗（只量不調，不改任何 content）。

用法::

    # 完整矩陣（存 JSON，供之後重新排名）
    uv run python scripts/skill_diagnosis.py matrix --seeds 5 --jobs 4 \
        --out docs/phases/BAL-12/12a_matrix.json
    # 診斷：每個技能的使用率、命中率、平均傷害、未使用
    uv run python scripts/skill_diagnosis.py diag --builds build_assassin,build_fire \
        --seeds 6 --jobs 4
    # 試驗：套用覆寫（只在 library 副本），重新排名
    uv run python scripts/skill_diagnosis.py trial --builds build_assassin --seeds 5 --jobs 4 \\
        --matrix docs/phases/BAL-12/12a_matrix.json --edit "skill_pick_off:dmg=1300"
    # 火系法力：Boss 戰情境的法力短缺
    uv run python scripts/skill_diagnosis.py mana --seeds 20 --jobs 4 \
        --edit "@build:build_fire:mana*0.9"

覆寫語法（``--edit``，可重複；``;`` 分隔多筆）：
``<技能ID（逗號分隔）、@標籤或@build:ID>:<鍵>=<值>|<鍵>*<倍率>``。
鍵：``dmg``（傷害效果的 ``multiplier_permille`` 乘以倍率‰，如 ``dmg=1300``）、
``mana``／``stamina``／``cd``（增減；``mana=-1``）、
``dur``（召喚持續回合增減）、``mana*0.9``（乘以倍率，費用至少 1，四捨五入）。
法術技的 ``dmg`` 改設技能層級 ``damage_permille``（法術傷害不看效果的 multiplier_permille）。
所有覆寫都只作用在記憶體內的 library 副本。
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from collections import defaultdict
from pathlib import Path

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, Ruleset, load_library
from trpg.content.skills.skill import SkillDef
from trpg.sim.attack_flow_report import SCENARIOS
from trpg.sim.batch import run_batches
from trpg.sim.matrix import (
    MATRIX_ADAPTER,
    MapInfo,
    MatrixReport,
    RawCell,
    assemble_matrix,
    matrix_specs,
    run_matrix,
)
from trpg.sim.resource_report import run_resources, summarize_resources


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


def apply_edit(skill: SkillDef, key: str, op: str, value: float) -> SkillDef:
    """對單一技能套用一個覆寫。"""
    if key == "dmg":
        if skill.category == "spell":
            # 法術技的傷害不看效果的 multiplier_permille（引擎只用骰子＋屬性）；改用技能層級的
            # damage_permille（高變異折扣，引擎對所有傷害效果一律乘上）。
            old = skill.damage_permille if skill.damage_permille is not None else 1000
            return skill.model_copy(update={"damage_permille": _round_half_up(old * value / 1000)})
        effects = []
        for eff in skill.effects:
            e = eff
            if e.type == "damage":
                old = e.multiplier_permille if e.multiplier_permille is not None else 1000
                e = e.model_copy(update={"multiplier_permille": _round_half_up(old * value / 1000)})
            effects.append(e)
        return skill.model_copy(update={"effects": tuple(effects)})
    if key == "dur":
        effects = [
            e.model_copy(update={"duration": max(1, (e.duration or 1) + int(value))})
            if e.type == "summon"
            else e
            for e in skill.effects
        ]
        return skill.model_copy(update={"effects": tuple(effects)})
    if key in ("mana", "stamina", "cd"):
        field = "cooldown" if key == "cd" else key
        old_v = getattr(skill.cost, field) or 0
        if op == "*":
            new_v = max(1, _round_half_up(old_v * value)) if old_v else 0
        else:
            new_v = max(0, old_v + int(value))
        if field == "cooldown" and new_v < 1:
            new_v = None  # type: ignore[assignment]
        return skill.model_copy(update={"cost": skill.cost.model_copy(update={field: new_v})})
    raise ValueError(f"未知的覆寫鍵：{key}")


def parse_edits(text: str) -> list[tuple[str, str, str, float]]:
    """``skill:key=val|key*val;…`` → ``[(selector, key, op, value)]``。"""
    out: list[tuple[str, str, str, float]] = []
    for part in (p.strip() for p in text.split(";") if p.strip()):
        head = 2 if part.startswith("@build:") else 1
        *sel, rest = part.split(":", head)
        selector = ":".join(sel)
        for item in rest.split("|"):
            op = "*" if "*" in item else "="
            key, _, val = item.partition(op)
            out.append((selector.strip(), key.strip(), op, float(val)))
    return out


def select_skills(library: ContentLibrary, selector: str) -> list[str]:
    if selector.startswith("@build:"):
        hero = library.builds.by_id()[selector.removeprefix("@build:")].hero
        return [s for s in hero.skills if library.skills[s].kind == "active"]
    if selector.startswith("@"):
        tag = selector[1:]
        return sorted(s.id for s in library.skills.values() if tag in s.tags and s.kind == "active")
    ids = selector.split(",")
    unknown = [s for s in ids if s not in library.skills]
    if unknown:
        raise ValueError(f"未知的技能：{','.join(unknown)}")
    return ids


def with_edits(library: ContentLibrary, edits: list[tuple[str, str, str, float]]) -> ContentLibrary:
    """套用覆寫的 library 副本（不動原物件）。"""
    if not edits:
        return library
    skills = dict(library.skills)
    for selector, key, op, value in edits:
        for skill_id in select_skills(library, selector):
            skills[skill_id] = apply_edit(skills[skill_id], key, op, value)
    ruleset: Ruleset = library.ruleset
    table = ruleset.skills.model_copy(
        update={"skills": tuple(skills[s.id] for s in ruleset.skills.skills)}
    )
    new_ruleset = ruleset.model_copy(update={"skills": table})
    new_ruleset.model_post_init(None)
    return dataclasses.replace(library, skills=skills, ruleset=new_ruleset)


def _progress(started: float, name: str) -> None:
    print(f"[{time.perf_counter() - started:7.1f}s] {name}", file=sys.stderr, flush=True)


def raw_cells(report: MatrixReport) -> list[RawCell]:
    return [
        RawCell(
            build_id=c.build_id,
            map_id=c.map_id,
            archetype=c.archetype,
            battles=c.battles,
            completed=c.completed,
            ally_wins=c.ally_wins,
            draws=c.draws,
            hero_dpr=c.hero_dpr,
            hero_survival=c.hero_survival,
            rounds_mean=c.rounds_mean,
            errors=c.errors,
            hero_healing=c.hero_healing,
            hero_shield=c.hero_shield,
            hero_taken=c.hero_taken,
            teammate_survival=c.teammate_survival,
        )
        for c in report.cells
    ]


def cmd_matrix(args: argparse.Namespace) -> int:
    library = load_library()
    maps = default_sim_maps(library)
    builds = [b.id for b in library.builds.sim_builds()]
    started = time.perf_counter()
    report = run_matrix(
        library, builds, maps, range(args.seed_start, args.seed_start + args.seeds), jobs=args.jobs
    )
    args.out.write_bytes(MATRIX_ADAPTER.dump_json(report))
    _progress(started, f"matrix 完成：{len(builds)} builds × {len(maps)} maps")
    return 0


def _hero_skill_rows(
    library: ContentLibrary, builds: list[str], seeds: range, jobs: int
) -> dict[str, dict[str, list[float]]]:
    maps = default_sim_maps(library)
    specs = matrix_specs(library, builds, maps, list(seeds))
    reports = run_batches([s for _, _, s in specs], jobs=jobs)
    acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0] * 5))
    known = library.builds.by_id()
    for (build, _, _), rep in zip(specs, reports, strict=True):
        hero = known[build].hero
        mine = set(hero.skills)
        n = rep.completed
        for row in rep.skills:
            if row.skill_id not in mine or "ally" not in row.teams:
                continue
            a = acc[build][row.skill_id]
            uses = row.uses_per_battle * n
            a[0] += uses
            a[1] += n
            a[2] += (row.hit_rate or 0.0) * uses
            a[3] += (row.avg_damage or 0.0) * uses
            a[4] += (row.avg_healed or 0.0) * uses
    return acc


def cmd_diag(args: argparse.Namespace) -> int:
    library = load_library()
    builds = args.builds.split(",")
    started = time.perf_counter()
    acc = _hero_skill_rows(library, builds, range(args.seeds), args.jobs)
    known = library.builds.by_id()
    for build in builds:
        print(f"\n### {build}（{known[build].hero.weapon}）")
        print("| 技能 | 階 | 類型 | 每場使用 | 命中率 | 每次傷害 | 每次治療 |")
        print("|---|---|---|---|---|---|---|")
        for skill_id in known[build].hero.skills:
            sk = library.skills[skill_id]
            a = acc[build].get(skill_id)
            if a is None or a[0] == 0:
                print(f"| {skill_id} | {sk.tier} | {sk.kind} | 0（未使用） | - | - | - |")
                continue
            uses, n, hit, dmg, heal = a
            print(
                f"| {skill_id} | {sk.tier} | {sk.kind} | {uses / n:.2f} | {hit / uses * 100:.0f}% "
                f"| {dmg / uses:.1f} | {heal / uses:.1f} |"
            )
    _progress(started, "diag 完成")
    return 0


def _summary(report: MatrixReport, build: str) -> str:
    cells = [c for c in report.cells if c.build_id == build]
    done = sum(c.completed for c in cells)
    rate = sum(c.ally_wins for c in cells) * 100 / done if done else 0.0
    dpr = sum(c.hero_dpr for c in cells) / len(cells)
    surv = sum(c.hero_survival for c in cells) * 100 / len(cells)
    tops = [a.archetype for a in report.archetype_cells if a.build_id == build and a.top]
    ranks = {a.archetype: a.rank for a in report.archetype_cells if a.build_id == build}
    rank_text = " ".join(f"{k[:6]}={v}" for k, v in sorted(ranks.items()))
    return f"勝率 {rate:.1f}%｜英雄存活 {surv:.0f}%｜DPR {dpr:.1f}｜前段 {len(tops)} 類｜名次 {rank_text}"


def cmd_trial(args: argparse.Namespace) -> int:
    base = load_library()
    maps = default_sim_maps(base)
    builds = args.builds.split(",")
    reference = MATRIX_ADAPTER.validate_json(args.matrix.read_bytes())
    started = time.perf_counter()
    infos = list(reference.maps)
    print(
        f"參考矩陣：seeds={len(reference.seeds)}；試驗 seeds={args.seeds}（不同種子數只影響雜訊）"
    )
    for label, edit_text in (("baseline", ""), *((e, e) for e in args.edit)):
        library = with_edits(base, parse_edits(edit_text))
        trial = run_matrix(
            library,
            builds,
            maps,
            range(args.seed_start, args.seed_start + args.seeds),
            jobs=args.jobs,
        )
        kept = [c for c in raw_cells(reference) if c.build_id not in builds]
        fresh = raw_cells(trial)
        merged = assemble_matrix(
            [*reference.builds],
            [MapInfo(map_id=i.map_id, archetype=i.archetype) for i in infos],
            [*kept, *fresh],
            reference.seeds,
        )
        print(f"\n## {label}")
        for b in builds:
            print(f"- {b}：{_summary(merged, b)}")
        _progress(started, label)
    return 0


def cmd_mana(args: argparse.Namespace) -> int:
    base = load_library()
    scenario = tuple(s for s in SCENARIOS if s.id == args.scenario)
    builds = tuple(args.builds.split(","))
    started = time.perf_counter()
    for label, edit_text in (("baseline", ""), *((e, e) for e in args.edit)):
        library = with_edits(base, parse_edits(edit_text))
        cells = summarize_resources(
            run_resources(
                library,
                scenarios=scenario,
                builds=builds,
                seeds=args.seeds,
                seed_start=args.seed_start,
                jobs=args.jobs,
            )
        )
        print(f"\n## {label}")
        for c in cells:
            print(
                f"- {c.scenario} {c.build}：法力不足 {c.mana_short * 100:.1f}%｜勝率 "
                f"{c.win_rate * 100:.1f}%｜傷害 {c.damage:.0f}（n={c.battles}）"
            )
        _progress(started, label)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("matrix", cmd_matrix),
        ("diag", cmd_diag),
        ("trial", cmd_trial),
        ("mana", cmd_mana),
    ):
        p = sub.add_parser(name)
        p.add_argument("--jobs", type=int, default=1)
        p.add_argument("--seeds", type=int, default=5)
        p.add_argument("--seed-start", type=int, default=0)
        p.set_defaults(fn=fn)
        if name == "matrix":
            p.add_argument("--out", type=Path, required=True)
        if name in ("diag", "trial", "mana"):
            p.add_argument("--builds", default="build_fire" if name == "mana" else "")
        if name in ("trial", "mana"):
            p.add_argument("--edit", action="append", default=[])
        if name == "trial":
            p.add_argument("--matrix", type=Path, required=True)
        if name == "mana":
            p.add_argument("--scenario", default="boss")
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
