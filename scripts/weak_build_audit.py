# ruff: noqa: E501, PLR2004
"""BAL-13b：弱 build（gambler、seer、assassin）診斷（只量不調，不改任何 content、AI 與引擎）。

用法::

    # 收集：每場戰鬥的英雄決策紀錄（AI 候選分數）＋事件統計
    uv run python scripts/weak_build_audit.py collect \
        --builds build_gambler,build_seer,build_assassin,build_ranged,build_striker,build_tank,build_bomber \
        --seeds 30 --jobs 4 --out docs/phases/BAL-13/13b_collect.json
    # 報表（Markdown 表格；--input 可直接給 .json.gz）
    uv run python scripts/weak_build_audit.py report --input docs/phases/BAL-13/13b_collect.json.gz
    uv run python scripts/weak_build_audit.py deep --input docs/phases/BAL-13/13b_collect.json.gz
    # 覆寫對照（只在記憶體內的 library 副本）
    uv run python scripts/weak_build_audit.py trial --run "<選項>:<build>" --seeds 30 --jobs 4 \
        --baseline-json docs/phases/BAL-13/13b_collect.json

收集內容（英雄＝build 英雄；敵方傷害只記對英雄一方的）：

- ``decisions``：英雄每個決策點（呼叫 AI 的當下）：輪數、HP、法力、耐力、AP、與最近敵人的距離（曼哈頓）、
  2 格內敵人數、「候選動作的最高分數」（依標籤：``skill:<id>``、``attack``、``move``、``defend``）與實際選的標籤
  （``end`` ＝ 結束回合）；選技能或普攻時另記目標的範本、目標身上是否已有標記／增益。
- ``skills``：每招的施放次數、命中判定與命中、傷害（對敵方，實際扣血）、暴擊、背刺命中。
- ``death``：英雄倒地的輪數、死前 2 輪承受傷害依（來源範本、cause）的分解、來源數。
- ``focus``：敵方每輪攻擊的目標分佈（英雄／隊友／召喚物）。
- ``marks``：咒印（``marked``）的施加與之後窗口內友方的攻擊（同目標、不同目標、命中率）。
- 其他：賭注結果、反噬、驅散／奪取的狀態數、揭露、回復法力量、隊友倒地輪數。
"""

from __future__ import annotations

