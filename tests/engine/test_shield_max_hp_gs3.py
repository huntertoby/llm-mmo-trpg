"""GS-3（#173，06 6.30 化形守護）：``shield`` 的「最大 HP ‰」參數。

- 每個目標的護盾＝施放者目前（變身後）最大 HP × ‰，不擲骰、不加屬性；
- 預算：‰ × ``shield_max_hp_points`` ÷ 100（再乘持續係數），代替骰子平均；
- 驗證：不能和 dice、flat_bonus、status 一起填；只給技能自己的護盾。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from trpg.engine.events import ShieldGained
from trpg.skillgen.budget import skill_budget


def shield_skill(permille: int = 150, **extra: Any):  # type: ignore[no-untyped-def]
    effect = {"type": "shield", "max_hp_permille": permille, "affects": "allies", **extra}
    return make_skill(SID, {"type": "allies_in_radius", "radius": 1}, [effect], weapon_req="any")


def test_the_shield_is_the_casters_max_hp_times_permille_without_dice_or_attribute() -> None:
    state = battle(shield_skill(150), allies=[(4, 3)])
    caster = state.units[U1]
    caster.attributes = {k: 300 for k in caster.attributes}  # 屬性再高也不加
    result = cast(state)
    gained = {e.unit_id: e for e in of(result, ShieldGained)}
    expected = caster.max_hp * 150 // 1000
    assert gained[U1].amount == expected and gained[U1].rolls == ()
    assert gained[U2].amount == expected  # 友方也是看「施放者」的最大 HP


def test_the_shield_reads_the_casters_current_max_hp() -> None:
    state = battle(shield_skill(200))
    state.units[U1].max_hp += 500  # 例如變身加了最大 HP：看「目前」的
    result = cast(state)
    mine = [e.amount for e in of(result, ShieldGained) if e.unit_id == U1]
    assert mine == [state.units[U1].max_hp * 200 // 1000]


def test_the_budget_prices_the_permille_with_the_table_value() -> None:
    lib = library()
    per = lib.budget.shield_max_hp_points
    effect = skill_budget(shield_skill(150), lib).effects[0]
    assert effect.base == Fraction(150 * per, 100)
    three = skill_budget(shield_skill(150, duration=3), lib).effects[0]
    table = lib.budget.shield_duration_permille
    index = min(3 - lib.budget.shield_duration_start, len(table) - 1)
    assert three.base == Fraction(150 * per, 100) * Fraction(table[index], 1000)


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ({"dice": "2d6"}, "不能再填 dice"),
        ({"flat_bonus": 5}, "不能再填 dice"),
        ({"status": "shielded"}, "不能再填 dice"),
    ],
)
def test_the_max_hp_shield_cannot_mix_with_dice_flat_or_status(
    extra: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        shield_skill(150, **extra)


def test_a_shield_needs_dice_or_max_hp() -> None:
    with pytest.raises(ValidationError, match="dice 或 max_hp_permille"):
        make_skill(
            SID,
            {"type": "self"},
            [{"type": "shield", "affects": "self"}],
            weapon_req="any",
        )
