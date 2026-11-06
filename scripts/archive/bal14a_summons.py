# ruff: noqa: PLR2004
"""BAL-14a：召喚批（B2～B5、summoner 74%、Boss 有召喚輪數）只量＋建議；覆寫只在記憶體內的 library 副本。

子命令（輸出 Markdown；``--out`` 另存檔）::

    # B2：長戰單體／範圍戰／Boss 戰 × build（普攻流、技能流、召喚流與其變體）
    uv run python scripts/archive/bal14a_summons.py flow --variants base,ai.infuse_value_permille=0 --seeds 30 --jobs 6
    # B3／B5（＋B4 持續覆寫）：起始包 × 5 張正式圖＋Boss × 種子；每種召喚物被打倒、灌注、高台站位
    uv run python scripts/archive/bal14a_summons.py packs --packs dev_summoner,dev_summon_fire --variants base --seeds 10 --jobs 6
    # B4：召喚技能的預算、持續、三支進化（靜態；``--variants`` 套預算覆寫）
    uv run python scripts/archive/bal14a_summons.py budget --variants base,budget.summon_round_value_permille=600
    # 第 5 項：build_summoner 矩陣（10 圖 × 30 種子）在各覆寫下的勝率
    uv run python scripts/archive/bal14a_summons.py matrix --variants base,shp.summon_elemental_spirit=700 --jobs 6
    # 第 6 項：Boss 戰（有召喚 3 包＋無召喚 3 包）在各覆寫下的勝率、輪數與召喚相關分解
    uv run python scripts/archive/bal14a_summons.py boss --variants base,bosshp=650 --seeds 60 --jobs 6

覆寫語法（``+`` 串接，依序套用；``base`` ＝ 不改）：

- ``ai.<欄位>=<值>``：所有行為模式的 ``summon:``（SummonAiRules）欄位；
- ``core.<欄位>=<整數>``：``rules/core.yaml`` 的整數欄位（例如 ``summon_limit_per_owner``、``boss_summon_damage_permille``）；
- ``budget.<欄位>=<整數>``：``skill_budget.yaml`` 的整數欄位；
- ``rolehp=<‰>``：所有定位 HP 係數 ×‰；``shp.<召喚物>=<‰>``：該召喚物範本 ``max_hp`` ×‰；
- ``sdice.<召喚物>=<骰>``：該召喚物武器骰面（武器複本）；
- ``dur=<±n>``：所有召喚技 ``duration`` ±n（夾在 1～上限）；
- ``add=<技能>``／``skills=<a/b/c>``：build_summoner 加一招／改成這幾招；
- ``bosshp=<‰>``：Boss 戰頭目範本 HP ×‰（同 BAL-9b）。
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bal9_sweep import with_boss_hp  # type: ignore[import-not-found]
from bal9b_boss import Rec, run_one, wilson  # type: ignore[import-not-found]
from trpg.cli.sim import default_sim_maps
from trpg.content.battle import Dice
from trpg.content.dev_starters import DevStarter
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.engine.actions import Step
from trpg.engine.events import SkillInfused, TurnEnded
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.sim.attack_flow_report import SCENARIOS, Scenario, run_attack_flow
from trpg.sim.attrition import PLAIN_PACKS, SUMMON_PACKS
from trpg.sim.batch import run_batches
from trpg.sim.matrix import matrix_specs
from trpg.sim.metrics import StepTrace, TrackedRun, battle_metrics
from trpg.sim.parallel import run_tasks
from trpg.sim.summon_report import BOSS_MAP, SUMMON_MAPS, _spec
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.evolution import EvolutionRequest
from trpg.skillgen.summon_evolution import is_summon_skill, summon_evolution_options
from trpg.skillgen.usage import SkillUsage

ROOT = Path(__file__).resolve().parents[2]
SUMMONER = "build_summoner"
FLOW_BUILDS = ("build_attack_archer", "build_skill_archer", SUMMONER)
LONG_TARGET = "bal14_long_target"
LONG_HP_PERMILLE = 20000
"""BAL-14b 長戰情境：``std_enemy_t5`` 的複本，範本 HP ×20（10 輪內打不死），戰鬥上限 10 輪。"""
LONG = Scenario("long", "長戰單體（10 輪，會反擊）", "open_plain", False, (LONG_TARGET,))
LONG_IDLE = Scenario(
    "long_idle", "長戰單體（10 輪，不反擊）", "open_plain", False, (LONG_TARGET + "_idle",)
)
"""不反擊版：同一個目標改用 ``idle`` 行為模式、速度 0（防禦屬性與護甲不變）。"""
LONG_ROUNDS = 10


def with_long_target(lib: ContentLibrary) -> ContentLibrary:
    tpl = lib.units["std_enemy_t5"]
    hp = tpl.max_hp * LONG_HP_PERMILLE // 1000
    target = tpl.model_copy(update={"id": LONG_TARGET, "max_hp": hp})
    idle = target.model_copy(update={"id": LONG_TARGET + "_idle", "ai_profile": "idle", "speed": 0})
    units = {**lib.units, LONG_TARGET: target, idle.id: idle}
    return dataclasses.replace(lib, units=units)


# ---------------------------------------------------------------------------
# 覆寫
# ---------------------------------------------------------------------------


def _value(text: str) -> Any:
    if text in ("true", "false"):
        return text == "true"
    return int(text)


def _with_ruleset(lib: ContentLibrary, **update: Any) -> ContentLibrary:
    rs = lib.ruleset.model_copy(update=update)
    rs.model_post_init(None)
    return dataclasses.replace(lib, ruleset=rs)


def _ai(lib: ContentLibrary, name: str, value: Any) -> ContentLibrary:
    table = lib.ai_profiles
    profiles = [
        p.model_copy(update={"summon": p.summon.model_copy(update={name: value})})
        for p in table.profiles
    ]
    return dataclasses.replace(lib, ai_profiles=table.model_copy(update={"profiles": profiles}))


def _core(lib: ContentLibrary, **update: Any) -> ContentLibrary:
    return _with_ruleset(lib, core=lib.ruleset.core.model_copy(update=update))


def _summons(lib: ContentLibrary, sid: str, **tpl: Any) -> ContentLibrary:
    table = lib.ruleset.summons
    out = []
    for s in table.summons:
        if s.id == sid:
            weapon = tpl.pop("weapon_def", None)
            s = s.model_copy(update={"template": s.template.model_copy(update=tpl)})  # noqa: PLW2901
            if weapon is not None:
                s = s.model_copy(update={"weapon": weapon})  # noqa: PLW2901
        out.append(s)
    return _with_ruleset(lib, summons=table.model_copy(update={"summons": tuple(out)}))


def _skills(lib: ContentLibrary, fn: Callable[[SkillDef], SkillDef]) -> ContentLibrary:
    new = {sid: fn(s) for sid, s in lib.skills.items()}
    table = lib.ruleset.skills
    lib = dataclasses.replace(lib, skills=new)
    return _with_ruleset(
        lib, skills=table.model_copy(update={"skills": tuple(fn(s) for s in table.skills)})
    )


def _duration(delta: int, cap: int) -> Callable[[SkillDef], SkillDef]:
    def fn(skill: SkillDef) -> SkillDef:
        if not is_summon_skill(skill):
            return skill
        effects = tuple(
            e.model_copy(update={"duration": max(1, min(cap, e.duration + delta))})
            if e.type == "summon" and e.duration is not None
            else e
            for e in skill.effects
        )
        return skill.model_copy(update={"effects": effects})

    return fn


def _summoner_skills(
    lib: ContentLibrary, fn: Callable[[tuple[str, ...]], tuple[str, ...]]
) -> ContentLibrary:
    builds = []
    for b in lib.builds.builds:
        if b.id == SUMMONER:
            hero = b.hero.model_copy(update={"skills": fn(tuple(b.hero.skills))})
            builds.append(b.model_copy(update={"hero": hero}))
        else:
            builds.append(b)
    return dataclasses.replace(lib, builds=lib.builds.model_copy(update={"builds": tuple(builds)}))


def _with_mod(skill: SkillDef, change: str, value: Any) -> SkillDef:
    mods = tuple(
        m.model_copy(update={"change": m.change.model_copy(update={change: value})})
        if getattr(m.change, change) is not None
        else m
        for m in skill.modifiers
    )
    return skill.model_copy(update={"modifiers": mods})


def _apply_token(lib: ContentLibrary, token: str) -> ContentLibrary:  # noqa: PLR0911, PLR0912
    if token == "base":
        return lib
    key, _, raw = token.partition("=")
    head, _, sub = key.partition(".")
    if head == "ai":
        return _ai(lib, sub, _value(raw))
    if head == "core":
        return _core(lib, **{sub: _value(raw)})
    if head == "budget":
        return dataclasses.replace(lib, budget=lib.budget.model_copy(update={sub: _value(raw)}))
    if head == "rolehp":
        core = lib.ruleset.core
        roles = {k: v * int(raw) // 1000 for k, v in core.summon_role_hp_permille.items()}
        return _core(lib, summon_role_hp_permille=roles)
    if head == "shp":
        tpl = lib.ruleset.summon_def(sub).template
        return _summons(lib, sub, max_hp=max(1, tpl.max_hp * int(raw) // 1000))
    if head == "sdice":
        s = lib.ruleset.summon_def(sub)
        weapon = s.weapon.model_copy(update={"dice": Dice.model_validate(raw)})
        return _summons(lib, sub, weapon_def=weapon)
    if head == "dur":
        return _skills(lib, _duration(int(raw), lib.ruleset.core.summon_max_duration))
    if head == "mod":  # mod.<技能>.<修正欄位>=<值>：改修正型技能的那一條修正
        skill_id, _, change = sub.partition(".")
        return _skills(lib, lambda s: _with_mod(s, change, _value(raw)) if s.id == skill_id else s)
    if head == "durfit":  # 每招召喚技的持續改成目前預算下（比 ≤ 1.0）最長的輪數
        fits = {sid: _longest_fit(lib, lib.skills[sid]) for sid in _summon_skill_ids(lib)}
        return _skills(lib, lambda s: _set_duration(s, fits[s.id]) if fits.get(s.id) else s)
    if head == "add":
        return _summoner_skills(lib, lambda s: (*s, raw))
    if head == "skills":
        return _summoner_skills(lib, lambda _s: tuple(raw.split("/")))
    if head == "pack":  # 臨時起始包：召喚技 ＋ 火焰箭（同 dev_summon_* 的組法）
        starter = DevStarter(
            id=sub,
            label_zh=sub,
            weapon="totem_staff",
            keywords=("summon", "ignite"),
            skills=(raw, "skill_fire_bolt"),
        )
        table = lib.dev_starters
        return dataclasses.replace(
            lib, dev_starters=table.model_copy(update={"packs": (*table.packs, starter)})
        )
    if head == "bosshp":
        out: ContentLibrary = with_boss_hp(lib, int(raw))
        return out
    raise ValueError(f"未知的覆寫：{token}")


def variant(lib: ContentLibrary, name: str) -> ContentLibrary:
    for token in name.split("+"):
        lib = _apply_token(lib, token)
    return lib


def _variants(base: ContentLibrary, names: str) -> dict[str, ContentLibrary]:
    return {n: variant(base, n) for n in names.split(",")}


def _write(lines: list[str], out: Path | None) -> None:
    text = "\n".join(lines) + "\n"
    print(text)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# B2 flow
# ---------------------------------------------------------------------------


def cmd_flow(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    if args.long:
        base = with_long_target(base)
    libs = _variants(base, args.variants)
    builds = tuple(args.builds.split(","))
    scenarios = (LONG, LONG_IDLE) if args.long else SCENARIOS
    rounds = LONG_ROUNDS if args.long else 30
    lines = [
        f"每格 {args.seeds} 場（種子 0–{args.seeds - 1}）；我方 DPR ＝ 我方總傷害（含召喚物、隊友）÷ 輪數，每場平均；"
        "召喚占比 ＝ 召喚物傷害 ÷ 我方總傷害（合計）",
        "",
        "| 覆寫 | 情境 | build | 勝率 | 輪數 | 英雄傷害/場 | 召喚物傷害/場 | 我方 DPR | 召喚占比 | 召喚次數/場 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    started = time.perf_counter()
    for name, lib in libs.items():
        only = builds if name == "base" or args.builds != ",".join(FLOW_BUILDS) else (SUMMONER,)
        samples = run_attack_flow(
            lib,
            scenarios=scenarios,
            builds=only,
            seeds=args.seeds,
            jobs=args.jobs,
            max_rounds=rounds,
        )
        cells: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for s in samples:
            if s.metrics is not None:
                cells[(s.scenario, s.build)].append(s.metrics)
        for (sc, b), ms in cells.items():
            n = len(ms)
            wins = sum(m.result == "ally" for m in ms)
            rounds = statistics.mean(m.rounds for m in ms)
            hero = statistics.mean(
                next(u.damage_dealt for u in m.units if u.team is Team.ALLY and u.template_id == b)
                for m in ms
            )
            summ = statistics.mean(m.summon_damage(Team.ALLY) for m in ms)
            total = sum(m.team_damage(Team.ALLY) for m in ms)
            dpr = statistics.mean(m.team_damage(Team.ALLY) / max(1, m.rounds) for m in ms)
            share = sum(m.summon_damage(Team.ALLY) for m in ms) / max(1, total)
            calls = statistics.mean(sum(1 for r in m.summons if r.team is Team.ALLY) for m in ms)
            lines.append(
                f"| {name} | {sc} | {b} | {wins * 100 / n:.0f}% | {rounds:.1f} | {hero:.0f} | {summ:.0f} "
                f"| {dpr:.1f} | {share * 100:.0f}% | {calls:.2f} |"
            )
        print(f"[{time.perf_counter() - started:7.1f}s] {name}", file=sys.stderr, flush=True)
    _write(lines, args.out)
    return 0


# ---------------------------------------------------------------------------
# B3／B5 packs
# ---------------------------------------------------------------------------


@dataclass
class PackRec:
    variant: str
    pack: str
    map_id: str
    seed: int
    ok: bool = False
    win: bool = False
    rounds: int = 0
    infusions: int = 0
    ally_damage: int = 0
    summon_damage: int = 0
    # (範本, 結束原因, 存活輪數)
    summons: list[tuple[str, str, int]] = field(default_factory=list)
    ranged_turns_platform: int = 0  # 有我方高台時，我方遠程（非召喚物）回合結束的次數
    ranged_on_platform: int = 0  # 其中站在高台上的次數


def _pack_one(libs: dict[str, ContentLibrary], task: tuple[str, str, str, int]) -> PackRec:
    name, pack, map_id, seed = task
    rec = PackRec(name, pack, map_id, seed)
    try:
        spec, _hero = _spec(libs[name], pack, map_id, seed, 30)
        trace = StepTrace()

        def on_step(step: Step | None, result: ResolveResult) -> None:
            trace(step, result)
            state = result.state
            for e in result.events:
                if isinstance(e, SkillInfused):
                    rec.infusions += 1
                elif isinstance(e, TurnEnded):
                    u = state.units.get(e.unit_id)
                    if u is None or u.team is not Team.ALLY or u.is_summon or u.weapon.is_melee:
                        continue
                    plats = [
                        (p.platform_pos.x, p.platform_pos.y)
                        for p in state.units.values()
                        if p.alive and p.team is Team.ALLY and p.platform_pos is not None
                    ]
                    if plats:
                        rec.ranged_turns_platform += 1
                        rec.ranged_on_platform += u.xy in plats

        run = run_battle(
            spec.setup,
            spec.seeds[0],
            spec.policy_factory(),
            on_step=on_step,
            max_actions=spec.max_actions,
        )
        m = battle_metrics(TrackedRun(run, trace))
    except Exception:  # 與 batch.run_one 一致：任何例外視為未完成
        return rec
    rec.ok = True
    rec.win = m.result == "ally"
    rec.rounds = m.rounds
    rec.ally_damage = m.team_damage(Team.ALLY)
    rec.summon_damage = m.summon_damage(Team.ALLY)
    alive = {u.unit_id: u.alive_rounds for u in m.units}
    rec.summons = [
        (r.template_id, r.end, alive[r.unit_id]) for r in m.summons if r.team is Team.ALLY
    ]
    return rec


def _pack_rows(recs: Sequence[PackRec], label: str) -> list[str]:
    done = [r for r in recs if r.ok]
    if not done:
        return []
    n = len(done)
    wins = sum(r.win for r in done)
    with_s = [r for r in done if r.summons]
    by_tpl: dict[str, Counter[str]] = defaultdict(Counter)
    life: dict[str, list[int]] = defaultdict(list)
    for r in done:
        for tpl, end, rounds in r.summons:
            by_tpl[tpl][end] += 1
            life[tpl].append(rounds)
    rows = []
    for tpl in sorted(by_tpl):
        c = by_tpl[tpl]
        total = sum(c.values())
        downed = c.get("downed", 0) * 100 / total
        ends = "、".join(f"{k} {v}" for k, v in sorted(c.items()))
        infuse = sum(r.infusions for r in with_s) / max(1, len(with_s))
        plat = sum(r.ranged_on_platform for r in done)
        plat_n = sum(r.ranged_turns_platform for r in done)
        plat_txt = f"{plat}/{plat_n}" if plat_n else "—"
        share = sum(r.summon_damage for r in done) * 100 / max(1, sum(r.ally_damage for r in done))
        rows.append(
            f"| {label} | {tpl} | {n} | {wins * 100 / n:.0f}% | {statistics.mean(r.rounds for r in done):.1f} "
            f"| {total} | **{downed:.0f}%** | {statistics.mean(life[tpl]):.1f} | {ends} | {infuse:.2f}（{len(with_s)} 場） "
            f"| {share:.0f}% | {plat_txt} |"
        )
    return rows


def cmd_packs(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    for extra in filter(None, args.extra.split(",")):  # 臨時起始包（id=召喚技）
        base = _apply_token(base, f"pack.{extra}")
    libs = _variants(base, args.variants)
    packs = args.packs.split(",")
    maps = [*SUMMON_MAPS, BOSS_MAP] if args.maps == "all" else args.maps.split(",")
    tasks = [(v, p, m, s) for v in libs for p in packs for m in maps for s in range(args.seeds)]
    started = time.perf_counter()
    recs = run_tasks(_pack_one, libs, tasks, jobs=args.jobs)
    print(f"[{time.perf_counter() - started:7.1f}s] {len(tasks)} 場", file=sys.stderr)
    head = (
        "| 覆寫／起始包／戰鬥 | 召喚物 | 場數 | 勝率 | 輪數 | 召喚物數 | 被打倒 | 平均存活輪 | 結束原因 "
        "| 灌注/有召喚場 | 召喚傷害占比 | 遠程站上高台（回合） |"
    )
    lines = [
        f"每格每圖 {args.seeds} 種子；一般戰 ＝ {', '.join(m for m in maps if m != BOSS_MAP)}",
        "",
        head,
        "|" + "---|" * 12,
    ]
    failed = sum(not r.ok for r in recs)
    for v in libs:
        for p in packs:
            sel = [r for r in recs if r.variant == v and r.pack == p]
            normal = [r for r in sel if r.map_id != BOSS_MAP]
            boss = [r for r in sel if r.map_id == BOSS_MAP]
            lines += _pack_rows(normal, f"{v}／{p}／一般")
            lines += _pack_rows(boss, f"{v}／{p}／Boss")
    lines.append("")
    lines.append(f"未完成（例外或動作上限）：{failed} 場")
    _write(lines, args.out)
    return 0


# ---------------------------------------------------------------------------
# B4 budget（靜態）
# ---------------------------------------------------------------------------


def _summon_skill_ids(lib: ContentLibrary) -> list[str]:
    return sorted(
        sid
        for sid, s in lib.skills.items()
        if is_summon_skill(s) and s.provenance.origin == "builtin"
    )


def _set_duration(skill: SkillDef, d: int) -> SkillDef:
    effects = tuple(
        e.model_copy(update={"duration": d}) if e.type == "summon" else e for e in skill.effects
    )
    return skill.model_copy(update={"effects": effects})


def _longest_fit(lib: ContentLibrary, skill: SkillDef) -> int:
    """預算比 ≤ 1.0 下最長可放幾輪（0 ＝ 1 輪也放不下）。"""
    fit = 0
    for d in range(1, lib.ruleset.core.summon_max_duration + 1):
        try:
            if skill_budget(_set_duration(skill, d), lib).ratio <= 1:
                fit = d
        except BudgetError:
            break
    return fit


def _budget_row(lib: ContentLibrary, sid: str) -> tuple[str, int, str, str, int, str]:
    skill = lib.skills[sid]
    eff = next(e for e in skill.effects if e.type == "summon")
    try:
        rep = skill_budget(skill, lib)
        ratio = f"{float(rep.ratio):.2f}"
        note = next((e.note for e in rep.effects if e.type == "summon"), "")
    except BudgetError as exc:
        ratio, note = "錯誤", str(exc)
    fit = _longest_fit(lib, skill)
    opts = summon_evolution_options(lib, EvolutionRequest(skill, SkillUsage(), {}, 5))
    names = "／".join(o.template.removeprefix("summon_") for o in opts) or "—"
    return eff.unit or "", eff.duration or 0, ratio, names, fit, note


def cmd_budget(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    lines: list[str] = []
    for name, lib in _variants(base, args.variants).items():
        ids = _summon_skill_ids(lib)
        full = 0
        lines += [
            f"### {name}",
            "",
            "| 技能 | 召喚物 | 持續 | 預算比 | ≤1.0 最長持續 | 進化支 | 點數明細 |",
            "|---|---|---|---|---|---|---|",
        ]
        for sid in ids:
            unit, dur, ratio, evo, fit, note = _budget_row(lib, sid)
            full += evo.count("／") == 2
            lines.append(f"| {sid} | {unit} | {dur} | {ratio} | {fit} | {evo} | {note} |")
        lines += ["", f"三支齊全：{full}／{len(ids)}", ""]
    _write(lines, args.out)
    return 0


# ---------------------------------------------------------------------------
# 第 5 項：summoner 矩陣
# ---------------------------------------------------------------------------


def cmd_matrix(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    libs = _variants(base, args.variants)
    seeds = tuple(range(args.seeds))
    maps = default_sim_maps(base)
    all_specs: list[tuple[str, str, Any]] = []
    for name, lib in libs.items():
        for b in args.builds.split(","):
            all_specs += [
                (f"{b}／{name}", m, spec) for _, m, spec in matrix_specs(lib, [b], maps, seeds)
            ]
    started = time.perf_counter()
    reports = run_batches([s for _, _, s in all_specs], jobs=args.jobs)
    print(f"[{time.perf_counter() - started:7.1f}s] {len(all_specs)} 格", file=sys.stderr)
    agg: dict[str, list[float]] = {}
    for (name, _m, _), rep in zip(all_specs, reports, strict=True):
        a = agg.setdefault(name, [0, 0, 0.0, 0.0])
        a[0] += rep.ally_wins
        a[1] += rep.completed
        a[2] += rep.rounds_mean * rep.completed
    lines = [
        f"{args.builds} × {len(maps)} 圖 × {len(seeds)} 種子（同種子；BAL-13d build_summoner 基準 74.3%）",
        "",
        "| 覆寫 | 勝率 | 95% CI | 平均輪數 |",
        "|---|---|---|---|",
    ]
    for name, (w, n, r, _) in agg.items():
        lo, hi = wilson(int(w), int(n))
        lines.append(
            f"| {name} | {w * 100 / max(1, n):.1f}% | {lo:.0f}–{hi:.0f} | {r / max(1, n):.2f} |"
        )
    _write(lines, args.out)
    return 0


# ---------------------------------------------------------------------------
# 第 6 項：Boss
# ---------------------------------------------------------------------------


def _boss_line(name: str, kind: str, recs: Sequence[Rec]) -> str:
    n = len(recs)
    w = sum(r.win for r in recs)
    lo, hi = wilson(w, n)
    rounds = statistics.mean(r.rounds for r in recs)
    killed = [r for r in recs if r.boss_dead_round is not None]
    kill_round = statistics.mean(r.boss_dead_round for r in killed) if killed else float("nan")
    after = (
        statistics.mean(r.rounds - r.boss_dead_round for r in killed) if killed else float("nan")
    )
    dmg_in: Counter[str] = Counter()
    for r in recs:
        for k, v in r.dmg.items():
            dmg_in[k.split(":")[1]] += v
    total_in = sum(dmg_in.values()) or 1
    boss_in = sum(r.in_by_source.get("bandit_warlord", 0) for r in recs)
    long = sum(r.rounds > 10 for r in recs)
    return (
        f"| {name} | {kind} | {w * 100 / n:.1f}%（{lo:.0f}–{hi:.0f}） | **{rounds:.1f}** | {long * 100 / n:.0f}% "
        f"| {len(killed) * 100 / n:.0f}% | {kill_round:.1f} | {after:.1f} "
        f"| {dmg_in['summon'] * 100 / total_in:.0f}% | {boss_in / n:.0f} |"
    )


def cmd_boss(args: argparse.Namespace) -> int:
    base = load_library(ROOT / "content")
    names = args.variants.split(",")
    libs = {i: variant(base, n) for i, n in enumerate(names)}
    packs = (*SUMMON_PACKS, *(() if args.summon_only else PLAIN_PACKS))
    tasks = [(p, s, i) for i in libs for p in packs for s in range(args.seeds)]
    started = time.perf_counter()
    recs: list[Rec] = run_tasks(run_one, libs, tasks, jobs=args.jobs)
    print(f"[{time.perf_counter() - started:7.1f}s] {len(tasks)} 場", file=sys.stderr)
    lines = [
        f"每包 {args.seeds} 種子；有召喚 ＝ {'、'.join(SUMMON_PACKS)}；無召喚 ＝ {'、'.join(PLAIN_PACKS)}",
        "",
        "| 覆寫 | 類別 | 勝率（95% CI） | 輪數 | >10 輪 | 打倒頭目 | 頭目倒下輪 | 之後還打幾輪 | 敵方傷害落在召喚物 | 頭目每場輸出 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, name in enumerate(names):
        sel = [r for r in recs if r.mult == i]
        lines.append(_boss_line(name, "有召喚", [r for r in sel if r.summon]))
        if not args.summon_only:
            lines.append(_boss_line(name, "無召喚", [r for r in sel if not r.summon]))
        for p in SUMMON_PACKS:
            lines.append(_boss_line(name, p, [r for r in sel if r.pack == p]))
    _write(lines, args.out)
    return 0


# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("flow")
    f.add_argument("--variants", default="base")
    f.add_argument("--builds", default=",".join(FLOW_BUILDS))
    f.add_argument("--seeds", type=int, default=30)
    f.add_argument("--long", action="store_true", help="BAL-14b 長戰單體：高 HP 目標、上限 10 輪")
    f.set_defaults(func=cmd_flow)
    p = sub.add_parser("packs")
    p.add_argument("--packs", required=True)
    p.add_argument("--variants", default="base")
    p.add_argument("--maps", default="all")
    p.add_argument("--extra", default="", help="臨時起始包 id=召喚技，逗號分隔")
    p.add_argument("--seeds", type=int, default=10)
    p.set_defaults(func=cmd_packs)
    b = sub.add_parser("budget")
    b.add_argument("--variants", default="base")
    b.set_defaults(func=cmd_budget)
    m = sub.add_parser("matrix")
    m.add_argument("--variants", default="base")
    m.add_argument("--seeds", type=int, default=30)
    m.add_argument("--builds", default=SUMMONER)
    m.set_defaults(func=cmd_matrix)
    bo = sub.add_parser("boss")
    bo.add_argument("--variants", default="base")
    bo.add_argument("--seeds", type=int, default=60)
    bo.add_argument("--summon-only", action="store_true")
    bo.set_defaults(func=cmd_boss)
    for sp in (f, p, b, m, bo):
        sp.add_argument("--jobs", type=int, default=6)
        sp.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
