"""BAL-13a：元素協同查修（只量不調，不改任何 content；覆寫只在記憶體內的 library 副本）。

用法::

    # 傷害來源拆解（從戰鬥事件算，不改引擎）
    uv run python scripts/synergy_audit.py decompose --builds build_fire,build_storm \
        --seeds 30 --jobs 4 --out docs/phases/BAL-13/13a_decompose.json
    # 覆寫選項試驗：目標 build 與連帶 build 的勝率，對照 BAL-12d 全矩陣（同種子 0..N-1）
    uv run python scripts/synergy_audit.py trial --option conduct_half --seeds 30 --jobs 4 \
        --matrix docs/phases/BAL-12/12d_matrix.json --builds build_fire,build_storm,...

拆解的分類（每筆 ``damage_dealt`` 的實際扣血 ``hp_before - hp_after``，與 ``trpg.sim.metrics`` 同口徑）：

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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    SkillTriggered,
    SkillUsed,
    StatusApplied,
    StatusRemoved,
    TurnStarted,
    UnitDowned,
    UnitSummoned,
)
from trpg.shared.types import Team
from trpg.sim.batch import BatchSpec
from trpg.sim.matrix import (
    MATRIX_ADAPTER,
    MapInfo,
    assemble_matrix,
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
    for event in run.events:
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
        elif isinstance(event, TurnStarted):
            current, ctx_kind = None, "turn"
        elif isinstance(event, DamageDealt):
            amount = event.hp_before - event.hp_after
            src = event.source_id
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
            cat = event.cause
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
                    cond_effect = (
                        order >= len(uncond)
                        if len(uncond) < len(fl)
                        else False
                    )
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
        print(f"\n### {build}：{n} 場，勝率 {wins * 100 / n:.1f}%，"
              f"平均輪數 {sum(r['rounds'] for r in mine) / n:.1f}，"
              f"每場對敵總傷害 {enemy_total / n:.1f}")
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
        print(f"\n燃燒中目標吃到的攻擊傷害 {scar / n:.2f}/場（灼傷之痕 +10% 約佔其 {100 / 11:.1f}%）")
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
        print("\n施放次數/場：" + "，".join(f"{k.removeprefix('skill_')} {v / n:.2f}" for k, v in
                                    sorted(uses.items(), key=lambda kv: -kv[1])))
        tpu: Counter[int] = Counter()
        for r in mine:
            for k, v in r["targets_per_use"].items():
                tpu[int(k)] += v
        print("burn/conduct 事件：" + "，".join(f"{k} {v / n:.2f}" for k, v in sorted(extra.items())
                                           if not k.startswith("use:")))
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
            rule = rule.model_copy(update={"then": then})
        rules.append(rule)
    table = library.ruleset.interactions.model_copy(update={"rules": tuple(rules)})
    return _with_ruleset(library, interactions=table)


def _edit_status(library: ContentLibrary, status_id: str, **fields: Any) -> ContentLibrary:
    items = []
    for st in library.ruleset.statuses.statuses:
        if st.id == status_id:
            st = st.model_copy(update=fields)
        items.append(st)
    table = library.ruleset.statuses.model_copy(update={"statuses": tuple(items)})
    return _with_ruleset(library, statuses=table)


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
    return handlers[option](library)


OPTIONS: dict[str, Any] = {}


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
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
