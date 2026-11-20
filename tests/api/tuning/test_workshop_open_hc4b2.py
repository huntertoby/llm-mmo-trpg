"""HC-4b2：搬進 content 的修正規則幅度、組合器與分歧進化的規則數值開進工坊。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

import pytest

from trpg.api.tuning.objects import TABLE_NAMES_ZH, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TABLE_KINDS, parse_path

CONTENT = bundled_content_dir()
CORE = "rules/core.yaml"
COMPOSER = "skill_composer.yaml"
EVOLUTION = "skill_evolution.yaml"
BOUNDS = "skill_limits.modifier_bounds."
OPENED = {
    ("rules", "core", CORE): (
        f"{BOUNDS}damage_permille_min",
        f"{BOUNDS}heal_permille_min",
        f"{BOUNDS}hit_bonus_max",
        f"{BOUNDS}cooldown_delta_max",
        f"{BOUNDS}push_distance_delta_max",
        f"{BOUNDS}range_delta_max",
        f"{BOUNDS}summon_duration_delta_max",
        f"{BOUNDS}on_hit_max_displace",
    ),
    ("skill_composer", "skill_composer", COMPOSER): (
        "whiteboard.summon_ap_cost",
        "whiteboard.self_ap_cost",
        "whiteboard.summon_cooldown_max",
        "structure.borrow_cooldown",
        "llm_cost.max_cooldown",
    ),
    ("skill_evolution", "skill_evolution", EVOLUTION): (
        "summon.deepen_hp_permille",
        "summon.count_power_permille",
    ),
}
"""對象（種類、ID、檔）→ 這段新開的欄位。"""


def _now(file: str, path: str) -> object:
    return lookup(read_data(CONTENT / file), parse_path(path))


@pytest.mark.parametrize(("target", "paths"), OPENED.items(), ids=lambda v: str(v[0]))
def test_moved_rule_numbers_are_open_with_chinese_notes(
    read_service: TuningService, target: tuple[str, str, str], paths: tuple[str, ...]
) -> None:
    kind, object_id, file = target
    detail = object_detail(CONTENT, read_service.table, kind, object_id)
    by_path = {f.path: f for f in detail.fields}
    for path in paths:
        field = by_path[path]
        assert field.value == _now(file, path), path
        assert field.label_zh and not field.label_zh.isascii(), path
        assert "調高" in field.note_zh and "調低" in field.note_zh, path


def test_summon_unit_ranges_are_open_per_unit(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "skill_composer", "skill_composer")
    units = read_data(CONTENT / COMPOSER)["recipes"]["summon_units"]
    by_path = {f.path: f for f in detail.fields}
    for i, unit in enumerate(units):
        assert by_path[f"recipes.summon_units[{i}].range"].value == unit["range"]


def test_the_evolution_table_is_listed(read_service: TuningService) -> None:
    assert "skill_evolution" in TABLE_KINDS
    found = [o for o in read_service.objects() if o.kind == "skill_evolution"]
    assert [(o.id, o.file, o.name_zh) for o in found] == [
        ("skill_evolution", EVOLUTION, TABLE_NAMES_ZH["skill_evolution"])
    ]


def test_an_evolution_draft_validates(read_service: TuningService) -> None:
    path = "summon.count_power_permille"
    now = _now(EVOLUTION, path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=EVOLUTION, path=path, old=now, new=now + 100)
    result = read_service.check("hc4b2-evo", [item])
    assert result.ok, (result.field_errors, result.page_errors)


@pytest.mark.parametrize("name", ["push_distance_delta_max", "on_hit_max_displace"])
def test_displacement_over_the_displace_cap_is_refused(
    read_service: TuningService, name: str
) -> None:
    """HC-4b 裁定 3：修正規則的推拉距離上限不能大於 ``max_displace_distance``。"""
    path = f"{BOUNDS}{name}"
    now = _now(CORE, path)
    top = _now(CORE, "max_displace_distance")
    assert isinstance(now, int) and isinstance(top, int)
    item = TuningChangeIn(file=CORE, path=path, old=now, new=top + 1)
    result = read_service.check(f"hc4b2-{name}", [item])
    assert not result.ok
    messages = [e.message_zh for e in result.field_errors] + list(result.page_errors)
    assert any("兩格要一起改" in m for m in messages), result


def test_whiteboard_ap_over_the_ap_cap_is_refused(read_service: TuningService) -> None:
    path = "whiteboard.summon_ap_cost"
    now = _now(COMPOSER, path)
    top = _now(CORE, "skill_limits.max_ap_cost")
    assert isinstance(now, int) and isinstance(top, int)
    item = TuningChangeIn(file=COMPOSER, path=path, old=now, new=top + 1)
    result = read_service.check("hc4b2-ap", [item])
    assert not result.ok
    messages = [e.message_zh for e in result.field_errors] + list(result.page_errors)
    assert any("whiteboard.summon_ap_cost" in m for m in messages), result


TIER_GROUP = "階級與升階"


def test_the_budget_table_has_a_tier_and_retier_group(read_service: TuningService) -> None:
    """HC-4b 裁定 4：預算表多一組「階級與升階」，放升階重配與最低角色階級的數字。"""
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    group = [f for f in detail.fields if f.group_zh == TIER_GROUP]
    data = read_data(CONTENT / "skill_budget.yaml")
    expected: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")
        elif isinstance(node, int) and not isinstance(node, bool):
            expected.append(path)

    for top in ("retier_growth", "min_character_tier"):
        walk(data[top], top)
    # 升降地形格數表的「階級」欄路徑上有 tier（工坊一律不開的欄位名），只開格數
    expected = [p for p in expected if not p.endswith("].tier")]
    assert sorted(f.path for f in group) == sorted(expected)
    for field in group:
        assert field.value == _now("skill_budget.yaml", field.path), field.path
        assert not field.label_zh.isascii(), field.path
        assert "調高" in field.note_zh and "調低" in field.note_zh, field.path


def test_a_tier_draft_validates(read_service: TuningService) -> None:
    path = "min_character_tier.kinds.stance"
    now = _now("skill_budget.yaml", path)
    assert isinstance(now, int)
    item = TuningChangeIn(file="skill_budget.yaml", path=path, old=now, new=now - 1)
    result = read_service.check("hc4b2-tier", [item])
    assert result.ok, (result.field_errors, result.page_errors)
