"""HC-5b（HC-5a 裁定 2）：組合器的伴生、護主配方和閃現轉型共用同一份代價、射程與強度嘗試順序。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.skillgen.beside_power import (
    COMPANION_TEMPLATE,
    GUARDIAN_TEMPLATE,
    beside_power_tries,
    beside_template,
)

LIB = library()


def test_both_templates_exist_with_the_old_costs() -> None:
    """值同 HC-5b 前 ``composer_recipes`` 寫死的 ``_COMPANION_COSTS``、``_GUARDIAN_COSTS``、
    ``_GUARDIAN_RANGE``。"""
    companion = beside_template(LIB, COMPANION_TEMPLATE)
    guardian = beside_template(LIB, GUARDIAN_TEMPLATE)
    assert list(companion.draft_costs) == [{}, {"mana": 2}, {"mana": 4}]
    assert list(guardian.draft_costs) == [
        {"cooldown": 1},
        {"mana": 2, "cooldown": 1},
        {"cooldown": 2},
        {"mana": 4, "cooldown": 2},
    ]
    assert guardian.draft_range == 2


def test_power_tries_match_the_old_composer_order() -> None:
    """強度：舊的組合器寫死 100‰ 間距、最低 100‰；現在讀閃現的同一格（值相同）。"""
    costs = [{}, {"mana": 2}]
    got = beside_power_tries(500, costs, LIB)
    powers = {500, *range(100, 1001, 100)}
    want = [(p, dict(c)) for p in sorted(powers, key=lambda p: (abs(p - 500), -p)) for c in costs]
    assert got == want
