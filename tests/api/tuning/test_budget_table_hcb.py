"""HC-B：技能預算的計價全部開進工坊（原語、狀態、表面的點數與形狀倍率搬到
``skill_budget.yaml``；預算表其他欄位、條件覆寫、協同係數、被動 n 次係數、階級預算一起開）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from trpg.api.tuning.check import prepare
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup, patch_text
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir
from trpg.content.skill_rules import POINTS_BASES, price_table_problems, primitive_points_problems
from trpg.content.tuning_fields import parse_path, path_matches
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


def test_status_and_surface_points_live_in_the_budget_table(
    content_library: ContentLibrary,
) -> None:
    budget = content_library.budget
    rules = content_library.ruleset
    assert price_table_problems(rules.statuses, rules.surfaces, budget) == []
    assert all(not rules.status_def(s).skill_pool_excluded for s in budget.status_points)
    excluded = sorted(rules.enemy_only_statuses())[0]
    broken = budget.model_copy(
        update={
            "status_points": {**budget.status_points, excluded: 1, "nope": 2},
            "surface_points": {**budget.surface_points, "lava": 1},
        }
    )
    assert price_table_problems(rules.statuses, rules.surfaces, broken) == [
        f"status_points.{excluded}：enemy_only、mechanic_only 的狀態不能有預算點數",
        "status_points.nope：沒有這個狀態",
        "surface_points.lava：沒有這個表面",
    ]


def test_every_number_in_the_budget_file_is_open_or_listed_as_structure(
    read_service: TuningService,
) -> None:
    """預算表的每個整數不是開了，就是在「結構、不計價」的清單裡（HC-B 報告第 2 節）。"""
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    opened = [f.path for f in detail.fields]
    patterns = [f.pattern for f in detail.fields]
    structure = (
        "max_rule_rewrite",
        "rarity.",
        "min_character_tier.",
        "terrain_area_rarity[",
        "retier_growth.",
        "allowance.self_status.fixed_duration.",
    )
    closed: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")
        elif (
            isinstance(node, int)
            and not isinstance(node, bool)
            and path not in opened
            and not path.startswith(structure)
        ):
            closed.append(path)

    walk(read_data(CONTENT / BUDGET), "")
    assert closed == []
    assert all(any(path_matches(p, o) for p in patterns) for o in opened)


def test_numbered_keys_and_lists_get_their_own_rows(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    by_path = {f.path: f for f in detail.fields}
    data = read_data(CONTENT / BUDGET)
    for ap in (1, 2, 3):
        field = by_path[f"ap_coefficient_permille.{ap}"]
        assert field.value == data["ap_coefficient_permille"][ap]
        assert f"{ap} AP" in field.label_zh
    for i, value in enumerate(data["obstacle_duration_permille"]):
        field = by_path[f"obstacle_duration_permille[{i}]"]
        assert field.value == value
        assert f"持續 {i + 1} 回合" in field.label_zh


def test_a_numbered_key_is_patched_in_place() -> None:
    text = (CONTENT / BUDGET).read_text(encoding="utf-8")
    parts = parse_path("ap_coefficient_permille.2")
    assert parts == ("ap_coefficient_permille", "2")
    now = lookup(read_data(CONTENT / BUDGET), parts)
    patched = patch_text(text, [(parts, now + 100)])
    before = text.splitlines()
    after = patched.splitlines()
    changed = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(changed) == 1
    assert f"2: {now + 100}" in changed[0][1]


def test_a_numbered_key_draft_validates(read_service: TuningService) -> None:
    now = read_data(CONTENT / BUDGET)["ap_coefficient_permille"][2]
    item = TuningChangeIn(file=BUDGET, path="ap_coefficient_permille.2", old=now, new=now + 50)
    result = read_service.check("hcb-ap", [item])
    assert not result.field_errors, result.field_errors


def test_condition_and_synergy_tables_are_open(read_service: TuningService) -> None:
    conditions = object_detail(CONTENT, read_service.table, "skill_conditions", "skill_conditions")
    rows = read_data(CONTENT / "skill_conditions.yaml")["conditions"]
    written = [i for i, r in enumerate(rows) if "budget_permille" in r]
    assert [f.path for f in conditions.fields] == [
        f"conditions[{i}].budget_permille" for i in written
    ]
    synergies = object_detail(CONTENT, read_service.table, "skill_synergies", "skill_synergies")
    rules = read_data(CONTENT / "skill_synergies.yaml")["synergies"]
    assert [f.value for f in synergies.fields] == [r["coefficient_permille"] for r in rules]
    assert synergies.fields[0].label_zh.startswith("協同「")


def test_the_budget_table_is_grouped(read_service: TuningService) -> None:
    """HC-B 第 3 項：每個欄位都有分組，至少有規格列的六組，同組的欄位排在一起。"""
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    groups = [f.group_zh for f in detail.fields]
    assert None not in groups
    order = list(dict.fromkeys(groups))
    assert {"原語點數", "狀態", "表面", "形狀", "係數", "召喚"} <= set(order)
    assert groups == sorted(groups, key=order.index)  # 同組連在一起
    by_path = {f.path: f.group_zh for f in detail.fields}
    assert by_path["primitive_points.raise_terrain"] == "原語點數"
    assert by_path["status_points.burning"] == "狀態"
    assert by_path["shape_budget.line.per_unit_permille"] == "形狀"
    assert by_path["ap_coefficient_permille.2"] == "係數"
