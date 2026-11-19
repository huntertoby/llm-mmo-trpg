"""X10-2a：程式認得 ``quantity_scale``（``docs/phases/PhaseX10-2a計畫.md``）。

內容的 ``quantity_scale`` 是 1，所有結果都不變；這裡把它換成 10 檢查各處的倍率。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.content.library import ContentLibrary
from trpg.content.rules import CoreRules
from trpg.engine import Attack, BattleState, resolve
from trpg.engine.effects import (
    ApplyStatusEffect,
    DamageEffect,
    HealEffect,
    ShieldEffect,
    run_effects,
)
from trpg.engine.events import AttackRolled, DamageDealt, Healed, ShieldGained
from trpg.engine.preview import dice_distribution
from trpg.shared.types import Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def test_content_scale_is_one(library: ContentLibrary) -> None:
    assert library.ruleset.core.quantity_scale == 1


@pytest.mark.parametrize("value", [0, 2, 5, 100])
def test_scale_accepts_only_one_or_ten(library: ContentLibrary, value: int) -> None:
    data = library.ruleset.core.model_dump()
    assert CoreRules.model_validate({**data, "quantity_scale": 10}).quantity_scale == 10
    with pytest.raises(ValidationError):
        CoreRules.model_validate({**data, "quantity_scale": value})


# ---------------------------------------------------------------------------
# 引擎：骰面 × scale，d20 不乘；寫死的 1 點下限 × scale


def _duel(scale: int) -> BattleState:
    m = make_map("000\n000\n000")
    a = spawn(Team.ALLY, (0, 1), "hero_fighter", weapon="one_handed_sword")
    t = spawn(Team.ENEMY, (1, 1), template("bandit", reactions=[]))
    return give_turn(make_state(m, [a, t], quantity_scale=scale), U1)


@pytest.mark.parametrize("scale", [1, 10])
def test_damage_heal_shield_dice_times_scale(scale: int) -> None:
    state = _duel(scale)
    damage = DamageEffect(target_id=U2, dice="1d6", flat=6)  # type: ignore[arg-type]
    events = run_effects(with_rolls(state, [(6, 4)]), [damage]).events
    dealt = next(e for e in events if isinstance(e, DamageDealt))
    assert dealt.rolls == (4 * scale,)
    assert dealt.amount == 4 * scale + 6
    heal = HealEffect(target_id=U2, dice="1d4")  # type: ignore[arg-type]
    events = run_effects(with_rolls(state, [(4, 3)]), [heal]).events
    assert next(e for e in events if isinstance(e, Healed)).rolls == (3 * scale,)
    shield = ShieldEffect(target_id=U1, dice="1d8")  # type: ignore[arg-type]
    events = run_effects(with_rolls(state, [(8, 5)]), [shield]).events
    assert next(e for e in events if isinstance(e, ShieldGained)).amount == 5 * scale


@pytest.mark.parametrize("scale", [1, 10])
def test_d20_is_not_scaled(scale: int) -> None:
    state = with_rolls(_duel(scale), [(20, 15)])
    events = resolve(state, Attack(unit_id=U1, target_id=U2)).events
    rolled = next(e for e in events if isinstance(e, AttackRolled))
    assert rolled.natural == 15
    dealt = next(e for e in events if isinstance(e, DamageDealt))
    assert dealt.rolls and all(r % scale == 0 and 0 < r <= 20 * scale for r in dealt.rolls)


@pytest.mark.parametrize("scale", [1, 10])
def test_undying_leaves_one_point_times_scale(scale: int) -> None:
    state = _duel(scale)
    state = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="undying")]).state
    hp = state.units[U2].hp
    after = run_effects(state, [DamageEffect(target_id=U2, flat=hp + 50)]).state
    assert after.units[U2].hp == scale


def test_preview_distribution_scales_faces() -> None:
    assert dice_distribution(2, 4, scale=10) == {
        k * 10: v for k, v in dice_distribution(2, 4).items()
    }
    assert dice_distribution(1, 6, 2, 10) == {
        k * 10: v for k, v in dice_distribution(1, 6, 2).items()
    }
