"""技能報表（Phase 2C-3 5.5；``docs/design/06-技能.md`` 6.8）。

每個技能以 :func:`trpg.sim.skill_fuzz.battle_setup` 的施放者陣容（施放者只裝備這個技能，加上
一名沒有技能的標準隊友弓手），對上 3 名 **同階** 標準敵人（``std_enemy_t1``～``t5``，
``test_flat_6x6``）跑若干種子，輸出施放者 DPR、勝率、平均輪數與技能使用率。

- **依階級彙總** 施放者 DPR 的分佈（P5、P50、P95；線性內插），標出 **DPR > 同階 P95 × 1.2** 的技能
  （6.8 的退回條件；這裡只標出、不退回）。
- **依骨架彙總** 平均 DPR 與使用率（給 2B-3 #3「結構型原語點數偏低」的判斷用）。

純函式 :func:`build_skill_report` 由各技能的批次報表計算；:func:`run_skill_report` 負責模擬。
報表不含時間，相同的輸入必得逐字相同的輸出，且與 ``jobs`` 無關。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from pydantic import BaseModel, ConfigDict

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.sim.batch import BatchReport, BatchSpec, UtilityPolicyFactory, run_batches
from trpg.sim.skill_fuzz import battle_setup, caster_base
from trpg.skillgen.random_composer import compose_with_stats

__all__ = [
    "DPR_OUTLIER_FACTOR_PERMILLE",
    "SkeletonSummary",
    "SkillCase",
    "SkillRow",
    "SkillsReport",
    "TierSummary",
    "build_skill_report",
    "format_skill_report",
    "percentile",
    "random_cases",
    "run_skill_report",
]

DPR_OUTLIER_FACTOR_PERMILLE = 1200
"""標出條件：DPR > 同階 P95 × 1.2（6.8 的退回門檻）。"""
ENEMY_COUNT = 3
COMPANION = "sim_companion_archer"


def standard_enemy(tier: int) -> str:
    return f"std_enemy_t{tier}"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


@dataclass(frozen=True)
class SkillCase:
    """要測的一個技能：來源（``demo``／``random``）與隨機種子。"""

    skill: SkillDef
    source: str
    seed: int | None = None


class SkillRow(_Model):
    skill_id: str
    name_zh: str
    source: str
    seed: int | None
    tier: int
    skeleton: str
    rarity: str
    ap_cost: int
    battles: int
    completed: int
    caster_dpr: float
    win_rate: float
    rounds_mean: float
    uses_per_battle: float
    uses_per_round: float
    hit_rate: float | None
    avg_damage: float | None
    flagged: bool = False
    """DPR > 同階 P95 × 1.2。"""


class TierSummary(_Model):
    tier: int
    skills: int
    p5: float
    p50: float
    p95: float
    threshold: float
    """``P95 × 1.2``。"""
    flagged: tuple[str, ...]


class SkeletonSummary(_Model):
    skeleton: str
    skills: int
    mean_dpr: float
    mean_uses_per_round: float
    mean_win_rate: float


class SkillsReport(_Model):
    seeds: tuple[int, ...]
    rows: tuple[SkillRow, ...]
    tiers: tuple[TierSummary, ...]
    skeletons: tuple[SkeletonSummary, ...]


# ---------------------------------------------------------------------------
# 純函式
# ---------------------------------------------------------------------------


def percentile(values: Sequence[float], q: int) -> float:
    """第 ``q`` 百分位（0–100），線性內插；空序列為 0。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = Fraction((len(ordered) - 1) * q, 100)
    low = int(position)
    frac = float(position - low)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def build_skill_report(
    cases: Sequence[SkillCase],
    reports: Sequence[BatchReport],
    seeds: Sequence[int],
    *,
    caster_ids: Sequence[str],
) -> SkillsReport:
    """由各技能的批次報表計算 :class:`SkillsReport`（純函式）。"""
    rows: list[SkillRow] = []
    for case, report, caster_id in zip(cases, reports, caster_ids, strict=True):
        skill = case.skill
        caster = next(
            (t for t in report.templates if t.template_id == caster_id and t.team.value == "ally"),
            None,
        )
        usage = next((s for s in report.skills if s.skill_id == skill.id), None)
        per_battle = 0.0 if usage is None else usage.uses_per_battle
        rows.append(
            SkillRow(
                skill_id=skill.id,
                name_zh=skill.name_zh,
                source=case.source,
                seed=case.seed,
                tier=skill.tier,
                skeleton=skill.skeleton,
                rarity=skill.rarity,
                ap_cost=skill.ap_cost or 0,
                battles=report.battles,
                completed=report.completed,
                caster_dpr=0.0 if caster is None else caster.dpr,
                win_rate=report.ally_win_rate,
                rounds_mean=report.rounds_mean,
                uses_per_battle=per_battle,
                uses_per_round=per_battle / report.rounds_mean if report.rounds_mean else 0.0,
                hit_rate=None if usage is None else usage.hit_rate,
                avg_damage=None if usage is None else usage.avg_damage,
            )
        )
    tiers: list[TierSummary] = []
    flagged_ids: set[str] = set()
    for tier in sorted({r.tier for r in rows}):
        group = [r for r in rows if r.tier == tier]
        dprs = [r.caster_dpr for r in group]
        p95 = percentile(dprs, 95)
        threshold = p95 * DPR_OUTLIER_FACTOR_PERMILLE / 1000
        flagged = tuple(
            r.skill_id for r in sorted(group, key=lambda r: r.skill_id) if r.caster_dpr > threshold
        )
        flagged_ids.update(flagged)
        tiers.append(
            TierSummary(
                tier=tier,
                skills=len(group),
                p5=percentile(dprs, 5),
                p50=percentile(dprs, 50),
                p95=p95,
                threshold=threshold,
                flagged=flagged,
            )
        )
    rows = [r.model_copy(update={"flagged": r.skill_id in flagged_ids}) for r in rows]
    by_skeleton: dict[str, list[SkillRow]] = defaultdict(list)
    for r in rows:
        by_skeleton[r.skeleton].append(r)
    skeletons = tuple(
        SkeletonSummary(
            skeleton=name,
            skills=len(group),
            mean_dpr=_mean([r.caster_dpr for r in group]),
            mean_uses_per_round=_mean([r.uses_per_round for r in group]),
            mean_win_rate=_mean([r.win_rate for r in group]),
        )
        for name, group in sorted(by_skeleton.items())
    )
    return SkillsReport(
        seeds=tuple(seeds), rows=tuple(rows), tiers=tuple(tiers), skeletons=skeletons
    )


