"""全面基線報表（BAL-3）：重用既有模擬，一次輸出各項平衡指標、目標值與偏離（只量不調）。

七個區塊：地圖（勝率、輪數）、Boss 戰、build 矩陣、資源短缺、武器類型、召喚物、一輪（roguelite）。
每一列是一個 :class:`Row`（數值、目標、偏離）；:func:`format_baseline` 輸出 Markdown，
:func:`rows_csv` 輸出 CSV。報表不含時間，相同的輸入必得逐字相同的輸出，且與 ``jobs`` 無關。
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Final

from trpg.content.library import ContentLibrary
from trpg.engine.events import SkillInfused
from trpg.roguelite.auto import FlashPolicy
from trpg.shared.types import Team
from trpg.sim.attack_flow_report import SCENARIOS
from trpg.sim.batch import BatchSpec, map_spec, run_batches
from trpg.sim.flash_report import RunMetrics, run_flash_sim
from trpg.sim.matrix import MatrixReport, run_matrix
from trpg.sim.metrics import battle_metrics, run_tracked
from trpg.sim.parallel import run_tasks
from trpg.sim.resource_report import BUILDS as RESOURCE_BUILDS
from trpg.sim.resource_report import ResourceCell, run_resources, summarize_resources
from trpg.sim.summon_report import (
    BOSS_MAP,
    DEFAULT_PACKS,
    SUMMON_MAPS,
    BattleSample,
    PackSummary,
    _spec,
    downed_ratio,
    summarize,
)

__all__ = [
    "BaselineSizes",
    "Row",
    "Target",
    "format_baseline",
    "rows_csv",
    "run_baseline",
    "top_deviations",
]

# ---------------------------------------------------------------------------
# 目標與列
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Target:
    """目標區間 ``[lo, hi]``（``None`` ＝ 不設該側）；``scale`` 是偏離正規化的尺度
    （偏離 ＝ 超出區間的距離 ÷ ``scale``，所以不同單位的列可以互相排序）。"""

    lo: float | None
    hi: float | None
    scale: float
    text: str


WIN_RATE: Final = Target(35, 65, 30, "35–65%")
NORMAL_ROUNDS: Final = Target(4, 6, 2, "4–6 輪")
BOSS_ROUNDS: Final = Target(6, 10, 4, "6–10 輪")
SHORTAGE: Final = Target(None, 20, 20, "≤ 20%（參考）")
DOWNED_NORMAL: Final = Target(10, 50, 40, "10–50%（B3）")
DOWNED_BOSS: Final = Target(None, 50, 50, "≤ 50%（B3）")
DPR_RATIO: Final = Target(75, 125, 25, "75–125%（對單手劍）")
NO_STANDARD_BREACH: Final = Target(0, 0, 3, "0（6.8 標準）")
_ZERO: Final = 1e-9
_COUNT_UNITS: Final = ("個", "種")


@dataclass(frozen=True, slots=True)
class Row:
    """一個指標：區塊、項目、數值（單位見 ``unit``）、樣本數與目標（``None`` ＝ 只列不排序）。"""

    section: str
    item: str
    value: float
    unit: str
    n: int
    target: Target | None
    note: str = ""

    @property
    def deviation(self) -> float | None:
        t = self.target
        if t is None:
            return None
        outside = 0.0
        if t.lo is not None and self.value < t.lo:
            outside = t.lo - self.value
        elif t.hi is not None and self.value > t.hi:
            outside = self.value - t.hi
        return outside / t.scale

    @property
    def status(self) -> str:
        dev = self.deviation
        if dev is None:
            return "—"
        return "✓" if dev <= _ZERO else "⚠"


def top_deviations(rows: Sequence[Row], count: int = 10) -> list[Row]:
    """偏離最大的前 ``count`` 列（依偏離由大到小；同分依區塊、項目排序，確定性）。"""
    flagged = [r for r in rows if r.deviation is not None and r.status == "⚠"]
    return sorted(flagged, key=lambda r: (-(r.deviation or 0.0), -r.n, r.section, r.item))[:count]


# ---------------------------------------------------------------------------
# 規模
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BaselineSizes:
    """各區塊的場數與範圍（``None`` ＝ 用預設全集）。"""

    map_seeds: int = 30
    matrix_seeds: int = 5
    weapon_seeds: int = 5
    boss_seeds: int = 30
    summon_seeds: int = 8
    resource_seeds: int = 20
    run_seeds: int = 20
    seed_start: int = 0
    maps: tuple[str, ...] = ()
    """空 ＝ 呼叫端傳入的預設地圖。"""
    builds: tuple[str, ...] = ()
    """矩陣的 build；空 ＝ 全部非白板、非對照。"""
    weapon_builds: tuple[str, ...] = ()
    """武器對照的白板 build；空 ＝ 全部白板。"""
    packs: tuple[str, ...] = DEFAULT_PACKS
    scenarios: tuple[str, ...] = ()
    """資源情境；空 ＝ 全部。"""
    resource_builds: tuple[str, ...] = (*RESOURCE_BUILDS, "build_fire")
    summon_maps: tuple[str, ...] = SUMMON_MAPS
    run_policy: FlashPolicy = "balanced"
    sections: tuple[str, ...] = ()
    """要跑的區塊（空 ＝ 全部）。"""


SECTIONS: Final = ("maps", "boss", "matrix", "resources", "weapons", "summons", "run")
SECTION_TITLES: Final = {
    "maps": "一、示範地圖（一般遭遇）",
    "boss": "二、Boss 戰",
    "matrix": "三、build 矩陣",
    "resources": "四、資源短缺",
    "weapons": "五、武器類型",
    "summons": "六、召喚物",
    "run": "七、一輪（roguelite）",
}
_SWORD_BUILD: Final = "build_blank_warrior"
_DPR_WEAPONS: Final = (
    "fist",
    "scythe",
    "whip",
    "dual_dagger",
    "shotgun",
    "one_handed_sword",
)
"""B16～B19 要對照的武器 ID（拳套、鐮刀、鞭、雙匕首、霰彈槍、單手劍）；實際 ID 以內容為準。"""


def _seeds(start: int, count: int) -> tuple[int, ...]:
    return tuple(range(start, start + count))


def _pct(num: float, den: float) -> float:
    return 0.0 if den == 0 else num * 100 / den


# ---------------------------------------------------------------------------
# 1. 地圖
# ---------------------------------------------------------------------------


def _maps_rows(
    library: ContentLibrary, maps: Sequence[str], sizes: BaselineSizes, jobs: int
) -> list[Row]:
    seeds = _seeds(sizes.seed_start, sizes.map_seeds)
    reports = run_batches([map_spec(library, m, seeds) for m in maps], jobs=jobs)
    rows: list[Row] = []
    for map_id, rep in zip(maps, reports, strict=True):
        n = rep.completed
        err = rep.battles - rep.completed
        note = f"平手 {rep.draws}" + (f"；異常 {err}" if err else "")
        rows.append(
            Row("maps", f"{map_id} 我方勝率", rep.ally_win_rate * 100, "%", n, WIN_RATE, note)
        )
        rows.append(
            Row("maps", f"{map_id} 平均輪數", rep.rounds_mean, "輪", n, NORMAL_ROUNDS, "一般遭遇")
        )
    return rows


# ---------------------------------------------------------------------------
# 召喚包（Boss 戰與召喚物共用）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _PackTask:
    pack: str
    map_id: str
    seed: int
    hero_id: str
    spec: BatchSpec


@dataclass(frozen=True, slots=True)
class _PackResult:
    sample: BattleSample
    infusions: int


def _pack_work(tasks: tuple[_PackTask, ...], index: int) -> _PackResult:
    task = tasks[index]
    spec = task.spec
    try:
        run = run_tracked(
            spec.setup, spec.seeds[0], spec.policy_factory(), max_actions=spec.max_actions
        )
        metrics = battle_metrics(run)
        infusions = sum(1 for e in run.events if isinstance(e, SkillInfused))
    except Exception:  # 與 batch.run_one 一致：任何例外視為未完成
        metrics, infusions = None, 0
    return _PackResult(
        BattleSample(task.pack, task.map_id, task.seed, task.hero_id, metrics), infusions
    )


def _run_packs(
    library: ContentLibrary,
    jobs_spec: Sequence[tuple[str, str, int]],
    jobs: int,
) -> list[_PackResult]:
    tasks: list[_PackTask] = []
    for pack, map_id, seed in jobs_spec:
        spec, hero_id = _spec(library, pack, map_id, seed, 30)
        tasks.append(_PackTask(pack, map_id, seed, hero_id, spec))
    return run_tasks(_pack_work, tuple(tasks), list(range(len(tasks))), jobs=jobs)


def _summaries(results: Sequence[_PackResult], map_ids: Sequence[str]) -> dict[str, PackSummary]:
    chosen = [r.sample for r in results if r.sample.map_id in map_ids]
    return {s.pack: s for s in summarize(chosen)}


def _infusions(
    results: Sequence[_PackResult], pack: str, map_ids: Sequence[str]
) -> tuple[int, int]:
    """（灌注次數, 有召喚的場數）；有召喚場數以該場我方召喚數 > 0 計。"""
    total = battles = 0
    for r in results:
        m = r.sample.metrics
        if r.sample.pack != pack or r.sample.map_id not in map_ids or m is None:
            continue
        if any(rec.team is Team.ALLY for rec in m.summons):
            battles += 1
            total += r.infusions
    return total, battles


def _boss_rows_from(results: Sequence[_PackResult], sizes: BaselineSizes) -> list[Row]:
    summaries = _summaries(results, (BOSS_MAP,))
    rows: list[Row] = []
    plain_wins = plain_n = 0
    for pack in sizes.packs:
        s = summaries.get(pack)
        if s is None or s.battles == 0:
            continue
        summoner = s.summons_total > 0
        note = "召喚包" if summoner else "無召喚對照包（B7）"
        if not summoner:
            plain_wins += s.wins
            plain_n += s.battles
        fail = f"；未完成 {s.failed}" if s.failed else ""
        rows.append(
            Row(
                "boss",
                f"{pack} Boss 勝率",
                _pct(s.wins, s.battles),
                "%",
                s.battles,
                WIN_RATE,
                note + fail,
            )
        )
        rows.append(
            Row("boss", f"{pack} Boss 輪數", s.rounds_mean, "輪", s.battles, BOSS_ROUNDS, note)
        )
    if plain_n:
        rows.append(
            Row(
                "boss",
                "無召喚對照包合計 Boss 勝率",
                _pct(plain_wins, plain_n),
                "%",
                plain_n,
                WIN_RATE,
                "B7",
            )
        )
    return rows


def _summon_rows_from(results: Sequence[_PackResult], sizes: BaselineSizes) -> list[Row]:
    normal = _summaries(results, sizes.summon_maps)
    boss = _summaries(results, (BOSS_MAP,))
    rows: list[Row] = []
    for pack in sizes.packs:
        for label, summary, maps, target in (
            ("一般戰", normal.get(pack), sizes.summon_maps, DOWNED_NORMAL),
            ("Boss 戰", boss.get(pack), (BOSS_MAP,), DOWNED_BOSS),
        ):
            if summary is None or summary.summons_total == 0:
                continue
            ratio = (downed_ratio(summary) or 0.0) * 100
            rows.append(
                Row(
                    "summons",
                    f"{pack} {label}召喚物被打倒",
                    ratio,
                    "%",
                    summary.summons_total,
                    target,
                    f"{summary.battles_with_summon}/{summary.battles} 場有召喚",
                )
            )
            total, with_summon = _infusions(results, pack, maps)
            per = 0.0 if with_summon == 0 else total / with_summon
            rows.append(
                Row(
                    "summons",
                    f"{pack} {label}灌注次數／有召喚場",
                    per,
                    "次",
                    with_summon,
                    None,
                    f"共 {total} 次（B5：3H 後頻率下降，無目標值）",
                )
            )
    return rows


# ---------------------------------------------------------------------------
# 3. build 矩陣、5. 武器
# ---------------------------------------------------------------------------


def _matrix_rows(report: MatrixReport) -> list[Row]:
    archetypes = report.archetypes
    top_target = Target(
        1,
        max(1, len(archetypes) - 1),
        2,
        f"1–{max(1, len(archetypes) - 1)} 種（共 {len(archetypes)}）",
    )
    rows: list[Row] = []
    for build in report.builds:
        cells = [c for c in report.cells if c.build_id == build]
        done = sum(c.completed for c in cells)
        wins = sum(c.ally_wins for c in cells)
        rate = _pct(wins, done)
        dpr = sum(c.hero_dpr for c in cells) / len(cells) if cells else 0.0
        label = "偏強" if rate > WIN_RATE.hi else "偏弱" if rate < WIN_RATE.lo else "正常"  # type: ignore[operator]
        rows.append(
            Row(
                "matrix", f"{build} 勝率", rate, "%", done, WIN_RATE, f"{label}；英雄 DPR {dpr:.1f}"
            )
        )
        tops = sum(1 for a in report.archetype_cells if a.build_id == build and a.top)
        rows.append(
            Row("matrix", f"{build} 前段類型數", tops, "種", len(archetypes), top_target, "")
        )
    s = report.standards
    rows.append(
        Row(
            "matrix",
            "標準1：所有類型都前段的 build 數",
            len(s.always_top),
            "個",
            len(report.builds),
            NO_STANDARD_BREACH,
            "、".join(s.always_top),
        )
    )
    rows.append(
        Row(
            "matrix",
            "標準2：沒有任何前段類型的 build 數",
            len(s.never_top),
            "個",
            len(report.builds),
            NO_STANDARD_BREACH,
            "、".join(s.never_top),
        )
    )
    return rows


def _matrix_builds(library: ContentLibrary, sizes: BaselineSizes) -> list[str]:
    return list(sizes.builds) or [b.id for b in library.builds.sim_builds()]


def _weapon_builds(library: ContentLibrary, sizes: BaselineSizes) -> list[str]:
    if sizes.weapon_builds:
        return list(sizes.weapon_builds)
    return sorted(b.id for b in library.builds.builds if b.blank)


def _weapon_rows(library: ContentLibrary, report: MatrixReport, sizes: BaselineSizes) -> list[Row]:
    weapon_of = {b.id: b.hero.weapon for b in library.builds.builds}
    dpr: dict[str, float] = {}
    rows: list[Row] = []
    for build in report.builds:
        cells = [c for c in report.cells if c.build_id == build]
        done = sum(c.completed for c in cells)
        dpr[build] = sum(c.hero_dpr for c in cells) / len(cells) if cells else 0.0
        rate = _pct(sum(c.ally_wins for c in cells), done)
        rows.append(
            Row(
                "weapons",
                f"{weapon_of[build]}（{build}）勝率",
                rate,
                "%",
                done,
                WIN_RATE,
                f"DPR {dpr[build]:.1f}",
            )
        )
    base = dpr.get(_SWORD_BUILD, 0.0)
    if base > 0:
        for build in report.builds:
            if build == _SWORD_BUILD:
                continue
            ratio = dpr[build] * 100 / base
            target = DPR_RATIO if weapon_of[build] in _DPR_WEAPONS else None
            rows.append(
                Row(
                    "weapons",
                    f"{weapon_of[build]}（{build}）DPR／單手劍",
                    ratio,
                    "%",
                    len(report.cells),
                    target,
                    "B16～B19 對照" if target else "參考（非 B16～B19 對照）",
                )
            )
    return rows


# ---------------------------------------------------------------------------
# 4. 資源、7. 一輪
# ---------------------------------------------------------------------------


def _resource_rows(cells: Sequence[ResourceCell]) -> list[Row]:
    rows: list[Row] = []
    for c in cells:
        note = f"耐力不足 {c.stamina_short * 100:.0f}%；英雄勝率 {c.win_rate * 100:.0f}%"
        rows.append(
            Row(
                "resources",
                f"{c.build} × {c.scenario} 法力不足回合",
                c.mana_short * 100,
                "%",
                c.turns,
                SHORTAGE,
                note,
            )
        )
    return rows


def _run_rows(results: Sequence[RunMetrics], policy: str) -> list[Row]:
    n = len(results)
    if n == 0:
        return []
    reached = sum(r.boss_reached for r in results)
    won = sum(r.boss_won for r in results)
    wins = sum(r.victory for r in results)
    mean_wins = sum(r.battles_won for r in results) / n
    return [
        Row("run", f"一輪勝率（{policy}閃現）", _pct(wins, n), "%", n, WIN_RATE, ""),
        Row(
            "run",
            "Boss 勝率（打到 Boss 的輪）",
            _pct(won, reached),
            "%",
            reached,
            WIN_RATE,
            f"{reached}/{n} 輪打到 Boss",
        ),
        Row("run", "平均贏幾場", mean_wins, "場", n, None, "現行靈感每勝 2 點；無目標值"),
    ]


# ---------------------------------------------------------------------------
# 總流程
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BaselineResult:
    rows: list[Row] = field(default_factory=list)
    sections: tuple[str, ...] = ()


def run_baseline(
    library: ContentLibrary,
    default_maps: Sequence[str],
    sizes: BaselineSizes,
    *,
    jobs: int = 1,
    progress: Callable[[str], None] | None = None,
) -> BaselineResult:
    """依 ``sizes`` 跑各區塊；回傳全部列（區塊順序固定）。"""
    wanted = sizes.sections or SECTIONS
    maps = list(sizes.maps) or list(default_maps)
    rows: list[Row] = []

    def note(name: str) -> None:
        if progress is not None:
            progress(name)

    if "maps" in wanted:
        note("maps")
        rows += _maps_rows(library, maps, sizes, jobs)
    if "boss" in wanted or "summons" in wanted:
        note("boss/summons")
        plan = _pack_plan(sizes)
        results = _run_packs(library, plan, jobs)
        if "boss" in wanted:
            rows += _boss_rows_from(results, sizes)
        if "summons" in wanted:
            rows += _summon_rows_from(results, sizes)
    if "matrix" in wanted:
        note("matrix")
        rows += _matrix_rows(
            run_matrix(
                library,
                _matrix_builds(library, sizes),
                maps,
                _seeds(sizes.seed_start, sizes.matrix_seeds),
                jobs=jobs,
            )
        )
    if "resources" in wanted:
        note("resources")
        rows += _resource_rows(_resources(library, sizes, jobs))
    if "weapons" in wanted:
        note("weapons")
        report = run_matrix(
            library,
            _weapon_builds(library, sizes),
            maps,
            _seeds(sizes.seed_start, sizes.weapon_seeds),
            jobs=jobs,
        )
        rows += _weapon_rows(library, report, sizes)
    if "run" in wanted:
        note("run")
        rows += _run_rows(
            run_flash_sim(
                library, [sizes.run_policy], _seeds(sizes.seed_start, sizes.run_seeds), jobs=jobs
            ),
            sizes.run_policy,
        )
    return BaselineResult(rows, tuple(s for s in SECTIONS if s in wanted))


def _pack_plan(sizes: BaselineSizes) -> list[tuple[str, str, int]]:
    boss_seeds = range(sizes.seed_start, sizes.seed_start + sizes.boss_seeds)
    seeds = range(sizes.seed_start, sizes.seed_start + sizes.summon_seeds)
    plan = [(p, BOSS_MAP, s) for p in sizes.packs for s in boss_seeds]
    plan += [(p, m, s) for p in sizes.packs for m in sizes.summon_maps for s in seeds]
    return plan


def _resources(library: ContentLibrary, sizes: BaselineSizes, jobs: int) -> list[ResourceCell]:
    scenarios = tuple(s for s in SCENARIOS if not sizes.scenarios or s.id in sizes.scenarios)
    samples = run_resources(
        library,
        scenarios=scenarios,
        builds=sizes.resource_builds,
        seeds=sizes.resource_seeds,
        seed_start=sizes.seed_start,
        jobs=jobs,
    )
    return summarize_resources(samples)


# ---------------------------------------------------------------------------
# 輸出
# ---------------------------------------------------------------------------


def _fmt_value(row: Row) -> str:
    if row.unit in _COUNT_UNITS:
        return f"{row.value:.0f}{row.unit}"
    return f"{row.value:.1f}{row.unit}"


def _fmt_dev(row: Row) -> str:
    dev = row.deviation
    return "—" if dev is None else f"{dev:.2f}"


def _table_row(row: Row) -> str:
    target = "—" if row.target is None else row.target.text
    cells = (row.item, _fmt_value(row), str(row.n), target, row.status, _fmt_dev(row), row.note)
    return "| " + " | ".join(cells) + " |"


_HEADER: Final = ("| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |", "|" + "---|" * 7)


def format_baseline(result: BaselineResult, *, sizes_text: str = "") -> str:
    """Markdown 總表：概覽、偏離最大的前 10 項、各區塊明細。"""
    rows = result.rows
    flagged = [r for r in rows if r.status == "⚠"]
    judged = [r for r in rows if r.deviation is not None]
    lines = ["# BAL-3 全面基線報表", ""]
    if sizes_text:
        lines += [sizes_text, ""]
    lines.append(f"共 {len(rows)} 項指標，有目標的 {len(judged)} 項，偏離（⚠）{len(flagged)} 項。")
    lines += [
        "偏離 ＝ 超出目標區間的距離 ÷ 指標尺度（勝率 30 個百分點、輪數為區間寬度），可跨單位排序。",
        "",
        "## 偏離最大的前 10 項",
        "",
        "| # | 區塊 | 項目 | 數值 | 目標 | 偏離 |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(top_deviations(rows), 1):
        target = r.target.text if r.target else "—"
        lines.append(
            f"| {i} | {r.section} | {r.item} | {_fmt_value(r)} | {target} | {_fmt_dev(r)} |"
        )
    for section in result.sections:
        part = [r for r in rows if r.section == section]
        bad = sum(1 for r in part if r.status == "⚠")
        lines += ["", f"## {SECTION_TITLES[section]}（{bad}/{len(part)} 項偏離）", "", *_HEADER]
        lines += [_table_row(r) for r in part]
    return "\n".join(lines) + "\n"


def rows_csv(result: BaselineResult) -> str:
    """CSV：每列一個指標。"""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        ["section", "item", "value", "unit", "n", "target", "status", "deviation", "note"]
    )
    for r in result.rows:
        writer.writerow([
            r.section, r.item, f"{r.value:.3f}", r.unit, r.n,
            "" if r.target is None else r.target.text, r.status,
            "" if r.deviation is None else f"{r.deviation:.3f}", r.note,
        ])  # fmt: skip
    return buf.getvalue()
