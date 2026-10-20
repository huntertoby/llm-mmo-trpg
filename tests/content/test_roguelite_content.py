"""``content/roguelite.yaml``（Phase 3-5a）：schema 與跨檔案檢查。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.roguelite import RunRules, roguelite_problems


def _data(**over: Any) -> dict[str, Any]:
    data = library().roguelite.model_dump(mode="json")
    data.update(over)
    return data


def test_shipped_rules_load_and_pass_cross_checks() -> None:
    lib = library()
    rules = lib.roguelite
    assert rules.battles == 5
    assert rules.offer_size == 3
    assert rules.off_route_per_offer == 1
    assert rules.attribute_points_per_level == 2
    assert rules.start_free_points == 4
    assert roguelite_problems(rules, lib.maps, lib.units, lib.ruleset.core.tier_budget) == []


def test_offer_tier_uses_the_last_entry_beyond_the_table() -> None:
    rules = library().roguelite
    assert rules.offer_tier(1) == rules.offer_tier_by_level[0]
    assert rules.offer_tier(99) == rules.offer_tier_by_level[-1]


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"battles": 4}, "encounters 必須有 4 場"),
        ({"level_thresholds": [100, 100]}, "嚴格遞增"),
        ({"campfire_after": [0]}, "campfire_after"),
        ({"off_route_per_offer": 4}, "off_route_per_offer"),
        ({"map_pool": ["ruined_fort", "open_plain"]}, "不可在一般地圖池內"),
    ],
)
def test_schema_rejects_bad_values(over: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        RunRules.model_validate(_data(**over))


def test_cross_checks_report_unknown_units_and_too_few_archetypes() -> None:
    lib = library()
    rules = RunRules.model_validate(_data(map_pool=["open_plain", "swamp"], companions=["nobody"]))
    problems = roguelite_problems(rules, lib.maps, lib.units, lib.ruleset.core.tier_budget)
    assert any("未知的單位範本：nobody" in p for p in problems)
    assert any("地圖類型" in p for p in problems)


def test_cross_checks_report_crowded_start_zones() -> None:
    lib = library()
    rules = RunRules.model_validate(_data(boss={"map": "ruined_fort", "enemies": ["bandit"] * 5}))
    problems = roguelite_problems(rules, lib.maps, lib.units, lib.ruleset.core.tier_budget)
    assert any("起始區放不下" in p for p in problems)
