"""難度與法力旋鈕掃描（BAL-4）：每個旋鈕組合量一組平衡指標（只量不調）。

每個組合（:class:`~trpg.sim.difficulty.Difficulty`）量：

- 示範地圖：我方勝率、平均輪數、勝率落在 35–65% 的地圖數（重用 ``run_batches``）；
- Boss 戰：有召喚包／無召喚對照包分開的勝率與輪數（重用 BAL-3 ``baseline`` 的起始包模擬）；
- Boss 戰法力短缺回合：``build_fire``、``build_summoner``（BAL-3 的 Boss 戰情境，重用資源報表）；
- 一輪：均衡閃現 AI 的勝率、平均贏幾場、打到 Boss 的輪的 Boss 勝率（重用 ``run_flash_sim``）。

亂數沿用各模擬自己的種子規則，結果與 ``jobs`` 無關。報表不含時間，相同輸入必得逐字相同輸出。
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields

from trpg.content.library import ContentLibrary
from trpg.sim.attack_flow_report import SCENARIOS
from trpg.sim.baseline import _run_packs, _summaries
from trpg.sim.batch import map_spec, run_batches
from trpg.sim.difficulty import Difficulty, with_difficulty
from trpg.sim.flash_report import run_flash_sim
from trpg.sim.resource_report import run_resources, summarize_resources
from trpg.sim.summon_report import BOSS_MAP

__all__ = [
    "KNOB_NAMES",
    "SINGLE_GRID",
    "Measure",
    "SweepSizes",
    "format_sweep",
    "measure",
    "parse_combo",
    "sweep_csv",
]

SUMMON_PACKS = ("dev_spirit", "dev_summoner", "dev_summoner_bone")
"""有召喚的起始包（BAL-3 的 Boss 戰「召喚包」）。"""
PLAIN_PACKS = ("dev_bulwark", "dev_blaze", "dev_hawkeye")
"""無召喚對照包（B7）。"""
MANA_BUILDS = ("build_fire", "build_summoner")
"""法力短缺最嚴重的兩個 build（BAL-3）。"""

KNOB_NAMES = tuple(f.name for f in fields(Difficulty))
SINGLE_GRID: dict[str, tuple[int, ...]] = {
    "enemy_hp": (1000, 1200, 1400),
    "enemy_damage": (800, 1000, 1200),
    "boss_hp": (800, 900, 1000),
    "boss_damage": (800, 900, 1000),
    "mana_cost": (800, 900, 1000),
    "mana_cap": (1000, 1200, 1400),
}
"""單一旋鈕掃描的值（‰）；1000 ＝ 現行，所有旋鈕共用同一組 baseline。"""

WIN_LO, WIN_HI = 35.0, 65.0


@dataclass(frozen=True, slots=True)
class SweepSizes:
    """各量測的規模。"""

    map_seeds: int = 8
    boss_seeds: int = 20
    resource_seeds: int = 20
    run_seeds: int = 16
    seed_start: int = 0
    maps: tuple[str, ...] = ()
    """空 ＝ 呼叫端傳入的預設地圖。"""


@dataclass(frozen=True, slots=True)
class Measure:
    """一個旋鈕組合的量測結果（比例為百分比）。"""

    difficulty: Difficulty
    map_win: float
    map_rounds: float
    maps_ok: int
    maps_total: int
    boss_summon_win: float
    boss_summon_rounds: float
    boss_plain_win: float
    boss_plain_rounds: float
    short_fire: float
    short_summoner: float
    run_win: float
    run_wins_mean: float
    run_boss_win: float
    run_n: int
    run_boss_n: int

    @property
    def short_max(self) -> float:
        return max(self.short_fire, self.short_summoner)


def _pct(num: float, den: float) -> float:
    return 0.0 if den == 0 else num * 100 / den


def _maps(
    library: ContentLibrary, maps: Sequence[str], sizes: SweepSizes, jobs: int
) -> tuple[float, float, int]:
    seeds = tuple(range(sizes.seed_start, sizes.seed_start + sizes.map_seeds))
    reports = run_batches([map_spec(library, m, seeds) for m in maps], jobs=jobs)
    done = sum(r.completed for r in reports)
    wins = sum(r.ally_win_rate * r.completed for r in reports)
    rounds = sum(r.rounds_mean * r.completed for r in reports)
    ok = sum(1 for r in reports if WIN_LO <= r.ally_win_rate * 100 <= WIN_HI)
    return _pct(wins, done), 0.0 if done == 0 else rounds / done, ok


def _boss(library: ContentLibrary, sizes: SweepSizes, jobs: int) -> tuple[float, ...]:
    seeds = range(sizes.seed_start, sizes.seed_start + sizes.boss_seeds)
    plan = [(p, BOSS_MAP, s) for p in (*SUMMON_PACKS, *PLAIN_PACKS) for s in seeds]
    summaries = _summaries(_run_packs(library, plan, jobs), (BOSS_MAP,))
    out: list[float] = []
    for packs in (SUMMON_PACKS, PLAIN_PACKS):
        group = [summaries[p] for p in packs if p in summaries and summaries[p].battles]
        battles = sum(s.battles for s in group)
        out.append(_pct(sum(s.wins for s in group), battles))
        out.append(0.0 if battles == 0 else sum(s.rounds_mean * s.battles for s in group) / battles)
    return tuple(out)


def _shortage(library: ContentLibrary, sizes: SweepSizes, jobs: int) -> tuple[float, float]:
    scenario = tuple(s for s in SCENARIOS if s.id == "boss")
    cells = summarize_resources(
        run_resources(
            library,
            scenarios=scenario,
            builds=MANA_BUILDS,
            seeds=sizes.resource_seeds,
            seed_start=sizes.seed_start,
            jobs=jobs,
        )
    )
    by_build = {c.build: c.mana_short * 100 for c in cells}
    return by_build.get(MANA_BUILDS[0], 0.0), by_build.get(MANA_BUILDS[1], 0.0)


def measure(
    library: ContentLibrary,
    difficulty: Difficulty,
    default_maps: Sequence[str],
    sizes: SweepSizes,
    *,
    jobs: int = 1,
) -> Measure:
    """量一個旋鈕組合。"""
    lib = with_difficulty(library, difficulty)
    maps = list(sizes.maps) or list(default_maps)
    map_win, map_rounds, maps_ok = _maps(lib, maps, sizes, jobs)
    sum_win, sum_rounds, plain_win, plain_rounds = _boss(lib, sizes, jobs)
    fire, summoner = _shortage(lib, sizes, jobs)
    seeds = range(sizes.seed_start, sizes.seed_start + sizes.run_seeds)
    runs = run_flash_sim(lib, ["balanced"], seeds, jobs=jobs)
    n = len(runs)
    reached = sum(r.boss_reached for r in runs)
    return Measure(
        difficulty=difficulty,
        map_win=map_win,
        map_rounds=map_rounds,
        maps_ok=maps_ok,
        maps_total=len(maps),
        boss_summon_win=sum_win,
        boss_summon_rounds=sum_rounds,
        boss_plain_win=plain_win,
        boss_plain_rounds=plain_rounds,
        short_fire=fire,
        short_summoner=summoner,
        run_win=_pct(sum(r.victory for r in runs), n),
        run_wins_mean=0.0 if n == 0 else sum(r.battles_won for r in runs) / n,
        run_boss_win=_pct(sum(r.boss_won for r in runs), reached),
        run_n=n,
        run_boss_n=reached,
    )


def parse_combo(spec: str) -> Difficulty:
    """``"enemy_hp=1200,boss_hp=900"`` → :class:`Difficulty`（沒寫的旋鈕 ＝ 1000）。"""
    values: dict[str, int] = {}
    for part in (p.strip() for p in spec.split(",")):
        if not part:
            continue
        key, sep, raw = part.partition("=")
        if not sep or key.strip() not in KNOB_NAMES:
            raise ValueError(f"旋鈕只能是 {', '.join(KNOB_NAMES)}（收到 {part!r}）")
        values[key.strip()] = int(raw)
    return Difficulty(**values)


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------

_HEADER = (
    "組合",
    "地圖勝率",
    "地圖輪數",
    "地圖達標數",
    "Boss勝率(召喚)",
    "Boss輪數(召喚)",
    "Boss勝率(無召喚)",
    "Boss輪數(無召喚)",
    "短缺 fire",
    "短缺 summoner",
    "一輪勝率",
    "平均贏幾場",
    "一輪 Boss 勝率",
)


def _cells(m: Measure) -> list[str]:
    return [
        m.difficulty.label,
        f"{m.map_win:.1f}%",
        f"{m.map_rounds:.1f}",
        f"{m.maps_ok}/{m.maps_total}",
        f"{m.boss_summon_win:.1f}%",
        f"{m.boss_summon_rounds:.1f}",
        f"{m.boss_plain_win:.1f}%",
        f"{m.boss_plain_rounds:.1f}",
        f"{m.short_fire:.1f}%",
        f"{m.short_summoner:.1f}%",
        f"{m.run_win:.1f}% ({m.run_n})",
        f"{m.run_wins_mean:.2f}",
        f"{m.run_boss_win:.1f}% ({m.run_boss_n})",
    ]


def format_sweep(title: str, measures: Sequence[Measure], notes: Sequence[str] = ()) -> str:
    """Markdown 表（一列一個組合）。"""
    lines = [f"## {title}", "", *notes, *([""] if notes else []), "| " + " | ".join(_HEADER) + " |"]
    lines.append("|" + "---|" * len(_HEADER))
    lines += ["| " + " | ".join(_cells(m)) + " |" for m in measures]
    return "\n".join(lines) + "\n"


def sweep_csv(measures: Sequence[Measure]) -> str:
    """CSV：旋鈕六欄 ＋ 全部指標。"""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    metric_names = [f.name for f in fields(Measure) if f.name != "difficulty"]
    writer.writerow([*KNOB_NAMES, *metric_names])
    for m in measures:
        knobs = [getattr(m.difficulty, k) for k in KNOB_NAMES]
        values = [getattr(m, n) for n in metric_names]
        writer.writerow([*knobs, *(f"{v:.3f}" if isinstance(v, float) else v for v in values)])
    return buf.getvalue()


def run_sweep(
    library: ContentLibrary,
    difficulties: Sequence[Difficulty],
    default_maps: Sequence[str],
    sizes: SweepSizes,
    *,
    jobs: int = 1,
    progress: Callable[[str], None] | None = None,
) -> list[Measure]:
    """依序量每個組合（順序同輸入）。"""
    out: list[Measure] = []
    for d in difficulties:
        if progress is not None:
            progress(d.label)
        out.append(measure(library, d, default_maps, sizes, jobs=jobs))
    return out
