"""技巧動作與互動（6.1-4）、以及沒有其他情境覆蓋的 1B 效果類型（3.4）。

- ``Trip``：敏捷對抗，成功時目標倒地；已倒地的目標不可再絆倒。
- ``Shove``：力量對抗失敗時不推動。
- ``Interact``：推動相鄰的 ``pushable`` 物件 1 格（推進深淵時物件掉落摧毀）。
- ``create_obstacle``、``spawn_unit``、``destroy_object`` 直接放進佇列執行。
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template, with_rolls
from trpg.engine import BattleState, Interact, Move, Shove, Trip, legal_actions, preview, resolve
from trpg.engine.effects import (
    CreateObstacleEffect,
    DestroyObjectEffect,
    SpawnUnitEffect,
    run_effects,
)
from trpg.engine.events import (
    EffectFizzled,
    EnteredDeadlyTerrain,
    ManeuverRolled,
    ObjectCreated,
    ObjectDestroyed,
    ObjectMoved,
    StatusApplied,
    UnitSpawned,
)
from trpg.engine.rules.combat import is_hit
from trpg.engine.rules.geometry import has_line_of_sight
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import ObjectId, Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
O1, O2 = ObjectId("obj_0001"), ObjectId("obj_0002")


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _chance(bonus: int) -> Fraction:
    return Fraction(sum(is_hit(n, n + bonus, 11) for n in range(1, 21)), 20)


# ---------------------------------------------------------------------------
# Trip / Shove
# ---------------------------------------------------------------------------


def _duel(**attrs: int) -> BattleState:
    m = make_map("000\n000", enemy=[(1, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", attributes=attrs or {})),
            spawn(Team.ENEMY, (1, 0), template("bandit", reactions=[])),
        ],
    )
    return give_turn(state, U1)


def test_trip_success_knocks_prone_and_costs_ap() -> None:
    state = _duel()
    trip = Trip(unit_id=U1, target_id=U2)
    assert trip in legal_actions(state)
    result = resolve(with_rolls(state, [(20, 15)]), trip)
    rolled = [e for e in result.events if isinstance(e, ManeuverRolled)]
    assert len(rolled) == 1 and rolled[0].maneuver == "trip" and rolled[0].success
    assert any(isinstance(e, StatusApplied) and e.status_id == "prone" for e in result.events)
    assert result.state.units[U2].has_status("prone")
    assert result.state.units[U1].ap == state.units[U1].ap - 1
    # 已倒地：legal_actions 不再列出 Trip，resolve 拒絕
    assert trip not in legal_actions(result.state)
    with pytest.raises(IllegalActionError, match="目標已經倒地"):
        resolve(result.state, trip)


def test_trip_failure_leaves_target_standing() -> None:
    state = _duel()
    result = resolve(with_rolls(state, [(20, 1)]), Trip(unit_id=U1, target_id=U2))
    rolled = next(e for e in result.events if isinstance(e, ManeuverRolled))
    assert not rolled.success
    assert not result.state.units[U2].has_status("prone")
    assert result.state.units[U1].ap == state.units[U1].ap - 1


def test_trip_uses_dex_contest_and_shove_uses_str() -> None:
    """Trip 比敏捷、Shove 比力量（比例公式）：改變敏捷只影響 Trip 的成功率。"""
    base = _duel(dex=12, str=16)  # 敏捷 12 vs 盜賊 14；力量 16 vs 12
    quick = _duel(dex=28, str=16)  # 敏捷 28 vs 14 → 2 倍 → +4
    for state, trip_mod in ((base, -1), (quick, 4)):
        p_trip = preview(state, Trip(unit_id=U1, target_id=U2))
        p_shove = preview(state, Shove(unit_id=U1, target_id=U2))
        assert p_trip.hit_chance == _chance(trip_mod + 2)
        assert p_shove.hit_chance == _chance(2 + 2)
        rolled = next(
            e
            for e in resolve(state, Trip(unit_id=U1, target_id=U2)).events
            if isinstance(e, ManeuverRolled)
        )
        assert rolled.modifier == trip_mod


def test_shove_failure_does_not_push() -> None:
    state = _duel()
    result = resolve(with_rolls(state, [(20, 1)]), Shove(unit_id=U1, target_id=U2))
    assert not next(e for e in result.events if isinstance(e, ManeuverRolled)).success
    assert result.state.units[U2].pos == P(1, 0)


@pytest.mark.parametrize(
    ("heights", "enemy", "fragment"),
    [
        ("000\n000", (2, 0), "目標必須相鄰"),
        ("020\n000", (1, 0), "高度差過大"),
    ],
)
def test_maneuver_target_rules(heights: str, enemy: tuple[int, int], fragment: str) -> None:
    m = make_map(heights, enemy=[enemy])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, enemy)]), U1
    )
    for action in (Shove(unit_id=U1, target_id=U2), Trip(unit_id=U1, target_id=U2)):
        assert action not in legal_actions(state)
        with pytest.raises(IllegalActionError, match=fragment):
            resolve(state, action)


# ---------------------------------------------------------------------------
# Interact：推動物件
# ---------------------------------------------------------------------------


def test_interact_pushes_crate_one_tile() -> None:
    m = make_map("0000\n0000", objects=[(1, 0, "crate")], enemy=[(3, 1)])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (3, 1))]), U1
    )
    action = Interact(unit_id=U1, object_id=O1)
    assert action in legal_actions(state)
    result = resolve(state, action)
    moved = [e for e in result.events if isinstance(e, ObjectMoved)]
    assert [(e.from_pos, e.to_pos) for e in moved] == [(P(1, 0), P(2, 0))]
    s = result.state
    assert s.objects[O1].pos == P(2, 0)
    assert s.tile(2, 0).object_id == O1 and s.tile(1, 0).object_id is None
    assert s.units[U1].ap == state.units[U1].ap - 1


def test_interact_pushes_barrel_into_chasm() -> None:
    m = make_map(
        "000\n000", "..x\n...", objects=[(1, 0, "oil_barrel")], ally=[(0, 0)], enemy=[(2, 1)]
    )
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (2, 1))]), U1
    )
    result = resolve(state, Interact(unit_id=U1, object_id=O1))
    destroyed = [e for e in result.events if isinstance(e, ObjectDestroyed)]
    assert [(d.object_id, d.cause) for d in destroyed] == [(O1, "fell")]
    assert result.state.objects[O1].destroyed and result.state.tile(2, 0).object_id is None


def test_interact_rejections() -> None:
    m = make_map(
        "0000\n0000",
        objects=[(1, 0, "low_wall"), (3, 0, "crate")],  # 3C-5a：石柱可以推倒，改用矮牆
        enemy=[(3, 1)],
    )
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (3, 1))]), U1
    )
    with pytest.raises(IllegalActionError, match="無法推動"):
        resolve(state, Interact(unit_id=U1, object_id=O1))
    with pytest.raises(IllegalActionError, match="物件必須相鄰"):
        resolve(state, Interact(unit_id=U1, object_id=O2))
    with pytest.raises(IllegalActionError, match="找不到物件"):
        resolve(state, Interact(unit_id=U1, object_id=ObjectId("obj_9999")))
    assert not any(isinstance(a, Interact) for a in legal_actions(state))
    tired = state.clone()
    tired.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(tired, Interact(unit_id=U1, object_id=O2))


# ---------------------------------------------------------------------------
# create_obstacle / spawn_unit / destroy_object
# ---------------------------------------------------------------------------


def test_create_obstacle_blocks_movement_and_sight() -> None:
    m = make_map("00000\n00000", enemy=[(4, 0)])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (4, 0))])
    assert has_line_of_sight(state, (0, 0), (4, 0))
    result = run_effects(
        state,
        [
            CreateObstacleEffect(pos=(2, 0)),
            CreateObstacleEffect(pos=(4, 0)),  # 有單位 → 沒有效果
            CreateObstacleEffect(pos=(2, 0)),  # 已有物件 → 沒有效果
        ],
    )
    created = [e for e in result.events if isinstance(e, ObjectCreated)]
    assert [(e.kind, e.pos) for e in created] == [("earth_wall", P(2, 0))]
    fizzled = [e.reason for e in result.events if isinstance(e, EffectFizzled)]
    assert fizzled == ["occupied", "occupied"]
    s = result.state
    oid = created[0].object_id
    assert s.tile(2, 0).object_id == oid and s.objects[oid].hp == s.objects[oid].max_hp == 25
    assert not has_line_of_sight(s, (0, 0), (4, 0))
    s = give_turn(s, U1)
    with pytest.raises(IllegalActionError):
        resolve(s, Move(unit_id=U1, path=(P(0, 0), P(1, 0), P(2, 0))))


def test_spawn_unit_effect_joins_turn_order_and_relocates() -> None:
    m = make_map("000\n000", "..x\n...", enemy=[(2, 1)])
    state = make_state(
        m,
        [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 1))],
        spawn_templates=["bandit_archer"],
    )
    result = run_effects(
        state,
        [
            SpawnUnitEffect(pos=(1, 1), template_id="bandit_archer", team=Team.ENEMY),
            SpawnUnitEffect(pos=(2, 0), template_id="bandit_archer", team=Team.ENEMY),  # 深淵
            SpawnUnitEffect(pos=(1, 0), template_id="unknown", team=Team.ENEMY),
        ],
    )
    spawned = [e for e in result.events if isinstance(e, UnitSpawned)]
    # 同時入列的效果依座標 (y, x) 排序：(2, 0) 先結算。深淵 (2, 0) → 最近的空格 (1, 0)；
    # 之後 (1, 1) 照原位置產生。
    assert [(e.unit_id, e.pos) for e in spawned] == [
        (U3, P(1, 0)),
        (UnitId("unit_0004"), P(1, 1)),
    ]
    s = result.state
    assert s.turn_order[-2:] == [U3, UnitId("unit_0004")]
    assert s.units[U3].team is Team.ENEMY and s.units[U3].template_id == "bandit_archer"
    assert [e.reason for e in result.events if isinstance(e, EffectFizzled)] == [
        "unknown_template:unknown"
    ]


def test_destroy_object_effect_on_bridge_drops_unit() -> None:
    m = make_map("000", ".x.", objects=[(1, 0, "wooden_bridge")], enemy=[(1, 0)])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (1, 0))])
    result = run_effects(state, [DestroyObjectEffect(object_id=O1)])
    types = [type(e) for e in result.events]
    assert types.index(ObjectDestroyed) < types.index(EnteredDeadlyTerrain)
    assert result.state.objects[O1].destroyed and result.state.units[U2].downed
    # 已摧毀的物件再摧毀一次：沒有事件
    again = run_effects(result.state, [DestroyObjectEffect(object_id=O1)])
    assert not any(isinstance(e, ObjectDestroyed) for e in again.events)
