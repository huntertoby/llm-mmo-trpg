"""靈感經濟掃描（平衡階段 BAL-1，``docs/phases/PhaseBAL計畫.md``）：只量不調。

把「每勝給幾點、開局給幾點、Boss 前加給幾點」三個旋鈕以參數覆寫在記憶體內的 library 副本上
（不改 ``content/``），對每個組合 × 策略 × 種子跑一整輪 AI（同 ``trpg sim flash``），輸出一張
Markdown 摘要表。亂數與一輪的流程完全沿用 :func:`trpg.sim.flash_report.simulate_run`，所以
相同參數必得逐字相同的輸出，且與 ``--jobs`` 無關。
"""

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.roguelite.auto import FlashPolicy
from trpg.sim.flash_report import RunMetrics, simulate_run
from trpg.sim.parallel import run_tasks

__all__ = [
    "Economy",
    "EconomyRow",
    "format_economy_report",
    "parse_economy",
    "run_economy_sweep",
    "with_economy",
]

_PERMILLE = 1000
_COMPLETE_PERMILLE = 120
_MAJOR_NTH = 3
_KEYS = {"win": "insight_per_win", "start": "insight_start", "preboss": "insight_preboss"}


@dataclass(frozen=True, slots=True)
class Economy:
    """一組靈感經濟參數（每勝、開局、Boss 前加給）。"""

    win: int
    start: int
    preboss: int

    @property
    def label(self) -> str:
        return f"win={self.win} start={self.start} preboss={self.preboss}"


def current_economy(library: ContentLibrary) -> Economy:
    """library 目前的靈感經濟（預設值＝現行行為：每勝 1、開局 0、Boss 前 0）。"""
    rules = library.flash.rules
    return Economy(rules.insight_per_win, rules.insight_start, rules.insight_preboss)


def with_economy(library: ContentLibrary, economy: Economy) -> ContentLibrary:
    """回傳覆寫靈感經濟的 library 副本（不動原物件，也不寫檔）。"""
    rules = library.flash.rules.model_copy(
        update={
            "insight_per_win": economy.win,
            "insight_start": economy.start,
            "insight_preboss": economy.preboss,
        }
    )
    flash = library.flash.model_copy(update={"rules": rules})
    return dataclasses.replace(library, flash=flash)


def parse_economy(library: ContentLibrary, spec: str) -> list[Economy]:
    """解析 ``"win=1,2;start=0,2;preboss=0,2"``，回傳所有組合（笛卡兒積，依輸入順序）。

    沒寫的旋鈕沿用 library 目前的值。值必須是非負整數；鍵只能是 win／start／preboss。
    """
    base = current_economy(library)
    values: dict[str, list[int]] = {
        "win": [base.win],
        "start": [base.start],
        "preboss": [base.preboss],
    }
    for part in (p.strip() for p in spec.split(";")):
        if not part:
            continue
        key, sep, raw = part.partition("=")
        key = key.strip()
        if not sep or key not in _KEYS:
            raise ValueError(f"--economy 的鍵只能是 {', '.join(_KEYS)}（收到 {part!r}）")
        try:
            numbers = [int(x) for x in raw.split(",") if x.strip()]
        except ValueError as exc:
            raise ValueError(f"--economy 的值必須是整數（{part!r}）") from exc
        if not numbers or any(n < 0 for n in numbers):
            raise ValueError(f"--economy 的值必須是非負整數（{part!r}）")
        values[key] = list(dict.fromkeys(numbers))
    return [
        Economy(w, s, b)
        for w, s, b in itertools.product(values["win"], values["start"], values["preboss"])
    ]


def _task(library: ContentLibrary, task: tuple[Economy, FlashPolicy, int]) -> RunMetrics:
    economy, policy, seed = task
    return simulate_run(with_economy(library, economy), policy, seed)


@dataclass(frozen=True, slots=True)
class EconomyRow:
    """一個（組合, 策略）× 全部種子的彙總。"""

    economy: Economy
    policy: str
    runs: tuple[RunMetrics, ...]


