"""效果原語的對應檢查（Phase 3E-2b）：``content/skill_primitives.yaml`` 的每個原語在解譯器、預算、
AI 估值、敘事、預覽都有對應項，缺了就拋出 :class:`ContentError`。

這五處分屬不同層（``engine``、``skillgen``、``narrative``），而 ``trpg.content`` 不能往上匯入，
所以檢查放在套件頂層，由載入內容的入口呼叫：CLI（:func:`load_checked_library`）、API 的
``create_app``，以及測試 ``tests/test_primitive_coverage.py``。

對應項：

- 解譯器：:data:`trpg.engine.skills.primitives.PRIMITIVE_HANDLERS`（原語 → handler）。
- 預算：原語的 ``budget_basis`` 在 :data:`trpg.skillgen.budget.BUDGET_BASES` 裡（有點數算法）。
- AI 估值：:data:`trpg.engine.ai.coverage.PRIMITIVE_VALUATION`（宣告表）。
- 敘事：:data:`trpg.narrative.skills.DESCRIBED_PRIMITIVES`（效果敘述）。
- 預覽：:data:`trpg.engine.preview.PRIMITIVE_PREVIEW`（宣告表）。
- 強度旋鈕（Phase 3T-1）：``budget_basis`` 不是 ``fixed`` 的原語，每個 ``int``／``dice`` 參數都要
  宣告 ``knob``（或明寫 ``knob: none``）；階梯來源要在
  :data:`trpg.skillgen.composer_parts.KNOB_LADDERS`。

修正規則的改變種類（``content/modifier_changes.yaml``，Phase 3T-1）也在這裡檢查：

- 引擎：:data:`trpg.engine.modifiers.CHANGE_HANDLERS`（改變 → 套用的查詢函式）。
- 卡片文字：:data:`trpg.narrative.skills.DESCRIBED_CHANGES`。
- 預算：``budget.unit: structured`` 的種類要在 :data:`trpg.skillgen.budget.STRUCTURED_CHANGES`；
  其他種類的 ``points`` 鍵與 ``ModifierChange`` 的欄位由
  :func:`~trpg.content.library.load_library` 檢查。
- 玩家文字：YAML 的 ``name_zh``（必填，schema 保證）。
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from trpg.content.forms import FormEffects, FormEntry
from trpg.content.library import ContentLibrary, load_library
from trpg.content.modifier_changes import MODIFIER_CHANGES_FILE, ModifierChangeDef
from trpg.content.races import RACE_EFFECT_SPECS
from trpg.content.skills import PrimitiveDef
from trpg.engine.ai.coverage import PRIMITIVE_VALUATION
from trpg.engine.ai.race import RACE_EFFECT_SCORERS, RIDER_ONLY_EFFECTS
from trpg.engine.forms import FORM_EFFECT_CONSUMERS, FORM_ENTRY_CONSUMERS
from trpg.engine.modifiers import CHANGE_HANDLERS
from trpg.engine.preview import PRIMITIVE_PREVIEW
from trpg.engine.race.skills import (
    RACE_EFFECT_EXECUTORS,
    RACE_EFFECT_PROBLEMS,
    UNCONDITIONAL_RACE_EFFECTS,
)
from trpg.engine.skills.primitives import PRIMITIVE_HANDLERS
from trpg.narrative.skills import DESCRIBED_CHANGES, DESCRIBED_PRIMITIVES
from trpg.shared.errors import ContentError
from trpg.skillgen.budget import BUDGET_BASES, STRUCTURED_CHANGES
from trpg.skillgen.composer_parts import KNOB_LADDERS

__all__ = [
    "change_coverage_problems",
    "check_primitive_coverage",
    "coverage_problems",
    "form_coverage_problems",
    "knob_problems",
    "load_checked_library",
    "race_coverage_problems",
    "race_lead_problems",
]

PRIMITIVES_FILE = "skill_primitives.yaml"

_TABLES: tuple[tuple[str, str, Collection[str]], ...] = (
    ("解譯器", "trpg.engine.skills.primitives 的 HANDLERS", PRIMITIVE_HANDLERS.keys()),
    ("AI 估值", "trpg.engine.ai.coverage.PRIMITIVE_VALUATION", PRIMITIVE_VALUATION.keys()),
    ("敘事", "trpg.narrative.skills 的 _EFFECT_TEXT", DESCRIBED_PRIMITIVES),
    ("預覽", "trpg.engine.preview.PRIMITIVE_PREVIEW", PRIMITIVE_PREVIEW.keys()),
)
"""（名稱, 要補的地方, 有對應項的原語 ID）。"""

_CHANGE_TABLES: tuple[tuple[str, str, Collection[str]], ...] = (
    ("引擎", "trpg.engine.modifiers.CHANGE_HANDLERS", CHANGE_HANDLERS.keys()),
    ("卡片文字", "trpg.narrative.skills.DESCRIBED_CHANGES", DESCRIBED_CHANGES),
)
"""（名稱, 要補的地方, 有對應項的修正規則改變種類）。"""


def coverage_problems(
    primitives: Collection[PrimitiveDef],
    tables: tuple[tuple[str, str, Collection[str]], ...] = _TABLES,
    budget_bases: Collection[str] = BUDGET_BASES,
) -> list[str]:
    """每個原語缺少的對應項（中文，依對應處、原語 ID 排序）；沒有問題時為空列表。對應表多出 YAML
    沒有的原語不算問題（例如測試或模組用的內容資料夾刪掉了某些原語）。``tables``、
    ``budget_bases`` 給測試替換用。"""
    ids = sorted(p.id for p in primitives)
    problems: list[str] = []
    for name, where, covered in tables:
        have = set(covered)
        problems += [f"原語 {i} 沒有{name}的對應項（請補 {where}）" for i in ids if i not in have]
    for primitive in sorted(primitives, key=lambda p: p.id):
        basis = primitive.budget_basis
        if basis is None:
            problems.append(f"原語 {primitive.id} 沒有預算算法（budget_basis）")
        elif basis not in budget_bases:
            problems.append(
                f"原語 {primitive.id} 的預算算法 {basis} 沒有實作（請補 trpg.skillgen.budget）"
            )
    return problems


_KNOBBED_TYPES = frozenset({"int", "dice"})
"""必須宣告旋鈕的參數型別（``budget_basis`` 不是 ``fixed`` 的原語）。"""


def knob_problems(
    primitives: Collection[PrimitiveDef], ladders: Collection[str] = KNOB_LADDERS.keys()
) -> list[str]:
    """強度旋鈕的宣告（Phase 3T-1）：``budget_basis`` 不是 ``fixed`` 的原語，每個 ``int``／``dice``
    參數都要寫 ``knob``（沒有旋鈕寫 ``knob: none``），階梯來源要有實作。中文、依原語與參數排序。"""
    have = set(ladders)
    problems: list[str] = []
    for primitive in sorted(primitives, key=lambda p: p.id):
        for name in sorted(primitive.params):
            param = primitive.params[name]
            needs = primitive.budget_basis != "fixed" and param.type in _KNOBBED_TYPES
            if needs and param.knob is None:
                problems.append(
                    f"原語 {primitive.id} 的參數 {name} 沒有宣告強度旋鈕"
                    "（請在 skill_primitives.yaml 補 knob；沒有旋鈕請寫 knob: none）"
                )
            problems += [
                f"原語 {primitive.id} 的參數 {name} 的旋鈕階梯 {k.ladder} 沒有實作"
                "（請補 trpg.skillgen.composer_parts.KNOB_LADDERS）"
                for k in param.knobs()
                if k.ladder not in have
            ]
    return problems


def change_coverage_problems(
    changes: Collection[ModifierChangeDef],
    tables: tuple[tuple[str, str, Collection[str]], ...] = _CHANGE_TABLES,
    structured: Collection[str] = STRUCTURED_CHANGES.keys(),
) -> list[str]:
    """每種修正規則改變缺少的對應項（中文，依對應處、種類排序）；沒有問題時為空列表。對應表多出
    YAML 沒有的種類不算問題。``tables``、``structured`` 給測試替換用。"""
    ids = sorted(c.id for c in changes)
    problems: list[str] = []
    for name, where, covered in tables:
        have = set(covered)
        problems += [
            f"修正規則改變 {i} 沒有{name}的對應項（請補 {where}）" for i in ids if i not in have
        ]
    have_structured = set(structured)
    problems += [
        f"修正規則改變 {c.id} 的預算算法 structured 沒有實作"
        "（請補 trpg.skillgen.budget.STRUCTURED_CHANGES）"
        for c in sorted(changes, key=lambda c: c.id)
        if c.budget.unit == "structured" and c.id not in have_structured
    ]
    return problems


def race_coverage_problems(
    *,
    effect_types: Collection[str] = RACE_EFFECT_SPECS.keys(),
    executors: Collection[str] = RACE_EFFECT_EXECUTORS.keys(),
    problems_table: Collection[str] = RACE_EFFECT_PROBLEMS.keys(),
    unconditional: Collection[str] = UNCONDITIONAL_RACE_EFFECTS,
    scorers: Collection[str] = RACE_EFFECT_SCORERS.keys(),
    riders: Collection[str] = RIDER_ONLY_EFFECTS,
) -> list[str]:
    """每種種族技效果缺少的對應項（中文，依種類排序）：結算（executor）、合法性檢查（或明確宣告
    無條件）、AI 計分函式（或明確宣告只作附帶效果）。參數給測試替換用。"""
    problems: list[str] = []
    for kind in sorted(effect_types):
        if kind not in executors:
            problems.append(f"種族技效果 {kind} 沒有結算（請補 race.skills.RACE_EFFECT_EXECUTORS）")
        if kind not in problems_table and kind not in unconditional:
            problems.append(
                f"種族技效果 {kind} 沒有合法性檢查"
                "（請補 race.skills.RACE_EFFECT_PROBLEMS，或列入 UNCONDITIONAL_RACE_EFFECTS）"
            )
        if kind not in scorers and kind not in riders:
            problems.append(
                f"種族技效果 {kind} 沒有 AI 計分函式"
                "（請補 ai.race.RACE_EFFECT_SCORERS，或列入 RIDER_ONLY_EFFECTS）"
            )
    return problems


def race_lead_problems(
    leads: Collection[tuple[str, str]], riders: Collection[str] = RIDER_ONLY_EFFECTS
) -> list[str]:
    """種族技（``(種族技 ID, 第一個效果類型)``）以只能作附帶效果的類型開頭時，AI 永遠不會用它。"""
    return [
        f"種族技 {skill_id} 以附帶效果 {kind} 開頭（AI 只看第一個效果，永遠不會使用）"
        for skill_id, kind in sorted(leads)
        if kind in riders
    ]


def form_coverage_problems(
    *,
    effect_fields: Collection[str] = FormEffects.model_fields.keys(),
    entry_fields: Collection[str] = FormEntry.model_fields.keys(),
    effect_consumers: Collection[str] = FORM_EFFECT_CONSUMERS.keys(),
    entry_consumers: Collection[str] = FORM_ENTRY_CONSUMERS.keys(),
) -> list[str]:
    """形態的效果欄位（``FormEffects``）與進入獎勵欄位（``FormEntry``）缺少的引擎對應項。"""
    problems = [
        f"形態效果欄位 {name} 沒有引擎處理（請補 engine.forms.FORM_EFFECT_CONSUMERS）"
        for name in sorted(effect_fields)
        if name not in effect_consumers
    ]
    problems += [
        f"形態進入獎勵欄位 {name} 沒有引擎處理（請補 engine.forms.FORM_ENTRY_CONSUMERS）"
        for name in sorted(entry_fields)
        if name not in entry_consumers
    ]
    return problems


def check_primitive_coverage(library: ContentLibrary) -> None:
    """檢查 ``library`` 的每個原語都有五處對應項與強度旋鈕的宣告、每種修正規則改變都有引擎、
    卡片文字與預算的對應項；
    有缺時拋出 :class:`ContentError`（列出全部）。"""
    primitives = library.ruleset.primitives.primitives
    problems = coverage_problems(primitives) + knob_problems(primitives)
    if problems:
        lines = "\n".join(f"  - {p}" for p in problems)
        raise ContentError(library.root / PRIMITIVES_FILE, f"原語的對應項不完整：\n{lines}")
    problems = change_coverage_problems(library.modifier_changes.changes)
    if problems:
        lines = "\n".join(f"  - {p}" for p in problems)
        raise ContentError(
            library.root / MODIFIER_CHANGES_FILE, f"修正規則改變的對應項不完整：\n{lines}"
        )
    race_table = library.ruleset.races
    races = () if race_table is None else race_table.races
    leads = [(r.skill.id, r.skill.effects[0].type) for r in races]
    problems = race_coverage_problems() + race_lead_problems(leads) + form_coverage_problems()
    if problems:
        lines = "\n".join(f"  - {p}" for p in problems)
        raise ContentError(library.root / "races.yaml", f"種族技與形態的對應項不完整：\n{lines}")


def load_checked_library(content_dir: Path | None = None) -> ContentLibrary:
    """:func:`~trpg.content.library.load_library` 之後再做原語的對應檢查。"""
    library = load_library(content_dir)
    check_primitive_coverage(library)
    return library
