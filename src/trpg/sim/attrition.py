"""一輪消耗量測（平衡階段 BAL-6）：守點戰輪數／格子與第 3 場人數的模擬覆寫。

只在記憶體內的 library 副本上覆寫，不寫檔、不改 ``content/``；戰間回血與敵人倍率不動。
每個設定跑 N 輪（均衡閃現 AI），回報一輪勝率、平均贏幾場、打到 Boss 的輪數、守點戰與第 3 場勝率。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.content.maps import AltObjective, AltObjectives, MapDef, check_map
from trpg.engine.rules.geometry import manhattan
from trpg.roguelite.auto import auto_play
from trpg.roguelite.start import default_start, new_keyword_run
from trpg.shared.types import Team
from trpg.sim.parallel import run_tasks

__all__ = [
    "TILE_MODES",
    "AttritionConfig",
    "AttritionResult",
    "RunOutcome",
    "apply_config",
    "format_rows",
    "run_config",
]

TILE_MODES = ("current", "wide", "back")
"""守點格：``current`` ＝ 現行；``wide`` ＝ 現行格加上四鄰格（範圍大一格，敵人更容易占到）；
``back`` ＝ 改成最貼近我方起始區、仍合法（不在起始區、可站立）的格子（敵人最難搶到）。"""

THIRD_BATTLE = 3

Tiles = tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class AttritionConfig:
    """一組覆寫（預設 ＝ content 現況）。"""

    defend_rounds_delta: int = 0
    tile_mode: str = "current"
    third_battle_enemies: int = 0
    """第 3 場每個選項保留前幾名敵人；0 ＝ 不改。"""

    @property
    def label(self) -> str:
        parts = []
        if self.defend_rounds_delta:
            parts.append(f"守點輪數{self.defend_rounds_delta:+d}")
        if self.tile_mode != "current":
            parts.append(f"格子={self.tile_mode}")
        if self.third_battle_enemies:
            parts.append(f"第3場{self.third_battle_enemies}名")
        return " ".join(parts) if parts else "現況"


@dataclass(frozen=True, slots=True)
class RunOutcome:
    victory: bool
    battles_won: int
    boss_reached: bool
    defend_played: int
    defend_won: int
    third_played: bool
    third_won: bool


@dataclass(frozen=True, slots=True)
class AttritionResult:
    config: AttritionConfig
    runs: int
    run_win: float
    wins_mean: float
    boss_runs: int
    defend_win: float
    defend_n: int
    third_win: float
    third_n: int


def _pct(num: float, den: float) -> float:
    return 0.0 if den == 0 else num * 100 / den


def _wide(tiles: Tiles, map_def: MapDef) -> Tiles:
    blocked = {o.at for o in map_def.objects}
    blocked |= {c for cells in map_def.start_zones.values() for c in cells}
    cells = set(tiles)
    for x, y in tiles:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < map_def.width and 0 <= ny < map_def.height and (nx, ny) not in blocked:
                cells.add((nx, ny))
    return tuple(sorted(cells))


def _back_tile(library: ContentLibrary, map_def: MapDef, tiles: Tiles) -> Tiles:
    starts = map_def.start_zones[Team.ALLY]
    zones = {c for cells in map_def.start_zones.values() for c in cells}
    occupied = zones | {o.at for o in map_def.objects}
    candidates = sorted(
        (
            (x, y)
            for y in range(map_def.height)
            for x in range(map_def.width)
            if (x, y) not in occupied
        ),
        key=lambda c: (
            min(manhattan(c, s) for s in starts),
            min(manhattan(c, t) for t in tiles),
            c,
        ),
    )
    ruleset = library.ruleset
    for cell in candidates:
        alt = AltObjective.model_construct(rounds=1, tiles=(cell,))
        trial = map_def.model_copy(
            update={"alt_objectives": AltObjectives.model_construct(escape=None, defend=alt)}
        )
        if not check_map(trial, ruleset.terrain.by_id(), ruleset.core, ruleset.objects.by_id()):
            return (cell,)
    return tiles


def _override_map(library: ContentLibrary, map_def: MapDef, config: AttritionConfig) -> MapDef:
    alt = map_def.alt_objectives
    if alt is None or alt.defend is None:
        return map_def
    defend = alt.defend
    tiles = defend.tiles
    if config.tile_mode == "wide":
        tiles = _wide(tiles, map_def)
    elif config.tile_mode == "back":
        tiles = _back_tile(library, map_def, tiles)
    rounds = max(1, defend.rounds + config.defend_rounds_delta)
    new_alt = AltObjectives.model_construct(
        escape=alt.escape, defend=AltObjective.model_construct(rounds=rounds, tiles=tiles)
    )
    return map_def.model_copy(update={"alt_objectives": new_alt})


def apply_config(library: ContentLibrary, config: AttritionConfig) -> ContentLibrary:
    """套用覆寫的 library 副本（``config`` 為預設時回傳原物件）。"""
    if config == AttritionConfig():
        return library
    maps = {k: _override_map(library, v, config) for k, v in sorted(library.maps.items())}
    rules = library.roguelite
    keep = config.third_battle_enemies
    if keep:
        steps = list(rules.encounters)
        step = steps[THIRD_BATTLE - 1]
        options = tuple(opt[:keep] for opt in step.options)
        steps[THIRD_BATTLE - 1] = step.model_copy(update={"options": options})
        rules = rules.model_copy(update={"encounters": tuple(steps)})
    return dataclasses.replace(library, maps=maps, roguelite=rules)


def _one_run(library: ContentLibrary, seed: int) -> RunOutcome:
    weapon, keywords = default_start(library, seed)
    run = new_keyword_run(library, weapon, keywords, seed)
    final, _ = auto_play(library, run, flash_policy="balanced")
    history = final.history
    defend = [r for r in history if not r.boss and final.plan_of(r.index).objective == "defend"]
    third = [r for r in history if r.index == THIRD_BATTLE and not r.boss]
    return RunOutcome(
        victory=bool(getattr(final.node, "victory", False)),
        battles_won=sum(1 for r in history if r.won),
        boss_reached=any(r.boss for r in history),
        defend_played=len(defend),
        defend_won=sum(1 for r in defend if r.won),
        third_played=bool(third),
        third_won=any(r.won for r in third),
    )


def run_config(
    library: ContentLibrary, config: AttritionConfig, seeds: Sequence[int], *, jobs: int = 1
) -> AttritionResult:
    """一個設定跑 ``seeds`` 輪。"""
    lib = apply_config(library, config)
    runs = run_tasks(_one_run, lib, list(seeds), jobs=jobs)
    n = len(runs)
    defend_n = sum(r.defend_played for r in runs)
    third_n = sum(r.third_played for r in runs)
    return AttritionResult(
        config=config,
        runs=n,
        run_win=_pct(sum(r.victory for r in runs), n),
        wins_mean=0.0 if n == 0 else sum(r.battles_won for r in runs) / n,
        boss_runs=sum(r.boss_reached for r in runs),
        defend_win=_pct(sum(r.defend_won for r in runs), defend_n),
        defend_n=defend_n,
        third_win=_pct(sum(r.third_won for r in runs), third_n),
        third_n=third_n,
    )


def format_rows(results: Sequence[AttritionResult]) -> str:
    """Markdown 表（一列一個設定）。"""
    head = (
        "| 設定 | 一輪勝率 | 平均贏幾場 | 打到 Boss 的輪數 | 守點戰勝率 | 第 3 場勝率 |\n"
        "|---|---|---|---|---|---|\n"
    )
    rows = [
        f"| {r.config.label} | {r.run_win:.1f}% ({round(r.run_win * r.runs / 100)}/{r.runs}) "
        f"| {r.wins_mean:.2f} | {r.boss_runs} | {r.defend_win:.1f}% ({r.defend_n}) "
        f"| {r.third_win:.1f}% ({r.third_n}) |"
        for r in results
    ]
    return head + "\n".join(rows) + "\n"