def run_economy_sweep(
    library: ContentLibrary,
    economies: Sequence[Economy],
    policies: Sequence[FlashPolicy],
    seeds: Iterable[int],
    *,
    jobs: int = 1,
) -> list[EconomyRow]:
    """所有（組合, 策略）的結果列，順序同 ``economies`` × ``policies``；與 ``jobs`` 無關。"""
    seed_list = list(seeds)
    tasks = [(e, p, s) for e in economies for p in policies for s in seed_list]
    results = run_tasks(_task, library, tasks, jobs=jobs)
    rows: list[EconomyRow] = []
    index = 0
    for economy in economies:
        for policy in policies:
            chunk = tuple(results[index : index + len(seed_list)])
            index += len(seed_list)
            rows.append(EconomyRow(economy, policy, chunk))
    return rows


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _pct(num: int, den: int) -> str:
    if den == 0:
        return "—"
    tenths = Fraction(num * 1000, den).__round__()
    return f"{tenths // 10}.{tenths % 10}%"


def _avg(values: Sequence[int]) -> str:
    if not values:
        return "—"
    hundredths = Fraction(sum(values) * 100, len(values)).__round__()
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def _acquired(run: RunMetrics) -> int:
    """這一輪累計取得的靈感點（最後一次勝利時：手上 ＋ 已花；開局點數算在第一個值裡）。"""
    if not run.curve:
        return 0
    _, held, spent = run.curve[-1]
    return held + spent


def _thirds(run: RunMetrics) -> int:
    return sum(1 for p in run.picks if p.kind == "flash" and p.nth == _MAJOR_NTH)


def _transform_share(runs: Sequence[RunMetrics]) -> str:
    third = [p for r in runs for p in r.picks if p.kind == "flash" and p.nth == _MAJOR_NTH]
    return _pct(sum(1 for p in third if p.source == "transform"), len(third))


def _complete_rate(runs: Sequence[RunMetrics]) -> str:
    known = [g for r in runs for g in r.complete_gains if g is not None]
    return _pct(sum(1 for g in known if g >= _COMPLETE_PERMILLE), len(known))


def _row_cells(row: EconomyRow) -> list[str]:
    runs = row.runs
    thirds = [_thirds(r) for r in runs]
    eco = row.economy
    return [
        str(eco.win),
        str(eco.start),
        str(eco.preboss),
        row.policy,
        str(len(runs)),
        _avg([_acquired(r) for r in runs]),
        _avg([sum(1 for p in r.picks if p.kind == "flash") for r in runs]),
        _avg(thirds),
        _pct(sum(1 for n in thirds if n >= 1), len(runs)),
        _transform_share(runs),
        _complete_rate(runs),
        _pct(sum(r.victory for r in runs), len(runs)),
        _pct(sum(r.boss_won for r in runs), sum(r.boss_reached for r in runs)),
        _avg([r.battles_won for r in runs]),
    ]


def format_economy_report(rows: Sequence[EconomyRow]) -> str:
    """Markdown 摘要表（標準輸出；同樣的結果必得逐字相同的輸出）。"""
    seeds = sorted({r.seed for row in rows for r in row.runs})
    combos = list(dict.fromkeys(row.economy for row in rows))
    header = [
        "每勝",
        "開局",
        "Boss前",
        "策略",
        "輪數",
        "每輪靈感",
        "閃現/輪",
        "第3次大變化/輪",
        "≥1招輪數比",
        "轉型比例",
        "完整+120‰",
        "勝率",
        "Boss勝率",
        "平均贏幾場",
    ]
    lines = [
        "# 靈感經濟掃描報表（BAL-1）",
        "",
        f"組合 {len(combos)} 種 × 策略 × 種子 {len(seeds)} 個"
        + (f"（{seeds[0]}–{seeds[-1]}）" if seeds else ""),
        "",
        "- 每輪靈感：累計取得（含開局與 Boss 前加給）。第3次大變化/輪：每輪練到第 3 次閃現的招數。",
        "- 轉型比例：第 3 次閃現選到轉型的占比。完整+120‰：完整技能實際加成達 120‰ 的占比。",
        "- 平均贏幾場：一輪平均打贏的戰鬥場數（含 Boss，滿分 6）。",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    lines += ["| " + " | ".join(_row_cells(row)) + " |" for row in rows]
    return "\n".join(lines) + "\n"
