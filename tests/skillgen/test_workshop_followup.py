"""Phase 3F-3b：技能工坊的「動作段」步驟（瞬移 → 錐形打擊、跳躍 → 十字震地）。

選項推導與檢查都走後端既有的函式；這裡確認「要不要接動作段」只出現在位移技能、動作段的骨架／形狀／
效果選項受複合技能的限制、一步步組出來的草稿通過檢查，且兩段明細與 CLI／內容庫的示範技能一致。
"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from trpg.content.skills import FOLLOWUP_FORBIDDEN, FOLLOWUP_SHAPES
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_conform import field_problems
from trpg.skillgen.option_models import DraftOptions, StepOptions
from trpg.skillgen.options import draft_options

BASICS: dict[str, Any] = {
    "skeleton": "displace",
    "name_zh": "瞬移斬",
    "kind": "active",
    "ap_cost": 2,
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "tier": 1,
}


def _step(options: DraftOptions, step_id: str) -> StepOptions:
    return next(s for s in options.steps if s.id == step_id)


def _teleport_draft() -> dict[str, Any]:
    return {
        **BASICS,
        "shape": {"type": "ground_tile", "range": 4},
        "effects": [{"type": "teleport"}],
    }


def test_the_followup_step_lists_the_kinds_the_first_part_allows() -> None:
    """3F-4b：「位移 → 動作」只給一個自身位移的位移技能；其他種類看第一段（見
    ``tests/skillgen/test_workshop_kinds.py``）。還沒有效果的技能沒有這一步。"""
    lib = library()
    ids = [s.id for s in draft_options(_teleport_draft(), lib).steps]
    assert ids.index("followup") == ids.index("effects") + 1
    when = _step(draft_options(_teleport_draft(), lib), "followup").fields[0]
    assert "after_move" in {c.value for c in when.choices}
    plain = {**_teleport_draft(), "effects": [{"type": "push", "distance": 1}]}
    when = _step(draft_options(plain, lib), "followup").fields[0]
    assert "after_move" not in {c.value for c in when.choices}
    strike = {"skeleton": "strike", "kind": "active", "ap_cost": 1}
    assert "followup" not in [s.id for s in draft_options(strike, lib).steps]


def test_the_followup_step_can_be_skipped() -> None:
    lib = library()
    draft = {**_teleport_draft(), "cost": {"stamina": 4}, "rarity": "rare"}
    options = draft_options(draft, lib)
    assert options.next_step is None
    assert _step(options, "followup").complete
    assert check_draft(draft, lib).complete  # 單純的傳送太弱（budget.weak），但草稿本身完整


def test_the_followup_fields_unfold_skeleton_then_shape_then_effects() -> None:
    lib = library()
    draft = _teleport_draft()
    step = _step(draft_options(draft, lib), "followup")
    assert [f.field for f in step.fields] == ["followup.when"]
    draft["followup"] = {"when": "after_move"}
    step = _step(draft_options(draft, lib), "followup")
    assert [f.field for f in step.fields] == ["followup.when", "followup.skeleton"]
    assert {"area", "strike"} <= {c.value for c in step.fields[1].choices}
    draft["followup"] = {"when": "after_move", "skeleton": "area"}
    step = _step(draft_options(draft, lib), "followup")
    shape = step.fields[2]
    assert shape.field == "followup.shape"
    offered = {c.value for c in shape.choices}
    assert "cone" in offered and offered <= set(FOLLOWUP_SHAPES)
    cross = next(c for c in shape.choices if c.value == "cross")
    assert (cross.params[0].min, cross.params[0].max) == (0, 0)  # 以落點為中心，射程固定 0
    draft["followup"]["shape"] = {"type": "cone", "size": 2}
    options = draft_options(draft, lib)
    step = _step(options, "followup")
    assert not step.complete and options.next_step == "followup"
    effects = step.fields[3]
    assert effects.field == "followup.effects"
    assert step.fields[4].field == "followup.condition"  # 3F-4b：第二段也可以有條件
    types = {c.value for c in effects.choices}
    assert "damage" in types and not types & set(FOLLOWUP_FORBIDDEN)
    assert effects.max_count == 3  # 兩段合計最多 4 個，位移段已經用掉 1 個


def test_walking_teleport_then_cone_builds_a_legal_composite() -> None:
    lib = library()
    draft = _teleport_draft()
    draft["followup"] = {
        "skeleton": "area",
        "shape": {"type": "cone", "size": 2},
        "effects": [{"type": "damage", "multiplier_permille": 900}],
    }
    draft["cost"] = {"stamina": 12, "cooldown": 3}
    draft["rarity"] = "rare"
    options = draft_options(draft, lib)
    assert options.next_step is None and options.problems == ()
    assert field_problems(_step(options, "followup").fields, draft) == []
    check = check_draft(draft, lib)
    assert check.complete and check.legal, [p.message_zh for p in check.problems]
    assert check.budget is not None
    assert [s.label for s in check.budget.segments] == ["位移段", "動作段"]
    assert check.budget.verdict == "ok"
    assert check.minimum_rarity == "rare"
    # 與內容庫的示範技能同一個預算
    demo = lib.skills["skill_shadow_whirl"]
    assert demo.followup is not None
    again = check_draft({**demo.model_dump(mode="json", exclude_none=True), "id": None}, lib)
    assert again.budget is not None and check.budget.total == again.budget.total


def test_a_common_composite_is_flagged_by_the_check() -> None:
    lib = library()
    draft = {
        **_teleport_draft(),
        "followup": {
            "skeleton": "area",
            "shape": {"type": "cone", "size": 2},
            "effects": [{"type": "damage", "multiplier_permille": 900}],
        },
        "cost": {"stamina": 12, "cooldown": 3},
        "rarity": "common",
    }
    check = check_draft(draft, lib)
    # 3W-9：稀有度只是標記，普通的複合技能不再被擋；工坊的「最低稀有度」仍照結構算
    assert not any("composite" in p.rule for p in check.problems)
    assert check.minimum_rarity == "rare"


def test_the_leap_then_cross_slam_walks_to_a_legal_skill() -> None:
    lib = library()
    draft = {
        **BASICS,
        "name_zh": "躍擊震地",
        "tier": 2,
        "shape": {"type": "ground_tile", "range": 3},
        "effects": [{"type": "leap"}],
        "followup": {
            "skeleton": "area",
            "shape": {"type": "cross", "range": 0},
            "effects": [
                {"type": "damage", "multiplier_permille": 600},
                {"type": "knock_prone"},
            ],
        },
        "cost": {"stamina": 12, "cooldown": 3},
        "rarity": "rare",
    }
    options = draft_options(draft, lib)
    assert options.problems == () and options.next_step is None
    check = check_draft(draft, lib)
    assert check.legal, [p.message_zh for p in check.problems]


def test_a_stale_followup_stays_visible_so_it_can_be_removed() -> None:
    lib = library()
    draft = {
        **_teleport_draft(),
        "effects": [{"type": "teleport"}, {"type": "push", "distance": 1}],
        "followup": {"skeleton": "area"},
    }
    ids = [s.id for s in draft_options(draft, lib).steps]
    assert "followup" in ids
