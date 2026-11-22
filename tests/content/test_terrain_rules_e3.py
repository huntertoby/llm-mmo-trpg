"""E3：共用規則表的三種新地形規則（08 8.29 E3，#175）。

種族被動與裝備地形規則都能用，參數檢查共用。"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from trpg.content.equipment import AffixDef, TerrainAffix
from trpg.content.races import RacePassive
from trpg.content.unit_rules import UNIT_RULE_PARAM_FIELDS, UNIT_RULE_SPECS
from trpg.shared.types import Surface

_ADAPTER: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)

_GOOD: dict[str, dict[str, object]] = {
    "trail_surface": {"surfaces": ["ice"], "duration": 1},
    "flat_climb": {"amount": 1},
    "surface_damage_immunity": {"surfaces": ["poison"]},
}


def _gear(rule: str, **params: object) -> AffixDef:
    data: dict[str, object] = {
        "id": "affix_test_e3",
        "name_zh": "測試",
        "category": "terrain",
        "slots": ["feet"],
        "rule": rule,
    }
    data.update(params)
    return _ADAPTER.validate_python(data)


def _race(rule: str, **params: object) -> RacePassive:
    data: dict[str, object] = {
        "id": "passive_test_e3",
        "name_zh": "測試",
        "description_zh": "測試",
        "rule": rule,
    }
    data.update(params)
    return RacePassive.model_validate(data)


def test_new_kinds_are_in_the_shared_table() -> None:
    assert UNIT_RULE_SPECS["trail_surface"].required == ("surfaces", "duration")
    assert UNIT_RULE_SPECS["flat_climb"].required == ("amount",)
    assert UNIT_RULE_SPECS["surface_damage_immunity"].required == ("surfaces",)
    assert "duration" in UNIT_RULE_PARAM_FIELDS


@pytest.mark.parametrize("rule", sorted(_GOOD))
def test_new_kinds_parse_for_gear_and_race(rule: str) -> None:
    affix = _gear(rule, **_GOOD[rule])
    assert isinstance(affix, TerrainAffix)
    passive = _race(rule, **_GOOD[rule])
    assert passive.rule == rule


def test_trail_surface_params() -> None:
    affix = _gear("trail_surface", surfaces=["ice"], duration=1)
    assert isinstance(affix, TerrainAffix)
    assert affix.surfaces == (Surface.ICE,)
    assert affix.duration == 1
    with pytest.raises(ValidationError, match="缺少必填參數 duration"):
        _gear("trail_surface", surfaces=["ice"])
    with pytest.raises(ValidationError, match="只能填一種表面"):
        _gear("trail_surface", surfaces=["ice", "water"], duration=1)
    with pytest.raises(ValidationError, match="只能填一種表面"):
        _race("trail_surface", surfaces=["ice", "water"], duration=1)


def test_duration_only_for_trail_surface() -> None:
    with pytest.raises(ValidationError, match="不可使用參數 duration"):
        _gear("flat_climb", amount=1, duration=1)
    with pytest.raises(ValidationError, match="不可使用參數 duration"):
        _race("surface_damage_immunity", surfaces=["poison"], duration=1)


def test_flat_climb_and_immunity_params() -> None:
    with pytest.raises(ValidationError, match="缺少必填參數 amount"):
        _gear("flat_climb")
    with pytest.raises(ValidationError, match="不可使用參數 surfaces"):
        _gear("flat_climb", amount=1, surfaces=["ice"])
    with pytest.raises(ValidationError, match="缺少必填參數 surfaces"):
        _race("surface_damage_immunity")


# ---------------------------------------------------------------------------
# 地形規則只能留表面，不能施加狀態（8.29 E3 第 6 點）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["status", "apply_status", "statuses", "status_id"])
def test_terrain_rule_cannot_apply_a_status(key: str) -> None:
    with pytest.raises(ValidationError, match="地形規則只能留下表面，不能施加狀態"):
        _gear("trail_surface", surfaces=["ice"], duration=1, **{key: "bleeding"})
    with pytest.raises(ValidationError, match="地形規則只能留下表面，不能施加狀態"):
        _race("trail_surface", surfaces=["ice"], duration=1, **{key: "bleeding"})


@pytest.mark.parametrize("rule", ["trail_status", "pass_through_status"])
def test_status_rule_kinds_get_the_chinese_message(rule: str) -> None:
    with pytest.raises(ValidationError, match="是改寫規則"):
        _gear(rule)
    with pytest.raises(ValidationError, match="是改寫規則"):
        _race(rule)


def test_content_check_message_through_the_affix_table() -> None:
    from trpg.content.equipment import AffixTable  # noqa: PLC0415

    data = {
        "affixes": [
            {
                "id": "affix_t_bleed_trail",
                "name_zh": "走過時讓相鄰敵人流血",
                "category": "terrain",
                "slots": ["feet"],
                "rule": "trail_surface",
                "surfaces": ["ice"],
                "duration": 1,
                "apply_status": "bleeding",
            }
        ]
    }
    with pytest.raises(ValidationError, match="affix_t_bleed_trail：地形規則只能留下表面"):
        AffixTable.model_validate(data)


# ---------------------------------------------------------------------------
# 收尾：預算點數先給 0、產生器不產（等 E6-a）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule", sorted(_GOOD))
def test_new_kinds_cost_zero_points_for_now(rule: str) -> None:
    from tests.engine.helpers import library  # noqa: PLC0415
    from trpg.content.item_budget import affix_points  # noqa: PLC0415

    lib = library()
    gen = lib.item_gen
    assert gen is not None
    assert affix_points(gen, _gear(rule, **_GOOD[rule]), None) == 0
    assert "terrain" not in gen.category_points


def test_no_content_uses_the_new_kinds_yet() -> None:
    from tests.engine.helpers import library  # noqa: PLC0415

    lib = library()
    used = {a.rule for a in lib.affixes.values() if isinstance(a, TerrainAffix)}
    races = lib.ruleset.races
    assert races is not None
    used |= {r.passive.rule for r in races.races}
    assert not used & set(_GOOD)
