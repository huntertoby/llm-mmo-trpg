"""Phase 3-48c：工坊試玩回饋第二批（稀有度步驟錯誤、法術技選項、最低花費、刻印）。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import STRIKE
from trpg.skillgen.option_models import FieldSpec, StepOptions
from trpg.skillgen.options import draft_options

LIB = library()


def _strike_draft() -> dict[str, Any]:
    draft: dict[str, Any] = {}
    for _step, picks in STRIKE[:-1]:
        draft.update(picks)
    return draft


def _step(draft: dict[str, Any], step_id: str) -> StepOptions:
    return next(s for s in draft_options(draft, LIB).steps if s.id == step_id)


def _field(step: StepOptions, name: str) -> FieldSpec:
    return next(f for f in step.fields if f.field == name)


def test_rarity_step_lists_the_plain_error_and_the_step_to_go_back_to() -> None:
    # 第二縮放屬性和主屬性相同：稀有度推導不出來，步驟要列出白話原因與「回到第 N 步修改」
    draft = {**_strike_draft(), "secondary_scaling_attr": "str"}
    notes = _step(draft, "rarity").notes_zh
    assert any("無法推導稀有度" in n for n in notes)
    assert not any("problems" in n or "見檢查結果" in n for n in notes)
    assert any(n.startswith("．") and "回到第" in n for n in notes)
    assert not any("secondary_scaling_attr" in n for n in notes)


def test_stale_weapon_requirement_is_reported_and_the_step_is_not_ticked() -> None:
    draft = {**_strike_draft(), "category": "spell"}  # 武器技換成法術技，武器需求還是近戰
    options = draft_options(draft, LIB)
    basics = next(s for s in options.steps if s.id == "basics")
    assert not basics.complete
    assert options.problems


def test_spell_shape_range_has_no_weapon_range_option() -> None:
    spell = {**_strike_draft(), "category": "spell", "weapon_req": "focus", "scaling_attr": "int"}
    weapon = _strike_draft()
    for draft, expected in ((spell, False), (weapon, True)):
        shape = _field(_step(draft, "shape"), "shape")
        single = next(c for c in shape.choices if c.value == "single")
        assert any(p.allow_weapon for p in single.params) is expected
