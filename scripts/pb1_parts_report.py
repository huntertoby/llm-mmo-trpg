"""PB-1d：霧鎖真人部位關／開的模擬報表（``docs/phases/PhasePB-1計畫.md`` 第 8 節）。

**只產報表，不調數值**（數值由使用者在數值工坊調）。

走大世界的真實路徑（:mod:`trpg.sim.boss_probe` 的建角、傭兵與 :class:`BossWatch` 歸屬規則）：
霧鎖真人 × 8 個 build × ``--seeds`` 個種子，部位「關」與「開」兩組同種子配對。部位「關」＝在記憶體裡
把範本的 ``parts`` 拿掉（``dataclasses.replace(library, units=...)``），內容檔不動。

- ``run``：跑兩組，逐場紀錄寫 JSON（放暫存區，不進 repo）。
- ``report``：把 JSON 重印成兩張表——報表一（關／開對照：勝率、輪數、分 build 勝率、各階段每招每回合
  施放率、歸一回血）、報表二（部位統計：被選為目標、破壞率、破壞輪數、誰打破、破壞時的階段、破壞
  效果的實際作用），另附氣海（``reach: behind``）的可選原因統計。

用法::

    uv run python scripts/pb1_parts_report.py run --seeds 13 --jobs 6 --out <暫存>/pb1d.json
    uv run python scripts/pb1_parts_report.py report <暫存>/pb1d.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.actions import Attack, Step, UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import TurnStarted
from trpg.engine.events.combat import DamageDealt, Healed
from trpg.engine.events.parts import PartBroken, PartDamaged
from trpg.engine.events.skills import FollowupCancelled, SkillUsed
from trpg.engine.parts import part_targets
from trpg.engine.results import ResolveResult
from trpg.engine.rules.geometry import manhattan
from trpg.engine.runner import run_battle
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId
from trpg.sim.boss_probe import (
    BOSSES,
    BUILDS,
    BossWatch,
    ProbeJob,
    base_skill,
    boss_jobs,
    character,
)
from trpg.sim.boss_probe import phase_skills as boss_phase_skills
from trpg.sim.parallel import run_tasks
from trpg.world.battle import prepare_battle

WHICH = "mist"
BOSS_ID = BOSSES[WHICH][0]
WHISK, DANTIAN, SWORD = "whisk", "dantian", "sword"
PART_NAMES = {WHISK: "拂塵", DANTIAN: "氣海", SWORD: "長劍"}
MIST_SHIFT = "skill_mist_shift"
MIST_PHASE = 2
"""鎖霧（``mist_lock``）是第 2 階段；氣海從這階段起露出。"""
RETURN_PHASE = 3
"""歸一（``return_to_one``）是第 3 階段；``mist_return`` 只在這階段每回合回血。"""
REASON_ZH = {
    "ok": "可選",
    "need_behind_adjacent": "相鄰但不在背後格（或非近戰）",
    "need_behind_far": "不相鄰（遠程或站得遠）",
    "area_skill": "範圍招",
    "no_damage": "無傷害招",
    "charge_attack": "蓄力普攻",
    "summon": "召喚物",
    "broken": "已破",
    "not_exposed": "未露出",
}

type Record = dict[str, Any]


# ---------------------------------------------------------------------------
# run：逐場紀錄
# ---------------------------------------------------------------------------


def parts_off(library: ContentLibrary) -> ContentLibrary:
    """霧鎖真人拿掉 ``parts`` 的內容庫（只在記憶體）。"""
    units = dict(library.units)
    units[BOSS_ID] = units[BOSS_ID].model_copy(update={"parts": ()})
    return dataclasses.replace(library, units=units)


_LIBRARIES: dict[bool, ContentLibrary] = {}


def _library(parts: bool) -> ContentLibrary:
    cached = _LIBRARIES.get(parts)
    if cached is None:
        base = _LIBRARIES.get(True) or load_library()
        _LIBRARIES[True] = base
        cached = base if parts else parts_off(base)
        _LIBRARIES[parts] = cached
    return cached


def _role(state: BattleState, unit_id: UnitId | None) -> str:
    unit = state.units.get(unit_id) if unit_id is not None else None
    if unit is None:
        return "?"
    if unit.is_summon:
        return "召喚物"
    template = str(unit.template_id)
    if template.startswith("merc_"):
        return template
    return "主角" if unit.team is Team.ALLY else template


class PartsWatch(BossWatch):
    """:class:`BossWatch` 再加上部位、霧遁、歸一回血、頭目傷害的逐件紀錄。"""

    def __init__(self) -> None:
        super().__init__(BOSS_ID)
        self.prev: BattleState | None = None
        self.active: str | None = None
        self.boss_turn_open = False
        self.broken: list[str] = []  # 已破（且結算了效果）的部位，依破壞順序
        self.casts: list[list[Any]] = []  # [輪, 階段, 招, 當時已破]
        self.heals: list[list[Any]] = []  # [輪, 量, 當時已破]
        self.boss_damage: list[list[Any]] = []  # [輪, 階段, 量, 當時已破]
        self.boss_turns: list[list[Any]] = []  # [輪, 階段, 當時已破]
        self.picks: list[list[str]] = []  # [部位, 角色]
        self.hits: Counter[str] = Counter()
        self.breaks: list[dict[str, Any]] = []
        self.interrupts: list[list[str]] = []  # [部位, 招]
        self.dantian: Counter[str] = Counter()

    def __call__(self, step: Step | None, result: ResolveResult) -> None:
        if step is not None and self.prev is not None:
            self._action(step, self.prev)
        state = result.state
        if not result.events:
            super().__call__(step, result)
        last_break: str | None = None
        for event in result.events:
            super().__call__(step, result._replace(events=[event]))  # 先更新輪與階段
            if isinstance(event, TurnStarted):
                self.active = event.unit_id
                self.boss_turn_open = self._is_boss(state, event.unit_id)
                if self.boss_turn_open:
                    self.boss_turns.append([self.round, self.phase, list(self.broken)])
            elif isinstance(event, PartBroken):
                last_break = event.part_id
                if event.applied:
                    self.broken.append(event.part_id)
                self.breaks.append(
                    {
                        "part": event.part_id,
                        "round": self.round,
                        "phase": self.phase,
                        "by": _role(state, event.source_id),
                        "applied": event.applied,
                    }
                )
            else:
                self._other(event, state, last_break)
        self.prev = state

    def _is_boss(self, state: BattleState, unit_id: UnitId | None) -> bool:
        unit = state.units.get(unit_id) if unit_id is not None else None
        return unit is not None and unit.template_id == BOSS_ID

    def _other(self, event: object, state: BattleState, last_break: str | None) -> None:
        if isinstance(event, PartDamaged):
            self.hits[event.part_id] += 1
        elif isinstance(event, SkillUsed) and self._is_boss(state, event.unit_id):
            skill = base_skill(event.skill_id)
            self.casts.append([self.round, self.phase, skill, list(self.broken)])
            self.boss_turn_open = False
        elif isinstance(event, Healed) and self._is_boss(state, event.target_id):
            if self.boss_turn_open and self.phase == RETURN_PHASE:
                self.heals.append([self.round, event.amount, list(self.broken)])
        elif isinstance(event, DamageDealt) and self._is_boss(state, event.source_id):
            target = state.units.get(event.target_id)
            if target is not None and target.team is Team.ALLY:
                row = [self.round, self.phase, event.amount, list(self.broken)]
                self.boss_damage.append(row)
        elif (
            isinstance(event, FollowupCancelled)
            and event.reason == "part_broken"
            and self._is_boss(state, event.unit_id)
        ):
            self.interrupts.append([last_break or "?", base_skill(event.skill_id)])

    def _action(self, step: Step, before: BattleState) -> None:
        if not isinstance(step, Attack | UseSkill) or step.target_id is None:
            return
        actor = before.units.get(step.unit_id)
        if actor is None or actor.team is not Team.ALLY:
            return
        if not self._is_boss(before, step.target_id):
            return
        self.boss_turn_open = False
        if step.target_part is not None:
            self.picks.append([step.target_part, _role(before, step.unit_id)])
        if self.phase < MIST_PHASE or step.target_part is not None:
            return
        for target in part_targets(before, step.model_copy(update={"target_part": None})):
            if target.part_id == DANTIAN:
                reason: str = target.reason or "ok"
                if reason == "need_behind":
                    boss = before.units[step.target_id]
                    near = manhattan(actor.xy, boss.xy) == 1
                    reason = "need_behind_adjacent" if near else "need_behind_far"
                self.dantian[reason] += 1


def run_one(_context: None, task: tuple[ProbeJob, bool]) -> Record:
    job, parts = task
    library = _library(parts)
    watch = PartsWatch()
    prepared = prepare_battle(library, character(library, job))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles), on_step=watch)
    return {
        "parts": parts,
        "build": job.build,
        "seed": job.seed,
        "won": run.state.winner is Team.ALLY,
        "rounds": run.state.round,
        "tally": dict(sorted(watch.tally.items())),
        "casts": watch.casts,
        "heals": watch.heals,
        "boss_damage": watch.boss_damage,
        "boss_turns": watch.boss_turns,
        "picks": watch.picks,
        "hits": dict(sorted(watch.hits.items())),
        "breaks": watch.breaks,
        "interrupts": watch.interrupts,
        "dantian": dict(sorted(watch.dantian.items())),
    }


def _run(seeds: int, jobs: int, out: Path) -> None:
    library = _library(True)
    tasks = [(job, parts) for parts in (False, True) for job in boss_jobs(library, WHICH, seeds)]
    print(f"霧鎖真人 {len(tasks)} 場（關／開各 {len(tasks) // 2}）", file=sys.stderr)
    records = run_tasks(run_one, None, tasks, jobs=jobs)
    out.write_text(json.dumps(records, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"寫出 {out}", file=sys.stderr)


# ---------------------------------------------------------------------------
# report：兩張表
# ---------------------------------------------------------------------------


def _row(cells: list[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _pct(num: int, den: int) -> str:
    return f"{num}/{den}（{num * 100 / den:.0f}%）" if den else "—"


def _rate(num: int, den: int) -> str:
    return f"{num}/{den}（{num * 100 / den:.0f}%）" if den else "—"


def _quart(values: list[int]) -> str:
    if not values:
        return "—"
    if len(values) < 2:  # noqa: PLR2004
        return f"{values[0]}"
    q1, q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return f"{q2:g}（{q1:g}～{q3:g}）"


def _report_one(library: ContentLibrary, off: list[Record], on: list[Record]) -> list[str]:
    lines = ["## 報表一：霧鎖真人部位關／開對照", ""]
    flips = sum(a["won"] != b["won"] for a, b in zip(off, on, strict=True))
    lines += [
        _row(["項目", "部位關", "部位開"]),
        _row(["---"] * 3),
        _row(["勝率", _pct(_wins(off), len(off)), _pct(_wins(on), len(on))]),
        _row(["平均輪數", _avg_rounds(off), _avg_rounds(on)]),
        _row(["歸一回血總量（場均）", _heal_sum(off), _heal_sum(on)]),
        _row(["勝負翻轉（同種子）", "—", f"{flips} 場"]),
        "",
        _row(["build", "關 勝場", "開 勝場", "關 平均輪", "開 平均輪"]),
        _row(["---"] * 5),
    ]
    for build in BUILDS:
        a = [r for r in off if r["build"] == build]
        b = [r for r in on if r["build"] == build]
        lines.append(
            _row(
                [
                    build.removeprefix("build_"),
                    _pct(_wins(a), len(a)),
                    _pct(_wins(b), len(b)),
                    _avg_rounds(a),
                    _avg_rounds(b),
                ]
            )
        )
    ta, tb = _tally(off), _tally(on)
    lines += ["", _row(["階段（行動回合 關／開）", "招", "關 施放率", "開 施放率"])]
    lines.append(_row(["---"] * 4))
    for phase, skills in boss_phase_skills(library, WHICH):
        head = f"第 {phase} 階段（{ta[f'turn|{phase}']}／{tb[f'turn|{phase}']}）"
        for skill in skills:
            key = f"cast|{phase}|{base_skill(skill)}"
            lines.append(
                _row(
                    [
                        head,
                        f"`{base_skill(skill)}`",
                        _rate(ta[key], ta[f"turn|{phase}"]),
                        _rate(tb[key], tb[f"turn|{phase}"]),
                    ]
                )
            )
            head = ""
    return [*lines, ""]


def _wins(records: list[Record]) -> int:
    return sum(r["won"] for r in records)


def _avg_rounds(records: list[Record]) -> str:
    return f"{sum(r['rounds'] for r in records) / len(records):.1f}" if records else "—"


def _heal_sum(records: list[Record]) -> str:
    total = sum(h[1] for r in records for h in r["heals"])
    return f"{total}（{total / len(records):.1f}）" if records else "—"


def _tally(records: list[Record]) -> Counter[str]:
    total: Counter[str] = Counter()
    for r in records:
        total.update(r["tally"])
    return total


def _break_of(record: Record, part: str) -> dict[str, Any] | None:
    return next((b for b in record["breaks"] if b["part"] == part), None)


def _report_two(off: list[Record], on: list[Record]) -> list[str]:
    lines = ["## 報表二：部位統計（部位開）", ""]
    lines += [
        _row(
            [
                "部位",
                "被選為目標",
                "打中",
                "破壞場數",
                "破壞輪（中位數，四分位）",
                "誰打破",
                "破壞時階段",
            ]
        ),
        _row(["---"] * 7),
    ]
    for part in (WHISK, DANTIAN, SWORD):
        picks = Counter(p[1] for r in on for p in r["picks"] if p[0] == part)
        breaks = [b for r in on if (b := _break_of(r, part)) is not None]
        by_build = Counter(r["build"].removeprefix("build_") for r in on if _break_of(r, part))
        lines.append(
            _row(
                [
                    PART_NAMES[part],
                    f"{sum(picks.values())}（{_counts(picks)}）",
                    sum(r["hits"].get(part, 0) for r in on),
                    f"{_pct(len(breaks), len(on))}；致命一擊未結算 "
                    f"{sum(not b['applied'] for b in breaks)}",
                    _quart([b["round"] for b in breaks]),
                    f"{_counts(Counter(b['by'] for b in breaks))}；build：{_counts(by_build)}",
                    _counts(Counter(f"第 {b['phase']} 階段" for b in breaks)),
                ]
            )
        )
    lines += ["", *_effects(off, on), "", *_dantian_reasons(on)]
    return [*lines, ""]


def _counts(counter: Counter[str]) -> str:
    return "、".join(f"{k} {v}" for k, v in sorted(counter.items())) or "—"


def _effects(off: list[Record], on: list[Record]) -> list[str]:
    """破壞效果：開組用「當時已破」旗標，關組用同種子、破壞輪（含）之後。"""
    shift = [0, 0, 0]  # 場數、關組次數、開組次數
    heal = [0, 0, 0]
    sword = [0, 0, 0, 0, 0]  # 場數、開組傷害、開組回合、關組傷害、關組回合
    for a, b in zip(off, on, strict=True):
        if (w := _break_of(b, WHISK)) is not None and w["applied"]:
            shift[0] += 1
            shift[1] += sum(c[2] == MIST_SHIFT and c[0] >= w["round"] for c in a["casts"])
            shift[2] += sum(c[2] == MIST_SHIFT and WHISK in c[3] for c in b["casts"])
        if (d := _break_of(b, DANTIAN)) is not None and d["applied"]:
            heal[0] += 1
            heal[1] += sum(h[1] for h in a["heals"] if h[0] >= d["round"])
            heal[2] += sum(h[1] for h in b["heals"] if DANTIAN in h[2])
        if (s := _break_of(b, SWORD)) is not None and s["applied"]:
            sword[0] += 1
            sword[1] += sum(x[2] for x in b["boss_damage"] if SWORD in x[3])
            sword[2] += sum(SWORD in t[2] for t in b["boss_turns"])
            sword[3] += sum(
                x[2] for x in a["boss_damage"] if x[0] >= s["round"] and x[1] == RETURN_PHASE
            )
            sword[4] += sum(t[0] >= s["round"] and t[1] == RETURN_PHASE for t in a["boss_turns"])
    p3_on = sum(
        x[2] for r in on for x in r["boss_damage"] if x[1] == RETURN_PHASE and SWORD not in x[3]
    )
    p3_on_t = sum(t[1] == RETURN_PHASE and SWORD not in t[2] for r in on for t in r["boss_turns"])
    interrupts = Counter(f"{i[0]}→{i[1]}" for r in on for i in r["interrupts"])
    return [
        _row(["破壞效果", "實際作用（同種子配對）"]),
        _row(["---"] * 2),
        _row(
            [
                "拂塵（封霧遁）",
                f"破的 {shift[0]} 場：關組破壞輪起霧遁 {shift[1]} 次；開組破壞後 {shift[2]} 次",
            ]
        ),
        _row(
            [
                "氣海（停歸一）",
                f"破的 {heal[0]} 場：關組破壞輪起歸一回血 {heal[1]}；開組破壞後 {heal[2]}",
            ]
        ),
        _row(["長劍（打斷蓄力）", f"打斷 {sum(interrupts.values())} 次（{_counts(interrupts)}）"]),
        _row(
            [
                "長劍（降傷）",
                f"破的 {sword[0]} 場：開組破後頭目對我方傷害 {sword[1]}／頭目回合 {sword[2]}"
                f"（{_per(sword[1], sword[2])}）；關組同種子破壞輪起的歸一 {sword[3]}／"
                f"{sword[4]}（{_per(sword[3], sword[4])}）；開組歸一長劍未破 {p3_on}／{p3_on_t}"
                f"（{_per(p3_on, p3_on_t)}）",
            ]
        ),
    ]


def _per(total: int, turns: int) -> str:
    return f"每回合 {total / turns:.1f}" if turns else "—"


def _dantian_reasons(on: list[Record]) -> list[str]:
    reasons: Counter[str] = Counter()
    for r in on:
        reasons.update(r["dantian"])
    total = sum(reasons.values())
    cells = "、".join(
        f"{REASON_ZH.get(k, k)} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])
    )
    return [
        f"氣海可選原因（第 2、3 階段我方對頭目本體的普攻／技能，共 {total} 次）：{cells or '—'}",
    ]


def _report(path: Path) -> None:
    records: list[Record] = json.loads(path.read_text(encoding="utf-8"))

    def order(r: Record) -> tuple[int, int]:
        return BUILDS.index(r["build"]), r["seed"]

    off = sorted((r for r in records if not r["parts"]), key=order)
    on = sorted((r for r in records if r["parts"]), key=order)
    library = load_library()
    print("\n".join([*_report_one(library, off, on), *_report_two(off, on)]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="跑部位關／開兩組（同種子配對），逐場紀錄寫 JSON")
    run.add_argument("--seeds", type=int, default=13)
    run.add_argument("--jobs", type=int, default=6)
    run.add_argument("--out", type=Path, required=True)
    render = sub.add_parser("report", help="把 run 的 JSON 重印成兩張表")
    render.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.cmd == "run":
        _run(args.seeds, args.jobs, args.out)
    else:
        _report(args.path)


if __name__ == "__main__":
    main()
