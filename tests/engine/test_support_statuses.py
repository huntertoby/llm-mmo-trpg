"""Phase 2D-1 3.9 第 1–4、7 項：護衛、激昂、加速、再生，以及技能施加 ``defending``。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, make_map, make_skill, make_state, spawn, template
from tests.engine.skill_helpers import U1, U2, battle, cast, of, script_rolls
from trpg.engine import Attack, EndTurn, UseSkill, preview, resolve
from trpg.engine.control import plan_status
from trpg.engine.effects import DamageEffect, run_effects
from trpg.engine.events import DamageDealt, Healed, StatusApplied, TurnStarted
from trpg.engine.rules.combat import defense_value_permille
from trpg.engine.rules.statuses import effective_attribute, move_points_for_turn
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Attribute, Element, Team

FLAT = "\n".join(["000000"] * 6)
SID = "skill_t_prim"


def _duel() -> BattleState:
    """U1 我方戰士 (1, 1)，U2 敵方盜賊 (2, 1)；輪到 U1。"""
    m = make_map(FLAT, ally=[(1, 1)], enemy=[(2, 1)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 1), template("hero_fighter", reactions=[])),
            spawn(Team.ENEMY, (2, 1), template("bandit", reactions=[])),
        ],
    )
    return give_turn(state, U1)


def _with(state: BattleState, uid: str, status_id: str, remaining: int = 2) -> BattleState:
    s = state.clone()
    unit = s.units[uid]  # type: ignore[index]
    others = [x for x in unit.statuses if x.status_id != status_id]
    unit.statuses = sorted(
        [*others, StatusInstance(status_id=status_id, remaining=remaining)],
        key=lambda x: x.status_id,
    )
    return s


def _hit(state: BattleState, flat: int = 10) -> DamageDealt:
    effect = DamageEffect(
        source_id=U1, target_id=U2, cause="attack", flat=flat, element=Element.PHYSICAL
    )
    (event,) = of(run_effects(state, [effect]), DamageDealt)
    return event


# ---------------------------------------------------------------------------
# 1. guarded
# ---------------------------------------------------------------------------


def test_guarded_takes_seventy_percent_of_the_damage() -> None:
    plain = _hit(_duel()).amount
    guarded = _hit(_with(_duel(), U2, "guarded"))
    assert plain == 10
    assert guarded.amount == 7 and guarded.status_ppm == 700_000


def test_guarded_and_vulnerable_multiply_in_order_and_floor_once() -> None:
    state = _with(_with(_duel(), U2, "guarded"), U2, "vulnerable")
    event = _hit(state, flat=11)
    assert event.status_ppm == 700 * 1250
    assert event.amount == 9  # 11 × 0.875 = 9.625 → 9（逐步捨去會得到 8）


# ---------------------------------------------------------------------------
# 2. empowered
# ---------------------------------------------------------------------------


def test_empowered_adds_two_to_every_effective_attribute() -> None:
    state = _with(_duel(), U1, "empowered")
    rules = state.ruleset
    unit = state.units[U1]
    for attr in Attribute:
        assert effective_attribute(rules, unit, attr) == unit.attributes[attr] + 2
    plain = _duel()
    assert defense_value_permille(unit, rules) > defense_value_permille(plain.units[U1], rules)


def test_empowered_changes_the_hit_chance_and_preview_matches_the_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain, boosted = _duel(), _with(_duel(), U1, "empowered")
    action = Attack(unit_id=U1, target_id=U2)
    assert (p_boost := preview(boosted, action)).hit_chance is not None
    assert (p_plain := preview(plain, action)).hit_chance is not None
    assert p_boost.hit_chance >= p_plain.hit_chance
    # 縮放屬性也用加值後的屬性：預覽的最小傷害 == 固定骰值的實際傷害
    script_rolls(monkeypatch, [19] + [1] * 10)
    low = resolve(boosted, action)
    (dealt,) = [e for e in of(low, DamageDealt) if e.cause == "attack"]
    assert p_boost.damage is not None and dealt.amount == p_boost.damage.minimum
    assert p_boost.damage.minimum > preview(plain, action).damage.minimum  # type: ignore[union-attr]


def test_empowered_boosts_spell_scaling_and_the_status_save() -> None:
    skill = make_skill(
        SID, {"type": "single", "range": 5}, [{"type": "damage", "dice": "1d4", "element": "fire"}]
    )
    state = battle(skill, foes=[(3, 5)])
    boosted = _with(state, U1, "empowered")
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    low = preview(state, action).targets[0].damage
    high = preview(boosted, action).targets[0].damage
    assert low is not None and high is not None
    assert high.minimum == low.minimum + 1  # 智力 +2 × 0.5
    # 抵抗判定：受術者的 save_attr 也看有效屬性
    shielded_wil = _with(state, U2, "empowered")
    base_value = plan_status(state, state.units[U2], "taunted").defense_value
    assert (
        plan_status(shielded_wil, shielded_wil.units[U2], "taunted").defense_value == base_value + 2
    )


# ---------------------------------------------------------------------------
# 3. hasted
# ---------------------------------------------------------------------------


def test_hasted_multiplies_the_move_points_by_one_and_a_half() -> None:
    state = _with(_duel(), U2, "hasted")
    speed = state.units[U2].speed
    assert move_points_for_turn(state.ruleset, state.units[U2]) == speed * 1500 // 1000
    result = resolve(state, EndTurn(unit_id=U1))
    started = next(e for e in of(result, TurnStarted) if e.unit_id == U2)
    assert started.move_points == speed * 3 // 2


def test_hasted_and_slow_multiply_in_order() -> None:
    state = _with(_with(_duel(), U2, "hasted"), U2, "slow")
    speed = state.units[U2].speed
    # 狀態依 ID 排序：hasted（×1.5）先、slow（×0.5）後，逐步捨去
    assert (
        move_points_for_turn(state.ruleset, state.units[U2]) == speed * 1500 // 1000 * 500 // 1000
    )


# ---------------------------------------------------------------------------
# 4. regenerating
# ---------------------------------------------------------------------------


def test_regenerating_heals_at_turn_start_and_lasts_three_turns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _duel()
    state.units[U2].hp = 10
    state = _with(state, U2, "regenerating", 3)
    script_rolls(monkeypatch, [3, 3, 3])
    expected_remaining = [2, 1, None]
    for remaining in expected_remaining:
        result = resolve(state, EndTurn(unit_id=U1))
        (healed,) = [e for e in of(result, Healed) if e.target_id == U2]
        assert healed.amount == 3 and healed.rolls == (3,)
        state = resolve(result.state, EndTurn(unit_id=U2)).state
        status = state.units[U2].get_status("regenerating")
        assert (None if status is None else status.remaining) == remaining
    assert state.units[U2].hp == 19


def test_regenerating_is_halved_by_poison(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _with(_with(_duel(), U2, "regenerating", 3), U2, "poison", 3)
    state.units[U2].hp = state.units[U2].max_hp - 10
    script_rolls(monkeypatch, [2, 4])  # 狀態依 ID 排序：poison 的 1d4＝2，再 regenerating 的 1d4＝4
    result = resolve(state, EndTurn(unit_id=U1))
    (healed,) = [e for e in of(result, Healed) if e.target_id == U2]
    assert healed.received_permille == 500 and healed.amount == 2  # 4 × 50%


def test_regenerating_never_exceeds_max_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _with(_duel(), U2, "regenerating", 3)
    state.units[U2].hp = state.units[U2].max_hp - 1
    script_rolls(monkeypatch, [4])
    result = resolve(state, EndTurn(unit_id=U1))
    (healed,) = [e for e in of(result, Healed) if e.target_id == U2]
    assert healed.amount == 1
    assert result.state.units[U2].hp == result.state.units[U2].max_hp


# ---------------------------------------------------------------------------
# 7. 技能施加 defending
# ---------------------------------------------------------------------------


def test_a_skill_can_apply_defending_to_an_ally_like_the_defend_action() -> None:
    skill = make_skill(
        SID,
        {"type": "single", "range": 4},
        [{"type": "apply_status", "status": "defending", "affects": "allies"}],
    )
    state = battle(skill, foes=[(6, 6)], allies=[(3, 4)])
    result = cast(state, target_id=U2)
    applied = [e for e in of(result, StatusApplied) if e.target_id == U2]
    assert [e.status_id for e in applied] == ["defending"]
    ally = result.state.units[U2]
    status = ally.get_status("defending")
    assert status is not None and status.remaining is None  # 持續到自己的下回合開始
    rules = state.ruleset
    plain = state.units[U2]
    assert defense_value_permille(ally, rules) == defense_value_permille(plain, rules) // 1000 * (
        1000 + rules.core.defend_defense_bonus_permille
    )
    # 與防禦動作相同：到自己的下回合開始時移除
    assert state.ruleset.status_def("defending").expires == "own_turn_start"
