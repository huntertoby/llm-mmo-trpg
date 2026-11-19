"""``scripts/x10/fields.yaml``（X10-1）：量類 ×10 的欄位清單涵蓋 ``content/`` 每一個數字欄位。

清單沒列到的數字欄位、同一個欄位落在兩類、過時的樣式都算失敗：新增內容欄位時，要先決定它是不是量類
（``docs/design/05-戰鬥.md`` 5.4.1），再寫進清單。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "x10" / "rescale.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("x10_rescale", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["x10_rescale"] = module
    spec.loader.exec_module(module)
    return module


rs = _load()


def test_fields_cover_every_numeric_content_field() -> None:
    result = rs.classify()
    found = rs.problems(result)
    assert not found, "\n".join(found[:40])


def test_core_quantities_are_scaled() -> None:
    """抽查：設計 5.4.1 點名的量類都在 scale，點名不變的都不在。"""
    result = rs.classify()
    scaled = {(leaf.file, leaf.display()) for leaf in result.by_category["scale"]}
    kept = {(leaf.file, leaf.display()) for leaf in result.by_category["keep"]}
    for item in [
        ("units/ash_hound.yaml", "max_hp"),
        ("units/ash_hound.yaml", "attributes.str"),
        ("units/ash_hound.yaml", "armor_bonus"),
        ("rules/core.yaml", "ability_mod_base"),
        ("rules/core.yaml", "resources.stamina_regen"),
        ("forms.yaml", "upkeep_mana"),
    ]:
        assert item in scaled, item
    for item in [
        ("units/ash_hound.yaml", "speed"),
        ("rules/core.yaml", "ap_per_turn"),
        ("rules/core.yaml", "hit_target"),
        ("rules/core.yaml", "proficiency"),
        ("rules/core.yaml", "budget_reference_weapon_damage"),
        ("rules/core.yaml", "tier_budget.1"),
    ]:
        assert item in kept, item


def _steps(data: object) -> list[object]:
    node = rs.compose(_dump(data))
    return [leaf.steps for leaf in rs._walk(node, "x.yaml", ())]


def _dump(data: object) -> str:
    return str(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("effects[type=damage].flat_bonus", [True, False, False]),
        ("effects[type!=damage].flat_bonus", [False, True, False]),
        ("effects[].flat_bonus", [True, True, False]),
        ("**.flat_bonus", [True, True, False]),
        ("effects[type=heal|damage].*", [True, True, True]),
        ("*.cost{kind=x}.mana", [False, False, False]),
        ("effects[tag=~].*", [True, True, True]),
        ('effects[path="a[*].b"].*', [False, False, False]),
        ("eff*[].flat_*", [True, True, False]),
    ],
)
def test_pattern_syntax(pattern: str, expected: list[bool]) -> None:
    data = {
        "effects": [
            {"type": "damage", "flat_bonus": 1},
            {"type": "heal", "flat_bonus": 2},
            {"type": "heal", "duration": 3},
        ]
    }
    toks = rs.parse_pattern(pattern)
    assert [rs.matches(toks, steps) for steps in _steps(data)] == expected


def test_key_filter_on_mapping_value() -> None:
    data = {"rider": {"resource": "mana", "amount": 2}, "other": {"resource": "x", "amount": 1}}
    toks = rs.parse_pattern("*{resource=mana}.amount")
    assert [rs.matches(toks, s) for s in _steps(data)] == [True, False]


@pytest.mark.parametrize("bad", ["a[b", "a{x=1}{y=2}", "**[]", "a..b", "a[x]"])
def test_bad_patterns(bad: str) -> None:
    with pytest.raises(rs.RescaleError):
        rs.parse_pattern(bad)