# ---------------------------------------------------------------------------
# 模擬
# ---------------------------------------------------------------------------


def random_cases(library: ContentLibrary, count: int, seed_start: int = 0) -> list[SkillCase]:
    """隨機組合器以種子 ``seed_start … seed_start + count − 1`` 組出的技能。"""
    return [
        SkillCase(compose_with_stats(seed, library=library).skill, "random", seed)
        for seed in range(seed_start, seed_start + count)
    ]


def demo_cases(library: ContentLibrary) -> list[SkillCase]:
    """示範技能（``content/skills/``，依 ID 排序）。"""
    return [SkillCase(library.skills[k], "demo") for k in sorted(library.skills)]


def skill_spec(library: ContentLibrary, case: SkillCase, seeds: Sequence[int]) -> BatchSpec:
    setup = battle_setup(
        library,
        case.skill,
        ally=COMPANION,
        enemies=(standard_enemy(case.skill.tier),) * ENEMY_COUNT,
    )
    return BatchSpec(
        name=case.skill.id,
        setup=setup,
        seeds=tuple(seeds),
        policy_factory=UtilityPolicyFactory(library.ai_profiles),
    )


def run_skill_report(
    library: ContentLibrary,
    cases: Sequence[SkillCase],
    seeds: Sequence[int],
    *,
    jobs: int = 1,
) -> SkillsReport:
    specs = [skill_spec(library, case, seeds) for case in cases]
    reports = run_batches(specs, jobs=jobs)
    return build_skill_report(
        cases, reports, seeds, caster_ids=[caster_base(c.skill) for c in cases]
    )


# ---------------------------------------------------------------------------
# 文字報表
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def format_skill_report(report: SkillsReport) -> str:
    """技能報表的文字格式（繁體中文）。"""
    seeds = report.seeds
    out = [
        f"技能報表：{len(report.rows)} 個技能，每個技能種子 {seeds[0]}–{seeds[-1]}"
        f"（{len(seeds)} 場），施放者＋標準隊友弓手 對 {ENEMY_COUNT} 名同階標準敵人，"
        "test_flat_6x6，max_rounds=20"
    ]
    out.append("")
    out.append("## 依階級的施放者 DPR 分佈（標出 DPR > 同階 P95 × 1.2）")
    out += _table(
        ["階級", "技能數", "P5", "P50", "P95", "門檻（P95×1.2）", "標出"],
        [
            [
                str(t.tier),
                str(t.skills),
                f"{t.p5:.2f}",
                f"{t.p50:.2f}",
                f"{t.p95:.2f}",
                f"{t.threshold:.2f}",
                "、".join(t.flagged) or "—",
            ]
            for t in report.tiers
        ],
    )
    out.append("")
    out.append("## 依骨架彙總")
    out += _table(
        ["骨架", "技能數", "平均 DPR", "使用率（次／輪）", "平均勝率"],
        [
            [
                s.skeleton,
                str(s.skills),
                f"{s.mean_dpr:.2f}",
                f"{s.mean_uses_per_round:.2f}",
                _pct(s.mean_win_rate),
            ]
            for s in report.skeletons
        ],
    )
    out.append("")
    out.append("## 各技能（依階級、DPR 由高到低；* ＝ 標出）")
    ordered = sorted(report.rows, key=lambda r: (r.tier, -r.caster_dpr, r.skill_id))
    out += _table(
        [
            "技能",
            "來源",
            "階",
            "骨架",
            "稀有度",
            "AP",
            "DPR",
            "勝率",
            "輪數",
            "次／場（被動＝觸發）",
            "次／輪",
            "命中率",
            "平均傷害",
        ],
        [
            [
                f"{r.skill_id}{'*' if r.flagged else ''}",
                r.source if r.seed is None else f"{r.source}:{r.seed}",
                str(r.tier),
                r.skeleton,
                r.rarity,
                str(r.ap_cost),
                f"{r.caster_dpr:.2f}",
                _pct(r.win_rate),
                f"{r.rounds_mean:.2f}",
                f"{r.uses_per_battle:.2f}",
                f"{r.uses_per_round:.2f}",
                "—" if r.hit_rate is None else _pct(r.hit_rate),
                "—" if r.avg_damage is None else f"{r.avg_damage:.1f}",
            ]
            for r in ordered
        ],
    )
    return "\n".join(out)
