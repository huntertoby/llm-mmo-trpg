"""BAL-10e 收回家族的量測（只量不調；不改任何模板與規則）。

1. **可出列數與倍數**：每種收回（精煉、多段併一段、合體、專注×4、陷阱／地面格的收束）在內建技能
   （技能自己的階級）閃一次，記「結構可出」（拿掉什麼的草稿不是空的）與「套得上」（換完通過預算、
   強度下限、單發上限）的招數，以及換到的倍數（收回後 ÷ 收回前）：
   - 主動、被動、反應：對單一目標的期望量（傷害／治療／護盾取最大的一組，:func:`target_power`）；
   - 合體：單隻召喚物的 HP 倍率（（1000＋``max_hp_permille``）×``power_permille``）；
   - 修正型被動：修正規則的點數（不含條件倍率）。
   需要先有「可以收回的部分」的（連打後併一段、雙生後合體、觸發範圍 +1 後專注、作用範圍 +1 後專注）
   另列「先擴張再收回」：第 1 次（雙生是第 3 次）擴張、下一次收回，倍數相對擴張後。
2. **AI 選中比例**：``trpg sim flash`` 的自動玩家（均衡為基準，另列集中、全指定、混合）整輪的小變化
   選擇裡，各收回佔的比例。

輸出 Markdown 到標準輸出（相同參數必得逐字相同）。

用法::

    uv run python scripts/flash_reclaim_measure.py --seeds 48 --jobs 8 \\
        > docs/phases/BAL-10/reclaim_bal10e.md
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.auto import ALL_FLASH_POLICIES, FlashPolicy
from trpg.sim.flash_report import RunMetrics, run_flash_sim
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_derive import FlashError, derive_chain
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation
from trpg.skillgen.flash_trade import TRADES, target_power
from trpg.skillgen.random_composer import default_library

SEED = 7
_PERMILLE = 1000

type Core = Callable[[SkillDef, ContentLibrary], Fraction]


def _power(skill: SkillDef, library: ContentLibrary) -> Fraction:
    return max(target_power(skill, library).values(), default=Fraction(0))


def _summon(skill: SkillDef, _library: ContentLibrary) -> Fraction:
    effect = next((e for e in skill.effects if e.type == "summon"), None)
    if effect is None:
        return Fraction(0)
    hp = Fraction(_PERMILLE + (effect.max_hp_permille or 0), _PERMILLE)
    return hp * Fraction(effect.power_permille or _PERMILLE, _PERMILLE)


def _modifier(skill: SkillDef, library: ContentLibrary) -> Fraction:
    report = skill_budget(skill, library)
    return sum((e.base for e in report.effects if e.type.startswith("modifier.")), Fraction(0))


@dataclass(frozen=True)
class Probe:
    """一種量測：收回模板、量什麼、（先擴張時）擴張的模板與第幾次。"""

    template: str
    label: str
    core: Core
    first: str | None = None
    first_nth: int = 1
    major_first: bool = False


DIRECT: tuple[Probe, ...] = (
    Probe("refine", "精煉（附帶效果）", _power),
    Probe("refine_merge", "精煉（多段併一段）", _power),
    Probe("fuse", "合體", _summon),
    Probe("focus_range", "專注（觸發範圍）", _power),
    Probe("focus_condition", "專注（觸發條件）", _power),
    Probe("focus_mod_range", "專注（修正：作用範圍）", _modifier),
    Probe("focus_mod_condition", "專注（修正：條件）", _modifier),
    Probe("converge_single", "收束・收成單體（陷阱／地面格）", _power),
    Probe("converge_step", "收束・縮小一級（陷阱／地面格）", _power),
)
CHAINED: tuple[Probe, ...] = (
    Probe("refine_merge", "連打 → 併一段", _power, first="multi_hit"),
    Probe("fuse", "雙生 → 合體", _summon, first="summon_count", first_nth=3, major_first=True),
    Probe("focus_range", "觸發範圍 +1 → 專注", _power, first="trigger_range"),
    Probe("focus_mod_range", "作用範圍 +1 → 專注", _modifier, first="mod_range"),
)


def _variation(library: ContentLibrary, template: str, *, major: bool = False) -> Variation:
    if major:
        return Variation(source="major", template=template, category="deepen")
    found = library.flash.minor_template(template)
    assert found is not None, template
    return Variation(source="minor", template=template, category=found.category)


def _derive(library: ContentLibrary, skill: SkillDef, records: Sequence[FlashRecord]) -> SkillDef:
    state = SkillFlash(base_id=skill.id, records=tuple(records))
    return derive_chain(library, skill, state, SEED)[-1]


def _subjects(library: ContentLibrary, probe: Probe) -> list[SkillDef]:
    """直接量的對象：陷阱／地面格的收束只看陷阱與帶持續區域的技能（一般範圍技見 BAL-10d 量測）。"""
    skills = [s for s in sorted(library.skills.values(), key=lambda s: s.id)]
    if probe.template.startswith("converge"):
        return [s for s in skills if s.trap is not None or any(e.type == "zone" for e in s.effects)]
    return skills


def _drafted(library: ContentLibrary, skill: SkillDef, template: str) -> bool:
    found = library.flash.minor_template(template)
    assert found is not None
    op = TRADES[found.op].remove
    return bool(op(skill, found, _variation(library, template), library))


def _measure(library: ContentLibrary, probe: Probe) -> tuple[int, int, int, list[float], str]:
    """（對象數, 結構可出, 套得上, 倍數, 例子）。"""
    subjects = 0
    drafted = ok = 0
    ratios: list[tuple[float, str]] = []
    for skill in _subjects(library, probe):
        records: list[FlashRecord] = []
        before = skill
        if probe.first is not None:
            first = FlashRecord(
                nth=probe.first_nth,
                variation=_variation(library, probe.first, major=probe.major_first),
            )
            try:
                before = _derive(library, skill, [first])
            except FlashError:
                continue
            records.append(first)
        found = library.flash.minor_template(probe.template)
        assert found is not None
        if before.kind not in (found.kinds or library.flash.category(found.category).kinds):
            continue
        subjects += 1
        if not _drafted(library, before, probe.template):
            continue
        drafted += 1
        nth = probe.first_nth + 1 if probe.first is not None else 1
        record = FlashRecord(nth=nth, variation=_variation(library, probe.template))
        try:
            after = _derive(library, skill, [*records, record])
        except FlashError:
            continue
        ok += 1
        base = probe.core(before, library)
        if base > 0:
            ratios.append((float(probe.core(after, library) / base), skill.id))
    values = sorted(r for r, _ in ratios)
    top = max(ratios, default=(0.0, "—"))
    return subjects, drafted, ok, values, f"{top[1]} {top[0]:.2f}" if ratios else "—"


def _stats(values: list[float]) -> str:
    if not values:
        return "— | — | —"
    return f"{values[0]:.2f} | {statistics.median(values):.2f} | {values[-1]:.2f}"


def multiples_table(library: ContentLibrary, probes: Sequence[Probe]) -> list[str]:
    lines = [
        "| 收回 | 模板 | 對象 | 結構可出 | 套得上 | 倍數 最小 | 中位 | 最大 | 最大的一招 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for probe in probes:
        subjects, drafted, ok, values, top = _measure(library, probe)
        lines.append(
            f"| {probe.label} | `{probe.template}` | {subjects} | {drafted} | {ok} "
            f"| {_stats(values)} | {top} |"
        )
    return lines


def _reclaims(library: ContentLibrary) -> list[str]:
    return [t.id for t in library.flash.minor if t.op in TRADES]


def ai_table(library: ContentLibrary, results: Sequence[RunMetrics]) -> list[str]:
    reclaims = _reclaims(library)
    head = "| 策略 | 輪數 | 小變化選擇 | 收回合計 | 收回／小變化 | " + " | ".join(reclaims) + " |"
    lines = [head, "|" + "---|" * (5 + len(reclaims))]
    order = ["balanced", *[p for p in ALL_FLASH_POLICIES if p != "balanced"]]
    for policy in order:
        runs = [r for r in results if r.policy == policy]
        picks = [p for r in runs for p in r.picks if p.source == "minor"]
        counts = [sum(1 for p in picks if p.template == t) for t in reclaims]
        total = sum(counts)
        share = "—" if not picks else f"{100 * total / len(picks):.1f}%"
        lines.append(
            f"| {policy} | {len(runs)} | {len(picks)} | {total} | {share} | "
            + " | ".join(str(c) for c in counts)
            + " |"
        )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=int, default=48, help="AI 模擬每個策略的種子數")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--no-ai", action="store_true", help="只量可出列數與倍數")
    args = parser.parse_args(argv)
    library = default_library()
    out = [
        "# BAL-10e 收回家族量測",
        "",
        f"每次閃現 +{library.flash.rules.budget_step_permille}‰；單發上限 "
        f"{library.flash.rules.single_hit_cap_permille}‰；種子 {SEED}；內建技能在自己的階級。"
        "「對象」＝種類相符的招數；「結構可出」＝拿掉什麼的草稿不是空的；「套得上」＝換完通過預算、"
        "強度下限與單發上限。倍數＝收回後 ÷ 收回前（主動／被動／反應：對單一目標的期望量；合體："
        "單隻召喚物 HP 倍率；修正型被動：規則點數，不含條件倍率）。",
        "",
        "## 直接收回（內建技能原樣）",
        "",
        *multiples_table(library, DIRECT),
        "",
        "## 先擴張再收回（第 1 次擴張、第 2 次收回；雙生是第 3 次、合體第 4 次）",
        "",
        *multiples_table(library, CHAINED),
    ]
    if not args.no_ai:
        policies: list[FlashPolicy] = list(ALL_FLASH_POLICIES)
        results = run_flash_sim(library, policies, range(1, args.seeds + 1), jobs=args.jobs)
        out += [
            "",
            f"## AI 選中收回的比例（每個策略 {args.seeds} 輪，種子 1–{args.seeds}）",
            "",
            "自動玩家一律選第一個選項（不指定類別時選項順序由種子洗牌）。",
            "",
            *ai_table(library, results),
        ]
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
