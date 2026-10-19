"""推倒（Phase 3C-5a，``docs/phases/Phase3C計畫.md`` 7A.3）。

``topplable`` 物件被推（互動的推、技能的推擊、風）時不移動，往推的方向倒下：從下一格起壓住
``topple_length``（2）格，格上的單位受 ``topple_damage_dice`` 物理傷害並倒地、``breakable`` 物件受
同樣傷害，其他物件擋住倒下；原物件移除，最後一個放得下的格子產生倒塌物。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
    template,
)
from trpg.content.environment import ObjectDef, ObjectTable
from trpg.engine import Attack, BattleState, Interact, UseSkill, legal_actions, resolve
from trpg.engine.actions import STEP_LIST_ADAPTER, Action
from trpg.engine.ai.simple import choose_action
from trpg.engine.battle import interact_options
from trpg.engine.effects import ElementTouchEffect, run_effects
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    ObjectCreated,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectToppled,
    StatusApplied,
)
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Element, ObjectId, Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
PILLAR = ObjectId("obj_0001")
ROW = "0000000"
FLAT = "\n".join([ROW] * 7)
CENTER = (3, 3)


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def always(monkeypatch: pytest.MonkeyPatch, die: int = 4) -> None:
    """d20 一律 19（命中、不暴擊）、其他骰子一律 ``die``。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(die, sides))


def arena(
    hero: tuple[int, int],
    *,
    pillar: tuple[int, int] = CENTER,
    kind: str = "stone_pillar",
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    objects: Sequence[tuple[int, int, str]] = (),
    terrain: str | None = None,
    skills: Sequence[str] = (),
) -> BattleState:
    """U1 我方戰士（在 ``hero``）；之後依序是 ``foes``（不反應、HP 200）。第一個物件是 ``kind``。"""
    m = make_map(
        FLAT,
        terrain,
        ally=[hero],
        enemy=list(foes),
        objects=[(*pillar, kind), *objects],
    )
    fighter = (
        template("hero_fighter", reactions=[], skills=list(skills), max_mana=99)
        if skills
        else "hero_fighter"
    )
    spawns = [spawn(Team.ALLY, hero, fighter)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def push(obj: ObjectId = PILLAR) -> Interact:
    return Interact(unit_id=U1, object_id=obj)


def toppled(events: Sequence[EventBase]) -> ObjectToppled:
    (event,) = of(events, ObjectToppled)
    return event


def tiles(event: ObjectToppled) -> list[tuple[int, int]]:
    return [(p.x, p.y) for p in event.tiles]


# ---------------------------------------------------------------------------
# 方向與範圍
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hero", "direction", "crushed"),
    [
        ((2, 3), (1, 0), [(4, 3), (5, 3)]),  # 從西邊推 → 往東倒
        ((4, 3), (-1, 0), [(2, 3), (1, 3)]),  # 從東邊推 → 往西倒
        ((3, 2), (0, 1), [(3, 4), (3, 5)]),  # 從北邊推 → 往南倒
        ((3, 4), (0, -1), [(3, 2), (3, 1)]),  # 從南邊推 → 往北倒
    ],
)
def test_a_pushed_pillar_falls_in_the_push_direction(
    hero: tuple[int, int], direction: tuple[int, int], crushed: list[tuple[int, int]]
) -> None:
    result = resolve(arena(hero), push())
    event = toppled(result.events)
    assert (event.direction, tiles(event), event.source_id) == (direction, crushed, U1)
    assert event.rubble_pos == Pos(x=crushed[-1][0], y=crushed[-1][1])
    state = result.state
    assert state.objects[PILLAR].destroyed and state.object_at(*CENTER) is None
    rubble = state.object_at(*crushed[-1])
    assert rubble is not None and rubble.kind == "rubble"
    assert all(state.object_at(*xy) is None for xy in crushed[:-1])  # 其餘格不留物件
    (gone,) = of(result.events, ObjectDestroyed)
    assert gone.cause == "toppled"
    (made,) = of(result.events, ObjectCreated)
    assert made.kind == "rubble" and made.pos == event.rubble_pos
    assert state.units[U1].ap == state.ruleset.core.ap_per_turn - 1  # 互動 1 AP


