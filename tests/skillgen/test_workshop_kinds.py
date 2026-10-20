"""Phase 3F-4b：技能工坊能組出六種複合技能（``docs/phases/Phase3F計畫.md`` 4.2）。

「第二段」步驟：``followup.when`` 只列第一段能接的種類 → 延遲段多一個 ``followup.release`` →
骨架、形狀（依種類限制）→ 效果（依種類限制）與條件。六個示範技能的草稿一步步走都在選項之內、
檢查合法，且與內容庫的預算相同。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.skills import COMPOSITE_MOVES, DELAYED_SHAPES, FOLLOWUP_CENTERED
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_conform import field_problems
from trpg.skillgen.option_models import DraftOptions, StepOptions
from trpg.skillgen.options import draft_options

DEMOS = {
    "skill_shadow_whirl": "after_move",
    "skill_retreating_slash": "after_action",
    "skill_gravity_burst": "after_gather",
    "skill_death_spiral": "on_kill",
    "skill_armor_break_combo": "on_hit",
    "skill_charged_cleave": "delayed",
    "skill_parry_riposte": "delayed",
}


def _step(options: DraftOptions, step_id: str) -> StepOptions:
    return next(s for s in options.steps if s.id == step_id)


def _draft(skill_id: str) -> dict[str, Any]:
    data = library().skills[skill_id].model_dump(mode="json", exclude_none=True)
    return {k: v for k, v in data.items() if k not in ("id", "provenance", "narrative")}


def _field(step: StepOptions, field: str) -> Any:
    return next(f for f in step.fields if f.field == field)


@pytest.mark.parametrize("skill_id", sorted(DEMOS))
def test_each_kind_walks_through_the_options_to_a_legal_skill(skill_id: str) -> None:
    lib = library()
    draft = _draft(skill_id)
    follow = draft.pop("followup")
    # 還沒接第二段：種類清單有這一種
    step = _step(draft_options(draft, lib), "followup")
    assert DEMOS[skill_id] in {c.value for c in _field(step, "followup.when").choices}
    # 一步步加回第二段的欄位：每一步都在選項之內
    draft["followup"] = {"when": follow["when"]}
    for key in ("release", "skeleton", "shape", "effects", "condition"):
        if key in follow:
            draft["followup"][key] = follow[key]
        options = draft_options(draft, lib)
        assert options.problems == (), (skill_id, key, options.problems)
        assert field_problems(_step(options, "followup").fields, draft) == [], (skill_id, key)
    options = draft_options(draft, lib)
    assert options.next_step is None and _step(options, "followup").complete
    check = check_draft(draft, lib)
    assert check.complete and check.legal, [p.message_zh for p in check.problems]
    shipped = check_draft(_draft(skill_id), lib)
    assert check.budget is not None and shipped.budget is not None
    assert check.budget.total == shipped.budget.total


def test_kinds_follow_the_first_part() -> None:
    lib = library()
    strike = _draft("skill_death_spiral")
    strike.pop("followup")
    kinds = {
        c.value
        for c in _field(_step(draft_options(strike, lib), "followup"), "followup.when").choices
    }
    assert kinds == {"after_action", "on_kill", "on_hit", "delayed"}  # 有傷害、沒有位移
    shield = _draft("skill_charged_cleave")
    shield.pop("followup")
    kinds = {
        c.value
        for c in _field(_step(draft_options(shield, lib), "followup"), "followup.when").choices
    }
    assert kinds == {"after_action", "delayed"}  # 沒有傷害：沒有擊殺、命中
    pull = _draft("skill_gravity_burst")
    pull.pop("followup")
    kinds = {
        c.value
        for c in _field(_step(draft_options(pull, lib), "followup"), "followup.when").choices
    }
    assert "after_gather" in kinds and "after_move" not in kinds


def test_the_delayed_kind_asks_when_to_release_and_limits_the_shapes() -> None:
    lib = library()
    draft = _draft("skill_charged_cleave")
    draft["followup"] = {"when": "delayed", "skeleton": "area"}
    step = _step(draft_options(draft, lib), "followup")
    release = _field(step, "followup.release")
    assert release.required and {c.value for c in release.choices} == {"next_turn", "attacked"}
    shapes = {c.value for c in _field(step, "followup.shape").choices}
    assert shapes and shapes <= set(DELAYED_SHAPES)
    draft["followup"].update(
        shape={"type": "square3", "range": 0},
        effects=[{"type": "damage", "multiplier_permille": 1000}],
    )
    assert not _step(draft_options(draft, lib), "followup").complete  # 還沒選何時釋放
    draft["followup"]["release"] = "attacked"
    assert _step(draft_options(draft, lib), "followup").complete


def test_hit_and_run_offers_only_the_move_skeleton_and_one_self_move() -> None:
    lib = library()
    draft = _draft("skill_retreating_slash")
    draft["followup"] = {"when": "after_action"}
    step = _step(draft_options(draft, lib), "followup")
    assert [c.value for c in _field(step, "followup.skeleton").choices] == ["displace"]
    draft["followup"].update(skeleton="displace", shape={"type": "ground_tile", "range": 2})
    effects = _field(_step(draft_options(draft, lib), "followup"), "followup.effects")
    assert effects.max_count == 1
    assert {c.value for c in effects.choices} <= set(COMPOSITE_MOVES)


def test_the_gather_burst_range_is_fixed_to_the_gather_range() -> None:
    lib = library()
    draft = {
        **_draft("skill_gravity_burst"),
        "shape": {"type": "square3", "range": 3},
        "followup": {"when": "after_gather", "skeleton": "area"},
    }
    shape = _field(_step(draft_options(draft, lib), "followup"), "followup.shape")
    assert {c.value for c in shape.choices} <= set(FOLLOWUP_CENTERED)
    for choice in shape.choices:
        reach = next(p for p in choice.params if p.field == "range")
        assert (reach.min, reach.max) == (3, 3)


def test_a_second_part_condition_is_offered_and_checked() -> None:
    lib = library()
    draft = _draft("skill_armor_break_combo")
    draft["followup"]["condition"] = {"type": "target_hp_below", "permille": 500}
    step = _step(draft_options(draft, lib), "followup")
    condition = _field(step, "followup.condition")
    assert "target_hp_below" in {c.value for c in condition.choices}
    assert field_problems(step.fields, draft) == []
    check = check_draft(draft, lib)
    assert check.complete and check.budget is not None
    plain = check_draft(_draft("skill_armor_break_combo"), lib)
    assert plain.budget is not None and check.budget.total < plain.budget.total  # 條件打折
