"""Phase 3-26a：``content/skill_growth.yaml`` 的 schema 與數值。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skill_growth import SkillGrowthRules


def test_the_shipped_table_matches_the_design() -> None:
    growth = library().ruleset.skill_growth
    assert growth.max_level == 5 and growth.points_per_level == 2 and growth.upgrade_cost == 1
    # 2 級、4 級 +10%（累計），3 級先只計等級，5 級沿用 4 級
    assert growth.effect_permille == (0, 100, 100, 200, 200)
    assert growth.trait_level == 5 and growth.evolve_level == 3
    assert growth.trait_area_delta == 1 and growth.trait_cooldown_delta == 1


def test_multiplier_is_an_integer_permille_and_clamped() -> None:
    growth = SkillGrowthRules()
    levels = (0, 1, 2, 3, 4, 5, 9)
    assert [growth.multiplier_permille(n) for n in levels] == [
        1000,
        1000,
        1100,
        1100,
        1200,
        1200,
        1200,
    ]


@pytest.mark.parametrize(
    "update",
    [
        {"effect_permille": (0, 100, 100, 200)},  # 個數不是 max_level
        {"effect_permille": (50, 100, 100, 200, 200)},  # 1 級必須是 0
        {"effect_permille": (0, 200, 100, 200, 200)},  # 不可遞減
        {"trait_level": 6},
        {"evolve_level": 1},
    ],
)
def test_bad_tables_are_rejected(update: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SkillGrowthRules(**update)  # type: ignore[arg-type]