import argparse
import dataclasses
import gzip
import json
import sys
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.actions import Action, Attack, Defend, EndTurn, Move, UseSkill
from trpg.engine.ai.utility import ActionScore, UtilityAI
from trpg.engine.events import (
    AttackRolled,
    BacklashTriggered,
    DamageDealt,
    GambleRolled,
    ReactionTriggered,
    ResourceRestored,
    SkillTriggered,
    SkillUsed,
    StatusApplied,
    StatusRemoved,
    TrapRevealed,
    TurnStarted,
    UnitDowned,
    UnitSummoned,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Team
from trpg.sim.batch import BatchSpec, UtilityPolicyFactory
from trpg.sim.matrix import matrix_specs, run_matrix
from trpg.sim.metrics import run_tracked
from trpg.sim.parallel import run_tasks

# ---------------------------------------------------------------------------
# 錄影用的 AI：行為與 UtilityAI 完全相同，只多記錄英雄每次決策的候選分數
# ---------------------------------------------------------------------------


def _label(action: Action) -> str:
    if isinstance(action, UseSkill):
        return "skill:" + action.skill_id
    if isinstance(action, Attack):
        return "attack"
    if isinstance(action, Move):
        return "move"
    if isinstance(action, Defend):
        return "defend"
    if isinstance(action, EndTurn):
        return "end"
    return action.type


def _dist(a: UnitState, b: UnitState) -> int:
    return abs(a.pos.x - b.pos.x) + abs(a.pos.y - b.pos.y)


def _status_ids(unit: UnitState) -> list[str]:
    return sorted(s.status_id for s in unit.statuses)


class RecordingAI(UtilityAI):
    """記錄 ``hero_template`` 的我方英雄每次決策（rank 的分數與最後選擇）。"""

    def __init__(self, profiles: Any, hero_template: str) -> None:
        super().__init__(profiles)
        self.hero_template = hero_template
        self.log: list[dict[str, Any]] = []
        self._last: list[ActionScore] | None = None

    def rank(self, state: BattleState) -> list[ActionScore]:
        ranked = super().rank(state)
        self._last = ranked
        return ranked

    def __call__(self, state: BattleState) -> Action:
        unit = state.active
        self._last = None
        action = super().__call__(state)
        if unit is None or unit.team is not Team.ALLY or unit.template_id != self.hero_template:
            return action
        enemies = [u for u in state.living_units() if u.team is not unit.team]
        near = sorted(_dist(unit, e) for e in enemies)
        cands: dict[str, float] = {}
        scored: list[ActionScore] = self._last or []
        for sc in scored:
            lab = _label(sc.action)
            val = float(sc.score)
            if lab not in cands or val > cands[lab]:
                cands[lab] = round(val, 2)
        rec: dict[str, Any] = {
            "r": state.round,
            "hp": unit.hp,
            "mhp": unit.max_hp,
            "mana": unit.mana,
            "sta": unit.stamina,
            "ap": unit.ap,
            "mp": unit.move_points,
            "near": near[0] if near else -1,
            "n2": sum(1 for d in near if d <= 2),
            "ne": len(enemies),
            "pos": [unit.pos.x, unit.pos.y],
            "cd": sorted(k for k, v in unit.cooldowns.items() if v > 0),
            "c": cands,
            "pick": _label(action),
            "pick_score": None,
        }
        for sc in self._last or []:
            if sc.action == action:
                rec["pick_score"] = round(float(sc.score), 2)
                break
        tid = getattr(action, "target_id", None)
        if tid is not None and tid in state.units:
            tgt = state.units[tid]
            rec["tt"] = tgt.template_id
            rec["tteam"] = "ally" if tgt.team is unit.team else "enemy"
            rec["thp"] = round(tgt.hp / max(1, tgt.max_hp), 2)
            rec["tst"] = _status_ids(tgt)
            rec["tdist"] = _dist(unit, tgt)
        self.log.append(rec)
        return action


# ---------------------------------------------------------------------------
# 單場收集
# ---------------------------------------------------------------------------


def collect_battle(  # noqa: C901, PLR0912, PLR0915 - 單一事件迴圈
    spec: BatchSpec, seed: int, build: str
) -> dict[str, Any]:
    factory = spec.policy_factory
    assert isinstance(factory, UtilityPolicyFactory)
    ai = RecordingAI(factory.profiles, build)
    run = run_tracked(spec.setup, seed, ai, max_actions=spec.max_actions)
    units = run.state.units
    hero = next(u.id for u in units.values() if u.template_id == build and u.team is Team.ALLY)
    team = {u.id: u.team for u in units.values()}
    tpl = {u.id: u.template_id for u in units.values()}
    summons: set[str] = set()
    current = "-"
    pending = ""
    roll_name: dict[str, str] = {}
    skills: dict[str, Counter[str]] = {}
    marked: set[str] = set()
    mark_open: dict[str, dict[str, int]] = {}
    marks: list[dict[str, int]] = []
    ally_vs_marked: Counter[str] = Counter()
    taken: Counter[str] = Counter()
    taken_round: list[tuple[int, str, str, int]] = []
    focus: Counter[str] = Counter()
    hero_down = 0
    ally_down: list[int] = []
    misc: Counter[str] = Counter()
    hero_turns: list[list[int]] = []
    gamble: list[list[Any]] = []
    removed: Counter[str] = Counter()
    hp_round: dict[int, int] = {}

    def sk(name: str) -> Counter[str]:
        return skills.setdefault(name, Counter())

    for ev in run.events:
        rnd = ev.round
        if isinstance(ev, UnitSummoned):
            team[ev.unit_id] = ev.team
            tpl[ev.unit_id] = tpl.get(ev.unit_id, "summon")
            if ev.owner_id == hero:
                summons.add(ev.unit_id)
        elif isinstance(ev, TurnStarted):
            current = "-"
            pending = ""
            if ev.unit_id == hero:
                hero_turns.append([rnd, ev.ap, ev.mana, ev.stamina])
        elif isinstance(ev, SkillUsed):
            if ev.unit_id == hero:
                current = ev.skill_id
                pending = ""
                c = sk(current)
                c["uses"] += 1
                c["ap"] += ev.ap
                c["hp_spent"] += ev.hp_spent
                c["mana"] += ev.mana
                c["stamina"] += ev.stamina
        elif isinstance(ev, SkillTriggered):
            if ev.unit_id == hero:
                pending = "trig:" + ev.skill_id
                sk(pending)["uses"] += 1
        elif isinstance(ev, ReactionTriggered):
            if ev.unit_id == hero:
                pending = "rx:" + ev.reaction
                sk(pending)["uses"] += 1
        elif isinstance(ev, AttackRolled):
            att_team = team.get(ev.attacker_id)
            if ev.attacker_id == hero:
                name = pending or ev.skill_id or "basic"
                if not pending and ev.skill_id is None:
                    current = "basic"
                pending = ""
                roll_name[ev.target_id] = name
                c = sk(name)
                c["rolls"] += 1
                c["hits"] += int(ev.hit)
                c["crits"] += int(ev.crit)
                c["backstab"] += int(ev.backstab > 0 and ev.hit)
                c["ambush"] += int(ev.ambush > 0 and ev.hit)
            if att_team is Team.ENEMY:
                bucket = "r1" if rnd == 1 else "r2" if rnd == 2 else "r3p"
                who = (
                    "hero"
                    if ev.target_id == hero
                    else "summon"
                    if ev.target_id in summons
                    else "ally"
                )
                focus[f"{bucket}:{who}"] += 1
            elif (
                att_team is Team.ALLY
                and ev.attacker_id != hero
                and team.get(ev.target_id) is Team.ENEMY
            ):
                key = "marked" if ev.target_id in marked else "plain"
                ally_vs_marked[key + ":rolls"] += 1
                ally_vs_marked[key + ":hits"] += int(ev.hit)
                for m in mark_open.values():
                    m["ally_atk_all"] += 1
                if ev.target_id in mark_open:
                    mark_open[ev.target_id]["ally_atk_same"] += 1
                    mark_open[ev.target_id]["ally_hit_same"] += int(ev.hit)
            elif ev.attacker_id == hero and ev.target_id in mark_open:
                mark_open[ev.target_id]["hero_atk_same"] += 1
        elif isinstance(ev, DamageDealt):
            amount = ev.hp_before - ev.hp_after
            if ev.target_id == hero:
                src = ev.source_id
                who = "env" if src is None else ("self" if src == hero else tpl.get(src, "?"))
                taken[f"{who}|{ev.cause}"] += amount
                taken_round.append((rnd, who, ev.cause, amount))
                hp_round[rnd] = ev.hp_after
            elif team.get(ev.target_id) is Team.ENEMY and ev.source_id == hero:
                name = (
                    roll_name.get(ev.target_id, "other")
                    if ev.cause == "attack"
                    else (current if current != "-" else "non_skill")
                )
                c = sk(name)
                c["dmg"] += amount
                c["dmg_events"] += 1
                if ev.cause != "attack":
                    c["dmg_indirect"] += amount
                if ev.target_id in marked:
                    c["dmg_on_marked"] += amount
            elif team.get(ev.target_id) is Team.ENEMY and ev.source_id is not None:
                if team.get(ev.source_id) is Team.ALLY and ev.source_id not in summons:
                    misc["ally_dmg"] += amount
                elif ev.source_id in summons:
                    misc["summon_dmg"] += amount
        elif isinstance(ev, GambleRolled):
            if ev.unit_id == hero:
                gamble.append([rnd, ev.skill_id, int(ev.success)])
        elif isinstance(ev, BacklashTriggered):
            if ev.unit_id == hero:
                misc["backlash"] += 1
                sk(ev.skill_id)["backlash"] += 1
        elif isinstance(ev, StatusApplied):
            if ev.status_id == "marked":
                marked.add(ev.target_id)
                if ev.source_id == hero:
                    misc["marks_applied"] += 1
                    if ev.refreshed:
                        misc["marks_refreshed"] += 1
                    mark_open[ev.target_id] = {
                        "round": rnd,
                        "ally_atk_same": 0,
                        "ally_hit_same": 0,
                        "hero_atk_same": 0,
                        "ally_atk_all": 0,
                        "closed": 0,
                    }
            elif ev.target_id == hero and ev.status_id == "prone":
                misc["hero_prone"] += 1
        elif isinstance(ev, StatusRemoved):
            if ev.status_id == "marked":
                marked.discard(ev.target_id)
                m = mark_open.pop(ev.target_id, {})
                if m:
                    m["len"] = rnd - m["round"]
                    marks.append(m)
            if ev.reason in ("dispelled", "stolen", "revealed") and current in (
                "skill_dispel_magic",
                "skill_blessing_thief",
                "skill_flare_sight",
            ):
                removed[f"{current}:{ev.reason}:{ev.status_id}"] += 1
        elif isinstance(ev, ResourceRestored):
            if ev.source_id == hero:
                misc[f"restored:{ev.resource}:{'cd' if ev.skill_ids else 'mana'}"] += ev.amount
                misc[f"restored_n:{ev.resource}"] += 1
        elif isinstance(ev, TrapRevealed):
            misc["trap_revealed"] += 1
        elif isinstance(ev, UnitDowned):
            if ev.unit_id == hero:
                hero_down = rnd
                m2 = mark_open
                _ = m2
            elif team.get(ev.unit_id) is Team.ALLY and ev.unit_id not in summons:
                ally_down.append(rnd)
            if ev.unit_id in marked:
                marked.discard(ev.unit_id)
                m = mark_open.pop(ev.unit_id, {})
                if m:
                    m["len"] = rnd - m["round"]
                    m["closed"] = 1
                    marks.append(m)
    for m in mark_open.values():
        m["len"] = run.state.round - m["round"]
        marks.append(m)
    # 英雄死前 2 輪承受傷害
    death: dict[str, Any] | None = None
    if hero_down:
        recent: Counter[str] = Counter()
        srcs: set[str] = set()
        for r, who, cause, amt in taken_round:
            if hero_down - 1 <= r <= hero_down:
                recent[f"{who}|{cause}"] += amt
                if who not in ("env", "self"):
                    srcs.add(who)
        death = {"round": hero_down, "recent": dict(recent), "sources": len(srcs)}
    return {
        "map": spec.name.split(" × ")[-1],
        "win": run.state.winner is Team.ALLY,
        "rounds": run.state.round,
        "hero_down": hero_down,
        "death": death,
        "ally_down": ally_down,
        "skills": {k: dict(v) for k, v in skills.items()},
        "taken": dict(taken),
        "taken_round": [list(t) for t in taken_round],
        "focus": dict(focus),
        "marks": marks,
        "ally_vs_marked": dict(ally_vs_marked),
        "gamble": gamble,
        "removed": dict(removed),
        "misc": dict(misc),
        "hero_turns": hero_turns,
        "decisions": ai.log,
        "hp_round": {str(k): v for k, v in hp_round.items()},
    }


def _worker(
    ctx: tuple[tuple[tuple[str, BatchSpec], ...]],
    task: tuple[int, int],
) -> dict[str, Any]:
    (specs,) = ctx
    index, seed = task
    build, spec = specs[index]
    try:
        out = collect_battle(spec, seed, build)
    except Exception as exc:  # 單場失敗不中止整批
        return {"error": f"{type(exc).__name__}: {exc}", "build": build, "map": spec.name}
    out["build"] = build
    out["seed"] = seed
    return out


def cmd_collect(args: argparse.Namespace) -> int:
    library = load_library()
    maps = default_sim_maps(library)
    builds = args.builds.split(",")
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    specs = matrix_specs(library, builds, maps, seeds)
    pairs = tuple((b, s) for b, _, s in specs)
    tasks = [(i, seed) for i in range(len(pairs)) for seed in seeds]
    started = time.perf_counter()
    rows = run_tasks(_worker, (pairs,), tasks, jobs=args.jobs)
    args.out.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8", newline="\n")
    errs = sum(1 for r in rows if "error" in r)
    print(f"collect 完成：{len(rows)} 場，錯誤 {errs}，{time.perf_counter() - started:.0f}s")
    return 0


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _pct(a: float, b: float) -> str:
    return f"{a * 100 / b:.0f}%" if b else "-"


def _load(path: Path) -> dict[str, list[dict[str, Any]]]:
    raw = (
        gzip.decompress(path.read_bytes()).decode("utf-8")
        if path.suffix == ".gz"
        else path.read_text(encoding="utf-8")
    )
    rows = [r for r in json.loads(raw) if "error" not in r]
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r["build"], []).append(r)
    return out


