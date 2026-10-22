"""普攻流對照模擬（Phase 3-32a，``docs/design/08-裝備.md`` 8.25；``scripts/sim_attack_flow.py``）。

三種情境各跑「普攻流弓手」與「技能流弓手」（``content/sim/builds.yaml``）：

- ``single``（長戰單體）：英雄單獨對 1 個高 HP 的單體敵人；
- ``area``（範圍戰）：英雄＋標準隊友對 4 個小兵（起始區最多 4 格）；
- ``boss``（Boss 戰）：英雄＋標準隊友對盜賊巢穴的預設陣容（Boss 加護衛）。

每格輸出勝率、英雄 DPR、平均輪數。**只量不調**：不改任何規則或數值；建議由 PM 決定。結果只取決於
（情境、build、種子），與 ``jobs`` 無關。
"""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.engine.actions import Step
from trpg.engine.events import UnitSpawned, UnitSummoned
from trpg.engine.ids import BOSS_TAG
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.attack_flow_diag import (
    FlowExtras,
    FlowTrace,
    analyze_flow,
    hero_mastery_permille,
)
from trpg.sim.batch import (
    DEFAULT_MAX_ROUNDS,
    BatchSpec,
    UtilityPolicyFactory,
)
from trpg.sim.matrix import library_with_builds
from trpg.sim.metrics import BattleMetrics, StepTrace, TrackedRun, battle_metrics

__all__ = [
    "BUILDS",
    "SCENARIOS",
    "CellSample",
    "CellSummary",
    "Scenario",
    "format_attack_flow",
    "format_diagnosis",
    "format_new_metrics",
    "run_attack_flow",
    "summarize",
]

BUILDS: tuple[str, ...] = ("build_attack_archer", "build_skill_archer")
"""普攻流弓手、技能流弓手。"""


@dataclass(frozen=True, slots=True)
class Scenario:
    """一種情境：地圖、我方有沒有標準隊友與敵方陣容（``None`` ＝ 地圖預設陣容）。"""

    id: str
    label_zh: str
    map_id: str
    companions: bool
    enemies: tuple[str, ...] | None


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("single", "長戰單體", "open_plain", False, ("std_enemy_t5",)),
    Scenario("area", "範圍戰", "open_plain", True, ("bandit",) * 4),
    Scenario("boss", "Boss 戰", "bandit_lair", True, None),
)


@dataclass(frozen=True, slots=True)
class CellSample:
    """一場戰鬥：情境、build、種子與指標（失敗時 ``metrics`` 為 ``None``）。"""

    scenario: str
    build: str
    seed: int
    metrics: BattleMetrics | None
    flow: FlowExtras | None = None
    """診斷與新指標（Phase 3-32d）；失敗時為 ``None``。"""


def _setup(library: ContentLibrary, scenario: Scenario, build_id: str, rounds: int) -> BattleSetup:
    map_def = library.map(scenario.map_id)
    enemies = scenario.enemies
    if enemies is None:
        assert map_def.encounter is not None
        enemies = tuple(map_def.encounter.enemies)
    companions = tuple(library.builds.companions) if scenario.companions else ()
    # build 的英雄範本 ID ＝ build ID（``library`` 須已加入 build 英雄，裝備一起解析）
    return build_setup(
        library, scenario.map_id, (build_id, *companions), enemies, max_rounds=rounds
    )


def run_attack_flow(
    library: ContentLibrary,
    *,
    scenarios: Sequence[Scenario] = SCENARIOS,
    builds: Sequence[str] = BUILDS,
    seeds: int = 20,
    seed_start: int = 0,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    jobs: int = 1,
) -> list[CellSample]:
    """每個情境 × build × ``seeds`` 個種子各打一場；結果依（情境、build、種子）排序。"""
    keys = [(sc, b) for sc in scenarios for b in builds]
    library = library_with_builds(library)  # build 英雄範本放進單位表
    specs = [
        (
            BatchSpec(
                name=f"{sc.id}/{b}",
                setup=_setup(library, sc, b, max_rounds),
                seeds=tuple(range(seed_start, seed_start + seeds)),
                policy_factory=UtilityPolicyFactory(library.ai_profiles),
            ),
            b,
        )
        for sc, b in keys
    ]
    results = _run_specs(specs, jobs)
    return [
        CellSample(sc.id, b, seed, metrics, flow)
        for (sc, b), batch in zip(keys, results, strict=True)
        for seed, metrics, flow in batch
    ]


type _Result = tuple[int, BattleMetrics | None, FlowExtras | None]


