"""HC-B：技能預算的計價全部開進工坊（原語點數從 ``skill_primitives.yaml`` 搬到
``skill_budget.yaml``）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from trpg.api.tuning.check import prepare
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.objects import object_detail
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir
from trpg.content.skill_rules import POINTS_BASES, primitive_points_problems
from trpg.skillgen.budget import skill_budget

CONTENT = bundled_content_dir()
BUDGET = "skill_budget.yaml"


def _raise_terrain_skills(library: ContentLibrary) -> list[str]:
    return sorted(
        sid
        for sid, skill in library.skills.items()
        if any(e.type == "raise_terrain" for e in skill.effects)
    )


def test_every_point_priced_primitive_is_in_the_budget_table(
    content_library: ContentLibrary,
) -> None:
    budget = content_library.budget
    priced = sorted(
        p.id
        for p in content_library.ruleset.primitives.primitives
        if p.budget_basis in POINTS_BASES
    )
    assert sorted(budget.primitive_points) == priced
    assert primitive_points_problems(content_library.ruleset.primitives, budget) == []
    missing = budget.model_copy(
        update={
            "primitive_points": {k: v for k, v in budget.primitive_points.items() if k != "push"}
        }
    )
    extra = budget.model_copy(
        update={"primitive_points": {**budget.primitive_points, "heal": 3, "nope": 1}}
    )
    prims = content_library.ruleset.primitives
    assert primitive_points_problems(prims, missing) == [
        "原語 push：budget_basis per_distance 必須在 primitive_points 有一項"
    ]
    assert primitive_points_problems(prims, extra) == [
        "primitive_points.heal：budget_basis dice_average 的原語不用這個點數",
        "primitive_points.nope：沒有這個原語",
    ]


def test_every_primitive_point_is_open_with_its_chinese_name(
    read_service: TuningService, content_library: ContentLibrary
) -> None:
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    by_path = {f.path: f for f in detail.fields}
    names = {p.id: p.name_zh for p in content_library.ruleset.primitives.primitives}
    for pid, value in content_library.budget.primitive_points.items():
        field = by_path[f"primitive_points.{pid}"]
        assert field.value == value
        assert names[pid] in field.label_zh
        assert "越大" in field.note_zh


def test_a_raise_terrain_draft_moves_the_raise_terrain_skills(
    read_service: TuningService, content_library: ContentLibrary
) -> None:
    skills = _raise_terrain_skills(content_library)
    assert skills, "內建技能裡要有隆起地形的招"
    path = "primitive_points.raise_terrain"
    now = content_library.budget.primitive_points["raise_terrain"]
    change = Change(file=BUDGET, path=path, old=now, new=now * 3)
    prepared = prepare(CONTENT, read_service.table, [change])
    assert not prepared.errors
    draft = load_library(read_service.workspace.draft(prepared.texts))
    assert draft.budget.primitive_points["raise_terrain"] == now * 3
    for sid in skills:
        before = skill_budget(content_library.skills[sid], content_library)
        after = skill_budget(draft.skills[sid], draft)
        assert after.usable == before.usable
        assert after.ratio > before.ratio, sid
    # 其他招不受影響
    other = next(s for s in sorted(content_library.skills) if s not in skills)
    assert (
        skill_budget(draft.skills[other], draft).ratio
        == skill_budget(content_library.skills[other], content_library).ratio
    )
    # 驗證會列出被推出合格區間的隆起地形技能
    item = TuningChangeIn(file=BUDGET, path=path, old=now, new=now * 3)
    result = read_service.check("hcb", [item])
    assert any(sid in p for p in result.page_errors for sid in skills), result.page_errors
