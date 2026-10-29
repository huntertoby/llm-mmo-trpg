"""``trpg skills budget``：技能預算明細與總表（Phase 2B-2 4.7）。"""

from __future__ import annotations

from fractions import Fraction
from typing import TextIO

from trpg.cli.skills import pad
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.narrative.skills import variant_change_text, variant_condition_text
from trpg.skillgen.budget import BudgetError, BudgetReport, skill_budget
from trpg.skillgen.validate import Violation, validate_skill

_PERMILLE = 1000

__all__ = ["cmd_skills_budget", "cmd_skills_budget_all", "library_violations", "print_skill_budget"]

_RARITY = {"common": "普通", "rare": "稀有", "epic": "史詩", "legendary": "傳說"}


_AP_LABEL = {"passive": "被動", "reaction": "反應", "stance": "姿態", "modifier": "修正"}


def _num(value: Fraction) -> str:
    return f"{float(value):.2f}"


def _mult(value: Fraction) -> str:
    return f"×{float(value):g}"


def _pct(value: Fraction) -> str:
    return f"{float(value) * 100:.1f}%"


_BUDGET_RANGE_RULES = frozenset({"budget.over", "budget.weak"})


def library_violations(library: ContentLibrary) -> list[Violation]:
    """全部技能的違規（依技能 ID 排序）。"""
    out: list[Violation] = []
    for skill_id in sorted(library.skills):
        found = validate_skill(library.skills[skill_id], library)
        if skill_id in library.budget.known_budget_exceptions:  # 3-49 已知例外：不計預算範圍
            found = [v for v in found if v.rule not in _BUDGET_RANGE_RULES]
        out += found
    return out


def _cost_label(skill: SkillDef) -> str:
    if skill.trigger is not None:
        return f"觸發 {skill.trigger.event}"
    if skill.is_modifier:
        return "修正（被動欄位，不花 AP）"
    return f"AP {skill.ap_cost}"


def _verdict(report: BudgetReport) -> str:
    if report.over_budget:
        return "超出預算"
    return "過弱" if report.too_weak else "合格"


def _print_effects(report: BudgetReport, out: TextIO, *, modifier: bool = False) -> None:
    if modifier:
        print("  規則點數 ＝ 使用次數（× 命中率）× 每次價值 × 規則條件：", file=out)
    else:
        print("  效果點數 ＝ 基礎點數 × 形狀 × 對象 × 效果條件：", file=out)
    for eb in report.effects:
        print(
            f"    {eb.index + 1}. {pad(eb.type, 16)}{pad(eb.note, 20)}"
            f"形狀 {pad(_mult(eb.shape), 7)}對象 {pad(_mult(eb.target), 6)}"
            f"條件 {pad(_mult(eb.condition), 7)}＝ {_num(eb.points)}"
            f"（基礎 {_num(eb.base)}）",
            file=out,
        )
    print(f"  raw ＝ {_num(report.raw)}", file=out)


def _print_segments(report: BudgetReport, out: TextIO) -> None:
    """複合技能（Phase 3F-3a）：兩段各自的效果點數、條件與協同，再加複合加成。"""
    for segment in report.segments:
        print(
            f"  【{segment.label}】骨架 {segment.skeleton}  形狀 {segment.shape}",
            file=out,
        )
        for eb in segment.effects:
            print(
                f"    {eb.index + 1}. {pad(eb.type, 16)}{pad(eb.note, 20)}"
                f"形狀 {pad(_mult(eb.shape), 7)}對象 {pad(_mult(eb.target), 6)}"
                f"條件 {pad(_mult(eb.condition), 7)}＝ {_num(eb.points)}"
                f"（基礎 {_num(eb.base)}）",
                file=out,
            )
        cond = "無" if segment.condition_multiplier == 1 else _mult(segment.condition_multiplier)
        synergies = "、".join(f"{'+'.join(t)} {_mult(c)}" for t, c in segment.synergies) or "無"
        print(
            f"    raw {_num(segment.raw)} × 條件 {cond} × 協同 {synergies}"
            f" ＝ {segment.label}點數 {_num(segment.total)}",
            file=out,
        )
    first, second = report.segments
    tax = report.composite_tax_permille
    second_text = _num(second.total)
    if second.chance_permille != _PERMILLE:  # 有條件的第二段（3F-4a）：× 觸發機率
        what = "延遲折扣" if second.label == "延遲段" else "觸發機率"  # 延遲段（3F-4b）
        second_text = f"{second_text} × {what} {second.chance_permille}‰"
    combo = report.self_combo_permille
    combo_text = f" × (1000 + 連鎖加價 {combo}) ÷ 1000" if combo else ""
    print(
        f"  複合加成 +{tax}‰：（{_num(first.total)} ＋ {second_text}）"
        f"× (1000 + {tax}) ÷ 1000{combo_text} ＝ {_num(report.total)}",
        file=out,
    )
    for reason in report.self_combo_reasons:
        print(f"    連鎖：{reason}", file=out)


