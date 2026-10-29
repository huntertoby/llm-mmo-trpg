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

from trpg.content.library import ContentLibrary, load_library
from trpg.content.modifier_changes import MODIFIER_CHANGES_FILE, ModifierChangeDef
from trpg.content.skills import PrimitiveDef
from trpg.engine.ai.coverage import PRIMITIVE_VALUATION
from trpg.engine.modifiers import CHANGE_HANDLERS
from trpg.engine.preview import PRIMITIVE_PREVIEW
from trpg.engine.skills.primitives import PRIMITIVE_HANDLERS
from trpg.narrative.skills import DESCRIBED_CHANGES, DESCRIBED_PRIMITIVES
from trpg.shared.errors import ContentError
from trpg.skillgen.budget import BUDGET_BASES, STRUCTURED_CHANGES

__all__ = [
    "change_coverage_problems",
    "check_primitive_coverage",
    "coverage_problems",
    "load_checked_library",
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


def check_primitive_coverage(library: ContentLibrary) -> None:
    """檢查 ``library`` 的每個原語都有五處對應項、每種修正規則改變都有引擎、卡片文字與預算的對應項；
    有缺時拋出 :class:`ContentError`（列出全部）。"""
    problems = coverage_problems(library.ruleset.primitives.primitives)
    if problems:
        lines = "\n".join(f"  - {p}" for p in problems)
        raise ContentError(library.root / PRIMITIVES_FILE, f"原語的對應項不完整：\n{lines}")
    problems = change_coverage_problems(library.modifier_changes.changes)
    if problems:
        lines = "\n".join(f"  - {p}" for p in problems)
        raise ContentError(
            library.root / MODIFIER_CHANGES_FILE, f"修正規則改變的對應項不完整：\n{lines}"
        )


def load_checked_library(content_dir: Path | None = None) -> ContentLibrary:
    """:func:`~trpg.content.library.load_library` 之後再做原語的對應檢查。"""
    library = load_library(content_dir)
    check_primitive_coverage(library)
    return library
