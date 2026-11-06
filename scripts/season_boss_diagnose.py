"""碎晶之主的敗因分析（Phase 5F-3b；``docs/archive/phases/Phase5F-3b報告.md``）。

同 ``scripts/season_boss_sim.py`` 的真實路徑（``prepare_battle`` → 效用 AI 雙方），每場多記：
停在哪個階段、怎麼輸（全滅／超過輪數）、柱子全倒在第幾輪、我方對柱子與本體的傷害（主角／傭兵分開）、
我方受到的傷害來源（敵方單位範本・技能；持續傷害另列）、第一個倒下的我方在第幾輪。

用法::

    uv run python scripts/season_boss_diagnose.py [--seeds 40] [--builds build_striker,...]
        [--set rift_shard_lord.max_hp=400,pillars.max_hp=60,rift_shard_lord.attr.int=14,
               rift_shard_lord.phase.rift_collapse.round=18,
               status:rift_channel.damage_dealt_permille=700]   # 不改 content 的候選

只輸出摘要表；數值建議寫進報告由 PM 決定（CLAUDE.md 第 11 條）。
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    BossPhaseChanged,
    DamageDealt,
    SkillUsed,
    UnitDowned,
)
from trpg.engine.runner import run_battle
from trpg.shared.types import Attribute, Team
from trpg.world.battle import prepare_battle
from trpg.world.state import CharacterState

_spec = importlib.util.spec_from_file_location(
    "season_boss_sim", Path(__file__).resolve().parent / "season_boss_sim.py"
)
assert _spec is not None and _spec.loader is not None
_sim = importlib.util.module_from_spec(_spec)
sys.modules["season_boss_sim"] = _sim
_spec.loader.exec_module(_sim)
BOSS: str = _sim.BOSS
BUILDS: tuple[str, ...] = _sim.BUILDS
PILLARS: tuple[str, ...] = _sim.PILLARS
make_char: Callable[[ContentLibrary, str, int], CharacterState] = _sim.make_char

PHASE_NAMES = ("三柱", "碎界脈動", "核心過載", "界崩")


@dataclass
class Diag:
    build: str
    won: bool
    rounds: int
    phase: int
    reason: str
    pillars_down_round: int | None
    first_down_round: int | None
    hero_to_pillar: int = 0
    merc_to_pillar: int = 0
    hero_to_boss: int = 0
    merc_to_boss: int = 0
    taken: Counter[str] = field(default_factory=Counter)
    downs_by: Counter[str] = field(default_factory=Counter)


type Overrides = tuple[tuple[str, str, str], ...]
"""（單位, 欄位, 值）：欄位是單位的整數欄位（``max_hp``）、``attr.<屬性>``，或 ``swap``（值＝
「舊技能:新技能」，換掉本體與各階段技能清單裡的技能）。"""


def _apply(template: UnitTemplate, name: str, value: str) -> UnitTemplate:
    if name == "swap":
        old, new = value.split(":")
        phases = tuple(
            p
            if p.skills is None
            else p.model_copy(update={"skills": tuple(new if s == old else s for s in p.skills)})
            for p in template.phases
        )
        skills = tuple(new if s == old else s for s in template.skills)
        return template.model_copy(update={"skills": skills, "phases": phases})
    if name.startswith("phase."):  # phase.<階段>.<觸發欄位>（例如 phase.rift_collapse.round）
        phase_id, key = name.removeprefix("phase.").split(".")
        phases = tuple(
            p.model_copy(update={"trigger": p.trigger.model_copy(update={key: int(value)})})
            if p.id == phase_id and p.trigger is not None
            else p
            for p in template.phases
        )
        return template.model_copy(update={"phases": phases})
    if name.startswith("attr."):
        attrs = dict(template.attributes)
        attrs[Attribute(name.removeprefix("attr."))] = int(value)
        return template.model_copy(update={"attributes": attrs})
    return template.model_copy(update={name: int(value)})


def _library(overrides: Overrides) -> ContentLibrary:
    library = load_library()
    if not overrides:
        return library
    units = dict(library.units)
    ruleset = library.ruleset
    for unit, name, value in overrides:
        if unit.startswith("status:"):  # status:<狀態>.<整數欄位>=值
            status_id = unit.removeprefix("status:")
            table = ruleset.statuses.model_copy(
                update={
                    "statuses": tuple(
                        s.model_copy(update={name: int(value)}) if s.id == status_id else s
                        for s in ruleset.statuses.statuses
                    )
                }
            )
            ruleset = ruleset.model_copy(update={"statuses": table})
            ruleset.model_post_init(None)
        else:
            units[unit] = _apply(units[unit], name, value)
    return dataclasses.replace(library, units=units, ruleset=ruleset)


def _run(args: tuple[str, int, Overrides]) -> Diag:  # noqa: C901, PLR0912, PLR0915 - 單一事件迴圈
    build_id, seed, overrides = args
    library = _library(overrides)
    prepared = prepare_battle(library, make_char(library, build_id, seed))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    units = run.state.units
    boss = next(u for u in units.values() if u.template_id == BOSS)
    hero = next(u for u in units.values() if u.team is Team.ALLY)  # 我方第一個＝主角
    last_skill: dict[str, str] = {}
    phase = 0
    pillars_down = 0
    pillars_round: int | None = None
    first_down: int | None = None
    diag = Diag(build_id, run.state.winner is Team.ALLY, run.state.round, 0, "", None, None)
    last_hit: dict[str, str] = {}
    for e in run.events:
        if isinstance(e, SkillUsed):
            last_skill[e.unit_id] = e.skill_id
        elif isinstance(e, BossPhaseChanged) and e.unit_id == boss.id:
            phase += 1
        elif isinstance(e, DamageDealt):
            dealt = e.hp_before - e.hp_after
            target = units.get(e.target_id)
            source = units.get(e.source_id) if e.source_id is not None else None
            if target is None:
                continue
            if target.team is Team.ALLY and source is not None and source.team is not Team.ALLY:
                how = "持續" if e.cause == "status" else last_skill.get(source.id, e.cause)
                key = f"{source.template_id}・{how}"
                diag.taken[key] += dealt
                last_hit[target.id] = key
            elif target.team is Team.ALLY:
                key = f"（{e.cause}）"
                diag.taken[key] += dealt
                last_hit[target.id] = key
            elif source is not None and source.team is Team.ALLY:
                is_hero = source.id == hero.id or source.template_id == hero.template_id
                if target.template_id in PILLARS:
                    if is_hero:
                        diag.hero_to_pillar += dealt
                    else:
                        diag.merc_to_pillar += dealt
                elif target.id == boss.id:
                    if is_hero:
                        diag.hero_to_boss += dealt
                    else:
                        diag.merc_to_boss += dealt
        elif isinstance(e, UnitDowned):
            unit = units.get(e.unit_id)
            if unit is None:
                continue
            if unit.template_id in PILLARS:
                pillars_down += 1
                if pillars_down == len(PILLARS):
                    pillars_round = e.round
            elif unit.team is Team.ALLY:
                if first_down is None:
                    first_down = e.round
                diag.downs_by[last_hit.get(unit.id, "?")] += 1
    diag.phase = phase
    diag.pillars_down_round = pillars_round
    diag.first_down_round = first_down
    if diag.won:
        diag.reason = "勝"
    elif any(
        u.team is Team.ALLY and not u.template_id.startswith("summon_") and u.hp > 0
        for u in units.values()
    ):
        diag.reason = "超過輪數"
    else:
        diag.reason = "主角與傭兵全倒"
    return diag


def _avg(values: Sequence[int]) -> str:
    return f"{sum(values) / len(values):.1f}" if values else "—"


def report(label: str, rows: Sequence[Diag]) -> list[str]:
    n = len(rows)
    lost = [r for r in rows if not r.won]
    phases = Counter(PHASE_NAMES[min(r.phase, 3)] for r in lost)
    reasons = Counter(r.reason for r in lost)
    head = (
        f"| {label} | {n} | {sum(r.won for r in rows) * 100 // n}% "
        f"| {_avg([r.rounds for r in rows])} "
        f"| {_avg([r.pillars_down_round for r in rows if r.pillars_down_round])} "
        f"| {_avg([r.hero_to_pillar for r in rows])}／{_avg([r.merc_to_pillar for r in rows])} "
        f"| {_avg([r.hero_to_boss for r in rows])}／{_avg([r.merc_to_boss for r in rows])} "
        f"| {'、'.join(f'{k} {v}' for k, v in phases.most_common()) or '—'} "
        f"| {'、'.join(f'{k} {v}' for k, v in reasons.most_common()) or '—'} |"
    )
    taken: Counter[str] = Counter()
    downs: Counter[str] = Counter()
    for r in lost or rows:
        taken.update(r.taken)
        downs.update(r.downs_by)
    total = sum(taken.values()) or 1
    detail = (
        f"  - {label} {'敗場' if lost else '全部'}受到的傷害前 5："
        + "、".join(f"{k} {v * 100 // total}%" for k, v in taken.most_common(5))
        + "；倒下時最後一擊："
        + ("、".join(f"{k} {v}" for k, v in downs.most_common(4)) or "—")
    )
    return [head, detail]


def _overrides(text: str) -> Overrides:
    out: list[tuple[str, str, str]] = []
    for item in (t for t in text.split(",") if t):
        key, value = item.split("=")
        unit, name = key.split(".", 1)
        units = PILLARS if unit == "pillars" else (unit,)
        out += [(u, name, value) for u in units]
    return tuple(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--builds", default=",".join(BUILDS))
    parser.add_argument("--set", default="", help="unit.field=value（pillars.max_hp＝三根柱子）")
    args = parser.parse_args(argv)
    builds = [b for b in args.builds.split(",") if b]
    overrides = _overrides(args.set)
    jobs = [(b, seed, overrides) for b in builds for seed in range(1, args.seeds + 1)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(_run, jobs))
    print(
        "| build | 場數 | 勝率 | 平均輪數 | 柱子全倒輪 | 對柱傷害 主角／傭兵 "
        "| 對本體傷害 主角／傭兵 | 敗場停在 | 敗因 |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    details: list[str] = []
    for build in builds:
        head, detail = report(build, [r for r in rows if r.build == build])
        print(head, flush=True)
        details.append(detail)
    head, detail = report("全部", rows)
    print(head)
    print()
    print("\n".join([*details, detail]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
