"""撥開（Phase 3C-1）：``Interact(mode="shove_aside", side=left|right)``。

物件往垂直於「主角 → 物件」方向移動 1 格；主角不動；合法性與推共用
（:func:`trpg.engine.battle.object_move_problem`）。
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, make_map, make_setup, make_state, spawn
from trpg.cli.battle import cmd_replay
from trpg.engine import BattleState, Interact, legal_actions, resolve
from trpg.engine.ai.simple import choose_action
from trpg.engine.events import EventBase, ObjectDestroyed, ObjectMoved
from trpg.engine.runner import run_battle
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import ObjectId, Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
O1 = ObjectId("obj_0001")
HERO = (2, 2)
NL = chr(10)
FLAT = "\n".join(["00000"] * 5)


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _state(
    obj_at: tuple[int, int],
    kind: str = "crate",
    *,
    heights: str = FLAT,
    terrain: str | None = None,
    extra_objects: list[tuple[int, int, str]] | None = None,
    surfaces: list[tuple[int, int, str]] | None = None,
    enemy: tuple[int, int] = (4, 4),
) -> BattleState:
    m = make_map(
        heights,
        terrain,
        ally=[HERO],
        enemy=[enemy],
        objects=[(*obj_at, kind), *(extra_objects or [])],
        surfaces=surfaces or [],
    )
    state = make_state(m, [spawn(Team.ALLY, HERO, "hero_fighter"), spawn(Team.ENEMY, enemy)])
    return give_turn(state, U1)


def _aside(side: str, obj: ObjectId = O1) -> Interact:
    return Interact(unit_id=U1, object_id=obj, mode="shove_aside", side=side)  # type: ignore[arg-type]


# 物件相對主角的方向 → (往左撥的落點偏移, 往右撥的落點偏移)；y 向下，北為 y − 1
_CASES = [
    ("north", (2, 1), (-1, 0), (1, 0)),
    ("east", (3, 2), (0, -1), (0, 1)),
    ("south", (2, 3), (1, 0), (-1, 0)),
    ("west", (1, 2), (0, 1), (0, -1)),
]


@pytest.mark.parametrize(("name", "obj_at", "left", "right"), _CASES)
@pytest.mark.parametrize("side", ["left", "right"])
def test_shove_aside_landing_for_all_eight_cases(
    name: str,
    obj_at: tuple[int, int],
    left: tuple[int, int],
    right: tuple[int, int],
    side: str,
) -> None:
    state = _state(obj_at)
    action = _aside(side)
    assert action in legal_actions(state)
    offset = left if side == "left" else right
    expected = (obj_at[0] + offset[0], obj_at[1] + offset[1])
    result = resolve(state, action)
    moved = [e for e in result.events if isinstance(e, ObjectMoved)]
    assert [(e.from_pos, e.to_pos, e.how) for e in moved] == [
        (P(*obj_at), P(*expected), "shove_aside")
    ], name
    s = result.state
    assert s.objects[O1].pos == P(*expected)
    assert s.tile(*expected).object_id == O1 and s.tile(*obj_at).object_id is None
    assert s.units[U1].pos == P(*HERO)  # 主角不動
    assert s.units[U1].ap == state.units[U1].ap - state.ruleset.core.interact_ap_cost


def test_push_is_unchanged_and_has_no_side() -> None:
    state = _state((3, 2))
    push = Interact(unit_id=U1, object_id=O1)
    assert push.mode == "push" and push.side is None
    result = resolve(state, push)
    assert result.state.objects[O1].pos == P(4, 2)
    assert [e.how for e in result.events if isinstance(e, ObjectMoved)] == ["push"]


def test_interact_side_validation() -> None:
    with pytest.raises(ValidationError):
        Interact(unit_id=U1, object_id=O1, mode="push", side="left")
    with pytest.raises(ValidationError):
        Interact(unit_id=U1, object_id=O1, mode="shove_aside")


def test_legal_actions_list_push_and_both_sides() -> None:
    state = _state((3, 2))
    modes = [(a.mode, a.side) for a in legal_actions(state) if isinstance(a, Interact)]
    assert modes == [("push", None), ("shove_aside", "left"), ("shove_aside", "right")]


# ---------------------------------------------------------------------------
# 拒絕：牆、單位、物件、地圖外、高度
# ---------------------------------------------------------------------------


def _reject(state: BattleState, side: str, fragment: str) -> None:
    action = _aside(side)
    assert action not in legal_actions(state)
    with pytest.raises(IllegalActionError, match=fragment):
        resolve(state, action)


def test_shove_aside_into_wall_is_rejected() -> None:
    terrain = ".....\n...#.\n.....\n.....\n....."  # 物件 (3, 2) 的左邊（北）(3, 1) 是牆
    state = _state((3, 2), terrain=terrain)
    _reject(state, "left", "撥不動：.*另一側被擋住")
    assert _aside("right") in legal_actions(state)  # 另一邊仍可撥


def test_shove_aside_onto_unit_is_rejected() -> None:
    state = _state((3, 2), enemy=(3, 3))  # 右邊（南）是敵人
    _reject(state, "right", "撥不動：.*另一側有單位")


def test_shove_aside_onto_other_object_is_rejected() -> None:
    state = _state((3, 2), extra_objects=[(3, 1, "crate")])
    _reject(state, "left", "撥不動：.*另一側被擋住")


def test_shove_aside_out_of_map_is_rejected() -> None:
    m = make_map("000\n000\n000", ally=[(0, 1)], enemy=[(2, 2)], objects=[(0, 0, "crate")])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 1), "hero_fighter"), spawn(Team.ENEMY, (2, 2))]), U1
    )
    # 物件在主角正北 (0, 0)：往左（西）會出地圖，往右（東）可以
    _reject(state, "left", "撥不動：.*會被推出地圖")
    assert _aside("right") in legal_actions(state)


def test_shove_aside_target_too_high_is_rejected() -> None:
    # 物件 (3, 2) 高度 0；往左（北）的 (3, 1) 高度 1
    state = _state((3, 2), heights="00000\n00010\n00000\n00000\n00000")
    _reject(state, "left", "撥不動：.*另一側比較高")
    assert _aside("right") in legal_actions(state)


def test_shove_aside_height_difference_between_actor_and_object_is_rejected() -> None:
    state = _state((3, 2), heights="00000\n00000\n00020\n00000\n00000")
    _reject(state, "left", "高度差過大：相差 2 層")
    _reject(state, "right", "高度差過大：相差 2 層")


def test_shove_aside_not_adjacent_not_pushable_and_no_ap_are_rejected() -> None:
    far = _state((4, 2))
    with pytest.raises(IllegalActionError, match="物件必須相鄰"):
        resolve(far, _aside("left"))
    wall = _state((3, 2), kind="low_wall")  # 3C-5a：石柱可以推倒（但不能撥開），改用矮牆
    with pytest.raises(IllegalActionError, match="無法推動"):
        resolve(wall, _aside("left"))
    assert not any(isinstance(a, Interact) for a in legal_actions(wall))
    pillar = _state((3, 2), kind="stone_pillar")
    with pytest.raises(IllegalActionError, match="只能推倒，不能撥開"):
        resolve(pillar, _aside("left"))
    tired = _state((3, 2))
    tired.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(tired, _aside("left"))


# ---------------------------------------------------------------------------
# 與推相同的互動、不能對單位
# ---------------------------------------------------------------------------


def _shape(events: list[EventBase]) -> list[str]:
    return [type(e).__name__ for e in events]


def test_shove_aside_barrel_onto_fire_matches_pushing_it_there() -> None:
    # 推：油桶 (3, 2) → (4, 2) 的火上；撥開（往左）：油桶 (3, 2) → (3, 1) 的火上。
    # 目前互動表沒有「物件移到火上」的規則，兩者都只是移動；重點是兩條路的結果一致
    pushed = resolve(
        _state((3, 2), "oil_barrel", surfaces=[(4, 2, "fire")]),
        Interact(unit_id=U1, object_id=O1),
    )
    aside = resolve(_state((3, 2), "oil_barrel", surfaces=[(3, 1, "fire")]), _aside("left"))
    assert _shape(pushed.events) == _shape(aside.events) == ["ObjectMoved"]
    assert pushed.state.objects[O1].destroyed == aside.state.objects[O1].destroyed
    assert pushed.state.tile(4, 2).surface is aside.state.tile(3, 1).surface


def test_shove_aside_barrel_into_chasm_falls_like_a_push() -> None:
    row = "....."
    aside_terrain = NL.join([row, "...x.", row, row, row])  # 左撥落點 (3, 1) 是深淵
    push_terrain = NL.join([row, row, "....x", row, row])  # 推的落點 (4, 2) 是深淵
    pushed = resolve(
        _state((3, 2), "oil_barrel", terrain=push_terrain), Interact(unit_id=U1, object_id=O1)
    )
    aside = resolve(_state((3, 2), "oil_barrel", terrain=aside_terrain), _aside("left"))
    assert _shape(pushed.events) == _shape(aside.events)
    destroyed = [e for e in aside.events if isinstance(e, ObjectDestroyed)]
    assert [(d.object_id, d.cause) for d in destroyed] == [(O1, "fell")]
    assert aside.state.objects[O1].destroyed


def test_shove_aside_cannot_target_a_unit() -> None:
    state = _state((3, 2))
    with pytest.raises(IllegalActionError, match="找不到物件"):
        resolve(state, _aside("left", ObjectId(str(U2))))
    unit_ids = {str(u) for u in state.units}
    assert not any(
        isinstance(a, Interact) and str(a.object_id) in unit_ids for a in legal_actions(state)
    )


# ---------------------------------------------------------------------------
# 重播
# ---------------------------------------------------------------------------


def test_replay_with_a_shove_aside_is_identical(tmp_path: Path) -> None:
    setup = make_setup(
        make_map(FLAT, ally=[HERO], enemy=[(4, 4)], objects=[(3, 2, "crate")]),
        [spawn(Team.ALLY, HERO, "hero_fighter"), spawn(Team.ENEMY, (4, 4))],
        max_rounds=3,
    )
    done = False

    def policy(s: BattleState) -> Interact | object:
        nonlocal done
        if not done and s.active_unit == U1 and _aside("left") in legal_actions(s):
            done = True
            return _aside("left")
        return choose_action(s)

    run = run_battle(setup, 5, policy)  # type: ignore[arg-type]
    assert any(isinstance(e, ObjectMoved) and e.how == "shove_aside" for e in run.events)
    path = tmp_path / "log.json"
    path.write_text(run.to_log().model_dump_json(), encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0
    assert "重播驗證通過" in out.getvalue()
