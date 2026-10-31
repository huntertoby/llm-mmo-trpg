"""BAL-13c：連鎖衰減（玩法決定 #77，06 6.5）與雷電擴散每輪一次（#78，05 互動規則表）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4, U5, script_rolls
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.effects import DamageEffect, run_effects
from trpg.engine.events import DamageDealt, Healed, ShieldGained, StatusApplied
from trpg.shared.types import Element, Team, UnitId

SID = "skill_t_chain"
CHAIN3 = {"type": "chain", "range": 6, "jumps": 3, "jump_range": 2}


def _chain_state(
    effects: list[dict[str, Any]], *, foes: bool = True, falloff: int = 250
) -> tuple[BattleState, list[UnitId]]:
    """施放者 U1 在 (0, 3)；四個同陣營目標排成一列 (2..5, 3)，連鎖依序跳 U2 → U3 → U4 → U5。"""
    skill = make_skill(SID, CHAIN3, effects)
    row = [(x, 3) for x in range(2, 6)]
    team = Team.ENEMY if foes else Team.ALLY
    m = make_map(
        FLAT7,
        ally=[(0, 3), *([] if foes else row)],
        enemy=row if foes else [(6, 6)],
    )
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([skill]))]
    spawns += [spawn(team, xy, no_reactions(max_hp=200)) for xy in row]
    if not foes:
        spawns.append(spawn(Team.ENEMY, (6, 6), no_reactions()))
    state = make_state(m, spawns, skills=[skill], chain_falloff_permille=falloff)
    for unit in state.units.values():
        if unit.team is team and unit.id != U1:
            unit.hp = 50  # 治療測試要有空間
    return give_turn(state, U1), [U2, U3, U4, U5]


def _cast(state: BattleState, target: UnitId) -> list[Any]:
    return list(resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=target)).events)


# ---------------------------------------------------------------------------
# 連鎖衰減（#77）
# ---------------------------------------------------------------------------


def test_chain_damage_falls_off_per_jump_down_to_the_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, order = _chain_state([{"type": "damage", "dice": "2d6", "element": "fire"}])
    script_rolls(monkeypatch, [19] * 4 + [6] * 8)  # 四次命中（不暴擊），每顆傷害骰 6
    events = _cast(state, U2)
    dealt = {e.target_id: e for e in events if isinstance(e, DamageDealt)}
    assert [dealt[u].chain_permille for u in order] == [1000, 750, 500, 250]
    first = dealt[U2].amount
    assert [dealt[u].amount for u in order] == [first * p // 1000 for p in (1000, 750, 500, 250)]


def test_chain_floor_holds_with_a_steeper_falloff(monkeypatch: pytest.MonkeyPatch) -> None:
    state, order = _chain_state([{"type": "damage", "dice": "2d6", "element": "fire"}], falloff=400)
    script_rolls(monkeypatch, [19] * 4 + [6] * 8)
    events = _cast(state, U2)
    dealt = {e.target_id: e.chain_permille for e in events if isinstance(e, DamageDealt)}
    assert [dealt[u] for u in order] == [1000, 600, 250, 250]  # 1000 − 800 ＝ 200 < 下限 250


def test_chain_falloff_reduces_heals_and_shields_but_not_statuses() -> None:
    effects: list[dict[str, Any]] = [
        {"type": "heal", "dice": "2d6", "affects": "allies"},
        {"type": "shield", "dice": "2d6", "affects": "allies", "duration": 2},
        {"type": "apply_status", "status": "slow", "duration": 2, "affects": "allies"},
    ]
    state, order = _chain_state(effects, foes=False)
    plain, _ = _chain_state(effects, foes=False, falloff=0)
    events = _cast(state, U2)
    base = _cast(plain, U2)
    heals = {e.target_id: e.amount for e in events if isinstance(e, Healed)}
    full_heals = {e.target_id: e.amount for e in base if isinstance(e, Healed)}
    assert heals[U2] == full_heals[U2]
    assert all(heals[u] <= full_heals[u] for u in order)
    assert heals[U5] < full_heals[U5]
    shields = {e.unit_id: e.amount for e in events if isinstance(e, ShieldGained)}
    full_shields = {e.unit_id: e.amount for e in base if isinstance(e, ShieldGained)}
    assert shields[U2] == full_shields[U2] and shields[U5] < full_shields[U5]
    slowed = {e.target_id for e in events if isinstance(e, StatusApplied)}
    assert slowed == set(order)  # 狀態照常施加到每一跳


def test_single_target_damage_has_no_falloff(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = make_skill(
        SID, {"type": "single", "range": 6}, [{"type": "damage", "dice": "2d6", "element": "fire"}]
    )
    m = make_map(FLAT7, ally=[(0, 3)], enemy=[(2, 3)])
    spawns = [
        spawn(Team.ALLY, (0, 3), caster_template([skill])),
        spawn(Team.ENEMY, (2, 3), no_reactions(max_hp=200)),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    script_rolls(monkeypatch, [19, 6, 6])
    (dealt,) = [e for e in _cast(state, U2) if isinstance(e, DamageDealt)]
    assert dealt.chain_permille == 1000


# ---------------------------------------------------------------------------
# 雷電擴散每輪一次（#78）
# ---------------------------------------------------------------------------


def _pool() -> BattleState:
    """一整排水 (0..3, 0)：U2、U3、U4 都是站在水裡的敵人；兩個我方施放者 U1、U5 在水外。"""
    m = make_map(
        "0000\n0000",
        surfaces=[(x, 0, "water") for x in range(4)],
        ally=[(0, 1), (1, 1)],
        enemy=[(0, 0)],
    )
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 1), template("hero_mage", max_hp=200), "lightning_staff"),
            spawn(Team.ENEMY, (0, 0), no_reactions(max_hp=200)),
            spawn(Team.ENEMY, (1, 0), no_reactions(max_hp=200)),
            spawn(Team.ENEMY, (2, 0), no_reactions(max_hp=200)),
            spawn(Team.ALLY, (1, 1), template("hero_mage", max_hp=200), "lightning_staff"),
        ],
    )


def _bolt(target: UnitId, source: UnitId = U1) -> DamageEffect:
    return DamageEffect(
        target_id=target, source_id=source, cause="attack", element=Element.LIGHTNING, flat=10
    )


def _conducted(events: list[Any]) -> list[str]:
    return sorted(
        e.target_id for e in events if isinstance(e, DamageDealt) and e.cause == "conduct"
    )


def test_conduct_hits_each_unit_once_per_round_across_strikes_and_casters() -> None:
    state = _pool()
    first = run_effects(state, [_bolt(U2)])
    assert _conducted(first.events) == [U3, U4]
    # 同一輪：另一名施放者再劈 U3 → U3 直接命中照常；U2 沒受過擴散，受一次；U4 已受過，不再受
    second = run_effects(first.state, [_bolt(U3, source=U5)])
    direct = [
        e.target_id for e in second.events if isinstance(e, DamageDealt) and e.cause == "attack"
    ]
    assert direct == [U3]
    assert _conducted(second.events) == [U2]
    third = run_effects(second.state, [_bolt(U4)])
    assert _conducted(third.events) == []  # 本輪每個人都受過擴散了
    later = third.state.clone()
    later.round += 1  # 下一輪重新計算
    assert _conducted(run_effects(later, [_bolt(U2)]).events) == [U3, U4]


def test_two_strikes_in_one_batch_conduct_once() -> None:
    result = run_effects(_pool(), [_bolt(U2), _bolt(U2)])
    assert _conducted(result.events) == [U3, U4]
    assert all(result.state.units[u].conducted_round == result.state.round for u in (U3, U4))
    assert result.state.units[U2].conducted_round == 0  # 直接命中不算擴散
