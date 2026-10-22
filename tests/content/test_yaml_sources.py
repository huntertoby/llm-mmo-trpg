"""YAML 唯一來源（Phase 3E-2f）：schema 常數與 ``content/`` 一致、範圍與清單的驗證訊息為中文。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content import skills
from trpg.content.skills import EffectSpec, ShapeTable
from trpg.content.yaml_sources import mechanic_status, primitive_status, shape_role

_SHAPES = {
    "followup": ("single", "line", "cone", "cross", "square3", "ring"),
    "on_kill_second": ("single", "line", "cone", "cross", "square3", "ring", "ground_tile"),
    "pierce": ("single", "line"),
    "zone_moving": ("line", "cone"),
    "zone_caster": ("self", "ring", "allies_in_radius"),
    "shape_to": ("line", "chain", "cone"),
}


def test_the_shape_lists_come_from_the_shape_table_and_keep_their_values() -> None:
    assert _SHAPES["followup"] == skills.FOLLOWUP_SHAPES
    assert _SHAPES["on_kill_second"] == skills.ON_KILL_SECOND_SHAPES
    assert _SHAPES["pierce"] == skills.PIERCE_SHAPES
    assert _SHAPES["zone_moving"] == skills.ZONE_MOVING_SHAPES
    assert _SHAPES["zone_caster"] == skills.ZONE_CASTER_SHAPES
    assert _SHAPES["shape_to"] == skills.SHAPE_TO_VALUES
    assert skills.SPLIT_SKELETONS == ("aura", "area")
    ruleset = library().ruleset
    assert dict(ruleset.shapes.shape_roles) == {k: v for k, v in _SHAPES.items()}
    for role in skills.SHAPE_ROLES:
        assert shape_role(role) == _SHAPES[role]


def test_status_constants_come_from_the_primitive_table() -> None:
    assert (skills.CHEAT_DEATH_STATUS, skills.REDIRECT_STATUS) == ("undying", "soul_link")
    assert (skills.TIME_BOMB, skills.CHARGING) == ("time_bomb", "charging")
    assert primitive_status("delayed_damage") == "time_bomb"
    assert mechanic_status("charging") == "charging"
    status_ids = {s.id for s in library().ruleset.statuses.statuses}
    assert library().ruleset.primitives.status_refs() <= status_ids


def test_a_primitive_pointing_at_an_unknown_status_is_rejected_when_the_ruleset_loads() -> None:
    ruleset = library().ruleset
    table = ruleset.primitives
    bad = table.model_copy(update={"mechanic_statuses": {"charging": "no_such_status"}})
    with pytest.raises(ValidationError, match=r"skill_primitives\.yaml 引用了未知的狀態"):
        type(ruleset).model_validate({**ruleset.__dict__, "primitives": bad})


def test_shape_roles_must_name_known_roles_and_existing_shapes() -> None:
    base = library().ruleset.shapes
    roles = dict(base.shape_roles)
    with pytest.raises(ValidationError, match=r"shape_roles\.pierce"):
        ShapeTable.model_validate(
            {**base.model_dump(), "shape_roles": {**roles, "pierce": ["nope"]}}
        )
    with pytest.raises(ValidationError, match="shape_roles 的用途必須是"):
        ShapeTable.model_validate({**base.model_dump(), "shape_roles": {"pierce": ["single"]}})


@pytest.mark.parametrize(
    ("fields", "limit"),
    [
        ({"type": "damage", "dice": "1d6", "lifesteal_permille": 501}, "1–500"),
        ({"type": "damage", "dice": "1d6", "multiplier_permille": 0}, "1–10000"),
        ({"type": "delayed_damage", "dice": "1d6", "rounds": 4, "radius": 1}, "1–3"),
        ({"type": "delayed_damage", "dice": "1d6", "rounds": 1, "radius": 3}, "0–2"),
        ({"type": "summon", "unit": "x", "duration": 2, "power_permille": 1000}, "100–999"),
        ({"type": "consume_status", "status": "burning", "splash": 2}, "1–1"),
    ],
)
def test_ranges_come_from_the_primitive_yaml_with_chinese_messages(
    fields: dict[str, Any], limit: str
) -> None:
    with pytest.raises(ValidationError, match=f"必須在 {limit}，收到"):
        EffectSpec.model_validate(fields)


def test_a_value_inside_the_yaml_range_is_accepted() -> None:
    effect = EffectSpec.model_validate({"type": "damage", "dice": "1d6", "lifesteal_permille": 500})
    assert effect.lifesteal_permille == 500
