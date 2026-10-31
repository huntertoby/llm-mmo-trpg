"""BAL-12e（玩法決定 #76，06 6.3、6.34.9）：狀態與表面的強度。

- 數值型狀態（非控制、非姿態）的 ``magnitude_permille`` 存進狀態實例：每回合傷害與治療乘上它，
  倍率欄位離中性值的距離放大（減益放大不利的一邊），屬性與攻擊加值乘上它（無條件捨去）；
- 沒有數值的狀態與控制類狀態一律 1000；
- 表面的強度記在地圖格上：回合開始的傷害與表面施加的狀態乘上它；換成別種表面時回到 1000。
"""

from __future__ import annotations

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.engine import EndTurn, ResolveResult, resolve
from trpg.engine.effects import ApplyStatusEffect, CreateSurfaceEffect, run_effects
from trpg.engine.events import DamageDealt, Healed
from trpg.engine.rules.statuses import (
    damage_dealt_permille,
    effective_attribute,
    healing_received_permille,
)
from trpg.engine.state import BattleState
from trpg.shared.types import Attribute, Surface, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
FLAT = "\n".join(["000000"] * 6)


def _duel() -> BattleState:
    m = make_map(FLAT, ally=[(1, 1)], enemy=[(2, 1)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 1), template("hero_fighter", reactions=[])),
            spawn(Team.ENEMY, (2, 1), template("bandit", reactions=[])),
        ],
    )
    return give_turn(state, U1)


def _apply(state: BattleState, status: str, magnitude: int, target: UnitId = U2) -> BattleState:
    effect = ApplyStatusEffect(
        target_id=target, status_id=status, source_id=U1, duration=3, magnitude_permille=magnitude
    )
    return run_effects(state, [effect]).state


def _ticks(result: ResolveResult, cause: str) -> list[DamageDealt]:
    return [
        e
        for e in result.events
        if isinstance(e, DamageDealt) and e.target_id == U2 and e.cause == cause
    ]


def test_poison_strength_scales_the_tick_and_the_healing_cut() -> None:
    state = _apply(_duel(), "poison", 1500)
    status = state.units[U2].get_status("poison")
    assert status is not None and status.magnitude_permille == 1500
    rules = state.ruleset
    # 中毒受到的治療 500‰：不利的一邊放大 ×1.5 → 250‰
    assert healing_received_permille(rules, state.units[U2]) == 250
    result = resolve(with_rolls(state, [(4, 3)]), EndTurn(unit_id=U1))
    (tick,) = _ticks(result, "status")
    assert tick.rolls == (3,) and tick.amount == 4  # 3 × 1.5 = 4.5 → 4
    # 回合結束倒數後強度還在
    kept = result.state.units[U2].get_status("poison")
    assert kept is not None and kept.magnitude_permille == 1500


def test_strength_floors_and_scales_debuff_and_buff_numbers() -> None:
    state = _apply(_apply(_duel(), "weaken", 1500), "empowered", 1500, target=U1)
    rules = state.ruleset
    assert damage_dealt_permille(rules, state.units[U2], None) == 625  # 1000 − 250 × 1.5
    hero = state.units[U1]
    assert effective_attribute(rules, hero, Attribute.STR) == hero.attributes[Attribute.STR] + 3


def test_unscalable_and_control_statuses_ignore_strength() -> None:
    state = _apply(_apply(_duel(), "marked", 1500), "slow", 1500)
    for status_id in ("marked", "slow"):
        status = state.units[U2].get_status(status_id)
        assert status is not None and status.magnitude_permille == 1000


def test_strength_1000_keeps_old_numbers() -> None:
    plain = _apply(_duel(), "poison", 1000)
    result = resolve(with_rolls(plain, [(4, 3)]), EndTurn(unit_id=U1))
    assert _ticks(result, "status")[0].amount == 3


def test_poison_surface_strength_scales_the_turn_start_damage() -> None:
    state = run_effects(
        _duel(),
        [CreateSurfaceEffect(pos=(2, 1), surface=Surface.POISON, magnitude_permille=1500)],
    ).state
    assert state.tile(2, 1).surface_magnitude_permille == 1500
    result = resolve(with_rolls(state, [(4, 4)]), EndTurn(unit_id=U1))
    (tick,) = _ticks(result, "surface")
    assert tick.amount == 6  # 4 × 1.5


def test_fire_surface_passes_strength_to_burning_and_water_resets_it() -> None:
    state = run_effects(
        _duel(),
        [CreateSurfaceEffect(pos=(2, 1), surface=Surface.FIRE, magnitude_permille=1300)],
    ).state
    burning = state.units[U2].get_status("burning")
    assert burning is not None and burning.magnitude_permille == 1300
    state = run_effects(state, [CreateSurfaceEffect(pos=(2, 1), surface=Surface.WATER)]).state
    tile = state.tile(2, 1)
    assert tile.surface is not Surface.FIRE and tile.surface_magnitude_permille == 1000


def test_regeneration_strength_scales_the_heal() -> None:
    state = _apply(_duel(), "regenerating", 2000)
    state.units[U2].hp = 1
    result = resolve(with_rolls(state, [(4, 2)]), EndTurn(unit_id=U1))
    heals = [e for e in result.events if isinstance(e, Healed) and e.target_id == U2]
    assert heals and heals[0].amount == 4  # 2 × 2.0


def _reapply(state: BattleState, duration: int, magnitude: int) -> BattleState:
    effect = ApplyStatusEffect(
        target_id=U2,
        status_id="poison",
        source_id=U1,
        duration=duration,
        magnitude_permille=magnitude,
    )
    return run_effects(state, [effect]).state


def test_reapply_strength_follows_the_longer_instance_then_the_higher() -> None:
    """BAL-12f：重複施加時強度跟著剩餘回合較長的；剩餘回合相同取較高者。"""

    def held(state: BattleState) -> tuple[int | None, int]:
        status = state.units[U2].get_status("poison")
        assert status is not None
        return status.remaining, status.magnitude_permille

    base = _reapply(_duel(), 3, 1500)
    assert held(_reapply(base, 5, 1100)) == (5, 1100)  # 新的較長：強度跟新的（即使較低）
    assert held(_reapply(base, 2, 2000)) == (3, 1500)  # 舊的較長：強度留舊的
    assert held(_reapply(base, 3, 1100)) == (3, 1500)  # 相同回合：取較高（舊的）
    assert held(_reapply(base, 3, 1800)) == (3, 1800)  # 相同回合：取較高（新的）