def _run_flow(spec: BatchSpec, hero: str, seed: int) -> _Result:
    """一場戰鬥：指標＋診斷（任何例外都轉成失敗結果）。"""
    try:
        trace, flow_trace = StepTrace(), FlowTrace(hero)

        def on_step(step: Step | None, result: ResolveResult) -> None:
            trace(step, result)
            flow_trace(step, result)

        run = run_battle(
            spec.setup,
            seed,
            spec.policy_factory(),
            on_step=on_step,
            max_actions=spec.max_actions,
        )
        tracked = TrackedRun(run, trace)
        metrics = battle_metrics(tracked)
        later = {e.unit_id for e in run.events if isinstance(e, UnitSpawned | UnitSummoned)}
        units = run.state.units.values()
        hero_id = next(u.id for u in units if u.team is Team.ALLY and u.template_id == hero)
        enemies = frozenset(u.id for u in units if u.team is Team.ENEMY and u.id not in later)
        bosses = frozenset(u.id for u in units if u.id in enemies and BOSS_TAG in u.tags)
        flow = analyze_flow(
            run.events,
            tracked.bounds,
            hero_id=hero_id,
            enemy_ids=enemies,
            boss_ids=bosses,
            mastery_permille=hero_mastery_permille(spec.setup, hero),
            trace=flow_trace,
        )
        return seed, metrics, flow
    except TrpgError:
        return seed, None, None


_SPECS: tuple[tuple[BatchSpec, str], ...] = ()


def _init(specs: tuple[tuple[BatchSpec, str], ...]) -> None:
    global _SPECS  # noqa: PLW0603 - 行程初始化：每個工作行程只收一次規格
    _SPECS = specs


def _work(task: tuple[int, int]) -> tuple[int, _Result]:
    index, seed = task
    spec, hero = _SPECS[index]
    return index, _run_flow(spec, hero, seed)


def _run_specs(specs: Sequence[tuple[BatchSpec, str]], jobs: int) -> list[list[_Result]]:
    if jobs < 1:
        raise ValueError("jobs 必須 >= 1")
    tasks = [(i, seed) for i, (spec, _) in enumerate(specs) for seed in spec.seeds]
    if jobs == 1 or len(tasks) <= 1:
        done = [(i, _run_flow(specs[i][0], specs[i][1], seed)) for i, seed in tasks]
    else:
        with multiprocessing.get_context("spawn").Pool(
            min(jobs, len(tasks)), initializer=_init, initargs=(tuple(specs),)
        ) as pool:
            done = pool.map(_work, tasks, chunksize=1)
    grouped: dict[int, list[_Result]] = {i: [] for i in range(len(specs))}
    for index, result in done:
        grouped[index].append(result)
    return [sorted(grouped[i], key=lambda r: r[0]) for i in range(len(specs))]


@dataclass(frozen=True, slots=True)
class CellSummary:
    """一格（情境 × build）的彙總（只計完成的戰鬥）。"""

    scenario: str
    build: str
    battles: int
    failed: int
    wins: int
    rounds_mean: float
    hero_dpr: float
    """英雄的平均 DPR（造成的傷害 ÷ 存活輪數，每場平均）。"""
    hero_damage: float
    """英雄每場造成的傷害。"""
    hero_survival: float
    """英雄在戰鬥結束時還活著的比例。"""
    boss_kill_rounds: float = 0.0
    """Boss 擊殺輪數的平均（沒打倒的場以輪數上限計；沒有 Boss 的情境為 0）。"""
    boss_kill_rate: float = 0.0
    """打倒 Boss 的場數比例。"""
    boss_kill_rounds_kills: float = 0.0
    """只計打倒 Boss 的場，擊殺輪數的平均。"""
    clear_rounds: float = 0.0
    """清場（敵方全滅）輪數的平均（沒清場的場以輪數上限計）。"""
    clear_rate: float = 0.0
    """清場的場數比例。"""
    clear_rounds_clears: float = 0.0
    """只計清場的場，輪數的平均。"""
    hero_turns: float = 0.0
    """每場英雄回合開始的次數（敵人還在場）。"""
    no_skill_turns: float = 0.0
    """每場其中打不出技能的次數。"""
    no_skill_mana: float = 0.0
    no_skill_cooldown: float = 0.0
    damage_sources: dict[str, float] | None = None
    """英雄每場的傷害來源拆解（見 :class:`~trpg.sim.attack_flow_diag.FlowExtras`）。"""
    crit_damage: float = 0.0
    skill_hits: dict[str, tuple[float, float, float]] | None = None
    """技能 ID → （每場使用次數，每次平均涵蓋的敵人數，每次平均受傷的敵人數）。"""


