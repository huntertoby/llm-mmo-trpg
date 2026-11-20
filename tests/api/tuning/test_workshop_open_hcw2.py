"""HC-W2：工坊開放 2（形狀查表倍率搬進 ``skill_budget.yaml``；形態、裝備規則、物品生成開進工坊）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from trpg.api.tuning.check import prepare
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.service import TuningService
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir
from trpg.skillgen.budget import skill_budget

CONTENT = bundled_content_dir()
BUDGET = "skill_budget.yaml"


def _cone_skills(library: ContentLibrary) -> dict[str, int]:
    """內建技能裡用錐形的招 → 錐形長度（size）。"""
    out: dict[str, int] = {}
    for sid, skill in sorted(library.skills.items()):
        if skill.shape.type == "cone":
            size = skill.shape.param_values().get("size")
            if isinstance(size, int):
                out[sid] = size
    return out


def test_shape_lookup_tables_are_open_in_the_shape_group(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    by_path = {f.path: f for f in detail.fields}
    prices = read_data(CONTENT / BUDGET)["shape_budget"]
    params = {"cone": "錐形長度", "cross": "十字臂長", "ring": "環形半徑", "chain": "連鎖跳"}
    for sid, word in params.items():
        assert by_path[f"shape_budget.{sid}.base_permille"].group_zh == "形狀"
        for key in ("by_value", "non_power_by_value"):
            for value, permille in (prices[sid].get(key) or {}).items():
                field = by_path[f"shape_budget.{sid}.{key}.{value}"]
                assert field.value == permille
                assert field.group_zh == "形狀"
                assert f"{word} {value}" in field.label_zh
                assert "越大" in field.note_zh


def test_a_cone_table_draft_moves_only_the_cones_of_that_size(
    read_service: TuningService, content_library: ContentLibrary
) -> None:
    cones = _cone_skills(content_library)
    size = max(set(cones.values()), key=list(cones.values()).count)  # 用最多招的長度
    path = f"shape_budget.cone.by_value.{size}"
    now = content_library.budget.shape_budget["cone"].by_value
    assert now is not None
    change = Change(file=BUDGET, path=path, old=now[size], new=now[size] * 2)
    prepared = prepare(CONTENT, read_service.table, [change])
    assert not prepared.errors
    draft = load_library(read_service.workspace.draft(prepared.texts))
    assert (draft.budget.shape_budget["cone"].by_value or {})[size] == now[size] * 2
    moved = 0
    for sid, skill_size in cones.items():
        before = skill_budget(content_library.skills[sid], content_library)
        after = skill_budget(draft.skills[sid], draft)
        assert after.usable == before.usable
        if skill_size != size:
            assert after.ratio == before.ratio, sid
        elif after.ratio != before.ratio:
            assert after.ratio > before.ratio, sid
            moved += 1
    assert moved, "至少要有一招這個長度的錐形預算比例變高"
    other = next(s for s in sorted(content_library.skills) if s not in cones)
    assert (
        skill_budget(draft.skills[other], draft).ratio
        == skill_budget(content_library.skills[other], content_library).ratio
    )
