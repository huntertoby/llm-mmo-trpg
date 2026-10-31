"""BAL-13a：元素協同查修（只量不調，不改任何 content；覆寫只在記憶體內的 library 副本）。

用法::

    # 傷害來源拆解（從戰鬥事件算，不改引擎）
    uv run python scripts/synergy_audit.py decompose --builds build_fire,build_storm \
        --seeds 30 --jobs 4 --out docs/phases/BAL-13/13a_decompose.json
    # 覆寫選項試驗：目標 build 與連帶 build 的勝率，對照 BAL-12d 全矩陣（同種子 0..N-1）
    uv run python scripts/synergy_audit.py trial --option conduct_half --seeds 30 --jobs 4 \
        --matrix docs/phases/BAL-12/12d_matrix.json --builds build_fire,build_storm,...

拆解的分類（每筆 ``damage_dealt`` 的實際扣血 ``hp_before - hp_after``，與 metrics 同口徑）：

- ``skill_base``：技能的無條件傷害效果；``skill_cond``：技能的有條件傷害效果（協同加成：
  燃燒時 4d6、站在水上 2d8、連段第二道……）；``basic``：武器普攻；``passive``：被動觸發的攻擊傷害
- ``dot_burning:<來源>``：燃燒每回合傷害，來源是最後一次施加燃燒的技能或「表面」（火焰表面進入／
  回合開始時施加，施加者查不到單位）
- ``conduct``：雷電沿水擴散（含友方）；``explosion``：爆炸（油桶、技能）；其他 cause 照名稱
- 英雄的召喚物（``summon``）、隊友（``companion``）與環境（``env``，沒有 source）分開記
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    RoundStarted,
    SkillTriggered,
    SkillUsed,
    StatusApplied,
    StatusRemoved,
    TurnStarted,
    UnitDowned,
    UnitEscaped,
    UnitSpawned,
    UnitSummoned,
)
from trpg.shared.types import Team
from trpg.sim.batch import BatchSpec
from trpg.sim.matrix import (
    matrix_specs,
    run_matrix,
)
from trpg.sim.metrics import run_tracked
from trpg.sim.parallel import run_tasks

# ---------------------------------------------------------------------------
# 拆解
# ---------------------------------------------------------------------------

type Key = tuple[str, str, str]  # (side, origin/category, skill)


def _damage_effects(library: ContentLibrary) -> dict[str, tuple[bool, ...]]:
    """技能 → 傷害效果的「是否有條件」旗標（依效果順序）。"""
    out: dict[str, tuple[bool, ...]] = {}
    for sid, skill in library.skills.items():
        flags = tuple(e.condition is not None for e in skill.effects if e.type == "damage")
        if flags:
            out[sid] = flags
    return out


def decompose_battle(  # noqa: C901, PLR0912, PLR0915 - 單一事件迴圈
    spec: BatchSpec, seed: int, build: str, flags: dict[str, tuple[bool, ...]]
) -> dict[str, Any]:
    """跑一場戰鬥，回傳英雄一方的傷害來源拆解（可 JSON 序列化）。"""
    run = run_tracked(spec.setup, seed, spec.policy_factory(), max_actions=spec.max_actions)
    units = run.state.units
    hero = next(u.id for u in units.values() if u.template_id == build and u.team is Team.ALLY)
    team = {u.id: u.team for u in units.values()}
    summons: set[str] = set()
    burn_origin: dict[str, str] = {}
    burning: set[str] = set()
    current: str | None = None
    ctx_kind = "skill"  # skill／trigger
    use_idx = 0
    seen: Counter[tuple[int, str]] = Counter()
    acc: Counter[Key] = Counter()
    count: Counter[Key] = Counter()
    extra: Counter[str] = Counter()
    chain_hits: Counter[int] = Counter()
    scar_base = 0
    enemy_alive = {u.id for u in units.values() if u.team is Team.ENEMY and "summon" not in u.tags}
    enemy_alive -= {e.unit_id for e in run.events if isinstance(e, UnitSpawned | UnitSummoned)}
    for event in run.events:
        if isinstance(event, RoundStarted):
            extra["enemy_unit_rounds"] += len(enemy_alive)
        elif isinstance(event, UnitSpawned):
            if event.team is Team.ENEMY:
                enemy_alive.add(event.unit_id)
        elif isinstance(event, UnitEscaped):
            enemy_alive.discard(event.unit_id)
        elif isinstance(event, AttackRolled) and team.get(event.attacker_id) is Team.ENEMY:
            extra["enemy_attacks"] += 1
        if isinstance(event, UnitSummoned):
            if event.owner_id == hero:
                summons.add(event.unit_id)
            team[event.unit_id] = event.team
        elif isinstance(event, SkillUsed):
            current, ctx_kind = event.skill_id, "skill"
            use_idx += 1
            if event.unit_id == hero:
                extra[f"use:{event.skill_id}"] += 1
        elif isinstance(event, SkillTriggered):
            current, ctx_kind = event.skill_id, "trigger"
            use_idx += 1
        elif isinstance(event, AttackRolled):
            if event.skill_id is None:
                current, ctx_kind = None, "basic"
                use_idx += 1
        elif isinstance(event, StatusApplied):
            if event.status_id == "burning":
                burning.add(event.target_id)
                if event.source_id is None:
                    burn_origin[event.target_id] = "surface"
                elif event.source_id == hero and current is not None:
                    burn_origin[event.target_id] = current
                else:
                    burn_origin[event.target_id] = "other"
                extra["burn_applied:" + burn_origin[event.target_id]] += 1
        elif isinstance(event, StatusRemoved):
            if event.status_id == "burning":
                burning.discard(event.target_id)
        elif isinstance(event, UnitDowned):
            burning.discard(event.unit_id)
            enemy_alive.discard(event.unit_id)
        elif isinstance(event, TurnStarted):
            current, ctx_kind = None, "turn"
        elif isinstance(event, DamageDealt):
            amount = event.hp_before - event.hp_after
            src = event.source_id
            if src is not None and team.get(src) is Team.ENEMY:
                if event.target_id == hero:
                    extra["taken_hero"] += amount
                elif team.get(event.target_id) is Team.ALLY and event.target_id not in summons:
                    extra["taken_companion"] += amount
            if src == hero:
                origin = "hero"
            elif src in summons:
                origin = "summon"
            elif src is None:
                origin = "env"
            elif team.get(src) is Team.ALLY:
                origin = "companion"
            else:
                continue  # 敵方造成的傷害不是這裡的主題
            side = "enemy" if team[event.target_id] is not team[hero] else "friendly"
            cat: str = event.cause
            skill = current or "-"
            if event.cause == "attack":
                if ctx_kind == "basic" or current is None:
                    cat, skill = "basic", "-"
                elif ctx_kind == "trigger":
                    cat = "passive"
                else:
                    seen[(use_idx, event.target_id)] += 1
                    order = seen[(use_idx, event.target_id)] - 1
                    fl = flags.get(current, ())
                    uncond = [i for i, c in enumerate(fl) if not c]
                    cond_effect = order >= len(uncond) if len(uncond) < len(fl) else False
                    cat = "skill_cond" if cond_effect else "skill_base"
                    if side == "enemy" and origin == "hero":
                        chain_hits[use_idx] += 1 if order == 0 else 0
                if side == "enemy" and event.target_id in burning:
                    scar_base += amount
            elif event.cause == "status":
                cat = "dot_burning:" + burn_origin.get(event.target_id, "?")
                if event.element.value != "fire":
                    cat = f"dot_{event.element.value}"
                skill = "-"
            elif event.cause == "conduct":
                extra[f"conduct_hit:{side}"] += 1
            acc[(side, origin + "/" + cat, skill)] += amount
            count[(side, origin + "/" + cat, skill)] += 1
    enemy_hp = sum(u.max_hp for u in units.values() if u.team is Team.ENEMY)
    # 一次施放命中的目標數（只算英雄的 ``skill_base`` 第一道傷害）
    per_use = Counter(chain_hits.values())
    return {
        "map": spec.name.split(" × ")[-1],
        "win": run.state.winner is Team.ALLY,
        "rounds": run.state.round,
        "enemy_hp": enemy_hp,
        "dmg": {"|".join(k): v for k, v in acc.items()},
        "n": {"|".join(k): v for k, v in count.items()},
        "extra": dict(extra),
        "scar_base": scar_base,
        "targets_per_use": dict(per_use),
    }


def _decompose_worker(
    ctx: tuple[tuple[tuple[str, BatchSpec], ...], dict[str, tuple[bool, ...]]],
    task: tuple[int, int],
) -> dict[str, Any]:
    specs, flags = ctx
    index, seed = task
    build, spec = specs[index]
    try:
        out = decompose_battle(spec, seed, build, flags)
    except Exception as exc:  # 單場失敗不中止整批
        return {"error": f"{type(exc).__name__}: {exc}", "build": build, "map": spec.name}
    out["build"] = build
    out["seed"] = seed
    return out


def cmd_decompose(args: argparse.Namespace) -> int:
    library = load_library()
    maps = default_sim_maps(library)
    builds = args.builds.split(",")
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    specs = matrix_specs(library, builds, maps, seeds)
    pairs = tuple((b, s) for b, _, s in specs)
    tasks = [(i, seed) for i in range(len(pairs)) for seed in seeds]
    started = time.perf_counter()
    rows = run_tasks(_decompose_worker, (pairs, _damage_effects(library)), tasks, jobs=args.jobs)
    args.out.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8", newline="\n")
    errs = sum(1 for r in rows if "error" in r)
    print(f"decompose 完成：{len(rows)} 場，錯誤 {errs}，{time.perf_counter() - started:.0f}s")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    rows = [r for r in json.loads(args.input.read_text(encoding="utf-8")) if "error" not in r]
    for build in args.builds.split(","):
        mine = [r for r in rows if r["build"] == build]
        n = len(mine)
        wins = sum(r["win"] for r in mine)
        dmg: Counter[str] = Counter()
        for r in mine:
            dmg.update(r["dmg"])
        extra: Counter[str] = Counter()
        for r in mine:
            extra.update(r["extra"])
        enemy_total = sum(v for k, v in dmg.items() if k.startswith("enemy|"))
        print(
            f"\n### {build}：{n} 場，勝率 {wins * 100 / n:.1f}%，"
            f"平均輪數 {sum(r['rounds'] for r in mine) / n:.1f}，"
            f"每場對敵總傷害 {enemy_total / n:.1f}"
        )
        print("| 來源 | 每場傷害 | 占對敵傷害 |")
        print("|---|---|---|")
        cats: Counter[str] = Counter()
        for k, v in dmg.items():
            side, cat, _ = k.split("|")
            cats[f"{side}|{cat}"] += v
        for k, v in sorted(cats.items(), key=lambda kv: -kv[1]):
            share = f"{v * 100 / enemy_total:.1f}%" if k.startswith("enemy|") else "-"
            print(f"| {k} | {v / n:.2f} | {share} |")
        scar = sum(r["scar_base"] for r in mine)
        print(
            f"\n燃燒中目標吃到的攻擊傷害 {scar / n:.2f}/場（灼傷之痕 +10% 約佔其 {100 / 11:.1f}%）"
        )
        print("| 技能（英雄）/ 類別 | 每場傷害 | 每場次數 |")
        print("|---|---|---|")
        per_skill: Counter[str] = Counter()
        per_n: Counter[str] = Counter()
        for r in mine:
            for k, v in r["dmg"].items():
                side, cat, skill = k.split("|")
                if side == "enemy" and cat.startswith("hero/"):
                    per_skill[f"{skill} {cat.split('/')[1]}"] += v
                    per_n[f"{skill} {cat.split('/')[1]}"] += r["n"][k]
        for k, v in sorted(per_skill.items(), key=lambda kv: -kv[1])[:14]:
            print(f"| {k} | {v / n:.2f} | {per_n[k] / n:.2f} |")
        uses = {k.removeprefix("use:"): v for k, v in extra.items() if k.startswith("use:")}
        print(
            "\n施放次數/場："
            + "，".join(
                f"{k.removeprefix('skill_')} {v / n:.2f}"
                for k, v in sorted(uses.items(), key=lambda kv: -kv[1])
            )
        )
        tpu: Counter[int] = Counter()
        for r in mine:
            for k, v in r["targets_per_use"].items():
                tpu[int(k)] += v
        print(
            "burn/conduct 事件："
            + "，".join(
                f"{k} {v / n:.2f}" for k, v in sorted(extra.items()) if not k.startswith("use:")
            )
        )
    return 0


# ---------------------------------------------------------------------------
# 覆寫選項（只在 library 副本；key 為選項名）
# ---------------------------------------------------------------------------


def _with_ruleset(library: ContentLibrary, **tables: Any) -> ContentLibrary:
    ruleset = library.ruleset.model_copy(update=tables)
    ruleset.model_post_init(None)
    return dataclasses.replace(library, ruleset=ruleset)


def _with_skills(library: ContentLibrary, changed: dict[str, Any]) -> ContentLibrary:
    skills = {**library.skills, **changed}
    table = library.ruleset.skills.model_copy(
        update={"skills": tuple(skills[s.id] for s in library.ruleset.skills.skills)}
    )
    lib = _with_ruleset(library, skills=table)
    return dataclasses.replace(lib, skills=skills)


def _edit_interaction(library: ContentLibrary, rule_id: str, **outcome: Any) -> ContentLibrary:
    rules = []
    for rule in library.ruleset.interactions.rules:
        if rule.id == rule_id:
            then = tuple(o.model_copy(update=outcome) for o in rule.then)
            rules.append(rule.model_copy(update={"then": then}))
        else:
            rules.append(rule)
    table = library.ruleset.interactions.model_copy(update={"rules": tuple(rules)})
    return _with_ruleset(library, interactions=table)


def _edit_status(library: ContentLibrary, status_id: str, **fields: Any) -> ContentLibrary:
    items = []
    for st in library.ruleset.statuses.statuses:
        items.append(st.model_copy(update=fields) if st.id == status_id else st)
    table = library.ruleset.statuses.model_copy(update={"statuses": tuple(items)})
    return _with_ruleset(library, statuses=table)


def _edit_surface(library: ContentLibrary, surface_id: str, **fields: Any) -> ContentLibrary:
    items = []
    for sf in library.ruleset.surfaces.surfaces:
        items.append(sf.model_copy(update=fields) if sf.id.value == surface_id else sf)
    table = library.ruleset.surfaces.model_copy(update={"surfaces": tuple(items)})
    return _with_ruleset(library, surfaces=table)


def _scale_damage_effect(skill: Any, index: int, dice: str) -> Any:
    effects = list(skill.effects)
    seen = -1
    for i, e in enumerate(effects):
        if e.type == "damage":
            seen += 1
            if seen == index:
                effects[i] = e.model_copy(update={"dice": dice})
    return skill.model_copy(update={"effects": tuple(effects)})


def _skill_edit(library: ContentLibrary, skill_id: str, **fields: Any) -> ContentLibrary:
    return _with_skills(library, {skill_id: library.skills[skill_id].model_copy(update=fields)})


def apply_option(library: ContentLibrary, option: str) -> ContentLibrary:
    """命名的覆寫選項（全部是內容層的數值覆寫，引擎行為不變）。"""
    if option == "baseline":
        return library
    handlers = OPTIONS
    if option not in handlers:
        raise ValueError(f"未知的選項：{option}（可用：{', '.join(handlers)}）")
    result: ContentLibrary = handlers[option](library)
    return result


def _conduct(permille: int) -> Any:
    def apply(lib: ContentLibrary) -> ContentLibrary:
        lib = _edit_interaction(lib, "lightning_conducts_water", damage_permille=permille)
        return _edit_interaction(lib, "lightning_conducts_object", damage_permille=permille)

    return apply


def _chain_jumps(jumps: int) -> Any:
    def apply(lib: ContentLibrary) -> ContentLibrary:
        skill = lib.skills["skill_chain_lightning"]
        shape = skill.shape.model_copy(update={"jumps": jumps})
        return _skill_edit(lib, "skill_chain_lightning", shape=shape)

    return apply


def _dice(skill_id: str, index: int, dice: str) -> Any:
    def apply(lib: ContentLibrary) -> ContentLibrary:
        edited = _scale_damage_effect(lib.skills[skill_id], index, dice)
        return _with_skills(lib, {skill_id: edited})

    return apply


def _burn_tick(dice: str) -> Any:
    def apply(lib: ContentLibrary) -> ContentLibrary:
        status = next(st for st in lib.ruleset.statuses.statuses if st.id == "burning")
        assert status.on_turn_start_damage is not None
        tick = status.on_turn_start_damage.model_copy(update={"dice": dice})
        return _edit_status(lib, "burning", on_turn_start_damage=tick)

    return apply


def _abl_ashen_surface(lib: ContentLibrary) -> ContentLibrary:
    """對照用（拆掉一層看勝率掉多少）：灰燼誓約不再產生火焰表面。"""
    skill = lib.skills["skill_ashen_oath"]
    effects = tuple(e for e in skill.effects if e.type != "create_surface")
    return _skill_edit(lib, "skill_ashen_oath", effects=effects)


def _abl_ember_ward(lib: ContentLibrary) -> ContentLibrary:
    """對照用：餘燼護體的護盾 1d6 → 1d1。"""
    skill = lib.skills["skill_ember_ward"]
    effects = tuple(
        e.model_copy(update={"dice": "1d1"}) if e.type == "shield" else e for e in skill.effects
    )
    return _skill_edit(lib, "skill_ember_ward", effects=effects)


def _fire_surface_enter_only(lib: ContentLibrary) -> ContentLibrary:
    return _edit_surface(lib, "fire", on_turn_start=None)


OPTIONS: dict[str, Any] = {
    "conduct_500": _conduct(500),
    "conduct_750": _conduct(750),
    "chain_jumps_1": _chain_jumps(1),
    "twin_1d4": _dice("skill_twin_strike", 0, "1d4"),
    "fire_surface_enter_only": _fire_surface_enter_only,
    "abl_ashen_surface": _abl_ashen_surface,
    "abl_ember_ward": _abl_ember_ward,
    "burn_tick_1d4": _burn_tick("1d4"),
    "cinder_cond_3d6": _dice("skill_cinder_burst", 1, "3d6"),
}


def _rates(report: Any, builds: list[str]) -> dict[str, tuple[float, float, float, float]]:
    """build → (勝率%, 英雄 DPR, 英雄存活%, 平均輪數)。"""
    out: dict[str, tuple[float, float, float, float]] = {}
    for b in builds:
        cs = [c for c in report.cells if c.build_id == b]
        done = sum(c.completed for c in cs)
        out[b] = (
            sum(c.ally_wins for c in cs) * 100 / done,
            sum(c.hero_dpr for c in cs) / len(cs),
            sum(c.hero_survival for c in cs) * 100 / len(cs),
            sum(c.rounds_mean for c in cs) / len(cs),
        )
    return out


def _json_baseline(path: Path, seeds: int) -> dict[str, tuple[float, float]]:
    """由 decompose 的 JSON 取前 ``seeds`` 個種子的基準：build → (勝率%, 平均輪數)。"""
    rows = [r for r in json.loads(path.read_text(encoding="utf-8")) if "error" not in r]
    out: dict[str, tuple[float, float]] = {}
    for b in sorted({r["build"] for r in rows}):
        mine = [r for r in rows if r["build"] == b and r["seed"] < seeds]
        out[b] = (
            sum(r["win"] for r in mine) * 100 / len(mine),
            sum(r["rounds"] for r in mine) / len(mine),
        )
    return out


def cmd_trial(args: argparse.Namespace) -> int:
    base = load_library()
    maps = default_sim_maps(base)
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    known = _json_baseline(args.baseline_json, args.seed_start + args.seeds)
    started = time.perf_counter()
    cache: dict[str, tuple[float, float]] = dict(known)
    for spec in args.run:
        option, _, build_text = spec.partition(":")
        builds = build_text.split(",")
        lib = apply_option(base, option)
        missing = [b for b in builds if b not in cache]
        if missing:
            ref_report = run_matrix(base, missing, maps, seeds, jobs=args.jobs)
            for b, v in _rates(ref_report, missing).items():
                cache[b] = (v[0], v[3])
            print(
                f"[baseline {','.join(missing)} 完成 {time.perf_counter() - started:.0f}s]",
                file=sys.stderr,
                flush=True,
            )
        trial = run_matrix(lib, builds, maps, seeds, jobs=args.jobs)
        got = _rates(trial, builds)
        print(f"\n## {option}（每格 {len(seeds)} 場）")
        print("| build | 基準勝率 | 本次勝率 | 差 | 基準輪數 | 本次輪數 | DPR | 存活% |")
        print("|---|---|---|---|---|---|---|---|")
        for b in builds:
            w, dpr, surv, rounds = got[b]
            print(
                f"| {b} | {cache[b][0]:.1f} | {w:.1f} | {w - cache[b][0]:+.1f} "
                f"| {cache[b][1]:.1f} | {rounds:.1f} | {dpr:.1f} | {surv:.0f} |",
                flush=True,
            )
        print(f"[{option} 完成 {time.perf_counter() - started:.0f}s]", file=sys.stderr, flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("decompose")
    p.add_argument("--builds", required=True)
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(fn=cmd_decompose)
    p = sub.add_parser("report")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--builds", required=True)
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("trial")
    p.add_argument("--run", action="append", required=True, help="選項:build,build,…")
    p.add_argument("--baseline-json", type=Path, required=True)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--jobs", type=int, default=1)
    p.set_defaults(fn=cmd_trial)
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