def test_units_under_the_pillar_take_damage_and_fall_prone(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(arena((2, 3), foes=[(4, 3), (5, 3)]), push())
    event = toppled(result.events)
    assert event.units == (U2, U3)
    hits = [d for d in of(result.events, DamageDealt) if d.cause == "topple"]
    assert [(d.target_id, d.source_id, d.rolls, d.element.value) for d in hits] == [
        (U2, U1, (4, 4), "physical"),
        (U3, U1, (4, 4), "physical"),
    ]
    prone = {s.target_id for s in of(result.events, StatusApplied) if s.status_id == "prone"}
    assert prone == {U2, U3}
    # 兩格都有單位：倒塌物退到原格
    assert event.rubble_pos == Pos(x=3, y=3)
    assert result.state.object_at(3, 3) is not None


def test_the_rubble_goes_to_the_last_tile_that_can_hold_it() -> None:
    result = resolve(arena((2, 3), foes=[(5, 3)]), push())
    event = toppled(result.events)
    assert tiles(event) == [(4, 3), (5, 3)]
    assert event.rubble_pos == Pos(x=4, y=3)  # 最後一格有單位，往回一格


def test_a_breakable_object_under_the_pillar_takes_the_same_damage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(arena((2, 3), objects=[(4, 3, "crate")]), push())
    event = toppled(result.events)
    crate = ObjectId("obj_0002")
    assert event.objects == (crate,) and tiles(event) == [(4, 3), (5, 3)]
    (hit,) = of(result.events, ObjectDamaged)
    assert (hit.object_id, hit.cause, hit.rolls, hit.source_id) == (crate, "topple", (4, 4), U1)
    assert result.state.objects[crate].hp == 15 - 8
    assert event.rubble_pos == Pos(x=5, y=3)


def test_a_non_breakable_object_stops_the_fall() -> None:
    state = arena((2, 3), objects=[(4, 3, "rubble")], foes=[(5, 3)])
    # 內容裡已經沒有「阻擋移動又不能破壞」的物件（倒塌物 3D-3 起可破壞）：測試把倒塌物換成不可破壞
    unbreakable = ObjectDef.model_validate(
        {"id": "rubble", "name_zh": "倒塌物", "glyph": "m", "tags": ["blocks_move", "half_cover"]}
    )
    rs = state.ruleset
    others = tuple(o for o in rs.objects.objects if o.id != "rubble")
    rs = rs.model_copy(update={"objects": ObjectTable(objects=(*others, unbreakable))})
    rs.model_post_init(None)
    state.ruleset = rs
    result = resolve(state, push())
    event = toppled(result.events)
    assert tiles(event) == [] and event.units == ()  # 停在倒塌物之前，壓不到後面的敵人
    assert event.rubble_pos == Pos(x=3, y=3)
    assert not [d for d in of(result.events, DamageDealt) if d.cause == "topple"]


def test_a_toppled_pillar_crushes_old_rubble_because_rubble_is_breakable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3D-3：倒塌物可以被打掉，所以倒下的柱子壓得到舊的倒塌物（和木箱一樣受傷）。"""
    always(monkeypatch)
    result = resolve(arena((2, 3), objects=[(4, 3, "rubble")], foes=[(5, 3)]), push())
    event = toppled(result.events)
    rubble = ObjectId("obj_0002")
    assert event.objects == (rubble,) and tiles(event) == [(4, 3), (5, 3)]
    assert event.units == (U2,)
    assert result.state.objects[rubble].hp == 15 - 8


def test_rubble_is_a_breakable_object_with_the_crate_hp_and_can_be_destroyed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3D-3：倒塌物加 ``breakable`` 與 HP（同木箱），可以被打掉，不會永久堵死窄路。"""
    always(monkeypatch, die=6)
    state = arena((2, 3), pillar=(3, 3))
    definition = state.ruleset.object_def("rubble")
    crate = state.ruleset.object_def("crate")
    assert "breakable" in definition.tags and definition.max_hp == crate.max_hp
    toppled_state = resolve(state, push()).state
    (rubble,) = [o for o in toppled_state.objects.values() if o.kind == "rubble"]
    toppled_state.units[U1].pos = Pos(x=rubble.pos.x - 1, y=rubble.pos.y)  # 走到倒塌物旁
    toppled_state = give_turn(toppled_state, U1)
    hits = 0
    while not rubble.destroyed and hits < 10:
        attack = Attack(unit_id=U1, target_object_id=rubble.id)
        toppled_state = give_turn(resolve(toppled_state, attack).state, U1)
        rubble = toppled_state.objects[rubble.id]
        hits += 1
    assert rubble.destroyed and toppled_state.object_at(*rubble.xy) is None


def test_tiles_off_the_map_and_walls_are_skipped() -> None:
    edge = toppled(resolve(arena((5, 3), pillar=(6, 3)), push()).events)
    assert tiles(edge) == [] and edge.rubble_pos == Pos(x=6, y=3)
    rows = ["......."] * 7
    rows[3] = "....#.."
    walled = toppled(resolve(arena((2, 3), terrain="\n".join(rows), foes=[(5, 3)]), push()).events)
    assert tiles(walled) == [(5, 3)] and walled.units == (U2,)  # 牆那一格跳過，後面照壓
    assert walled.rubble_pos == Pos(x=3, y=3)  # (5, 3) 有敵人、(4, 3) 不算：退回原格


# ---------------------------------------------------------------------------
# 互動、撥開、技能、風
# ---------------------------------------------------------------------------


def test_topplable_objects_cannot_be_shoved_aside() -> None:
    state = arena((2, 3))
    with pytest.raises(IllegalActionError, match="只能推倒，不能撥開"):
        resolve(state, Interact(unit_id=U1, object_id=PILLAR, mode="shove_aside", side="left"))
    options = {
        (mode, side): problem
        for obj, mode, side, problem in interact_options(state, state.units[U1])
    }
    assert options[("push", None)] is None
    assert options[("shove_aside", "left")] == "撥不動：石柱只能推倒，不能撥開"
    assert options[("shove_aside", "right")] == "撥不動：石柱只能推倒，不能撥開"
    assert push() in legal_actions(state)
    far = arena((1, 3))
    with pytest.raises(IllegalActionError, match="物件必須相鄰"):
        resolve(far, push())


def test_a_dead_tree_falls_too() -> None:
    event = toppled(resolve(arena((2, 3), kind="dead_tree"), push()).events)
    assert tiles(event) == [(4, 3), (5, 3)]


def test_a_skill_push_topples_the_pillar_away_from_the_caster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena((2, 3), skills=["skill_gale_kick"], foes=[(5, 3)])
    kick = UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_object_id=PILLAR)
    result = resolve(state, kick)
    event = toppled(result.events)
    assert event.direction == (1, 0) and event.units == (U2,)
    # 颶風踢的傷害先打在石柱上，接著推擊把它推倒
    assert of(result.events, ObjectDamaged)[0].cause == "attack"