def cmd_skills_budget(library: ContentLibrary, skill_id: str, out: TextIO) -> int:
    skill = library.skills.get(skill_id)
    if skill is None:
        raise KeyError(f"找不到技能：{skill_id}")
    return print_skill_budget(library, skill, out)


def print_skill_budget(library: ContentLibrary, skill: SkillDef, out: TextIO) -> int:
    """技能的預算明細與驗證結果；有違規時回傳 1。"""
    print(
        f"{skill.name_zh}（{skill.id}）  階級 T{skill.tier}  稀有度 {_RARITY[skill.rarity]}"
        f"  骨架 {skill.skeleton}  {_cost_label(skill)}",
        file=out,
    )
    violations = validate_skill(skill, library)
    try:
        report = skill_budget(skill, library)
    except BudgetError as exc:
        print(f"  無法計算預算：{exc}", file=out)
    else:
        if report.segments:
            _print_segments(report, out)
        else:
            _print_effects(report, out, modifier=skill.is_modifier)
        _print_totals(report, out)
        _print_variants(library, skill, report, out)
    if violations:
        print(f"  違規（{len(violations)} 項）：", file=out)
        for v in violations:
            print(f"    - ［{v.rule}］{v.message}", file=out)
        return 1
    print("  驗證：通過", file=out)
    return 0


def _print_variants(
    library: ContentLibrary, skill: SkillDef, report: BudgetReport, out: TextIO
) -> None:
    """戰場變奏（Phase 3-25a）：基礎型態的加價，再逐型態列出各自的點數與比例。"""
    if not report.variants:
        return
    print(
        f"  戰場變奏 {len(report.variants)} 個：基礎型態加價 +{report.variant_surcharge_permille}‰"
        f"（已含在 total）",
        file=out,
    )
    for form in report.variants:
        sub = form.report
        variant = skill.variant(form.id)
        when = variant_condition_text(library, variant.when)
        change = variant_change_text(library, skill, variant)
        print(f"  【型態：{form.name_zh}】（{form.id}）{when} → {change}", file=out)
        print(
            f"    total {_num(sub.total)} ÷ 可用預算 {_num(sub.usable)} ＝ {_pct(sub.ratio)}"
            f" → {_verdict(sub)}",
            file=out,
        )


