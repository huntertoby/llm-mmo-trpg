"""普攻流對照模擬（Phase 3-32a，``docs/design/08-裝備.md`` 8.25；``scripts/sim_attack_flow.py``）。

三種情境各跑「普攻流弓手」與「技能流弓手」（``content/sim/builds.yaml``）：

- ``single``（長戰單體）：英雄單獨對 1 個高 HP 的單體敵人；
- ``area``（範圍戰）：英雄＋標準隊友對 4 個小兵（起始區最多 4 格）；
- ``boss``（Boss 戰）：英雄＋標準隊友對盜賊巢穴的預設陣容（Boss 加護衛）。

每格輸出勝率、英雄 DPR、平均輪數。**只量不調**：不改任何規則或數值；建議由 PM 決定。結果只取決於
（情境、build、種子），與 ``jobs`` 無關。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.engine.setup import BattleSetup, build_setup
from trpg.shared.types import Team
from trpg.sim.batch import (
    DEFAULT_MAX_ROUNDS,
    BatchSpec,
    UtilityPolicyFactory,
    run_outcomes,
)
from trpg.sim.matrix import library_with_builds
from trpg.sim.metrics import BattleMetrics

__all__ = [
    "BUILDS",
    "SCENARIOS",
    "CellSample",
    "CellSummary",
    "Scenario",
    "format_attack_flow",
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
        BatchSpec(
            name=f"{sc.id}/{b}",
            setup=_setup(library, sc, b, max_rounds),
            seeds=tuple(range(seed_start, seed_start + seeds)),
            policy_factory=UtilityPolicyFactory(library.ai_profiles),
        )
        for sc, b in keys
    ]
    outcomes = run_outcomes(specs, jobs=jobs)
    return [
        CellSample(sc.id, b, o.seed, o.metrics)
        for (sc, b), batch in zip(keys, outcomes, strict=True)
        for o in batch
    ]


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


def summarize(samples: Sequence[CellSample]) -> list[CellSummary]:
    """依（情境、build）彙總（保持出現順序）。"""
    order: list[tuple[str, str]] = []
    for s in samples:
        if (s.scenario, s.build) not in order:
            order.append((s.scenario, s.build))
    return [
        _cell(sc, b, [s for s in samples if (s.scenario, s.build) == (sc, b)]) for sc, b in order
    ]


def _cell(scenario: str, build: str, samples: Sequence[CellSample]) -> CellSummary:
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