def _overview(data: dict[str, list[dict[str, Any]]]) -> None:
    print("## 1. 總覽（每 build 300 場）\n")
    print(
        "| build | 勝率 | 輪數 | 英雄存活 | 英雄倒地輪(均) | 隊友倒地數/場 | 英雄回合數 | "
        "每回合 AP | 結束回合時未用 AP | 技能 AP 占比 | 英雄對敵傷害/場 | 隊友對敵傷害/場 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for b, rows in data.items():
        n = len(rows)
        wins = sum(r["win"] for r in rows)
        downs = [r["hero_down"] for r in rows if r["hero_down"]]
        turns = sum(len(r["hero_turns"]) for r in rows)
        ap = sum(t[1] for r in rows for t in r["hero_turns"])
        unused = [d["ap"] for r in rows for d in r["decisions"] if d["pick"] == "end"]
        skill_ap = sum(
            v.get("ap", 0)
            for r in rows
            for k, v in r["skills"].items()
            if k.startswith("skill_") and not k.startswith("trig:")
        )
        hero_dmg = sum(
            v.get("dmg", 0) + v.get("dmg_indirect", 0) for r in rows for v in r["skills"].values()
        )
        ally = sum(r["misc"].get("ally_dmg", 0) for r in rows)
        print(
            f"| {b} | {wins * 100 / n:.1f}% | {sum(r['rounds'] for r in rows) / n:.1f} "
            f"| {100 - len(downs) * 100 / n:.0f}% "
            f"| {(sum(downs) / len(downs)) if downs else 0:.1f} "
            f"| {sum(len(r['ally_down']) for r in rows) / n:.2f} "
            f"| {turns / n:.1f} | {ap / max(1, turns):.2f} "
            f"| {(sum(unused) / len(unused)) if unused else 0:.2f} "
            f"| {_pct(skill_ap, ap)} | {hero_dmg / n:.1f} | {ally / n:.1f} |"
        )


def _skill_table(data: dict[str, list[dict[str, Any]]], build: str) -> None:
    rows = data[build]
    n = len(rows)
    agg: dict[str, Counter[str]] = {}
    for r in rows:
        for k, v in r["skills"].items():
            agg.setdefault(k, Counter()).update(v)
    # 決策層：可選次數（候選中出現）與被選次數
    avail: Counter[str] = Counter()
    chosen: Counter[str] = Counter()
    pos_avail: Counter[str] = Counter()
    decisions = 0
    for r in rows:
        for d in r["decisions"]:
            if d["pick"] == "end" and not d["c"]:
                continue
            decisions += 1
            for lab, sc in d["c"].items():
                if lab.startswith("skill:"):
                    avail[lab] += 1
                    pos_avail[lab] += int(sc > 0)
            chosen[d["pick"]] += 1
    print(f"\n### {build}：技能使用率與每次期望效果（{n} 場，{decisions} 個有候選的決策點）\n")
    print(
        "| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | "
        "命中率 | 暴擊率 | 背刺命中 | 代價/次 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    names = sorted(agg, key=lambda k: -agg[k].get("uses", 0))
    for name in names:
        c = agg[name]
        uses = c.get("uses", 0)
        lab = "skill:" + name
        cost = []
        if c.get("stamina"):
            cost.append(f"耐{c['stamina'] / max(1, uses):.0f}")
        if c.get("mana"):
            cost.append(f"法{c['mana'] / max(1, uses):.0f}")
        if c.get("hp_spent"):
            cost.append(f"血{c['hp_spent'] / max(1, uses):.1f}")
        ap_per = c.get("ap", 0) / max(1, uses) if name.startswith("skill_") else 1
        dmg_use = c.get("dmg", 0) / max(1, uses)
        print(
            f"| {name} | {uses / n:.2f} | {avail[lab] / max(1, decisions) * 100:.0f}% "
            f"| {pos_avail[lab] / max(1, decisions) * 100:.0f}% "
            f"| {_pct(chosen[lab], avail[lab]) if avail[lab] else '-'} "
            f"| {dmg_use:.1f} | {dmg_use / max(1, ap_per):.1f} "
            f"| {_pct(c.get('hits', 0), c.get('rolls', 0))} "
            f"| {_pct(c.get('crits', 0), c.get('rolls', 0))} "
            f"| {c.get('backstab', 0) / n:.2f} | {' '.join(cost) or '-'} |"
        )
    pick_total = sum(chosen.values())
    print(
        "\n英雄決策分佈："
        + "，".join(f"{k} {v * 100 / pick_total:.0f}%" for k, v in chosen.most_common(10))
    )


def _death_table(data: dict[str, list[dict[str, Any]]]) -> None:
    print("\n## 3. 死因與死亡回合\n")
    print(
        "| build | 英雄倒地場數 | 倒地輪數分布(1/2/3/4/5+) | 死前 2 輪主因（來源|cause） | 平均來源數 | 純自傷占比 |"
    )
    print("|---|---|---|---|---|---|")
    for b, rows in data.items():
        deaths = [r["death"] for r in rows if r["death"]]
        if not deaths:
            print(f"| {b} | 0 | - | - | - | - |")
            continue
        dist = Counter(min(d["round"], 5) for d in deaths)
        agg: Counter[str] = Counter()
        for d in deaths:
            agg.update(d["recent"])
        tot = sum(agg.values())
        top = "；".join(f"{k} {v * 100 / tot:.0f}%" for k, v in agg.most_common(4))
        selfd = sum(v for k, v in agg.items() if k.startswith("self|"))
        print(
            f"| {b} | {len(deaths)}/{len(rows)} | "
            + "/".join(str(dist.get(i, 0)) for i in range(1, 6))
            + f" | {top} | {sum(d['sources'] for d in deaths) / len(deaths):.1f} "
            f"| {selfd * 100 / tot:.0f}% |"
        )
    print("\n### 敵方攻擊的目標分佈（每輪桶；比例＝打在英雄上 / 所有敵方攻擊）\n")
    print("| build | 第1輪 | 第2輪 | 第3輪+ | 每場英雄承傷 | 其中第1~2輪承傷占比 |")
    print("|---|---|---|---|---|---|")
    for b, rows in data.items():
        cells = []
        for bucket in ("r1", "r2", "r3p"):
            h = sum(r["focus"].get(f"{bucket}:hero", 0) for r in rows)
            t = sum(
                r["focus"].get(f"{bucket}:{w}", 0) for r in rows for w in ("hero", "ally", "summon")
            )
            cells.append(f"{_pct(h, t)}（{t / len(rows):.1f}）")
        total = sum(a for r in rows for _, _, _, a in r["taken_round"])
        early = sum(a for r in rows for rr, _, _, a in r["taken_round"] if rr <= 2)
        print(f"| {b} | {' | '.join(cells)} | {total / len(rows):.1f} | {_pct(early, total)} |")
    print("\n### 英雄承傷來源（每場，依來源範本與 cause，前 5）\n")
    for b, rows in data.items():
        agg2: Counter[str] = Counter()
        for r in rows:
            agg2.update(r["taken"])
        print(f"- {b}：" + "；".join(f"{k} {v / len(rows):.1f}" for k, v in agg2.most_common(5)))


def _seer(data: dict[str, list[dict[str, Any]]], build: str = "build_seer") -> None:
    rows = data[build]
    n = len(rows)
    print("\n## 4a. seer：咒印、驅散、奪取、揭露、法力回復\n")
    marks = [m for r in rows for m in r["marks"]]
    print(
        f"- 咒印施加：{len(marks)} 次（每場 {len(marks) / n:.2f}）；刷新已有咒印 "
        f"{sum(r['misc'].get('marks_refreshed', 0) for r in rows)} 次"
    )
    if marks:
        same = sum(m["ally_atk_same"] for m in marks)
        allatk = sum(m["ally_atk_all"] for m in marks)
        hero_same = sum(m["hero_atk_same"] for m in marks)
        followed = sum(1 for m in marks if m["ally_atk_same"] + m["hero_atk_same"] > 0)
        print(
            f"- 上咒印後窗口內（到咒印消失／目標倒地）：有接攻擊（隊友或英雄打同目標）的咒印 "
            f"{followed}/{len(marks)}（{_pct(followed, len(marks))}）；隊友對咒印目標的攻擊平均 "
            f"{same / len(marks):.2f} 次/咒印，窗口內隊友全部攻擊 {allatk / len(marks):.2f} 次/咒印"
            f"（同目標占 {_pct(same, allatk)}）；英雄自己打同目標 {hero_same / len(marks):.2f} 次/咒印；"
            f"窗口平均 {sum(m['len'] for m in marks) / len(marks):.1f} 輪；"
            f"目標在咒印中倒地 {sum(m['closed'] for m in marks)} 次"
        )
    mr = sum(r["ally_vs_marked"].get("marked:rolls", 0) for r in rows)
    mh = sum(r["ally_vs_marked"].get("marked:hits", 0) for r in rows)
    pr = sum(r["ally_vs_marked"].get("plain:rolls", 0) for r in rows)
    ph = sum(r["ally_vs_marked"].get("plain:hits", 0) for r in rows)
    print(
        f"- 隊友攻擊命中率：對咒印目標 {_pct(mh, mr)}（{mr} 次），對其他目標 {_pct(ph, pr)}（{pr} 次）"
    )
    # 咒印使用時機（決策層）
    ds = [d for r in rows for d in r["decisions"] if d["pick"] == "skill:skill_hex_bolt"]
    already = sum(1 for d in ds if "marked" in d.get("tst", []))
    print(
        f"- hex_bolt 被選 {len(ds)} 次；目標當下已有咒印 {already} 次（{_pct(already, len(ds))}）"
    )
    rem: Counter[str] = Counter()
    for r in rows:
        rem.update(r["removed"])
    print(
        "- 破魔／奪取／照明彈實際移除的狀態（總數）："
        + "；".join(f"{k} {v}" for k, v in rem.most_common(12))
    )
    for sid in ("skill_dispel_magic", "skill_blessing_thief", "skill_flare_sight"):
        dd = [d for r in rows for d in r["decisions"] if d["pick"] == "skill:" + sid]
        uses = sum(r["skills"].get(sid, {}).get("uses", 0) for r in rows)
        got = sum(v for r in rows for k, v in r["removed"].items() if k.startswith(sid))
        print(
            f"  - {sid}：每場施放 {uses / n:.2f}，移除狀態合計 {got}，每次 {got / max(1, uses):.2f}；"
            f"目標身上有任何狀態 {sum(1 for d in dd if d.get('tst'))}/{len(dd)}"
        )
    print(
        "- 法力／冷卻回復（給隊友）："
        + "；".join(
            f"{k} {sum(r['misc'].get(k, 0) for r in rows) / n:.2f}/場"
            for k in sorted({k for r in rows for k in r["misc"] if k.startswith("restored")})
        )
    )


def _gambler(data: dict[str, list[dict[str, Any]]], build: str = "build_gambler") -> None:
    rows = data[build]
    n = len(rows)
    print("\n## 4b. gambler：賭注結果、反噬、使用時機\n")
    g: dict[str, list[int]] = {}
    for r in rows:
        for _, sid, ok in r["gamble"]:
            g.setdefault(sid, []).append(ok)
    for sid, v in g.items():
        print(f"- {sid} 賭注：{len(v)} 次（每場 {len(v) / n:.2f}），成功 {_pct(sum(v), len(v))}")
    print(
        f"- 反噬（失手）：每場 {sum(r['misc'].get('backlash', 0) for r in rows) / n:.2f}；"
        f"因而倒地（prone）每場 {sum(r['misc'].get('hero_prone', 0) for r in rows) / n:.2f}"
    )
    selfdmg = sum(v for r in rows for k, v in r["taken"].items() if k.startswith("self|"))
    alltaken = sum(v for r in rows for v in r["taken"].values())
    print(
        f"- 英雄承傷：每場 {alltaken / n:.1f}，其中自傷（血祭／反噬／狂戰士之怒）{selfdmg / n:.1f}（{_pct(selfdmg, alltaken)}）"
    )
    hp_spent = sum(v.get("hp_spent", 0) for r in rows for v in r["skills"].values())
    print(f"- 技能以 HP 付費：每場 {hp_spent / n:.1f}")
    # 高變異招的使用時機：被選時的 HP 比、與敵人距離、AP
    for sid in (
        "skill_blood_sacrifice",
        "skill_all_in",
        "skill_wild_blade",
        "skill_reckless_lunge",
        "skill_berserker_rage",
    ):
        ds = [d for r in rows for d in r["decisions"] if d["pick"] == "skill:" + sid]
        if not ds:
            continue
        hpr = sorted(d["hp"] / d["mhp"] for d in ds)
        print(
            f"  - {sid}：選用 {len(ds)} 次；選用時 HP 比 中位 {hpr[len(hpr) // 2] * 100:.0f}%、"
            f"低於 30% {sum(1 for x in hpr if x < 0.3)} 次；平均分數 "
            f"{sum(d['pick_score'] or 0 for d in ds) / len(ds):.1f}；耐力中位 "
            f"{sorted(d['sta'] for d in ds)[len(ds) // 2]}"
        )
    # 耐力
    turns = [t for r in rows for t in r["hero_turns"]]
    low = sum(1 for t in turns if t[3] < 6)
    print(
        f"- 回合開始耐力 < 6（最便宜的耐力技都付不起）：{_pct(low, len(turns))}；耐力 < 10：{_pct(sum(1 for t in turns if t[3] < 10), len(turns))}；"
        f"平均 {sum(t[3] for t in turns) / max(1, len(turns)):.1f}"
    )


def _assassin(data: dict[str, list[dict[str, Any]]], build: str = "build_assassin") -> None:
    rows = data[build]
    n = len(rows)
    print("\n## 4c. assassin：背刺、瞬步、撤退\n")
    for sid in (
        "skill_shadow_backstab",
        "skill_shadow_ambush",
        "skill_blink",
        "skill_retreating_slash",
        "skill_pincer_strike",
        "skill_pick_off",
    ):
        ds = [d for r in rows for d in r["decisions"] if d["pick"] == "skill:" + sid]
        if not ds:
            print(f"- {sid}：從未被選用")
            continue
        near = sum(d["near"] for d in ds) / len(ds)
        n2 = sum(d["n2"] for d in ds) / len(ds)
        thp = [d.get("thp", 1) for d in ds if "thp" in d]
        print(
            f"- {sid}：選用 {len(ds)} 次（{len(ds) / n:.2f}/場）；用前離最近敵人 {near:.1f} 格、2 格內敵人 {n2:.1f}；"
            f"目標 HP 比平均 {sum(thp) / max(1, len(thp)) * 100:.0f}%"
        )
    # 背刺：普攻與技能命中中背刺的比例
    tot = Counter[str]()
    for r in rows:
        for v in r["skills"].values():
            tot["rolls"] += v.get("rolls", 0)
            tot["hits"] += v.get("hits", 0)
            tot["back"] += v.get("backstab", 0)
            tot["amb"] += v.get("ambush", 0)
            tot["crit"] += v.get("crits", 0)
    print(
        f"- 英雄命中 {tot['hits'] / n:.1f}/場（命中率 {_pct(tot['hits'], tot['rolls'])}），其中背刺 {tot['back'] / n:.2f}/場"
        f"（{_pct(tot['back'], tot['hits'])}），潛行偷襲 {tot['amb'] / n:.2f}/場，暴擊 {tot['crit'] / n:.2f}/場"
    )
    # 撤退：每個英雄回合，首個決策的距離 vs EndTurn 決策的距離（同輪）
    start_d: list[int] = []
    end_d: list[int] = []
    retreated = attacked = turns = 0
    far_after_attack = 0
    for r in rows:
        by_round: dict[int, list[dict[str, Any]]] = {}
        for d in r["decisions"]:
            by_round.setdefault(d["r"], []).append(d)
        for ds in by_round.values():
            if not ds or ds[-1]["pick"] != "end" or ds[0]["near"] < 0:
                continue
            turns += 1
            s, e = ds[0]["near"], ds[-1]["near"]
            start_d.append(s)
            end_d.append(e)
            hit = any(d["pick"] in ("attack",) or d["pick"].startswith("skill:") for d in ds)
            attacked += int(hit)
            if e > s:
                retreated += 1
            if hit and ds[-1]["n2"] == 0:
                far_after_attack += 1
    print(
        f"- 英雄回合（可觀測 {turns}）：回合開始離最近敵人 {sum(start_d) / max(1, turns):.1f} 格 -> 結束 {sum(end_d) / max(1, turns):.1f} 格；"
        f"結束時比開始更遠 {_pct(retreated, turns)}；有攻擊 {_pct(attacked, turns)}；攻擊後結束時 2 格內無敵人 {_pct(far_after_attack, attacked)}"
    )
    # 低血撤退：HP < 35% 的決策點
    low = [d for r in rows for d in r["decisions"] if d["hp"] / d["mhp"] < 0.35]
    print(
        f"- HP < 35% 的決策點 {len(low)} 個（每場 {len(low) / n:.2f}）；選："
        + "，".join(f"{k} {v}" for k, v in Counter(d["pick"] for d in low).most_common(6))
    )


def _damaging_skills(rows: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for r in rows:
        for k, v in r["skills"].items():
            if k.startswith("skill_") and (
                v.get("dmg", 0) + v.get("dmg_indirect", 0) > 0 or v.get("rolls", 0) > 0
            ):
                out.add(k)
    return out


def _is_offense(pick: str, dmg_skills: set[str]) -> bool:
    return pick == "attack" or (pick.startswith("skill:") and pick[6:] in dmg_skills)


def _deep_row(b: str, rows: list[dict[str, Any]]) -> str:
    n = len(rows)
    dmg_skills = _damaging_skills(rows)
    turns = off = defend = move = no_off_turns = first_rounds = first_n = never = left_turns = 0
    left_near: list[int] = []
    dmg = 0
    for r in rows:
        by_round: dict[int, list[dict[str, Any]]] = {}
        for d in r["decisions"]:
            by_round.setdefault(d["r"], []).append(d)
        first = 0
        for rd in sorted(by_round):
            ds = by_round[rd]
            turns += 1
            o = sum(1 for d in ds if _is_offense(d["pick"], dmg_skills))
            off += o
            defend += sum(1 for d in ds if d["pick"] == "defend")
            move += sum(1 for d in ds if d["pick"] in ("move", "run"))
            if o == 0:
                no_off_turns += 1
            elif not first:
                first = rd
            if ds[-1]["pick"] == "end" and ds[-1]["ap"] >= 1:
                left_turns += 1
                if ds[-1]["near"] >= 0:
                    left_near.append(ds[-1]["near"])
        if first:
            first_rounds += first
            first_n += 1
        else:
            never += 1
        dmg += sum(v.get("dmg", 0) + v.get("dmg_indirect", 0) for v in r["skills"].values())
    return (
        f"| {b} | {turns / n:.1f} | {off / turns:.2f} | {_pct(no_off_turns, turns)} "
        f"| {first_rounds / max(1, first_n):.1f} | {_pct(never, n)} | {defend / turns:.2f} "
        f"| {move / turns:.2f} | {_pct(left_turns, turns)} "
        f"| {sum(left_near) / max(1, len(left_near)):.1f} | {dmg / n:.1f} | {dmg / max(1, off):.1f} |"
    )


def _deep_seer(rows: list[dict[str, Any]]) -> None:
    print("\n### seer：給友方的支援技（專注湧流、疾時之潮）使用時\n")
    for sid in ("skill_focus_surge", "skill_quicken_tide"):
        ds = [d for r in rows for d in r["decisions"] if d["pick"] == "skill:" + sid]
        if not ds:
            continue
        tgt = Counter(d.get("tt", "?") for d in ds)
        hex_ok = sum(1 for d in ds if d["c"].get("skill:skill_hex_bolt", 0) > 0)
        print(
            f"- {sid}：{len(ds)} 次；目標："
            + "，".join(f"{k} {v}" for k, v in tgt.most_common(4))
            + f"；施放時英雄法力平均 {sum(d['mana'] for d in ds) / len(ds):.0f}（上限 40）；"
            f"同時 hex_bolt 候選分>0 {_pct(hex_ok, len(ds))}；本招平均分數 "
            f"{sum(d['pick_score'] or 0 for d in ds) / len(ds):.1f}，同決策 hex_bolt 最高候選分平均 "
            f"{sum(d['c'].get('skill:skill_hex_bolt', 0) for d in ds) / len(ds):.1f}"
        )
    hexes = [d for r in rows for d in r["decisions"] if d["pick"] == "skill:skill_hex_bolt"]
    tgt = Counter(d.get("tt", "?") for d in hexes)
    print("- hex_bolt 的目標範本：" + "，".join(f"{k} {v}" for k, v in tgt.most_common(5)))
    print(
        f"- hex_bolt 選用時最近敵人距離平均 {sum(d['near'] for d in hexes) / max(1, len(hexes)):.1f}；"
        f"選用時分數平均 {sum(d['pick_score'] or 0 for d in hexes) / max(1, len(hexes)):.1f}"
    )


def cmd_deep(args: argparse.Namespace) -> int:
    """傷害與回合使用的分解：存活回合 x 進攻比例 x 每次進攻傷害。"""
    data = _load(args.input)
    print("## 5. 傷害落差分解（英雄每場）\n")
    print(
        "| build | 英雄回合/場 | 進攻決策/回合 | 無進攻回合比 | 第一次進攻的輪數(均) | 死前沒進攻過 | "
        "防禦決策/回合 | 移動決策/回合 | 結束時剩 AP>=1 的回合比 | 剩 AP 時最近敵人(均) | 英雄傷害/場 | 傷害/進攻決策 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for b, rows in data.items():
        print(_deep_row(b, rows))
    print("\n### 普攻（1 AP）\n")
    for b, rows in data.items():
        basic: Counter[str] = Counter()
        for r in rows:
            basic.update(r["skills"].get("basic", {}))
        print(
            f"- {b}：{basic.get('rolls', 0) / len(rows):.2f} 次/場，命中 {_pct(basic.get('hits', 0), basic.get('rolls', 0))}，"
            f"每次 {basic.get('dmg', 0) / max(1, basic.get('rolls', 0)):.1f} 傷害"
        )
    print("\n### 防禦決策發生時（HP 比、最近敵人、2 格內敵人）\n")
    for b, rows in data.items():
        ds = [d for r in rows for d in r["decisions"] if d["pick"] == "defend"]
        if not ds:
            continue
        hp = sorted(d["hp"] / d["mhp"] for d in ds)
        alt = sum(
            1
            for d in ds
            if any(v > 0 for k, v in d["c"].items() if k == "attack" or k.startswith("skill:"))
        )
        print(
            f"- {b}：{len(ds) / len(rows):.2f} 次/場；HP 比中位 {hp[len(hp) // 2] * 100:.0f}%；"
            f"最近敵人平均 {sum(d['near'] for d in ds) / len(ds):.1f} 格；2 格內敵人 "
            f"{sum(d['n2'] for d in ds) / len(ds):.1f}；同時有進攻候選分>0 的比例 {_pct(alt, len(ds))}"
        )
    print("\n### 第一輪英雄決策的選擇\n")
    for b, rows in data.items():
        c = Counter(d["pick"] for r in rows for d in r["decisions"] if d["r"] == 1)
        tot = sum(c.values())
        print(f"- {b}：" + "，".join(f"{k} {v * 100 / tot:.0f}%" for k, v in c.most_common(6)))
    if "build_seer" in data:
        _deep_seer(data["build_seer"])
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    data = _load(args.input)
    _overview(data)
    print("\n## 2. 技能使用率\n")
    for b in data:
        _skill_table(data, b)
    _death_table(data)
    if "build_seer" in data:
        _seer(data)
    if "build_gambler" in data:
        _gambler(data)
    if "build_assassin" in data:
        _assassin(data)
    return 0


# ---------------------------------------------------------------------------
# 覆寫對照（記憶體內）
# ---------------------------------------------------------------------------


def _with_hero(library: ContentLibrary, build: str, **fields: Any) -> ContentLibrary:
    """改 build 英雄範本的欄位（``ai_profile``、``max_hp``、``skills``……）。"""
    builds = []
    for item in library.builds.builds:
        if item.id == build:
            hero = item.hero.model_copy(update=fields)
            builds.append(item.model_copy(update={"hero": hero}))
        else:
            builds.append(item)
    table = library.builds.model_copy(update={"builds": tuple(builds)})
    return dataclasses.replace(library, builds=table)


def _with_profile_weights(library: ContentLibrary, profile: str, **weights: int) -> ContentLibrary:
    profs = []
    for prof in library.ai_profiles.profiles:
        if prof.id == profile:
            new_w = prof.weights.model_copy(update=weights)
            profs.append(prof.model_copy(update={"weights": new_w}))
        else:
            profs.append(prof)
    table = library.ai_profiles.model_copy(update={"profiles": tuple(profs)})
    return dataclasses.replace(library, ai_profiles=table)


def _clone_profile(library: ContentLibrary, src: str, new: str, **weights: int) -> ContentLibrary:
    base = next(p for p in library.ai_profiles.profiles if p.id == src)
    clone = base.model_copy(update={"id": new, "weights": base.weights.model_copy(update=weights)})
    table = library.ai_profiles.model_copy(
        update={"profiles": (*library.ai_profiles.profiles, clone)}
    )
    return dataclasses.replace(library, ai_profiles=table)


def _status_value(library: ContentLibrary, **values: int) -> ContentLibrary:
    table = library.ai_profiles.model_copy(
        update={"status_values": {**library.ai_profiles.status_values, **values}}
    )
    return dataclasses.replace(library, ai_profiles=table)


def apply_option(library: ContentLibrary, option: str) -> ContentLibrary:
    lib: ContentLibrary = OPTIONS[option](library)
    return lib


def _with_ruleset(library: ContentLibrary, **tables: Any) -> ContentLibrary:
    ruleset = library.ruleset.model_copy(update=tables)
    ruleset.model_post_init(None)
    return dataclasses.replace(library, ruleset=ruleset)


def _skill_edit(library: ContentLibrary, skill_id: str, **fields: Any) -> ContentLibrary:
    changed = library.skills[skill_id].model_copy(update=fields)
    skills = {**library.skills, skill_id: changed}
    table = library.ruleset.skills.model_copy(
        update={"skills": tuple(skills[s.id] for s in library.ruleset.skills.skills)}
    )
    lib = _with_ruleset(library, skills=table)
    return dataclasses.replace(lib, skills=skills)


def _clone_rewrite(library: ContentLibrary, src: str, new: str, **rewrite: int) -> ContentLibrary:
    """複製行為模式 ``src`` 為 ``new``，並改寫它的 ``rewrite`` 欄位（改寫規則型原語的估值）。"""
    base = next(p for p in library.ai_profiles.profiles if p.id == src)
    clone = base.model_copy(update={"id": new, "rewrite": base.rewrite.model_copy(update=rewrite)})
    table = library.ai_profiles.model_copy(
        update={"profiles": (*library.ai_profiles.profiles, clone)}
    )
    return dataclasses.replace(library, ai_profiles=table)


def _seer_no_selfrestore(lib: ContentLibrary) -> ContentLibrary:
    """seer 的 AI 不再重視「給自己回法力／縮短冷卻」（mana_points 1→0、cooldown_points 4→1）。"""
    lib = _clone_rewrite(lib, "cunning", "cunning_nr", mana_points=0, cooldown_points=1)
    return _with_hero(lib, "build_seer", ai_profile="cunning_nr")


def _seer_swap_dmg(lib: ContentLibrary) -> ContentLibrary:
    """技能結構：專注湧流、疾時之潮換成灰燼收割、寒鎖（炸彈流的兩招；只量結構差異）。"""
    skills = tuple(
        {
            "skill_focus_surge": "skill_ash_harvest",
            "skill_quicken_tide": "skill_frost_shackle",
        }.get(s, s)
        for s in lib.builds.by_id()["build_seer"].hero.skills
    )
    return _with_hero(lib, "build_seer", skills=skills)


def _gambler_no_allin(lib: ContentLibrary) -> ContentLibrary:
    skills = tuple(
        s for s in lib.builds.by_id()["build_gambler"].hero.skills if s != "skill_all_in"
    )
    return _with_hero(lib, "build_gambler", skills=skills)


def _gambler_charge(lib: ContentLibrary) -> ContentLibrary:
    lib = _clone_profile(lib, "brute", "brute_charge", approach=12)
    return _with_hero(lib, "build_gambler", ai_profile="brute_charge")


def _assassin_bs_1ap(lib: ContentLibrary) -> ContentLibrary:
    return _skill_edit(lib, "skill_shadow_backstab", ap_cost=1)


def _assassin_no_defend(lib: ContentLibrary) -> ContentLibrary:
    return _with_profile_weights(lib, "assassin", defend=0)


def _assassin_dmg_x15(lib: ContentLibrary) -> ContentLibrary:
    """資訊用：assassin 的四招攻擊技傷害 ×1.5（每個傷害效果的 multiplier_permille ×1.5；超出預算，只看槓桿）。"""
    for sid in (
        "skill_shadow_backstab",
        "skill_shadow_ambush",
        "skill_pick_off",
        "skill_retreating_slash",
    ):
        skill = lib.skills[sid]
        effects = tuple(
            e.model_copy(update={"multiplier_permille": e.multiplier_permille * 3 // 2})
            if e.type == "damage" and e.multiplier_permille
            else e
            for e in skill.effects
        )
        lib = _skill_edit(lib, sid, effects=effects)
    return lib


def _gambler_hp_x13(lib: ContentLibrary) -> ContentLibrary:
    """資訊用：gambler 英雄 HP 44 → 57（×1.3），看存活槓桿。"""
    return _with_hero(lib, "build_gambler", max_hp=57)


def _no_fury(build: str) -> Any:
    """資訊用：拿掉狂怒姿態（力量 +2、受到骰值傷害 ×1.2，AI 不會取消）。"""

    def apply(lib: ContentLibrary) -> ContentLibrary:
        skills = tuple(s for s in lib.builds.by_id()[build].hero.skills if s != "skill_fury_stance")
        return _with_hero(lib, build, skills=skills)

    return apply


OPTIONS: dict[str, Any] = {
    "gambler_no_fury": _no_fury("build_gambler"),
    "assassin_no_fury": _no_fury("build_assassin"),
    "assassin_dmg_x15": _assassin_dmg_x15,
    "gambler_hp_x13": _gambler_hp_x13,
    "seer_no_selfrestore": _seer_no_selfrestore,
    "seer_swap_dmg": _seer_swap_dmg,
    "gambler_no_allin": _gambler_no_allin,
    "gambler_charge": _gambler_charge,
    "assassin_bs_1ap": _assassin_bs_1ap,
    "assassin_no_defend": _assassin_no_defend,
}


def _rates(report: Any, builds: list[str]) -> dict[str, tuple[float, float, float, float]]:
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


def cmd_trial(args: argparse.Namespace) -> int:
    base = load_library()
    maps = default_sim_maps(base)
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    data = _load(args.baseline_json)
    cache: dict[str, tuple[float, float]] = {
        b: (
            sum(r["win"] for r in rows if r["seed"] < args.seed_start + args.seeds)
            * 100
            / sum(1 for r in rows if r["seed"] < args.seed_start + args.seeds),
            sum(r["rounds"] for r in rows) / len(rows),
        )
        for b, rows in data.items()
    }
    started = time.perf_counter()
    for spec in args.run:
        option, _, build_text = spec.partition(":")
        builds = build_text.split(",")
        lib = apply_option(base, option)
        trial = run_matrix(lib, builds, maps, seeds, jobs=args.jobs)
        got = _rates(trial, builds)
        print(f"\n## {option}（每格 {len(seeds)} 場）")
        print("| build | 基準勝率 | 本次勝率 | 差 | 基準輪數 | 本次輪數 | DPR | 存活% |")
        print("|---|---|---|---|---|---|---|---|")
        for b in builds:
            w, dpr, surv, rounds = got[b]
            ref = cache.get(b, (float("nan"), float("nan")))
            print(
                f"| {b} | {ref[0]:.1f} | {w:.1f} | {w - ref[0]:+.1f} "
                f"| {ref[1]:.1f} | {rounds:.1f} | {dpr:.1f} | {surv:.0f} |",
                flush=True,
            )
        print(f"[{option} 完成 {time.perf_counter() - started:.0f}s]", file=sys.stderr, flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("collect")
    p.add_argument("--builds", required=True)
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("report")
    p.add_argument("--input", type=Path, required=True)
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("deep")
    p.add_argument("--input", type=Path, required=True)
    p.set_defaults(fn=cmd_deep)
    p = sub.add_parser("trial")
    p.add_argument("--run", action="append", required=True, help="選項:build,build,…")
    p.add_argument("--baseline-json", type=Path, required=True)
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--seed-start", type=int, default=0)
    p.add_argument("--jobs", type=int, default=1)
    p.set_defaults(fn=cmd_trial)
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())


_ = (Fraction,)
