"""GS-3（#173）：新參數都開進工坊——實心環形的形狀倍率、看最大 HP 的護盾的點數與 ‰、帶進入時效果的
化身技最短冷卻。每格要有中文名、寫清楚調高與調低的效果；超出規則的值驗證會擋。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

import pytest

from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path

CONTENT = bundled_content_dir()
BUDGET_PATHS = (
    "shape_budget.ring.solid_by_value.1",
    "shape_budget.ring.solid_by_value.2",
    "shield_max_hp_points",
)
COOLDOWN = "skill_limits.min_form_entry_cooldown"


def _now(file: str, path: str) -> int:
    value = lookup(read_data(CONTENT / file), parse_path(path))
    assert isinstance(value, int)
    return value


def _explains_both_directions(note: str) -> bool:
    return ("調高" in note and "調低" in note) or ("越大" in note and "越小" in note)


@pytest.mark.parametrize("path", BUDGET_PATHS)
def test_the_budget_fields_are_open_with_chinese_labels(
    read_service: TuningService, path: str
) -> None:
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    field = {f.path: f for f in detail.fields}[path]
    assert field.value == _now("skill_budget.yaml", path)
    assert field.label_zh and not field.label_zh.isascii()
    assert field.group_zh
    assert _explains_both_directions(field.note_zh)
    assert field.hint_min is not None and field.hint_max is not None
    assert field.hint_min <= field.value <= field.hint_max  # type: ignore[operator]


def test_the_cooldown_floor_is_open_on_the_core_rules(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "rules", "core")
    field = {f.path: f for f in detail.fields}[COOLDOWN]
    assert field.value == _now("rules/core.yaml", COOLDOWN)
    assert field.label_zh and "調高" in field.note_zh and "調低" in field.note_zh


def test_the_guardian_shield_permille_is_open_on_the_skill(read_service: TuningService) -> None:
    detail = read_service.object("skill", "skill_form_guardian")
    field = {f.path: f for f in detail.fields}["effects[0].max_hp_permille"]
    assert field.value == 150
    assert field.label_zh and "調高" in field.note_zh and "調低" in field.note_zh


def test_raising_the_cooldown_floor_above_the_avatars_is_refused(
    read_service: TuningService,
) -> None:
    now = _now("rules/core.yaml", COOLDOWN)
    ok = TuningChangeIn(file="rules/core.yaml", path=COOLDOWN, old=now, new=3)
    assert read_service.check("gs3-cooldown-ok", [ok]).ok
    high = TuningChangeIn(file="rules/core.yaml", path=COOLDOWN, old=now, new=4)
    result = read_service.check("gs3-cooldown-high", [high])
    assert not result.ok  # 4 招高階化身的冷卻是 3


def test_a_huge_solid_ring_price_pushes_the_quake_out_of_the_band(
    read_service: TuningService,
) -> None:
    path = "shape_budget.ring.solid_by_value.2"
    now = _now("skill_budget.yaml", path)
    item = TuningChangeIn(file="skill_budget.yaml", path=path, old=now, new=now * 2)
    result = read_service.check("gs3-solid-ring", [item])
    flagged = {flag.skill_id for flag in result.needs_confirm_budget}
    assert not result.ok or "skill_form_quake" in flagged
