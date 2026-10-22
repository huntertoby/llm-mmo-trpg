"""效果原語的對應檢查（Phase 3E-2b）：解譯器、預算、AI 估值、敘事、預覽。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trpg.content.library import load_library
from trpg.content.skills import PrimitiveDef
from trpg.engine.ai.coverage import PRIMITIVE_VALUATION
from trpg.engine.preview import PRIMITIVE_PREVIEW
from trpg.engine.skills.primitives import PRIMITIVE_HANDLERS, primitive_handler
from trpg.narrative.skills import DESCRIBED_PRIMITIVES
from trpg.primitive_coverage import (
    check_primitive_coverage,
    coverage_problems,
    load_checked_library,
)
from trpg.shared.errors import ContentError

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_FROST_NOVA = """
  - id: frost_nova
    name_zh: 霜爆
    description_zh: 測試用的新原語（沒有任何對應項）。
    category: numeric
    harmful: true
    budget_basis: fixed
    base_points: 3
"""


def _fake(primitive_id: str, basis: str | None = "fixed") -> PrimitiveDef:
    return PrimitiveDef.model_validate(
        {
            "id": primitive_id,
            "name_zh": "測試",
            "description_zh": "測試",
            "category": "numeric",
            "harmful": True,
            "budget_basis": basis,
            "base_points": 1,
        }
    )


def test_real_content_is_fully_covered() -> None:
    library = load_library()
    check_primitive_coverage(library)  # 不拋出
    ids = set(library.ruleset.primitives.by_id())
    # 對應表與 YAML 完全一致（沒有漏掉，也沒有過時的多餘項）
    assert set(PRIMITIVE_HANDLERS) == ids
    assert set(PRIMITIVE_VALUATION) == ids
    assert set(PRIMITIVE_PREVIEW) == ids
    assert ids == DESCRIBED_PRIMITIVES


def test_new_primitive_without_entries_lists_every_missing_place() -> None:
    library = load_library()
    primitives = (*library.ruleset.primitives.primitives, _fake("frost_nova"))
    problems = coverage_problems(primitives)
    assert problems == [
        "原語 frost_nova 沒有解譯器的對應項（請補 trpg.engine.skills.primitives 的 HANDLERS）",
        "原語 frost_nova 沒有AI 估值的對應項（請補 trpg.engine.ai.coverage.PRIMITIVE_VALUATION）",
        "原語 frost_nova 沒有敘事的對應項（請補 trpg.narrative.skills 的 _EFFECT_TEXT）",
        "原語 frost_nova 沒有預覽的對應項（請補 trpg.engine.preview.PRIMITIVE_PREVIEW）",
    ]


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        (None, "原語 frost_nova 沒有預算算法（budget_basis）"),
        ("fixed", None),
    ],
)
def test_budget_basis_must_be_implemented(basis: str | None, expected: str | None) -> None:
    problems = coverage_problems([_fake("frost_nova", basis)], tables=())
    assert problems == ([] if expected is None else [expected])


def test_unimplemented_budget_basis_is_reported() -> None:
    problems = coverage_problems([_fake("frost_nova")], tables=(), budget_bases=frozenset())
    assert problems == ["原語 frost_nova 的預算算法 fixed 沒有實作（請補 trpg.skillgen.budget）"]


def test_extra_table_entries_are_not_problems() -> None:
    """測試或模組用的內容資料夾刪掉某個原語時，對應表多出的項不算錯。"""
    assert coverage_problems([_fake("heal")], tables=(("解譯器", "x", {"heal", "damage"}),)) == []


def test_load_checked_library_raises_content_error(tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", content)
    yaml_path = content / "skill_primitives.yaml"
    yaml_path.write_text(yaml_path.read_text(encoding="utf-8") + _FROST_NOVA, encoding="utf-8")
    load_library(content)  # 內容本身合法
    with pytest.raises(ContentError) as caught:
        load_checked_library(content)
    assert caught.value.path == yaml_path
    assert "原語 frost_nova 沒有解譯器的對應項" in caught.value.reason


def test_interpreter_has_no_default_branch() -> None:
    """登錄表沒有的原語不會靜默略過（舊的 ``tile_effect`` 沒有 else）。"""
    with pytest.raises(KeyError, match="frost_nova"):
        primitive_handler("frost_nova")