def _print_totals(report: BudgetReport, out: TextIO) -> None:
    cond = "無" if report.condition_multiplier == 1 else _mult(report.condition_multiplier)
    print(f"  技能條件倍率 {cond}", file=out)
    if report.range_value is not None:
        print(
            f"  射程 {report.range_value}：×{float(report.range_coefficient):g}"
            f"（已乘在作用於單位的效果點數上）",
            file=out,
        )
    print(f"  機制標籤 {'、'.join(report.tags) or '（無）'}", file=out)
    if report.synergies:
        parts = "、".join(f"{'+'.join(tags)} {_mult(c)}" for tags, c in report.synergies)
        print(f"  協同係數 {parts}", file=out)
    else:
        print("  協同係數 無", file=out)
    if report.variants:
        print(
            f"  total ＝ raw × 條件 × 協同 × (1000 + 變奏加價 {report.variant_surcharge_permille})"
            f" ÷ 1000 ＝ {_num(report.total)}",
            file=out,
        )
    elif report.segments:
        print(f"  total ＝ 兩段點數加總 × 複合加成 ＝ {_num(report.total)}", file=out)
    else:
        print(f"  total ＝ raw × 條件 × 協同 ＝ {_num(report.total)}", file=out)
    parts = "、".join(f"{label} +{value}‰" for label, value in report.allowance_parts) or "無"
    print(
        f"  可用預算 ＝ tier_budget {report.tier_budget}"
        f" × {report.coefficient_label} {_num(report.ap_coefficient)}"
        f" × (1000 + 折抵 {report.allowance_permille}‰) ÷ 1000"
        + (f" × (1000 + 閃現 {report.bonus_permille}‰) ÷ 1000" if report.bonus_permille else "")
        + f" ＝ {_num(report.usable)}",
        file=out,
    )
    print(f"  代價折抵 {parts}", file=out)
    if report.allowance_capped:
        print(
            f"  代價折抵 +{report.allowance_raw_permille}‰ → 上限 +{report.allowance_cap}‰",
            file=out,
        )
    print(
        f"  比例 ＝ total ÷ 可用預算 ＝ {_pct(report.ratio)}"
        f"（合格區間 {_pct(report.min_ratio)}–{_pct(report.max_ratio)}）→ {_verdict(report)}",
        file=out,
    )


def _row_cells(report: BudgetReport | None) -> tuple[str, str, str, str]:
    """總表一列的 total、可用預算、比例與折抵；算不出預算時都是「—」。"""
    if report is None:
        return ("—", "—", "—", "—")
    allow = f"+{report.allowance_permille}"
    if report.allowance_capped:
        allow = f"+{report.allowance_raw_permille}→{report.allowance_cap}"
    return (_num(report.total), _num(report.usable), _pct(report.ratio), allow)


def cmd_skills_budget_all(library: ContentLibrary, out: TextIO) -> int:
    skills = sorted(library.skills.values(), key=lambda s: s.id)
    print(f"技能預算總表（共 {len(skills)} 個；合格區間以 total ÷ 可用預算計）：", file=out)
    print(
        f"  {pad('ID', 26)}{pad('名稱', 12)}{pad('T', 3)}{pad('AP', 4)}{pad('total', 8)}"
        f"{pad('可用', 8)}{pad('折抵‰', 11)}{pad('比例', 8)}違規",
        file=out,
    )
    bad = known = 0
    for skill in skills:
        violations = validate_skill(skill, library)
        is_known = skill.id in library.budget.known_budget_exceptions
        if is_known and all(v.rule in _BUDGET_RANGE_RULES for v in violations):
            known += bool(violations)  # 3-49 已知例外：只有預算範圍違規，另計
        else:
            bad += bool(violations)
        try:
            report: BudgetReport | None = skill_budget(skill, library)
        except BudgetError:
            report = None
        cells = _row_cells(report)
        rules = "、".join(v.rule for v in violations) or "—"
        if is_known and violations:
            rules += "（已知例外）"
        print(
            f"  {pad(skill.id, 26)}{pad(skill.name_zh, 12)}{pad(str(skill.tier), 3)}"
            f"{pad(_AP_LABEL.get(skill.kind) or str(skill.ap_cost), 4)}"
            f"{pad(cells[0], 8)}{pad(cells[1], 8)}"
            f"{pad(cells[3], 11)}{pad(cells[2], 8)}{rules}",
            file=out,
        )
        for form in report.variants if report is not None else ():  # 戰場變奏（3-25a）逐型態
            sub = _row_cells(form.report)
            print(
                f"  {pad('  └ ' + form.id, 26)}{pad(form.name_zh, 12)}{pad('', 7)}"
                f"{pad(sub[0], 8)}{pad(sub[1], 8)}{pad(sub[3], 11)}{pad(sub[2], 8)}",
                file=out,
            )
    tail = f"，已知例外 {known} 個（射程係數，見 Phase3-49報告）" if known else ""
    print(f"通過 {len(skills) - bad - known} 個，違規 {bad} 個{tail}。", file=out)
    return 1 if bad else 0
