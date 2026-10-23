"""技能工坊：檢查完整或部分的技能（Phase 3F-1）。

:func:`check_draft` 回傳是否合法、違反的規則（中文；骨架限制、互斥規則、稀有度、預算……沿用
:func:`~trpg.skillgen.validate.validate_skill` 的規則代碼與訊息）、預算明細（與 ``trpg skills
budget`` 同一份 :func:`~trpg.skillgen.budget.skill_budget`）與最低稀有度。

部分技能（還有步驟沒完成）只回報「缺哪些步驟」與已填內容的問題（:func:`draft_options` 的
``problems``），不算預算。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from pydantic import BaseModel, ConfigDict

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import (
    BudgetError,
    BudgetReport,
    EffectBudget,
    SegmentBudget,
    VariantBudget,
    skill_budget,
)
from trpg.skillgen.draft import Draft, DraftError, build_skill
from trpg.skillgen.option_followup import followup_visible
from trpg.skillgen.option_models import STEP_IDS, StepId
from trpg.skillgen.option_variant import variants_visible
from trpg.skillgen.options import draft_options, minimum_rarity
from trpg.skillgen.player_text import plain_name, plainify
from trpg.skillgen.validate import validate_skill

__all__ = [
    "BudgetLine",
    "BudgetSummary",
    "DraftCheck",
    "Problem",
    "SegmentLine",
    "budget_summary",
    "check_draft",
]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Problem(_Model):
    """一項問題：``rule`` 規則代碼（``skeleton.shape``、``exclusion.<id>``、``rarity.*``、
    ``budget.*``、``schema``、``draft``……），``message_zh`` 中文說明。"""

    rule: str
    message_zh: str


class BudgetLine(_Model):
    """一個效果（或修正規則）的點數：基礎點數 × 形狀 × 對象 × 條件。"""

    index: int
    type: str
    note: str
    base: float
    shape: float
    target: float
    condition: float
    points: float
    range: float = 1.0
    """射程係數（Phase 3-49）；``points`` 已乘上它。"""


class SegmentLine(_Model):
    """複合技能（Phase 3F-3a）一段的預算：``label`` 位移段／動作段，該段自己的效果點數、條件
    與協同。"""

    label: str
    skeleton: str
    shape: str
    lines: tuple[BudgetLine, ...]
    raw: float
    condition_multiplier: float
    synergies: tuple[str, ...]
    total: float
    chance_permille: int = 1000
    """有條件的第二段（擊殺後、命中後，Phase 3F-4a）的觸發機率（‰）；其他段為 1000。"""
    range_text: str = ""
    """這一段的射程係數說明（例 ``射程 6：×1.1``）；沒有固定射程時為空字串。"""


class VariantLine(_Model):
    """戰場變奏（Phase 3-25b）一個型態的預算：與基礎型態各自落在預算窗內。"""

    id: str
    name_zh: str
    total: float
    usable: float
    ratio: float
    ratio_text: str
    verdict: str
    verdict_zh: str
    range_text: str = ""
    """射程係數說明（Phase 3-49，例 ``射程 5：×1.05``）；沒有固定射程時為空字串。"""


class BudgetSummary(_Model):
    """預算（與 ``trpg skills budget`` 的數字相同；``ratio_text`` 也是同樣的格式，
    例 ``85.3%``）。"""

    lines: tuple[BudgetLine, ...]
    raw: float
    condition_multiplier: float
    synergies: tuple[str, ...]
    total: float
    tier_budget: int
    coefficient_label: str
    coefficient: float
    allowance_permille: int
    allowance_parts: tuple[str, ...]
    usable: float
    ratio: float
    ratio_text: str
    min_ratio: float
    max_ratio: float
    verdict: str
    """``ok``（合格）、``weak``（過弱）、``over``（超出預算）。"""
    verdict_zh: str
    segments: tuple[SegmentLine, ...] = ()
    """複合技能：兩段各自的明細（``total`` ＝ 兩段加總 ×（1000 ＋ ``composite_tax_permille``）
    ÷ 1000）；一般技能為空。"""
    composite_tax_permille: int = 0
    self_combo_permille: int = 0
    """兩段之間有元素／表面連鎖時的加價（‰，Phase 3F-4a）；沒有時為 0。"""
    self_combo_reasons: tuple[str, ...] = ()
    variants: tuple[VariantLine, ...] = ()
    """戰場變奏（Phase 3-25b）：每個型態自己的預算；沒有變奏為空。"""
    variant_surcharge_permille: int = 0
    """基礎型態因變奏多算的比例（‰，已含在 ``total``）。"""
    range_text: str = ""
    """射程係數說明（Phase 3-49，例 ``射程 6：×1.1``，已乘在作用於單位的效果點數上）；
    沒有固定射程（武器射程、自身、光環等）時為空字串。"""
    range_coefficient: float = 1.0


class DraftCheck(_Model):
    complete: bool
    missing_steps: tuple[StepId, ...]
    """還沒完成的步驟（依序）。"""
    legal: bool
    """技能完整且沒有任何問題。"""
    problems: tuple[Problem, ...]
    budget: BudgetSummary | None
    minimum_rarity: str | None
    rarity_reasons: tuple[str, ...]
    skill: dict[str, Any] | None
    """完整且通過 schema 時：正規化後的技能定義（JSON；含補上的 ``id``）。"""


def _f(value: Fraction) -> float:
    return round(float(value), 4)


def _verdict(report: BudgetReport) -> tuple[str, str]:
    if report.over_budget:
        return "over", "超出預算"
    if report.too_weak:
        return "weak", "過弱"
    return "ok", "合格"


def _zh(text: str, library: ContentLibrary | None, *, name: bool = False) -> str:
    """玩家看的文字換成中文（3-48）；沒有內容庫（CLI 等）時原樣。"""
    if library is None:
        return text
    return plain_name(text, library) if name else plainify(text, library)


def _line(e: EffectBudget, library: ContentLibrary | None = None) -> BudgetLine:
    return BudgetLine(
        index=e.index,
        type=_zh(e.type, library, name=True),
        note=_zh(e.note, library),
        base=_f(e.base),
        shape=_f(e.shape),
        target=_f(e.target),
        condition=_f(e.condition),
        points=_f(e.points),
        range=_f(e.range),
    )


def range_text(value: int | None, coefficient: Fraction) -> str:
    """預算明細的射程一行（玩家文字，不含英文）：固定射程才有，例 ``射程 6：×1.1``。"""
    return "" if value is None else f"射程 {value}：×{float(coefficient):g}"


def _synergy_text(
    synergies: tuple[tuple[tuple[str, ...], Fraction], ...], library: ContentLibrary | None = None
) -> tuple[str, ...]:
    return tuple(
        f"{'+'.join(_zh(t, library, name=True) for t in tags)} ×{float(c):g}"
        for tags, c in synergies
    )


def _segment_line(segment: SegmentBudget, library: ContentLibrary | None = None) -> SegmentLine:
    return SegmentLine(
        label=segment.label,
        skeleton=_zh(segment.skeleton, library, name=True),
        shape=_zh(segment.shape, library, name=True),
        lines=tuple(_line(e, library) for e in segment.effects),
        raw=_f(segment.raw),
        condition_multiplier=_f(segment.condition_multiplier),
        synergies=_synergy_text(segment.synergies, library),
        total=_f(segment.total),
        chance_permille=segment.chance_permille,
        range_text=range_text(segment.range_value, segment.range_coefficient),
    )


def _variant_line(v: VariantBudget) -> VariantLine:
    verdict, verdict_zh = _verdict(v.report)
    return VariantLine(
        id=v.id,
        name_zh=v.name_zh,
        total=_f(v.report.total),
        usable=_f(v.report.usable),
        ratio=_f(v.report.ratio),
        ratio_text=f"{float(v.report.ratio) * 100:.1f}%",
        verdict=verdict,
        verdict_zh=verdict_zh,
        range_text=range_text(v.report.range_value, v.report.range_coefficient),
    )


def budget_summary(report: BudgetReport, library: ContentLibrary | None = None) -> BudgetSummary:
    verdict, verdict_zh = _verdict(report)
    return BudgetSummary(
        lines=tuple(_line(e, library) for e in report.effects),
        raw=_f(report.raw),
        condition_multiplier=_f(report.condition_multiplier),
        synergies=_synergy_text(report.synergies, library),
        total=_f(report.total),
        tier_budget=report.tier_budget,
        coefficient_label=report.coefficient_label,
        coefficient=_f(report.ap_coefficient),
        allowance_permille=report.allowance_permille,
        allowance_parts=tuple(f"{label} +{value}‰" for label, value in report.allowance_parts),
        usable=_f(report.usable),
        ratio=_f(report.ratio),
        ratio_text=f"{float(report.ratio) * 100:.1f}%",
        min_ratio=_f(report.min_ratio),
        max_ratio=_f(report.max_ratio),
        verdict=verdict,
        verdict_zh=verdict_zh,
        segments=tuple(_segment_line(s, library) for s in report.segments),
        composite_tax_permille=report.composite_tax_permille,
        self_combo_permille=report.self_combo_permille,
        self_combo_reasons=tuple(_zh(r, library) for r in report.self_combo_reasons),
        variants=tuple(_variant_line(v) for v in report.variants),
        variant_surcharge_permille=report.variant_surcharge_permille,
        range_text=range_text(report.range_value, report.range_coefficient),
        range_coefficient=_f(report.range_coefficient),
    )


def _complete_check(skill: SkillDef, library: ContentLibrary) -> DraftCheck:
    problems = tuple(
        Problem(rule=v.rule, message_zh=plainify(v.message, library))
        for v in validate_skill(skill, library)
    )
    try:
        budget: BudgetSummary | None = budget_summary(skill_budget(skill, library), library)
    except BudgetError:
        budget = None
    floor = minimum_rarity(skill, library)
    return DraftCheck(
        complete=True,
        missing_steps=(),
        legal=not problems,
        problems=problems,
        budget=budget,
        minimum_rarity=floor.minimum,
        rarity_reasons=tuple(plainify(r, library) for r in floor.reasons),
        skill=skill.model_dump(mode="json", exclude_none=True),
    )


def check_draft(draft: Draft, library: ContentLibrary) -> DraftCheck:
    """檢查草稿（純函式）。"""
    options = draft_options(draft, library)
    if options.next_step is not None:
        missing = tuple(
            s
            for s in STEP_IDS[STEP_IDS.index(options.next_step) :]
            if (s != "followup" or followup_visible(draft))
            and (s != "variants" or variants_visible(draft, library))
        )
        problems = tuple(Problem(rule="draft", message_zh=p) for p in options.problems)
        return DraftCheck(
            complete=False,
            missing_steps=missing,
            legal=False,
            problems=problems,
            budget=None,
            minimum_rarity=None,
            rarity_reasons=(),
            skill=None,
        )
    try:
        skill = build_skill(draft)
    except DraftError as exc:
        problems = tuple(
            Problem(rule="schema", message_zh=plainify(m, library)) for m in exc.messages
        )
        extra = tuple(Problem(rule="draft", message_zh=p) for p in options.problems)
        return DraftCheck(
            complete=True,
            missing_steps=(),
            legal=False,
            problems=extra + problems,
            budget=None,
            minimum_rarity=None,
            rarity_reasons=(),
            skill=None,
        )
    return _complete_check(skill, library)
