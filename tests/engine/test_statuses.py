"""Phase 2B-1 3.1：七種新狀態的數值效果（驗收 2）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.engine import EndTurn, Move, ResolveResult, legal_actions, resolve
from trpg.engine.effects import DamageEffect, HealEffect, PushEffect, run_effects
from trpg.engine.events import (
    DamageCause,
    DamageDealt,
    EventBase,
    Healed,
    ReactionTriggered,
    TurnEnded,
    TurnSkipped,
    TurnStarted,
    UnitMoved,
)
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
FLAT = "\n".join(["000000"] * 6)


def _duel(*, foe: str = "bandit", foe_pos: tuple[int, int] = (2, 1)) -> BattleState:
    """U1 是我方戰士 (1, 1)，U2 是敵人（預設盜賊，無反應規則可由 template 另給）。輪到 U1。"""
    m = make_map(FLAT, ally=[(1, 1)], enemy=[foe_pos])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 1), template("hero_fighter", reactions=[])),
            spawn(Team.ENEMY, foe_pos, template(foe, reactions=[])),
        ],
    )
    return give_turn(state, U1)


def _with_status(state: BattleState, uid: UnitId, status_id: str, remaining: int) -> BattleState:
    s = state.clone()
    unit = s.units[uid]
    others = [x for x in unit.statuses if x.status_id != status_id]
    unit.statuses = sorted(
        [*others, StatusInstance(status_id=status_id, remaining=remaining)],
        key=lambda x: x.status_id,
    )
    return s


def _of[E: EventBase](result: ResolveResult, kind: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, kind)]


def _end_turn(state: BattleState) -> ResolveResult:
    return resolve(state, EndTurn(unit_id=U1))


# ---------------------------------------------------------------------------
# 緩速
# ---------------------------------------------------------------------------


def test_slow_halves_the_move_points_rounding_down() -> None:
    state = _with_status(_duel(), U2, "slow", 2)
    result = _end_turn(state)
    started = [e for e in _of(result, TurnStarted) if e.unit_id == U2]
    assert started, "輪到 U2 時應該有 turn_started"
    speed = state.units[U2].speed
    assert started[0].move_points == speed * 500 // 1000 == 2  # 速度 5 → 2（無條件捨去）
    healthy = _end_turn(_duel())
    assert next(e for e in _of(healthy, TurnStarted) if e.unit_id == U2).move_points == speed


# ---------------------------------------------------------------------------
# 定身
# ---------------------------------------------------------------------------


def test_root_blocks_voluntary_movement_but_not_forced_movement() -> None:
    state = _with_status(_duel(), U1, "root", 1)
    assert not [a for a in legal_actions(state) if isinstance(a, Move)]
    with pytest.raises(IllegalActionError, match="定身"):
        resolve(state, Move(unit_id=U1, path=(Pos(x=1, y=1), Pos(x=1, y=2))))
    # 強制位移照常：被推擊的定身單位仍然移動
    pushed = run_effects(
        state, [PushEffect(source_id=U2, target_id=U1, direction=(0, 1), distance=1)]
    )
    moves = _of(pushed, UnitMoved)
    assert [(m.unit_id, m.to_pos) for m in moves] == [(U1, Pos(x=1, y=2))]
    assert pushed.state.units[U1].xy == (1, 2)


def test_without_root_the_unit_can_move() -> None:
    assert any(isinstance(a, Move) for a in legal_actions(_duel()))


# ---------------------------------------------------------------------------
# 暈眩
# ---------------------------------------------------------------------------


def test_stun_skips_the_whole_turn_and_expires() -> None:
    state = _with_status(_duel(), U2, "stun", 1)
    result = _end_turn(state)
    skipped = _of(result, TurnSkipped)
    assert [(e.unit_id, e.status_id) for e in skipped] == [(U2, "stun")]
    started = [e for e in _of(result, TurnStarted) if e.unit_id == U2]
    assert started and started[0].ap == 3  # 回合開始照常發生，然後整個回合被跳過
    ended = [e for e in _of(result, TurnEnded) if e.unit_id == U2]
    assert ended and ended[0].ap_carried == 0
    assert not result.state.units[U2].has_status("stun")  # 倒數後移除
    assert result.state.units[U2].ap == 0 and result.state.units[U2].move_points == 0
    # 跳過之後輪到下一位（U1 的新一輪），而不是讓 U2 行動
    assert result.state.active_unit == U1


def test_stun_still_ticks_damage_and_cooldowns_at_turn_start() -> None:
    state = _with_status(_with_status(_duel(), U2, "stun", 1), U2, "bleed", 3)
    state.units[U2].cooldowns["skill_x"] = 2
    result = _end_turn(with_rolls(state, [(4, 2)]))
    ticks = [e for e in _of(result, DamageDealt) if e.target_id == U2 and e.cause == "status"]
    assert [t.amount for t in ticks] == [2]
    assert result.state.units[U2].cooldowns == {"skill_x": 1}


def test_a_stunned_unit_cannot_react() -> None:
    def leave_reactor_reach(stunned: bool) -> list[ReactionTriggered]:
        m = make_map(FLAT, ally=[(1, 1)], enemy=[(2, 1)])
        state = give_turn(
            make_state(
                m,
                [
                    spawn(Team.ALLY, (1, 1), template("hero_fighter", reactions=[])),
                    spawn(Team.ENEMY, (2, 1), "bandit"),  # 預設反應：藉機攻擊
                ],
            ),
            U1,
        )
        if stunned:
            state = _with_status(state, U2, "stun", 1)
        result = resolve(state, Move(unit_id=U1, path=(Pos(x=1, y=1), Pos(x=0, y=1))))
        return _of(result, ReactionTriggered)

    assert [r.unit_id for r in leave_reactor_reach(False)] == [U2]
    assert leave_reactor_reach(True) == []


# ---------------------------------------------------------------------------
# 虛弱與易傷
# ---------------------------------------------------------------------------


def _hit(
    state: BattleState,
    *,
    flat: int = 10,
    cause: DamageCause = "attack",
    percent: int | None = None,
    min_damage: int = 1,
) -> DamageDealt:
    """U1 對 U2 的傷害（固定值，沒有骰子）；``percent`` 給定時為最大 HP 百分比傷害。"""
    effect = DamageEffect(
        source_id=U1,
        target_id=U2,
        cause=cause,
        flat=flat,
        element=Element.PHYSICAL,
        mode="roll" if percent is None else "percent_max_hp",
        permille=percent or 0,
        apply_element_mod=percent is None,
        min_damage=min_damage,
    )
    (event,) = _of(run_effects(state, [effect]), DamageDealt)
    return event


def test_weaken_scales_the_attackers_attack_damage() -> None:
    base = _duel()
    assert _hit(base).amount == 10
    weak = _hit(_with_status(base, U1, "weaken", 2))
    assert weak.amount == 7  # 10 × 750‰ = 7.5 → 7
    assert weak.status_ppm == 750_000


def test_weaken_only_applies_to_attack_damage() -> None:
    weak = _with_status(_duel(), U1, "weaken", 2)
    assert _hit(weak, cause="status").amount == 10
    assert _hit(weak, cause="explosion").amount == 10


def test_vulnerable_scales_dice_damage_taken() -> None:
    state = _with_status(_duel(), U2, "vulnerable", 2)
    event = _hit(state)
    assert event.amount == 12  # 10 × 1250‰ = 12.5 → 12
    assert event.status_ppm == 1_250_000
    assert _hit(state, cause="explosion").amount == 12  # 不限傷害來源


def test_vulnerable_does_not_scale_percentage_damage() -> None:
    state = _with_status(_duel(), U2, "vulnerable", 2)
    plain = _hit(_duel(), percent=100)
    boosted = _hit(state, percent=100)
    assert plain.amount == boosted.amount == 3  # 30 HP × 10%
    assert boosted.status_ppm == 1_000_000


def test_weaken_and_vulnerable_multiply_and_floor_once() -> None:
    state = _with_status(_with_status(_duel(), U1, "weaken", 2), U2, "vulnerable", 2)
    event = _hit(state)
    assert event.status_ppm == 750 * 1250
    assert event.amount == 9  # 10 × 0.75 × 1.25 = 9.375 → 9（只在最後捨去一次）
    # 逐步捨去會得到 7 × 1.25 = 8，所以這同時證明沒有中間捨去
    assert _hit(state, flat=16).amount == 15  # 16 × 0.9375 = 15.0


def test_status_multipliers_respect_the_minimum_damage() -> None:
    weak = _with_status(_duel(), U1, "weaken", 2)
    assert _hit(weak, flat=1).amount == 1  # 0.75 → 0，最低傷害 1
    assert _hit(weak, flat=1, min_damage=0).amount == 0


# ---------------------------------------------------------------------------
# 流血與中毒
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "element"), [("bleed", Element.PHYSICAL), ("poison", Element.POISON)]
)
def test_bleed_and_poison_tick_at_turn_start(status: str, element: Element) -> None:
    state = with_rolls(_with_status(_duel(), U2, status, 3), [(4, 3)])
    result = _end_turn(state)
    ticks = [e for e in _of(result, DamageDealt) if e.target_id == U2 and e.cause == "status"]
    assert len(ticks) == 1
    assert (ticks[0].element, ticks[0].rolls, ticks[0].amount) == (element, (3,), 3)
    assert result.state.units[U2].hp == state.units[U2].hp - 3
    assert result.state.units[U2].get_status(status) is not None


def test_bleed_lasts_three_turns() -> None:
    state = _with_status(_duel(), U2, "bleed", 3)
    for expected_remaining in (2, 1, None):
        # U1 結束 → U2 的回合開始（流血）→ 手動結束 U2 → 回到 U1
        state = resolve(state, EndTurn(unit_id=U1)).state
        assert state.active_unit == U2
        state = resolve(state, EndTurn(unit_id=U2)).state
        status = state.units[U2].get_status("bleed")
        assert (None if status is None else status.remaining) == expected_remaining


def test_poison_halves_healing_received() -> None:
    def healed(poisoned: bool) -> Healed:
        state = _duel()
        state.units[U2].hp = 10
        if poisoned:
            state = _with_status(state, U2, "poison", 3)
        result = run_effects(state, [HealEffect(target_id=U2, flat=10)])
        (event,) = _of(result, Healed)
        return event

    assert healed(False).amount == 10
    sick = healed(True)
    assert (sick.amount, sick.received_permille) == (5, 500)


def test_poison_healing_rounds_down() -> None:
    state = _with_status(_duel(), U2, "poison", 3)
    state.units[U2].hp = 10
    result = run_effects(state, [HealEffect(target_id=U2, flat=7)])
    assert _of(result, Healed)[0].amount == 3  # 3.5 → 3
