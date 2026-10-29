"""閃現系統的模擬報表（Phase 3W-8，``docs/design/06-技能.md`` 6.34；``trpg sim flash``）。

只量不調：每個（策略, 種子）用 ``trpg run auto`` 同一套 AI（:func:`trpg.roguelite.auto.auto_play`）
打完一整輪，從每個節點前後的 ``RunState`` 差異收集數字——

- 靈感點：每場勝利後手上的點數、累計花費（取得曲線）。
- 閃現選擇：次數、類別、模板、轉型、指定類別與否、選了之後的預算比例（``skill_budget().ratio``）。
- 每招閃了幾次（一輪結束時，每個學會的技能；完整技能另計）。
- 完整技能三選一：出現次數、選了幾次、實際加上的 +‰ 是否達到 ``complete.budget_permille``。
- 勝率、Boss 勝率。

策略（:data:`~trpg.roguelite.auto.FLASH_POLICIES`）：``none`` 不指定類別、``all`` 全指定類別、
``mixed`` 混合。溶掉與傳承：AI 不使用，固定 0（報表照實標出）。

確定性：結果只取決於（策略, 種子）；與 ``--jobs`` 無關。亂數只來自一輪自己的 ``Rng``。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.auto import FlashPolicy, auto_play
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.start import default_start, new_keyword_run
from trpg.roguelite.state import BattleNode, CompleteOfferNode, RunState
from trpg.sim.parallel import run_tasks
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.complete import complete_gain_permille
from trpg.skillgen.flash_state import SkillFlash

__all__ = [
    "FlashPick",
    "RunMetrics",
    "format_flash_report",
    "run_flash_sim",
    "simulate_run",
]

_PERMILLE = 1000
_FULL = 3
"""「練滿」的次數門檻（對照平衡待辦 B-3W）。"""
_MAJOR_NTH = 3
_COMPLETE_PERMILLE = 120


@dataclass(frozen=True, slots=True)
class FlashPick:
    """一次閃現（或重閃）選擇。"""

    nth: int
    kind: str
    """``flash`` 閃現、``reflash`` 重閃。"""
    source: str
    """變化來源：``minor``、``major``、``transform``。"""
    category: str
    template: str
    focused: bool
    cost: int
    ratio_permille: int
    """選了之後這招的預算比例（總點數 ÷ 可用預算，‰）；算不出來時 -1。"""


@dataclass(frozen=True, slots=True)
class RunMetrics:
    """一輪（一個策略、一個種子）的數字。"""

    policy: str
    seed: int
    victory: bool
    boss_reached: bool
    boss_won: bool
    battles_won: int
    curve: tuple[tuple[int, int, int], ...]
    """每場勝利之後：（場次, 手上未花的靈感點, 到這時為止累計花掉的點）。"""
    picks: tuple[FlashPick, ...]
    skill_flashes: tuple[int, ...]
    """一輪結束時，每個學會的非完整技能被閃現的次數（依 ID 排序）。"""
    complete_skills: int
    complete_offers: int
    complete_gains: tuple[int | None, ...]
    """選到的每個完整技能實際加上的 ‰（查不到時 ``None``）。"""
    leftover: int
    """結束時沒花掉的靈感點。"""


# ---------------------------------------------------------------------------
# 一輪
# ---------------------------------------------------------------------------


def _ratio_permille(library: ContentLibrary, run: RunState, skill_id: str) -> int:
    try:
        skill = skill_defs(library, run, [skill_id])[0]
        return int(skill_budget(skill, library).ratio * _PERMILLE)
    except (BudgetError, KeyError, ValueError):
        return -1


def _new_states(
    before: RunState, after: RunState
) -> list[tuple[str, SkillFlash, SkillFlash | None]]:
    """這個節點新出現的閃現狀態：（新技能 ID, 新狀態, 同一招之前的狀態）。依 ID 排序。"""
    old = {s.base_id: s for s in before.flash.values()}
    return [
        (skill_id, state, old.get(state.base_id))
        for skill_id, state in sorted(after.flash.items())
        if skill_id not in before.flash
    ]


def _pick_of(
    library: ContentLibrary, before: RunState, after: RunState, new: tuple[str, SkillFlash]
) -> FlashPick | None:
    skill_id, state = new
    previous = next((s for s in before.flash.values() if s.base_id == state.base_id), None)
    flashed = len(state.records) > (0 if previous is None else len(previous.records))
    record = state.records[-1] if flashed else state.adjustment
    if record is None or (state.complete and flashed):
        return None
    cost = before.insight - after.insight
    focus_cost = library.flash.pricing.rule(True).cost
    variation = record.variation
    return FlashPick(
        nth=record.nth,
        kind="flash" if flashed else "reflash",
        source=variation.source,
        category=variation.category,
        template=variation.template,
        focused=cost >= focus_cost > library.flash.pricing.rule(False).cost,
        cost=cost,
        ratio_permille=_ratio_permille(library, after, skill_id),
    )


class _Collector:
    """``auto_play`` 的 ``on_node`` 回呼：收集一輪的數字。:meth:`complete` 是 ``on_complete``
    觀察者：比較完整技能前後的定義，記下實際加上的 ‰。"""

    def __init__(self, library: ContentLibrary) -> None:
        self.library = library
        self.gains: dict[str, int] = {}
        self.picks: list[FlashPick] = []
        self.curve: list[tuple[int, int, int]] = []
        self.spent = 0
        self.complete_offers = 0
        self.complete_gains: list[int | None] = []

    def __call__(self, before: RunState, after: RunState) -> None:
        if isinstance(before.node, BattleNode) and after.battles_done > before.battles_done:
            if before.history != after.history and after.history[-1].won:
                self.curve.append((after.battles_done, after.insight, self.spent))
            return
        if isinstance(before.node, CompleteOfferNode):
            self.complete_offers += 1
            for skill_id, state, _old in _new_states(before, after):
                if state.complete:
                    self.complete_gains.append(self.gains.get(skill_id))
            return
        self._flashes(before, after)

    def complete(self, before: SkillDef, after: SkillDef) -> None:
        self.gains[after.id] = complete_gain_permille(before, after, self.library)

    def _flashes(self, before: RunState, after: RunState) -> None:
        if before.insight <= after.insight:
            return
        self.spent += before.insight - after.insight
        for skill_id, state, _old in _new_states(before, after):
            pick = _pick_of(self.library, before, after, (skill_id, state))
            if pick is not None:
                self.picks.append(pick)


def simulate_run(library: ContentLibrary, policy: FlashPolicy, seed: int) -> RunMetrics:
    """一個（策略, 種子）的一整輪（開局為種子抽的武器與關鍵字，同 ``trpg run auto``）。"""
    weapon, keywords = default_start(library, seed)
    run = new_keyword_run(library, weapon, keywords, seed)
    collector = _Collector(library)
    final, _ = auto_play(
        library, run, on_node=collector, flash_policy=policy, on_complete=collector.complete
    )
    return _metrics(library, policy, seed, final, collector)


def _metrics(
    library: ContentLibrary, policy: str, seed: int, final: RunState, collector: _Collector
) -> RunMetrics:
    boss = [r for r in final.history if r.boss]
    states = [final.flash[k] for k in sorted(final.flash)]
    victory = getattr(final.node, "victory", False)
    return RunMetrics(
        policy=policy,
        seed=seed,
        victory=bool(victory),
        boss_reached=bool(boss),
        boss_won=any(r.won for r in boss),
        battles_won=sum(1 for r in final.history if r.won),
        curve=tuple(collector.curve),
        picks=tuple(collector.picks),
        skill_flashes=tuple(len(s.records) for s in states if not s.complete),
        complete_skills=sum(1 for s in states if s.complete),
        complete_offers=collector.complete_offers,
        complete_gains=tuple(collector.complete_gains),
        leftover=final.insight,
    )


def _task(library: ContentLibrary, task: tuple[FlashPolicy, int]) -> RunMetrics:
    policy, seed = task
    return simulate_run(library, policy, seed)


def run_flash_sim(
    library: ContentLibrary,
    policies: Sequence[FlashPolicy],
    seeds: Iterable[int],
    *,
    jobs: int = 1,
) -> list[RunMetrics]:
    """所有（策略, 種子）的結果，順序同 ``policies`` × ``seeds``；與 ``jobs`` 無關。"""
    seed_list = list(seeds)
    tasks = [(p, s) for p in policies for s in seed_list]
    return run_tasks(_task, library, tasks, jobs=jobs)


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _pct(num: int, den: int) -> str:
    if den == 0:
        return "—"
    tenths = (Fraction(num * 1000, den)).__round__()
    return f"{tenths // 10}.{tenths % 10}%"


def _avg(values: Sequence[int]) -> str:
    if not values:
        return "—"
    hundredths = Fraction(sum(values) * 100, len(values)).__round__()
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def _percentile(values: Sequence[int], percent: int) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, len(ordered) * percent // 100)]


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _by_policy(results: Sequence[RunMetrics]) -> dict[str, list[RunMetrics]]:
    groups: dict[str, list[RunMetrics]] = {}
    for result in results:
        groups.setdefault(result.policy, []).append(result)
    return groups


def _overview(groups: dict[str, list[RunMetrics]]) -> list[str]:
    rows = []
    for policy, runs in groups.items():
        picks = [p for r in runs for p in r.picks]
        rows.append(
            [
                policy,
                str(len(runs)),
                _pct(sum(r.victory for r in runs), len(runs)),
                _pct(sum(r.boss_won for r in runs), sum(r.boss_reached for r in runs)),
                _avg([r.battles_won for r in runs]),
                _avg([sum(1 for p in r.picks if p.kind == "flash") for r in runs]),
                _avg([sum(p.cost for p in r.picks) for r in runs]),
                _avg([r.leftover for r in runs]),
                _pct(sum(1 for p in picks if p.focused), len(picks)),
            ]
        )
    header = [
        "策略",
        "輪數",
        "勝率",
        "Boss 勝率",
        "平均贏幾場",
        "閃現/輪",
        "花點/輪",
        "剩點/輪",
        "指定類別占比",
    ]
    return ["## 概況", "", *_table(header, rows), ""]


def _curve(groups: dict[str, list[RunMetrics]]) -> list[str]:
    width = max((n for runs in groups.values() for r in runs for n, _, _ in r.curve), default=0)
    rows = []
    for policy, runs in groups.items():
        for n in range(1, width + 1):
            cells = [c for r in runs for c in r.curve if c[0] == n]
            if cells:
                rows.append(
                    [
                        policy,
                        str(n),
                        str(len(cells)),
                        _avg([held for _, held, _ in cells]),
                        _avg([spent for _, _, spent in cells]),
                        _avg([held + spent for _, held, spent in cells]),
                    ]
                )
    header = ["策略", "第幾場勝利後", "樣本", "手上點數", "累計花費", "累計取得"]
    return ["## 靈感點曲線（手上點數是花之前的值）", "", *_table(header, rows), ""]


def _distribution(
    groups: dict[str, list[RunMetrics]], pick: Callable[[RunMetrics], Sequence[int]], top: int
) -> list[list[str]]:
    rows = []
    for policy, runs in groups.items():
        counts = Counter(v for r in runs for v in pick(r))
        total = sum(counts.values())
        rows.append(
            [
                policy,
                *(
                    _pct(sum(c for v, c in counts.items() if _bucket(v, top) == i), total)
                    for i in range(top + 1)
                ),
            ]
        )
    return rows


def _bucket(value: int, top: int) -> int:
    return min(value, top)


def _per_skill(groups: dict[str, list[RunMetrics]]) -> list[str]:
    top = 5
    header = ["策略", *(f"閃 {i} 次" for i in range(top)), f"閃 {top} 次"]
    lines = ["## 每招閃現次數分布（一輪結束時，每個學會的技能）", ""]
    lines += _table(header, _distribution(groups, lambda r: r.skill_flashes, top))
    lines += ["", "### 練滿 3 次以上的招數（每輪幾招；對照平衡待辦 B-3W）", ""]
    rows = []
    for policy, runs in groups.items():
        full = [sum(1 for n in r.skill_flashes if n >= _FULL) for r in runs]
        rows.append(
            [
                policy,
                _avg(full),
                *(_pct(sum(1 for n in full if n == i), len(full)) for i in range(4)),
                _pct(sum(1 for n in full if n > _FULL), len(full)),
                str(max(full, default=0)),
            ]
        )
    header = ["策略", "平均招數", "0 招", "1 招", "2 招", "3 招", "4 招以上", "最多"]
    return [*lines, *_table(header, rows), ""]


def _ratio(groups: dict[str, list[RunMetrics]]) -> list[str]:
    rows = []
    for policy, runs in groups.items():
        values = [p.ratio_permille for r in runs for p in r.picks if p.ratio_permille >= 0]
        if not values:
            continue
        rows.append(
            [
                policy,
                str(len(values)),
                *(f"{_percentile(values, q) / 10:.1f}%" for q in (0, 10, 50, 90)),
                f"{max(values) / 10:.1f}%",
                _pct(sum(1 for v in values if v > _PERMILLE), len(values)),
            ]
        )
    header = ["策略", "樣本", "最小", "p10", "p50", "p90", "最大", "超過 100% 占比"]
    lines = ["## 閃現後預算比例（總點數 ÷ 可用預算）", "", *_table(header, rows), ""]
    rows = []
    for policy, runs in groups.items():
        for nth in range(1, 6):
            values = [
                p.ratio_permille
                for r in runs
                for p in r.picks
                if p.kind == "flash" and p.nth == nth and p.ratio_permille >= 0
            ]
            if values:
                rows.append(
                    [policy, str(nth), str(len(values)), f"{int(_avg_float(values)) / 10:.1f}%"]
                )
    return [
        *lines,
        "### 依第幾次閃現的平均比例",
        "",
        *_table(["策略", "第幾次", "樣本", "平均"], rows),
        "",
    ]


def _avg_float(values: Sequence[int]) -> float:
    return sum(values) / len(values)


def _mix(groups: dict[str, list[RunMetrics]]) -> list[str]:
    lines = ["## 模板與類別分布（只算閃現，不含重閃）", ""]
    categories = sorted({p.category for runs in groups.values() for r in runs for p in r.picks})
    rows = []
    for category in categories:
        row = [category]
        for runs in groups.values():
            picks = [p for r in runs for p in r.picks if p.kind == "flash"]
            row.append(_pct(sum(1 for p in picks if p.category == category), len(picks)))
        rows.append(row)
    lines += _table(["類別", *groups], rows)
    lines += ["", "### 前 12 名模板", ""]
    rows = []
    for policy, runs in groups.items():
        picks = [p for r in runs for p in r.picks if p.kind == "flash"]
        counts = Counter(p.template for p in picks)
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
        rows.append([policy, "、".join(f"{t} {_pct(c, len(picks))}" for t, c in ranked)])
    lines += _table(["策略", "模板（占比）"], rows)
    lines += ["", "### 第 3 次（大變化）選到的來源", ""]
    rows = []
    for policy, runs in groups.items():
        third = [p for r in runs for p in r.picks if p.kind == "flash" and p.nth == _MAJOR_NTH]
        rows.append(
            [
                policy,
                str(len(third)),
                _pct(sum(1 for p in third if p.source == "major"), len(third)),
                _pct(sum(1 for p in third if p.source == "transform"), len(third)),
            ]
        )
    lines += _table(["策略", "樣本", "大變化", "轉型"], rows)
    overall = []
    for policy, runs in groups.items():
        picks = [p for r in runs for p in r.picks if p.kind == "flash"]
        overall.append(
            [
                policy,
                str(len(picks)),
                _pct(sum(1 for p in picks if p.source == "transform"), len(picks)),
            ]
        )
    return [
        *lines,
        "",
        "### 轉型占全部閃現的比例",
        "",
        *_table(["策略", "閃現次數", "轉型"], overall),
        "",
    ]


def _complete(groups: dict[str, list[RunMetrics]]) -> list[str]:
    rows = []
    for policy, runs in groups.items():
        gains = [g for r in runs for g in r.complete_gains]
        known = [g for g in gains if g is not None]
        rows.append(
            [
                policy,
                str(sum(r.complete_offers for r in runs)),
                str(sum(r.complete_skills for r in runs)),
                _pct(sum(1 for g in known if g >= _COMPLETE_PERMILLE), len(known)),
                _avg(known),
                str(min(known, default=0)),
                "0",
                "0",
            ]
        )
    header = [
        "策略",
        "三選一出現",
        "選了完整技能",
        "達到 +120‰",
        "平均實際 ‰",
        "最低 ‰",
        "溶掉",
        "傳承",
    ]
    return [
        "## 完整技能與溶掉／傳承（AI 不溶掉也不傳承，固定 0）",
        "",
        *_table(header, rows),
        "",
    ]


def format_flash_report(results: Sequence[RunMetrics]) -> str:
    """Markdown 報表（標準輸出；同樣的結果必得逐字相同的輸出）。"""
    groups = _by_policy(results)
    seeds = sorted({r.seed for r in results})
    head = [
        "# 閃現模擬報表（Phase 3W-8）",
        "",
        f"策略 {len(groups)} 種 × 種子 {len(seeds)} 個"
        + (f"（{seeds[0]}–{seeds[-1]}）" if seeds else "")
        + f" ＝ {len(results)} 輪",
        "",
    ]
    sections = [_overview, _curve, _per_skill, _ratio, _mix, _complete]
    lines = head
    for section in sections:
        lines += section(groups)
    return "\n".join(lines).rstrip() + "\n"