def test_the_topple_primitive_targets_a_topplable_object_in_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena((3, 1), skills=["skill_quake_topple"], foes=[(3, 4)])  # 石柱在南方 2 格
    cast = UseSkill(unit_id=U1, skill_id="skill_quake_topple", target_object_id=PILLAR)
    result = resolve(state, cast)
    event = toppled(result.events)
    assert (event.direction, tiles(event), event.units) == ((0, 1), [(3, 4), (3, 5)], (U2,))
    with pytest.raises(IllegalActionError, match="只能以可推倒的物件為目標"):
        resolve(state, UseSkill(unit_id=U1, skill_id="skill_quake_topple", target_id=U2))
    crate = arena((3, 1), kind="crate", skills=["skill_quake_topple"])
    with pytest.raises(IllegalActionError, match="無法推倒"):
        resolve(crate, cast)


def test_wind_topples_a_pillar() -> None:
    state = arena((0, 0))
    gust = ElementTouchEffect(
        source_id=U1, pos=CENTER, element=Element.WIND, direction=(0, 1), push_distance=1
    )
    event = toppled(run_effects(state, [gust]).events)
    assert event.direction == (0, 1) and tiles(event) == [(3, 4), (3, 5)]


def test_a_battle_with_a_topple_is_deterministic_and_replays() -> None:
    """主角第一個動作推倒石柱、之後交給 AI；同設定重跑與「初始狀態 ＋ 步驟（經 JSON）」重播一致。"""
    m = make_map(FLAT, ally=[(2, 3)], enemy=[(5, 3), (6, 1)], objects=[(3, 3, "stone_pillar")])
    spawns = [
        spawn(Team.ALLY, (2, 3), "hero_fighter"),
        spawn(Team.ENEMY, (5, 3), no_reactions(max_hp=30)),
        spawn(Team.ENEMY, (6, 1), no_reactions(max_hp=30)),
    ]
    setup = make_setup(m, spawns, max_rounds=6)

    def policy(state: BattleState) -> Action:
        if state.active_unit == U1 and push() in legal_actions(state):
            return push()
        return choose_action(state)

    first = run_battle(setup, 7, policy)
    assert any(isinstance(e, ObjectToppled) for e in first.events)
    again = run_battle(setup, 7, policy)
    assert state_to_json(again.state) == state_to_json(first.state)
    steps = STEP_LIST_ADAPTER.validate_json(STEP_LIST_ADAPTER.dump_json(first.actions))
    replayed = replay(setup, 7, steps)
    assert state_to_json(replayed.state) == state_to_json(first.state)
    assert [e.model_dump() for e in replayed.events] == [e.model_dump() for e in first.events]
