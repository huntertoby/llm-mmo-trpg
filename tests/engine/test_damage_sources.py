"""墜落、致命地形、爆炸與燒斷木橋的傷害帶有來源（Phase 2C-3，0.1 #2）。

來源 ＝ 推擊者、打斷橋的人、降低地形的施放者、點燃者；走進去或追溯不到的為 ``None``。
"""

from __future__ import annotations

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template
from trpg.engine import BattleState, EndTurn, resolve
from trpg.engine.effects import (
    DamageObjectEffect,
    ElementTouchEffect,
    LowerTerrainEffect,
    MoveUnitEffect,
    PushEffect,
    run_effects,
)
from trpg.engine.events import DamageDealt, EventBase
from trpg.shared.types import Element, ObjectId, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
O1 = ObjectId("obj_0001")


def _damage(events: list[EventBase], cause: str) -> DamageDealt:
    found = [e for e in events if isinstance(e, DamageDealt) and e.cause == cause]
    assert len(found) == 1, [type(e).__name__ for e in events]
    return found[0]


def _ledge() -> BattleState:
    """一排三格：(0, 0) 站著敵人（U2），(1, 0) 是深淵；英雄（U1）在 (2, 0)。"""
    m = make_map("000", ".x.", ally=[(2, 0)], enemy=[(0, 0)])
    state = make_state(
        m, [spawn(Team.ALLY, (2, 0), "hero_fighter"), spawn(Team.ENEMY, (0, 0), "bandit")]
    )
    return give_turn(state, U1)


def test_pushed_into_chasm_credits_the_pusher() -> None:
    state = _ledge()
    # 把 U2 從 (0, 0) 向右推進 (1, 0) 的深淵，由 U1 推
    result = run_effects(
        state, [PushEffect(target_id=U2, direction=(1, 0), distance=1, source_id=U1)]
    )
    assert _damage(result.events, "deadly_terrain").source_id == U1


def test_walking_into_chasm_has_no_source() -> None:
    state = _ledge()
    result = run_effects(state, [MoveUnitEffect(unit_id=U2, dest=(1, 0))])
    assert _damage(result.events, "deadly_terrain").source_id is None


def test_fall_damage_from_a_push_credits_the_pusher() -> None:
    # (0, 0) 高 3，往 +x 推到 (1, 0) 高 0
    m = make_map("30\n00", ally=[(0, 1)], enemy=[(0, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 1), "hero_fighter"),
            spawn(Team.ENEMY, (0, 0), template("bandit", max_hp=100)),
        ],
    )
    result = run_effects(
        state, [PushEffect(target_id=U2, direction=(1, 0), distance=1, source_id=U1)]
    )
    assert _damage(result.events, "fall").source_id == U1


def test_lowering_terrain_under_a_unit_credits_the_caster() -> None:
    m = make_map("30", ally=[(1, 0)], enemy=[(0, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 0), "hero_fighter"),
            spawn(Team.ENEMY, (0, 0), template("bandit", max_hp=100)),
        ],
    )
    result = run_effects(state, [LowerTerrainEffect(pos=(0, 0), amount=3, source_id=U1)])
    assert _damage(result.events, "fall").source_id == U1


def _bridge() -> BattleState:
    m = make_map(
        "000\n000\n000",
        ".x.\n.x.\n.x.",
        objects=[(1, 1, "wooden_bridge")],
        ally=[(0, 1)],
        enemy=[(1, 1)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 1), "hero_fighter"),
            spawn(Team.ENEMY, (1, 1), "bandit"),
            spawn(Team.ENEMY, (2, 2)),
        ],
    )
    return give_turn(state, U1)


def test_breaking_the_bridge_credits_whoever_broke_it() -> None:
    result = run_effects(_bridge(), [DamageObjectEffect(object_id=O1, flat=100, source_id=U1)])
    assert _damage(result.events, "deadly_terrain").source_id == U1


def test_a_bridge_burned_down_credits_the_igniter() -> None:
    s = run_effects(
        _bridge(), [ElementTouchEffect(pos=(1, 1), element=Element.FIRE, source_id=U1)]
    ).state
    assert s.objects[O1].burn_source == U1
    events: list[EventBase] = []
    while s.round == 1 and not s.ended:
        assert s.active_unit is not None
        r = resolve(s, EndTurn(unit_id=s.active_unit))
        s, events = r.state, events + r.events
    assert _damage(events, "deadly_terrain").source_id == U1


def test_a_bridge_burned_by_the_environment_alone_has_no_source() -> None:
    s = run_effects(
        _bridge(), [ElementTouchEffect(pos=(1, 1), element=Element.FIRE, source_id=None)]
    ).state
    events: list[EventBase] = []
    while s.round == 1 and not s.ended:
        assert s.active_unit is not None
        r = resolve(s, EndTurn(unit_id=s.active_unit))
        s, events = r.state, events + r.events
    assert _damage(events, "deadly_terrain").source_id is None


def test_explosion_damage_keeps_the_source() -> None:
    m = make_map("000", ally=[(2, 0)], enemy=[(0, 0)], objects=[(1, 0, "oil_barrel")])
    state = make_state(
        m,
        [spawn(Team.ALLY, (2, 0), "hero_fighter"), spawn(Team.ENEMY, (0, 0), "bandit")],
    )
    result = run_effects(
        give_turn(state, U1),
        [ElementTouchEffect(pos=(1, 0), element=Element.FIRE, source_id=U1)],
    )
    blasts = [e for e in result.events if isinstance(e, DamageDealt) and e.cause == "explosion"]
    assert blasts and all(e.source_id == U1 for e in blasts)