def summarize(
    samples: Sequence[CellSample], *, max_rounds: int = DEFAULT_MAX_ROUNDS
) -> list[CellSummary]:
    """依（情境、build）彙總（保持出現順序）；``max_rounds`` 是沒打倒／沒清場時的設限輪數。"""
    order: list[tuple[str, str]] = []
    for s in samples:
        if (s.scenario, s.build) not in order:
            order.append((s.scenario, s.build))
    return [
        _cell(
            sc,
            b,
            [s for s in samples if (s.scenario, s.build) == (sc, b)],
            max_rounds=max_rounds,
        )
        for sc, b in order
    ]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _cell(
    scenario: str,
    build: str,
    samples: Sequence[CellSample],
    *,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> CellSummary:
    flows = [s.flow for s in samples if s.flow is not None]
    n_flow = len(flows)
    kills = [f.boss_kill_round for f in flows if f.boss_kill_round is not None]
    clears = [f.clear_round for f in flows if f.clear_round is not None]
    sources: dict[str, float] = {}
    for f in flows:
        for key, value in f.damage_by_source.items():
            sources[key] = sources.get(key, 0.0) + value / n_flow
    uses: dict[str, list[int]] = {}
    for f in flows:
        for key, (count, covered, hit) in f.skill_uses.items():
            acc = uses.setdefault(key, [0, 0, 0])
            acc[0] += count
            acc[1] += covered
            acc[2] += hit
    done = [s.metrics for s in samples if s.metrics is not None]
    dprs: list[Fraction] = []
    damage = alive = wins = 0
    for m in done:
        hero = next(u for u in m.units if u.team is Team.ALLY and u.template_id == build)
        dprs.append(hero.dpr)
        damage += hero.damage_dealt
        alive += 0 if hero.downed else 1
        wins += m.result == "ally"
    n = len(done)
    return CellSummary(
        scenario=scenario,
        build=build,
        battles=n,
        failed=len(samples) - n,
        wins=wins,
        rounds_mean=sum(m.rounds for m in done) / n if n else 0.0,
        hero_dpr=float(sum(dprs, Fraction(0)) / n) if n else 0.0,
        hero_damage=damage / n if n else 0.0,
        hero_survival=alive / n if n else 0.0,
        boss_kill_rounds=_mean([*kills, *[max_rounds] * (n_flow - len(kills))])
        if any(f.has_boss for f in flows)
        else 0.0,
        boss_kill_rate=len(kills) / n_flow if n_flow else 0.0,
        boss_kill_rounds_kills=_mean(kills),
        clear_rounds=_mean([*clears, *[max_rounds] * (n_flow - len(clears))]) if n_flow else 0.0,
        clear_rate=len(clears) / n_flow if n_flow else 0.0,
        clear_rounds_clears=_mean(clears),
        hero_turns=_mean([f.hero_turns for f in flows]),
        no_skill_turns=_mean([f.no_skill_turns for f in flows]),
        no_skill_mana=_mean([f.no_skill_mana for f in flows]),
        no_skill_cooldown=_mean([f.no_skill_cooldown for f in flows]),
        damage_sources={k: v for k, v in sorted(sources.items())},
        crit_damage=_mean([f.crit_damage for f in flows]),
        skill_hits={k: (v[0] / n_flow, v[1] / v[0], v[2] / v[0]) for k, v in sorted(uses.items())},
    )


def format_attack_flow(
    summaries: Sequence[CellSummary], labels: dict[str, str], builds: dict[str, str]
) -> str:
    """Markdown 摘要表（情境 × build）。"""
    lines = [
        "| 情境 | build | 場數 | 勝率 | 英雄 DPR | 英雄傷害/場 | 英雄存活 | 平均輪數 |",
        "|" + "---|" * 8,
    ]
    for s in summaries:
        win = "—" if s.battles == 0 else f"{s.wins * 100 // s.battles}%"
        lines.append(
            f"| {labels.get(s.scenario, s.scenario)} | {builds.get(s.build, s.build)} "
            f"| {s.battles} | {win} | {s.hero_dpr:.1f} | {s.hero_damage:.0f} "
            f"| {s.hero_survival * 100:.0f}% | {s.rounds_mean:.1f} |"
        )
    failed = sum(s.failed for s in summaries)
    lines.append("")
    lines.append(f"未完成（例外或動作上限）：{failed} 場")
    return "\n".join(lines)


def _find(summaries: Sequence[CellSummary], scenario: str, build: str) -> CellSummary | None:
    return next((s for s in summaries if (s.scenario, s.build) == (scenario, build)), None)


def format_new_metrics(summaries: Sequence[CellSummary], builds: dict[str, str]) -> str:
    """三情境的新指標表（Phase 3-32d）：Boss 擊殺輪數比、範圍清場輪數比、長戰 DPR。

    輪數比 ＝ 普攻流 ÷ 技能流（輪數越大越慢）。判斷門檻（玩法 PM）：Boss 戰比值 ≥ 0.90、
    範圍戰比值 ≥ 1.15、長戰單體 DPR 相當。輪數沒打倒／沒清場的場以輪數上限計入。"""
    attack, skill = BUILDS
    lines = [
        f"| 指標 | {builds.get(attack, attack)} | {builds.get(skill, skill)} | 比值 | 門檻 |",
        "|---|---|---|---|---|",
    ]
    rows: tuple[tuple[str, str, Callable[[CellSummary], float], str], ...] = (
        ("boss", "Boss 擊殺輪數（含設限）", lambda s: s.boss_kill_rounds, "≥ 0.90"),
        ("boss", "Boss 擊殺輪數（只計打倒的場）", lambda s: s.boss_kill_rounds_kills, "—"),
        ("boss", "Boss 擊殺率", lambda s: s.boss_kill_rate * 100, "—"),
        ("boss", "Boss 戰勝率", lambda s: 100 * s.wins / s.battles if s.battles else 0.0, "—"),
        ("area", "範圍清場輪數（含設限）", lambda s: s.clear_rounds, "≥ 1.15"),
        ("area", "範圍清場輪數（只計清場的場）", lambda s: s.clear_rounds_clears, "—"),
        ("area", "範圍清場率", lambda s: s.clear_rate * 100, "—"),
        ("single", "長戰單體 DPR", lambda s: s.hero_dpr, "相當"),
    )
    for scenario, label, getter, gate in rows:
        a, b = _find(summaries, scenario, attack), _find(summaries, scenario, skill)
        if a is None or b is None:
            continue
        va, vb = getter(a), getter(b)
        ratio = f"{va / vb:.2f}" if vb else "—"
        lines.append(f"| {label} | {va:.1f} | {vb:.1f} | {ratio} | {gate} |")
    return "\n".join(lines)


def format_diagnosis(summaries: Sequence[CellSummary], builds: dict[str, str]) -> str:
    """診斷表（Phase 3-32d）：傷害來源拆解、技能流打不出技能的回合比例、範圍技平均命中數。"""
    lines = ["傷害來源（英雄每場，近似；精通為普攻命中的加成部分）：", ""]
    keys = ("basic", "combo", "cleave", "mastery", "indirect")
    head = "| 情境 | build | " + " | ".join(keys) + " | 技能合計 | 暴擊命中傷害(重疊) |"
    lines += [head, "|" + "---|" * (len(keys) + 4)]
    for s in summaries:
        src = s.damage_sources or {}
        skills_total = sum(v for k, v in src.items() if k.startswith("skill:"))
        cells = " | ".join(f"{src.get(k, 0.0):.1f}" for k in keys)
        lines.append(
            f"| {s.scenario} | {builds.get(s.build, s.build)} | {cells} | {skills_total:.1f} "
            f"| {s.crit_damage:.1f} |"
        )
    lines += ["", "打不出技能的回合（英雄回合開始時沒有任何主動技能可用）：", ""]
    lines += [
        "| 情境 | build | 英雄回合/場 | 打不出技能/場 | 比例 | 其中法力不足 | 其中全冷卻 |",
        "|" + "---|" * 7,
    ]
    for s in summaries:
        pct = f"{s.no_skill_turns / s.hero_turns * 100:.0f}%" if s.hero_turns else "—"
        lines.append(
            f"| {s.scenario} | {builds.get(s.build, s.build)} | {s.hero_turns:.1f} "
            f"| {s.no_skill_turns:.1f} | {pct} | {s.no_skill_mana:.1f} "
            f"| {s.no_skill_cooldown:.1f} |"
        )
    lines += [
        "",
        "技能使用（每場次數／每次平均涵蓋與受傷的敵人數；涵蓋 ＝ 有命中判定的敵人）：",
        "",
    ]
    lines += [
        "| 情境 | build | 技能 | 次數/場 | 平均涵蓋敵人數 | 平均受傷敵人數 |",
        "|" + "---|" * 6,
    ]
    for s in summaries:
        for sid, (count, covered, hit) in (s.skill_hits or {}).items():
            name = builds.get(s.build, s.build)
            lines.append(
                f"| {s.scenario} | {name} | {sid} | {count:.1f} | {covered:.2f} | {hit:.2f} |"
            )
    return "\n".join(lines)
