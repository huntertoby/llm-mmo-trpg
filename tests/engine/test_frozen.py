"""Phase 2H-1 3.1–3.2：冰凍狀態（跳過回合、遇火解除、Boss 轉換、控制遞減）與冰元素凍住水中單位。"""

from __future__ import annotations

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template
from trpg.engine import BattleState, EndTurn, ResolveResult, resolve
from trpg.engine.control import plan_status
from trpg.engine.effects import (
    ApplyStatusEffect,
    DamageEffect,
    ElementTouchEffect,
    run_effects,
)
from trpg.engine.events import (
    EventBase,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    TurnSkipped,
)
from trpg.engine.state import StatusInstance
from trpg.shared.types import Element, Pos, Surface, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def _duel(*, surface: str | None = None, foe: str = "bandit", boss: bool = False) -> BattleState:
    """U1 我方戰士 (0, 0)；U2 敵人 (1, 0)（可選：腳下是 ``surface``、帶 boss 標籤）。"""
    m = make_map(
        "000\n000",
        ally=[(0, 0)],
        enemy=[(1, 0)],
        surfaces=[] if surface is None else [(1, 0, surface)],
    )
    tags = ("boss",) if boss else ()
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", reactions=[])),
            spawn(Team.ENEMY, (1, 0), template(foe, reactions=[], tags=tags)),
        ],
    )
    return give_turn(state, U1)


def _frozen(state: BattleState, remaining: int = 1) -> BattleState:
    s = state.clone()
    s.units[U2].statuses = [StatusInstance("frozen", remaining, U1)]
    return s


def _of[E: EventBase](result: ResolveResult, kind: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, kind)]


def test_frozen_skips_the_turn_and_expires() -> None:
    result = resolve(_frozen(_duel()), EndTurn(unit_id=U1))
    assert [(e.unit_id, e.status_id) for e in _of(result, TurnSkipped)] == [(U2, "frozen")]
    assert not result.state.units[U2].has_status("frozen")
    assert result.state.units[U2].ap == 0
    assert result.state.active_unit == U1


def test_fire_damage_thaws_the_unit_with_an_event() -> None:
    state = _frozen(_duel())
    result = run_effects(state, [DamageEffect(target_id=U2, element=Element.FIRE, flat=3)])
    (removed,) = _of(result, StatusRemoved)
    assert (removed.target_id, removed.status_id, removed.reason) == (U2, "frozen", "thawed")
    assert not result.state.units[U2].has_status("frozen")


def test_non_fire_damage_does_not_thaw() -> None:
    for element in (Element.PHYSICAL, Element.ICE, Element.LIGHTNING):
        state = _frozen(_duel())
        result = run_effects(state, [DamageEffect(target_id=U2, element=element, flat=3)])
        assert result.state.units[U2].has_status("frozen"), element
        assert not _of(result, StatusRemoved)


def test_frozen_on_a_boss_becomes_slow() -> None:
    state = _duel(boss=True)
    result = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="frozen")])
    (conv,) = _of(result, StatusConverted)
    assert (conv.from_status, conv.to_status) == ("frozen", "slow")
    boss = result.state.units[U2]
    assert boss.has_status("slow") and not boss.has_status("frozen")


def test_frozen_shares_hard_control_diminishing_returns_with_stun() -> None:
    state = _duel()
    result = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="frozen")])
    unit = result.state.units[U2]
    assert unit.control_dr == {"hard": state.round + 2}
    assert plan_status(result.state, unit, "stun").diminished
    assert plan_status(result.state, unit, "frozen").diminished
    assert not plan_status(result.state, unit, "root").diminished


# ---------------------------------------------------------------------------
# 3.2 冰元素凍住水中的單位
# ---------------------------------------------------------------------------


def test_ice_damage_freezes_a_unit_standing_in_water_and_the_water_freezes_too() -> None:
    """順序：判斷單位條件用觸及前的表面（水），同一次觸及水才變冰。"""
    state = _duel(surface="water")
    result = run_effects(
        state, [DamageEffect(target_id=U2, element=Element.ICE, flat=2, source_id=U1)]
    )
    assert result.state.tile(1, 0).surface is Surface.ICE
    unit = result.state.units[U2]
    assert unit.has_status("frozen")
    (applied,) = _of(result, StatusApplied)
    assert (applied.status_id, applied.duration, applied.source_id) == ("frozen", 1, U1)


def test_ice_touch_on_a_tile_freezes_the_unit_in_water() -> None:
    state = _duel(surface="water")
    result = run_effects(state, [ElementTouchEffect(pos=(1, 0), element=Element.ICE, source_id=U1)])
    assert result.state.units[U2].has_status("frozen")
    assert result.state.tile(1, 0).surface is Surface.ICE


def test_ice_damage_does_not_freeze_a_unit_on_dry_ground() -> None:
    result = run_effects(
        _duel(), [DamageEffect(target_id=U2, element=Element.ICE, flat=2, source_id=U1)]
    )
    assert not result.state.units[U2].has_status("frozen")


def test_non_ice_damage_does_not_freeze_a_unit_in_water() -> None:
    result = run_effects(
        _duel(surface="water"),
        [DamageEffect(target_id=U2, element=Element.PHYSICAL, flat=2, source_id=U1)],
    )
    assert not result.state.units[U2].has_status("frozen")


def test_ice_on_a_boss_in_water_becomes_slow() -> None:
    result = run_effects(
        _duel(surface="water", boss=True),
        [DamageEffect(target_id=U2, element=Element.ICE, flat=2, source_id=U1)],
    )
    boss = result.state.units[U2]
    assert boss.has_status("slow") and not boss.has_status("frozen")
    assert _of(result, StatusConverted)


def test_unit_surface_positions_are_pre_touch() -> None:
    """水變冰之後（已經是冰面）再被冰傷打中，不會再次冰凍（沒有水了）。"""
    state = _duel(surface="water")
    first = run_effects(state, [DamageEffect(target_id=U2, element=Element.ICE, flat=1)]).state
    cleared = first.clone()
    cleared.units[U2].statuses = []
    again = run_effects(cleared, [DamageEffect(target_id=U2, element=Element.ICE, flat=1)])
    assert not again.state.units[U2].has_status("frozen")
    assert Pos(x=1, y=0) == again.state.units[U2].pos
