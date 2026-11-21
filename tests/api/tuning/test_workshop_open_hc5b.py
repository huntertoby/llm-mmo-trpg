"""HC-5b：從 ``skillgen/`` 搬進 content 的組合器、預算、進化與挑選的規則數值開進工坊。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

import pytest

from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn, TuningFieldView
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path

CONTENT = bundled_content_dir()
COMPOSER_OPENED = (
    "structure.gamble_backlash_chance_permille",
    "structure.second_element_multiplier_permille",
    "structure.delayed_damage_rounds.min",
    "structure.delayed_damage_rounds.max",
    "structure.delayed_damage_radius.min",
    "structure.delayed_damage_radius.max",
    "sacrifice.radius.min",
    "sacrifice.radius.max",
    "special.condition_permille",
    "recipes.param_permille",
    "recipes.high_ground_permille",
    "recipes.exploit_surface_permille",
    "condition.point_blank_min_reach",
    "llm_cost.default_ap",
    "llm_topic.max_keywords",
)
"""``skill_composer`` 表新開的欄位（接在 HC-4b2 的整招召喚射程後面）。"""
OPENED: dict[tuple[str, str, str], tuple[str, ...]] = {
    ("skill_composer", "skill_composer", "skill_composer.yaml"): COMPOSER_OPENED,
    ("budget", "skill_budget", "skill_budget.yaml"): (
        "shield_duration_start",
        "modifier.shape_to_reference_size",
        "retier_growth.weak_floor_exempt_min_tier",
        "retier_growth.rock_multiplier_permille",
    ),
    ("skill_evolution", "skill_evolution", "skill_evolution.yaml"): (
        "low_multiplier_floor",
        "low_multiplier_step",
        "first_knob_weight",
        "extra_cooldown_steps",
        "min_cooldown",
        "max_cooldown",
    ),
    ("pick", "skill_pick", "skill_pick.yaml"): ("pool.max_off_route",),
}


def _now(name: str, path: str) -> object:
    return lookup(read_data(CONTENT / name), parse_path(path))


def _detail(read_service: TuningService, kind: str, object_id: str) -> dict[str, TuningFieldView]:
    detail = object_detail(CONTENT, read_service.table, kind, object_id)
    return {f.path: f for f in detail.fields}


@pytest.mark.parametrize(("target", "paths"), OPENED.items(), ids=lambda v: str(v[0]))
def test_moved_numbers_are_open_with_chinese_notes(
    read_service: TuningService, target: tuple[str, str, str], paths: tuple[str, ...]
) -> None:
    kind, object_id, name = target
    by_path = _detail(read_service, kind, object_id)
    for path in paths:
        field = by_path[path]
        assert field.value == _now(name, path), path
        assert field.label_zh and not field.label_zh.isascii(), path
        assert "調高" in field.note_zh and "調低" in field.note_zh, path
        assert "HC-5b" not in field.label_zh, path
        low, high = field.hint_min, field.hint_max
        assert isinstance(field.value, int) and low is not None and high is not None, path
        assert low <= field.value <= high, path


def test_list_rows_of_the_retier_steps_are_open(read_service: TuningService) -> None:
    """升階重配的召喚物 HP 檔與減輕費用檔每一項各一列（同護盾持續時間表）。"""
    by_path = _detail(read_service, "budget", "skill_budget")
    data = read_data(CONTENT / "skill_budget.yaml")["retier_growth"]
    for name in ("summon_hp_steps", "cost_scales_permille"):
        for i, value in enumerate(data[name]):
            assert by_path[f"retier_growth.{name}[{i}]"].value == value


def test_search_parameters_stay_closed(read_service: TuningService) -> None:
    """純搜尋參數（重抽次數、候選上限）照 HC-5a ``rules.search`` 的前例不開。"""
    composer = _detail(read_service, "skill_composer", "skill_composer")
    assert not [p for p in composer if p.startswith(("search.", "special.ladders"))]
    pick = _detail(read_service, "pick", "skill_pick")
    for path in ("pool.slot_keyword_tries", "pool.wish_seed_permille", "pool.wish_tag_extra"):
        assert path not in pick


def test_a_composer_draft_validates(read_service: TuningService) -> None:
    path = "recipes.param_permille"
    now = _now("skill_composer.yaml", path)
    assert isinstance(now, int)
    item = TuningChangeIn(file="skill_composer.yaml", path=path, old=now, new=now - 100)
    result = read_service.check("hc5b-param", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_default_ap_over_the_ap_cap_is_refused(read_service: TuningService) -> None:
    path = "llm_cost.default_ap"
    now = _now("skill_composer.yaml", path)
    assert isinstance(now, int)
    item = TuningChangeIn(file="skill_composer.yaml", path=path, old=now, new=4)
    result = read_service.check("hc5b-ap", [item])
    assert not result.ok


def test_a_reversed_range_is_refused(read_service: TuningService) -> None:
    """「最少」大於「最多」被擋（``IntRange`` 的檢查）。"""
    path = "sacrifice.radius.min"
    now = _now("skill_composer.yaml", path)
    assert isinstance(now, int)
    item = TuningChangeIn(file="skill_composer.yaml", path=path, old=now, new=3)
    result = read_service.check("hc5b-radius", [item])
    assert not result.ok
