"""一輪消耗量測（平衡階段 BAL-6）：守點戰輪數／格子與第 3 場人數的模擬覆寫。

只在記憶體內的 library 副本上覆寫，不寫檔、不改 ``content/``；戰間回血與敵人倍率不動。
每個設定跑 N 輪（均衡閃現 AI），回報一輪勝率、平均贏幾場、打到 Boss 的輪數、守點戰與第 3 場勝率。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.content.maps import (
    AltObjective,
    AltObjectives,
    MapDef,
    MapEvent,
    SpawnPlacement,
    SpawnUnitsEvent,
    check_map,
)
from trpg.engine.rules.geometry import manhattan
from trpg.roguelite.auto import auto_play
from trpg.roguelite.start import default_start, new_keyword_run
from trpg.shared.types import Team
from trpg.sim.baseline import _run_packs  # 與基準線同一套 Boss 戰跑法
from trpg.sim.parallel import run_tasks
from trpg.sim.summon_report import BOSS_MAP

__all__ = [
    "TILE_MODES",
    "AttritionConfig",
    "AttritionResult",
    "BossResult",
    "RunOutcome",
    "apply_config",
    "format_boss_rows",
    "format_rows",
    "run_boss_config",
    "run_config",
]

TILE_MODES = ("current", "wide", "back")
"""守點格：``current`` ＝ 現行；``wide`` ＝ 現行格加上四鄰格（範圍大一格，敵人更容易占到）；
``back`` ＝ 改成最貼近我方起始區、仍合法（不在起始區、可站立）的格子（敵人最難搶到）。"""

THIRD_BATTLE = 3
NO_REINFORCE = -1
"""``boss_reinforce_round`` 的值：拿掉 Boss 戰的援軍事件。"""

Tiles = tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class AttritionConfig:
    """一組覆寫（預設 ＝ content 現況）。"""

    defend_rounds_delta: int = 0
    tile_mode: str = "current"
    third_battle_enemies: int = 0
    """第 3 場每個選項保留前幾名敵人；0 ＝ 不改。"""
    boss_guards_delta: int = 0
    """Boss 戰護衛人數差（負數；從陣容尾端去掉，即先拿掉盾兵護衛，再拿掉弓手護衛）；0 ＝ 不改。"""
    boss_reinforce_round: int = 0
    """Boss 戰援軍出現的輪數；0 ＝ 不改，``NO_REINFORCE``（-1）＝ 無援軍。"""
    boss_reinforce_delta: int = 0
    """Boss 戰援軍人數差（負數，從事件單位列表尾端去掉）；0 ＝ 不改。"""

    @property
    def label(self) -> str:
        parts = []
        if self.defend_rounds_delta:
            parts.append(f"守點輪數{self.defend_rounds_delta:+d}")
        if self.tile_mode != "current":
            parts.append(f"格子={self.tile_mode}")
        if self.third_battle_enemies:
            parts.append(f"第3場{self.third_battle_enemies}名")
        if self.boss_guards_delta:
            parts.append(f"護衛{self.boss_guards_delta:+d}")
        if self.boss_reinforce_round == NO_REINFORCE:
            parts.append("無援軍")
        elif self.boss_reinforce_round:
            parts.append(f"援軍第{self.boss_reinforce_round}輪")
        if self.boss_reinforce_delta:
            parts.append(f"援軍人數{self.boss_reinforce_delta:+d}")
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


def _override_boss_events(map_def: MapDef, config: AttritionConfig) -> MapDef:
    """援軍事件（``spawn_units``）：改輪數、人數或整個拿掉；其他事件不動。"""
    events: list[MapEvent] = []
    for event in map_def.events:
        if not isinstance(event, SpawnUnitsEvent):
            events.append(event)
            continue
        if config.boss_reinforce_round == NO_REINFORCE:
            continue
        units: tuple[SpawnPlacement, ...] = event.units
        if config.boss_reinforce_delta:
            units = units[: max(1, len(units) + config.boss_reinforce_delta)]
        rnd = config.boss_reinforce_round or event.round
        events.append(event.model_copy(update={"round": rnd, "units": units}))
    return map_def.model_copy(update={"events": tuple(events)})


def _is_boss_config(config: AttritionConfig) -> bool:
    return bool(
        config.boss_guards_delta or config.boss_reinforce_round or config.boss_reinforce_delta
    )


def apply_config(library: ContentLibrary, config: AttritionConfig) -> ContentLibrary:
    """套用覆寫的 library 副本（``config`` 為預設時回傳原物件）。"""
    if config == AttritionConfig():
        return library
    maps = {k: _override_map(library, v, config) for k, v in sorted(library.maps.items())}
    rules = library.roguelite
    if _is_boss_config(config):
        boss_map = rules.boss.map
        maps[boss_map] = _override_boss_events(maps[boss_map], config)
        if config.boss_guards_delta:
            enemies = rules.boss.enemies
            keep = max(1, len(enemies) + config.boss_guards_delta)  # 第一名是頭目，永遠保留
            rules = rules.model_copy(
                update={"boss": rules.boss.model_copy(update={"enemies": enemies[:keep]})}
            )
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


# ---------------------------------------------------------------------------
# Boss 戰護衛與援軍（BAL-7）
# ---------------------------------------------------------------------------

SUMMON_PACKS: tuple[str, ...] = ("dev_spirit", "dev_summoner", "dev_summoner_bone")
PLAIN_PACKS: tuple[str, ...] = ("dev_bulwark", "dev_blaze", "dev_hawkeye")


@dataclass(frozen=True, slots=True)
class BossResult:
    """一個設定的 Boss 戰（有召喚包與無召喚對照包分開）。"""

    config: AttritionConfig
    summon_win: float
    summon_rounds: float
    summon_n: int
    plain_win: float
    plain_rounds: float
    plain_n: int


def run_boss_config(
    library: ContentLibrary,
    config: AttritionConfig,
    seeds: Sequence[int],
    *,
    jobs: int = 1,
    summon_packs: Sequence[str] = SUMMON_PACKS,
    plain_packs: Sequence[str] = PLAIN_PACKS,
) -> BossResult:
    """Boss 戰（效用 AI、專屬地圖）：每包每個種子一場。"""
    lib = apply_config(library, config)
    plan = [(p, BOSS_MAP, s) for p in (*summon_packs, *plain_packs) for s in seeds]
    results = _run_packs(lib, plan, jobs)

    def agg(packs: Sequence[str]) -> tuple[float, float, int]:
        battles = wins = 0
        rounds: list[int] = []
        for r in results:
            m = r.sample.metrics
            if r.sample.pack not in packs or m is None:
                continue
            battles += 1
            wins += 1 if m.result == "ally" else 0
            rounds.append(m.rounds)
        return _pct(wins, battles), (sum(rounds) / len(rounds) if rounds else 0.0), battles

    sw, sr, sn = agg(summon_packs)
    pw, pr, pn = agg(plain_packs)
    return BossResult(config, sw, sr, sn, pw, pr, pn)


def format_boss_rows(boss: Sequence[BossResult], runs: Sequence[AttritionResult]) -> str:
    """Markdown 表（一列一個設定；``boss`` 與 ``runs`` 同序）。"""
    head = (
        "| 設定 | Boss 有召喚勝率／輪數 | Boss 無召喚勝率／輪數 | 一輪勝率 "
        "| 平均贏幾場 | 打到 Boss 的輪數 |\n"
        "|---|---|---|---|---|---|\n"
    )
    rows = [
        f"| {b.config.label} | {b.summon_win:.1f}%（{b.summon_n}）／{b.summon_rounds:.1f} "
        f"| {b.plain_win:.1f}%（{b.plain_n}）／{b.plain_rounds:.1f} "
        f"| {r.run_win:.1f}%（{round(r.run_win * r.runs / 100)}/{r.runs}） "
        f"| {r.wins_mean:.2f} | {r.boss_runs} |"
        for b, r in zip(boss, runs, strict=True)
    ]
    return head + "\n".join(rows) + "\n"
