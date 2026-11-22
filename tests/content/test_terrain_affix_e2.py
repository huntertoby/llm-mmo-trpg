"""E2：第 12 類詞條「地形規則」的 schema 與載入檢查（08 8.29，#175）。"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from tests.engine.helpers import library
from trpg.content.equipment import (
    AFFIX_CATEGORIES,
    AFFIX_CATEGORY_NUMBER,
    AFFIX_CATEGORY_ZH,
    NUMERIC_CATEGORIES,
    AffixDef,
    TerrainAffix,
)
from trpg.content.library.gear_checks import _terrain_affix_problems
from trpg.content.races import PASSIVE_RULE_SPECS
from trpg.content.unit_rules import EQUIPMENT_FORBIDDEN_RULES, UNIT_RULE_SPECS
from trpg.shared.types import Surface

_ADAPTER: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)


def _terrain(**extra: object) -> AffixDef:
    data: dict[str, object] = {
        "id": "affix_test_fire_walk",
        "name_zh": "火焰表面不會讓你燃燒",
        "category": "terrain",
        "slots": ["feet"],
        "rule": "burn_immunity_on",
        "surfaces": ["fire"],
    }
    data.update(extra)
    return _ADAPTER.validate_python(data)


def test_terrain_is_category_12_and_non_numeric() -> None:
    assert AFFIX_CATEGORIES[-1] == "terrain"
    assert AFFIX_CATEGORY_NUMBER["terrain"] == 12
    assert AFFIX_CATEGORY_ZH["terrain"] == "地形規則"
    assert "terrain" not in NUMERIC_CATEGORIES


def test_race_and_equipment_share_the_rule_table() -> None:
    assert PASSIVE_RULE_SPECS is UNIT_RULE_SPECS


def test_terrain_affix_parses() -> None:
    affix = _terrain()
    assert isinstance(affix, TerrainAffix)
    assert affix.surfaces == (Surface.FIRE,)
    assert not affix.numeric


def test_terrain_affix_rejects_unknown_rule() -> None:
    with pytest.raises(ValidationError, match="不在允許清單內"):
        _terrain(rule="fly")


def test_terrain_affix_rejects_wrong_params() -> None:
    with pytest.raises(ValidationError, match="不可使用參數 amount"):
        _terrain(amount=1)
    with pytest.raises(ValidationError, match="缺少必填參數 surfaces"):
        _terrain(surfaces=None)


def test_terrain_affix_rejects_element_resist_rule() -> None:
    assert {"damage_taken_permille"} == EQUIPMENT_FORBIDDEN_RULES
    with pytest.raises(ValidationError, match="地形規則不能用 damage_taken_permille"):
        _terrain(rule="damage_taken_permille", surfaces=None, element="fire", permille=-100)


def test_terrain_reference_checks() -> None:
    lib = library()
    ruleset = lib.ruleset
    bad = _terrain(
        rule="knockback_reduction_at_hazard", surfaces=None, terrain=["nowhere"], amount=1
    )
    assert isinstance(bad, TerrainAffix)
    assert _terrain_affix_problems(bad, ruleset, ()) == [
        "詞條 affix_test_fire_walk：未知的地形 nowhere"
    ]
    rain = _terrain(rule="weather_move_bonus", surfaces=None, weathers=["no_such"], amount=1)
    assert isinstance(rain, TerrainAffix)
    assert _terrain_affix_problems(rain, ruleset, ("rain",)) == [
        "詞條 affix_test_fire_walk：未知的天氣 no_such"
    ]
    sight = _terrain(rule="sight_penalty_reduction", surfaces=None, weathers=["rain"], permille=999)
    assert isinstance(sight, TerrainAffix)
    problems = _terrain_affix_problems(sight, ruleset, ("rain",))
    assert len(problems) == 1 and "permille 必須在" in problems[0]


def test_content_has_no_terrain_affix_yet() -> None:
    """``affixes.yaml`` 先不放（產生器也不產），每種規則都還是在種族表裡。"""
    assert not [a for a in library().affixes.values() if a.category == "terrain"]
    assert set(UNIT_RULE_SPECS) >= {"burn_immunity_on", "slip_immunity", "surface_move_bonus"}
