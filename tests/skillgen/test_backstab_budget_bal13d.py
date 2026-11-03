"""BAL-13d 第 4 項：條件的預算倍率可在 skill_conditions.yaml 以 ``budget_permille`` 覆寫。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import library
from trpg.skillgen.budget import skill_budget


def test_condition_budget_permille_overrides_the_harshness_table() -> None:
    lib = library()
    behind = lib.ruleset.conditions.by_id()["from_behind"]
    assert behind.harshness == "common"  # 分類不變（武器親和照舊）
    assert behind.budget_permille is not None
    rows = skill_budget(lib.skills["skill_shadow_backstab"], lib).effects
    conditional = [r for r in rows if r.type == "damage" and r.condition != 1]
    assert [r.condition for r in conditional] == [Fraction(behind.budget_permille, 1000)]


def test_conditions_without_an_override_use_the_harshness_table() -> None:
    lib = library()
    table = lib.budget.condition_permille
    for cond in lib.ruleset.conditions.conditions:
        if cond.budget_permille is None:
            assert table[cond.harshness] > 0
