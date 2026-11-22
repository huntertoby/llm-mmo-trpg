"""暴擊傷害倍率（CR-1，``docs/design/05-戰鬥.md`` 5.4.2，#178）：算法與捨去、屬性和固定值不放大、
200% 時和改版前的「骰數加倍」逐位相同（結果與亂數取用次數）、預覽的分布。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U2, battle, of
from trpg.content.battle import Dice
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.effects import DamageEffect, run_effects
from trpg.engine.events import DamageDealt
from trpg.engine.preview import crit_distribution, dice_distribution
from trpg.engine.rules.combat import crit_extra_total
from trpg.shared.rng import Rng
from trpg.shared.types import Element


def _state() -> BattleState:
    skill = SkillDef.model_validate(
        make_skill(
            SID,
            {"type": "single", "range": 5},
            [{"type": "damage", "dice": "1d6", "element": "fire"}],
        ).model_dump(mode="json")
    )
    return battle(skill, [(5, 3)])


def _dice(count: int, sides: int) -> Dice:
    return Dice(count=count, sides=sides)


def _script(monkeypatch: pytest.MonkeyPatch, values: Sequence[int]) -> list[int]:
    queue = list(values)

    def randint(self: Rng, lo: int, hi: int) -> int:
        assert queue, "骰值用完了"
        value = queue.pop(0)
        assert lo <= value <= hi
        return value

    monkeypatch.setattr(Rng, "randint", randint)
    return queue


def _hit(state: BattleState, **fields: Any) -> DamageDealt:
    effect = DamageEffect(
        target_id=U2,
        element=Element.PHYSICAL,
        apply_element_mod=False,
        apply_weather=False,
        min_damage=0,
        **fields,
    )
    (event,) = of(run_effects(state, [effect]), DamageDealt)
    return event


# ---------------------------------------------------------------------------
# 算法與捨去（5.4.2 第 1 點的例子，骰面 ×10）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("permille", "amount"),
    [(None, 140), (2000, 140), (1500, 110), (2500, 170)],
)
def test_the_design_example(
    monkeypatch: pytest.MonkeyPatch, permille: int | None, amount: int
) -> None:
    """1d8、屬性加成 30：第一組擲 5、多擲的擲 6 → 200%＝140、150%＝110、250%＝170。"""
    state = _state()
    _script(monkeypatch, [5, 6])
    hit = _hit(state, dice=_dice(1, 8), scaled_permille=30_000, crit=True, crit_permille=permille)
    assert hit.rolls == (50, 60)  # 照擲出的原值記
    assert hit.amount == amount


def test_the_extra_set_is_floored(monkeypatch: pytest.MonkeyPatch) -> None:
    """多擲的那組乘（倍率 − 100%）後無條件捨去：50 × 55.5% ＝ 27.75 → 27。"""
    state = _state()
    _script(monkeypatch, [3, 5])
    hit = _hit(state, dice=_dice(1, 8), crit=True, crit_permille=1555)
    assert hit.amount == 30 + 27
    assert crit_extra_total(50, 1555) == 27
    assert crit_extra_total(55, 2500) == 82  # 82.5 → 82
    assert crit_extra_total(55, 1500) == 27  # 27.5 → 27


@pytest.mark.parametrize("permille", [1500, 2000, 2500, 3000])
def test_attribute_and_flat_are_not_amplified(
    monkeypatch: pytest.MonkeyPatch, permille: int
) -> None:
    """固定值 20、屬性加成 33 不放大，只有多擲的骰子乘倍率。"""
    state = _state()
    _script(monkeypatch, [4, 4, 2, 6])
    hit = _hit(
        state,
        dice=_dice(2, 6),
        flat=20,
        scaled_permille=33_000,
        crit=True,
        crit_permille=permille,
    )
    extra = 80 * (permille - 1000) // 1000
    assert hit.amount == 80 + extra + 20 + 33


def test_a_non_crit_ignores_the_multiplier(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    queue = _script(monkeypatch, [4])
    hit = _hit(state, dice=_dice(1, 6), crit=False, crit_permille=3000)
    assert hit.amount == 40 and hit.rolls == (40,) and queue == []


def test_exploding_dice_in_the_extra_set_are_amplified_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """爆骰照常，每一顆都會爆；多擲那組（含爆出來的）一起乘倍率。"""
    state = _state()
    queue = _script(monkeypatch, [3, 6, 2])
    hit = _hit(state, dice=_dice(1, 6), crit=True, crit_permille=2500, explode_max=2)
    assert hit.rolls == (30, 60, 20) and hit.exploded == 1 and queue == []
    assert hit.amount == 30 + (80 * 1500 // 1000)


# ---------------------------------------------------------------------------
# 200% ＝ 改版前（結果、亂數取用次數）
# ---------------------------------------------------------------------------


def _old_doubled(state: BattleState, dice: Dice, explode_max: int) -> tuple[tuple[int, ...], Any]:
    """改版前的算法：暴擊時一次擲 ``count × 2`` 顆（每顆照常爆骰）；回傳骰值與擲完後的亂數狀態。"""
    rng = Rng.from_state(state.rng_state)
    scale = state.ruleset.core.quantity_scale
    rolls: list[int] = []
    for _ in range(dice.count * 2):
        value = rng.roll(dice.sides)
        rolls.append(value * scale)
        again = 0
        while dice.sides > 1 and value == dice.sides and again < explode_max:
            value = rng.roll(dice.sides)
            rolls.append(value * scale)
            again += 1
    return tuple(rolls), rng.get_state()


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize(("count", "sides", "explode"), [(1, 8, 0), (3, 6, 0), (2, 4, 2)])
def test_two_hundred_percent_matches_the_old_doubled_dice(
    seed: int, count: int, sides: int, explode: int
) -> None:
    """200%：骰值、傷害與擲完後的亂數狀態都和改版前一次擲兩倍顆數相同。"""
    dice = _dice(count, sides)
    for permille in (None, 2000):
        state = _state().clone()
        state.rng_state = Rng(seed).get_state()
        old_rolls, old_rng = _old_doubled(state, dice, explode)
        effect = DamageEffect(
            target_id=U2,
            dice=dice,
            flat=10,
            scaled_permille=12_345,
            crit=True,
            crit_permille=permille,
            explode_max=explode,
            apply_element_mod=False,
            apply_weather=False,
        )
        result = run_effects(state, [effect])
        (hit,) = of(result, DamageDealt)
        assert hit.rolls == old_rolls
        assert hit.amount == sum(old_rolls) + 10 + 12
        assert result.state.rng_state == old_rng


@pytest.mark.parametrize(("count", "sides", "explode"), [(1, 8, 0), (2, 6, 0), (1, 6, 2)])
def test_the_preview_distribution_matches_at_two_hundred_percent(
    count: int, sides: int, explode: int
) -> None:
    doubled = dice_distribution(count * 2, sides, explode, 10)
    assert crit_distribution(count, sides, explode, 10, 2000) == doubled
    assert crit_distribution(count, sides, explode, 10, None) == doubled


def test_the_preview_distribution_at_two_hundred_fifty_percent() -> None:
    dist = crit_distribution(1, 2, 0, 10, 2500)
    # 第一組 10／20，多擲那組 10→15、20→30
    assert dist == {25: 1, 40: 1, 35: 1, 50: 1}


def test_the_effect_serialization_is_unchanged_without_a_multiplier() -> None:
    """沒有倍率（None）時不輸出 ``crit_permille``：效果的序列化和改版前一樣。"""
    assert "crit_permille" not in DamageEffect(target_id=U2, crit=True).model_dump(mode="json")
    dumped = DamageEffect(target_id=U2, crit=True, crit_permille=2500).model_dump(mode="json")
    assert dumped["crit_permille"] == 2500
