"""資源不足回合比例（Phase 3H-2，雙資源；``scripts/sim_resources.py``）。

武器技花耐力、法術技花法力之後，量各流派的英雄有多少回合「想用技能但資源不夠」。情境沿用普攻流
對照模擬（:data:`trpg.sim.attack_flow_report.SCENARIOS`：長戰單體、範圍戰、Boss 戰），預設的
build 是技能流弓手、普攻流弓手、召喚師，另加近戰技能流（推擊流）對照。

每回合開始時（英雄的 ``turn_started`` 之後的狀態）檢查英雄裝備的每個主動技能：

- **法力不足回合**：至少一招因「法力不足」不能用；
- **耐力不足回合**：至少一招因「耐力不足」不能用；
- **任一不足回合**：以上任一。

另外記戰鬥結束時剩餘的法力、耐力比例與勝率。**只量不調**：不改任何規則或數值。結果只取決於
（情境、build、種子），與 ``jobs`` 無關。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from trpg.content.library import ContentLibrary
from trpg.engine.actions import Step
from trpg.engine.events import DamageDealt, TurnStarted
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.engine.skills.targeting import resource_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.attack_flow_report import SCENARIOS, Scenario
from trpg.sim.batch import DEFAULT_MAX_ROUNDS, UtilityPolicyFactory
from trpg.sim.matrix import library_with_builds
from trpg.sim.parallel import run_tasks

__all__ = [
    "BUILDS",
    "ResourceCell",
    "ResourceSample",
    "format_resources",
    "run_resources",
    "summarize_resources",
]

BUILDS: tuple[str, ...] = (
    "build_skill_archer",
    "build_attack_archer",
    "build_summoner",
    "build_push",
)
"""技能流（弓）、普攻流（弓）、召喚流，另加近戰技能流對照。"""

_MANA = "法力不足"
_STAMINA = "耐力不足"


@dataclass(slots=True)
class ResourceSample:
    """一場戰鬥：英雄的回合數、各種不足的回合數與結束時的資源（失敗時 ``ok`` 為 ``False``）。"""

    scenario: str
    build: str
    seed: int
    ok: bool = True
    won: bool = False
    turns: int = 0
    mana_short: int = 0
    stamina_short: int = 0
    any_short: int = 0
    damage: int = 0
    """英雄這場造成的傷害總量（3H-6 加，量武器技縮放改動前後）。"""
    mana_left_permille: int | None = None
    stamina_left_permille: int | None = None


def scenario_setup(
    library: ContentLibrary, scenario: Scenario, build_id: str, rounds: int
) -> BattleSetup:
    """情境的戰鬥設定（同普攻流對照模擬：``library`` 須已加入 build 英雄）。"""
    enemies = scenario.enemies
    if enemies is None:
        encounter = library.map(scenario.map_id).encounter
        assert encounter is not None
        enemies = tuple(encounter.enemies)
    companions = tuple(library.builds.companions) if scenario.companions else ()
    return build_setup(
        library, scenario.map_id, (build_id, *companions), enemies, max_rounds=rounds
    )


def _hero(state: BattleState, build: str) -> UnitState | None:
    return next(
        (u for u in state.units_sorted() if u.team is Team.ALLY and u.template_id == build), None
    )


def _shortages(state: BattleState, hero: UnitState) -> tuple[bool, bool]:
    """英雄裝備的主動技能中，有沒有因法力、耐力不足而不能用的。"""
    mana = stamina = False
    for skill_id in hero.skills:
        skill = state.ruleset.skill_def(skill_id)
        if skill.kind != "active":
            continue
        problem = resource_problem(state, hero, skill) or ""
        mana = mana or problem.startswith(_MANA)
        stamina = stamina or problem.startswith(_STAMINA)
    return mana, stamina


@dataclass(slots=True)
class _Tracker:
    build: str
    sample: ResourceSample
    seen: set[tuple[int, str]] = field(default_factory=set)

    def __call__(self, step: Step | None, result: ResolveResult) -> None:
        hero = _hero(result.state, self.build)
        if hero is None:
            return
        for event in result.events:
            if isinstance(event, DamageDealt) and event.source_id == hero.id:
                self.sample.damage += event.amount
            if not isinstance(event, TurnStarted) or event.unit_id != hero.id:
                continue
            key = (result.state.round, hero.id)
            if key in self.seen:
                continue
            self.seen.add(key)
            mana, stamina = _shortages(result.state, hero)
            self.sample.turns += 1
            self.sample.mana_short += mana
            self.sample.stamina_short += stamina
            self.sample.any_short += mana or stamina


def _permille(value: int, total: int) -> int | None:
    return None if total <= 0 else value * 1000 // total


def _run_one(
    setup: BattleSetup, build: str, scenario: str, seed: int, factory: UtilityPolicyFactory
) -> ResourceSample:
    sample = ResourceSample(scenario, build, seed)
    tracker = _Tracker(build, sample)
    try:
        run = run_battle(setup, seed, factory(), on_step=tracker)
    except TrpgError:
        sample.ok = False
        return sample
    hero = _hero(run.state, build)
    sample.won = run.state.winner is Team.ALLY
    if hero is not None:
        sample.mana_left_permille = _permille(hero.mana, hero.max_mana)
        sample.stamina_left_permille = _permille(hero.stamina, hero.max_stamina)
    return sample


type _Context = tuple[tuple[tuple[str, str, BattleSetup], ...], UtilityPolicyFactory]


def _work(context: _Context, task: tuple[int, int]) -> ResourceSample:
    cells, factory = context
    index, seed = task
    scenario, build, setup = cells[index]
    return _run_one(setup, build, scenario, seed, factory)


def run_resources(
    library: ContentLibrary,
    *,
    scenarios: Sequence[Scenario] = SCENARIOS,
    builds: Sequence[str] = BUILDS,
    seeds: int = 20,
    seed_start: int = 0,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    jobs: int = 1,
) -> list[ResourceSample]:
    """每個情境 × build × ``seeds`` 個種子各打一場；結果依（情境、build、種子）排序。"""
    library = library_with_builds(library)
    cells = tuple(
        (sc.id, b, scenario_setup(library, sc, b, max_rounds)) for sc in scenarios for b in builds
    )
    tasks = [(i, s) for i in range(len(cells)) for s in range(seed_start, seed_start + seeds)]
    factory = UtilityPolicyFactory(library.ai_profiles)
    return run_tasks(_work, (cells, factory), tasks, jobs=jobs)


@dataclass(frozen=True, slots=True)
class ResourceCell:
    """一格（情境 × build）的彙總（只計完成的戰鬥）。比例是 0～1。"""

    scenario: str
    build: str
    battles: int
    failed: int
    win_rate: float
    turns: int
    mana_short: float
    stamina_short: float
    any_short: float
    damage: float
    mana_left: float | None
    stamina_left: float | None


def _mean(values: Sequence[int | None]) -> float | None:
    found = [v for v in values if v is not None]
    return None if not found else sum(found) / len(found) / 1000


def summarize_resources(samples: Sequence[ResourceSample]) -> list[ResourceCell]:
    keys = list(dict.fromkeys((s.scenario, s.build) for s in samples))
    cells: list[ResourceCell] = []
    for scenario, build in keys:
        group = [s for s in samples if (s.scenario, s.build) == (scenario, build)]
        done = [s for s in group if s.ok]
        turns = sum(s.turns for s in done)

        def ratio(value: int, total: int = turns) -> float:
            return 0.0 if total == 0 else value / total

        cells.append(
            ResourceCell(
                scenario=scenario,
                build=build,
                battles=len(done),
                failed=len(group) - len(done),
                win_rate=ratio(sum(s.won for s in done), len(done)),
                turns=turns,
                mana_short=ratio(sum(s.mana_short for s in done)),
                stamina_short=ratio(sum(s.stamina_short for s in done)),
                any_short=ratio(sum(s.any_short for s in done)),
                damage=ratio(sum(s.damage for s in done), len(done)),
                mana_left=_mean([s.mana_left_permille for s in done]),
                stamina_left=_mean([s.stamina_left_permille for s in done]),
            )
        )
    return cells


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def format_resources(
    cells: Sequence[ResourceCell], scenarios: dict[str, str], builds: dict[str, str]
) -> str:
    """Markdown 表格：情境、build、場數、勝率、英雄回合數、各種不足回合比例、結束時剩餘資源。"""
    columns = (
        "情境", "build", "場數", "勝率", "英雄回合", "法力不足", "耐力不足", "任一不足",
        "剩餘法力", "剩餘耐力", "平均傷害",
    )  # fmt: skip
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for c in cells:
        lines.append(
            f"| {scenarios.get(c.scenario, c.scenario)} | {builds.get(c.build, c.build)} "
            f"| {c.battles}{f'（失敗 {c.failed}）' if c.failed else ''} | {_pct(c.win_rate)} "
            f"| {c.turns} | {_pct(c.mana_short)} | {_pct(c.stamina_short)} | {_pct(c.any_short)} "
            f"| {_pct(c.mana_left)} | {_pct(c.stamina_left)} | {c.damage:.0f} |"
        )
    return "\n".join(lines)
