"""推不動算撞擊（SK-2，#166，06 6.38 第 9 點、05 5.12.4 第 6 點）：推、拉打到推不動的目標時，
照撞牆結算一次撞擊傷害，目標不移動。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
    spawn_giant,
    template,
)
from trpg.engine import BattleState, state_to_json
from trpg.engine.effects import PushEffect, run_effects
from trpg.engine.events import Collided, DamageDealt, EventBase, PushResisted
from trpg.engine.runner import LOG_FORMAT
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
FLAT = "\n".join(["0" * 9] * 9)
NO_PERK = {"str": 10}


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def collisions(events: Sequence[EventBase]) -> list[DamageDealt]:
    return [e for e in of(events, DamageDealt) if e.cause == "collision"]


@pytest.fixture(autouse=True)
def fixed_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(4, sides))


def arena(foe_tags: tuple[str, ...] = (), *, base: str = "bandit") -> BattleState:
    m = make_map(FLAT, None, ally=[(0, 4)], enemy=[(2, 4)])
    spawns = [
        spawn(Team.ALLY, (0, 4), template("hero_fighter", attributes=NO_PERK)),
        spawn(Team.ENEMY, (2, 4), no_reactions(base, max_hp=200, tags=foe_tags)),
    ]
    return give_turn(make_state(m, spawns), U1)


def giant_arena() -> BattleState:
    m = make_map(FLAT, None, ally=[(4, 8)], enemy=[(4, 4)])
    spawns = [
        spawn(Team.ALLY, (4, 8), template("hero_fighter", attributes=NO_PERK)),
        spawn_giant(Team.ENEMY, (4, 4)),
    ]
    return give_turn(make_state(m, spawns), U1)


def east(distance: int, **kw: object) -> PushEffect:
    return PushEffect(source_id=U1, target_id=U2, direction=(1, 0), distance=distance, **kw)  # type: ignore[arg-type]


@pytest.mark.parametrize("pull", [False, True])
@pytest.mark.parametrize("distance", [1, 2])
def test_an_immovable_tag_takes_one_wall_collision_and_stays(pull: bool, distance: int) -> None:
    state = arena(("immovable",))
    direction = (-1, 0) if pull else (1, 0)
    effect = PushEffect(
        source_id=U1, target_id=U2, direction=direction, distance=distance, pull=pull
    )
    result = run_effects(state, [effect])
    (hit,) = of(result.events, Collided)
    assert (hit.unit_id, hit.obstacle, hit.shortfall, hit.source_id) == (U2, "immovable", 1, U1)
    assert (hit.pos.x, hit.pos.y) == (2, 4)
    assert [(d.target_id, d.source_id, d.amount) for d in collisions(result.events)] == [
        (U2, U1, 4)
    ]  # 推 2 格也只算一次（照撞牆一次）
    assert result.state.units[U2].xy == (2, 4)
    assert result.state.units[U2].collided_round == result.state.round
    (resisted,) = of(result.events, PushResisted)
    assert resisted.reason == "immovable"


@pytest.mark.parametrize("pull", [False, True])
def test_the_giant_boss_takes_one_collision(pull: bool) -> None:
    """05 5.12.4 第 6 點：巨型頭目推不動、拉不動，照撞牆結算一次撞擊傷害。"""
    state = giant_arena()
    giant = next(u for u in state.units.values() if u.footprint == 3)
    direction = (0, 1) if pull else (0, -1)
    effect = PushEffect(
        source_id=U1, target_id=giant.id, direction=direction, distance=2, pull=pull
    )
    result = run_effects(state, [effect])
    (hit,) = of(result.events, Collided)
    assert (hit.unit_id, hit.obstacle, hit.shortfall) == (giant.id, "immovable", 1)
    assert result.state.units[giant.id].xy == (4, 4)
    assert result.state.units[giant.id].hp == giant.hp - 4


def test_steadfast_reduced_to_zero_counts_but_a_partial_push_does_not() -> None:
    """「因任何原因推不動」：穩固（×50%）把 1 格減成 0 格＝推不動；2 格減成 1 格照常移動、不撞。"""
    zero = run_effects(arena(("steadfast",)), [east(1)])
    assert [c.obstacle for c in of(zero.events, Collided)] == ["immovable"]
    assert zero.state.units[U2].xy == (2, 4)
    one = run_effects(arena(("steadfast",)), [east(2)])
    assert of(one.events, Collided) == []
    assert one.state.units[U2].xy == (3, 4)


def test_harmless_racial_pushes_and_zero_requests_do_not_collide() -> None:
    harmless = run_effects(arena(("immovable",)), [east(1, harmless=True)])
    assert of(harmless.events, Collided) == [] and collisions(harmless.events) == []
    zero = run_effects(arena(("immovable",)), [east(0)])
    assert of(zero.events, Collided) == []


def test_excess_distance_still_adds_its_own_collisions() -> None:
    """修正規則把距離加到超過上限的部分照舊另算（``excess``），推不動的那一次另外算。"""
    result = run_effects(arena(("immovable",)), [east(1, extra_collisions=1)])
    assert [c.obstacle for c in of(result.events, Collided)] == ["immovable", "excess"]
    assert len(collisions(result.events)) == 2


def test_movable_targets_are_unchanged() -> None:
    result = run_effects(arena(), [east(2)])
    assert of(result.events, Collided) == [] and of(result.events, PushResisted) == []
    assert result.state.units[U2].xy == (4, 4)


def test_log_text() -> None:
    result = run_effects(arena(("immovable",)), [east(1)])
    (hit,) = of(result.events, Collided)
    text = describe_event(hit, result.state) or ""
    assert "推不動" in text and "1 次撞擊" in text


def test_same_input_same_result() -> None:
    state = arena(("immovable",))
    first = run_effects(state, [east(1)])
    second = run_effects(state, [east(1)])
    assert state_to_json(first.state) == state_to_json(second.state)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
    assert LOG_FORMAT.endswith("/135")
