"""技能形狀與選取（docs/phases/Phase2A計畫.md 3.3、4.6、5.5 第 3 條）。"""

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
)
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, legal_actions
from trpg.engine.skills.targeting import SkillArea, compute_area
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
FLAT7 = "\n".join(["0000000"] * 7)
OIL: list[dict[str, Any]] = [{"type": "create_surface", "surface": "oil"}]
BOLT: list[dict[str, Any]] = [{"type": "damage", "dice": "1d4", "element": "fire"}]
SKILL_ID = "skill_t_shape"


def _skill(shape: dict[str, Any], effects: list[dict[str, Any]] | None = None) -> SkillDef:
    return make_skill(SKILL_ID, shape, effects or OIL)


def _terrain(*walls: tuple[int, int]) -> str:
    rows = [["."] * 7 for _ in range(7)]
    for x, y in walls:
        rows[y][x] = "#"
    return "\n".join("".join(r) for r in rows)


def _state(
    skill: SkillDef,
    *,
    at: tuple[int, int] = (3, 3),
    walls: tuple[tuple[int, int], ...] = (),
    objects: tuple[tuple[int, int, str], ...] = (),
    foes: tuple[tuple[int, int], ...] = ((6, 6),),
) -> BattleState:
    m = make_map(FLAT7, _terrain(*walls), ally=[at], enemy=list(foes), objects=objects)
    spawns = [spawn(Team.ALLY, at, caster_template([skill]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def _area(state: BattleState, **fields: Any) -> SkillArea:
    action = UseSkill(unit_id=U1, skill_id=SKILL_ID, **fields)
    return compute_area(state, state.units[U1], state.ruleset.skill_def(SKILL_ID), action)


def _tiles(state: BattleState, **fields: Any) -> set[tuple[int, int]]:
    return set(_area(state, **fields).tiles)


def _square(cx: int, cy: int, r: int) -> set[tuple[int, int]]:
    return {(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)}


# ---------------------------------------------------------------------------
# self／single
# ---------------------------------------------------------------------------


def test_self_shape_is_caster_tile() -> None:
    state = _state(_skill({"type": "self"}))
    assert _area(state).tiles == ((3, 3),)
    with pytest.raises(IllegalActionError, match="不能指定"):
        _area(state, direction="north")


def test_single_selects_unit_or_object_within_range_and_sight() -> None:
    skill = _skill({"type": "single", "range": 3}, BOLT)
    state = _state(skill, objects=((3, 1, "crate"),), foes=((5, 3), (6, 6)))
    assert _area(state, target_id=U2).tiles == ((5, 3),)
    assert _area(state, target_object_id="obj_0001").tiles == ((3, 1),)
    with pytest.raises(IllegalActionError, match="射程"):
        _area(state, target_id=U3)
    with pytest.raises(IllegalActionError, match="恰好指定"):
        _area(state)
    with pytest.raises(IllegalActionError, match="不能指定"):
        _area(state, target_id=U2, direction="east")
    blocked = _state(skill, walls=((4, 3),), foes=((5, 3),))
    with pytest.raises(IllegalActionError, match="視線"):
        _area(blocked, target_id=U2)


def test_single_weapon_range_uses_the_weapon() -> None:
    skill = make_skill(
        SKILL_ID, {"type": "single", "range": "weapon"}, [{"type": "damage"}], category="weapon"
    )
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3), (5, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([skill], base="hero_fighter")),
        spawn(Team.ENEMY, (4, 3), no_reactions()),
        spawn(Team.ENEMY, (5, 3), no_reactions()),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    assert _area(state, target_id=U2).tiles == ((4, 3),)
    with pytest.raises(IllegalActionError, match="射程"):
        _area(state, target_id=U3)  # 劍的射程 1


# ---------------------------------------------------------------------------
# line／cone
# ---------------------------------------------------------------------------


def test_line_in_each_direction_is_cut_by_the_map_edge() -> None:
    state = _state(_skill({"type": "line", "size": 5}))
    assert _tiles(state, direction="east") == {(4, 3), (5, 3), (6, 3)}
    assert _tiles(state, direction="west") == {(2, 3), (1, 3), (0, 3)}
    assert _tiles(state, direction="north") == {(3, 2), (3, 1), (3, 0)}
    assert _tiles(state, direction="south") == {(3, 4), (3, 5), (3, 6)}
    short = _state(_skill({"type": "line", "size": 2}))
    assert _tiles(short, direction="east") == {(4, 3), (5, 3)}


def test_line_stops_before_a_wall_and_empty_line_is_illegal() -> None:
    state = _state(_skill({"type": "line", "size": 5}), walls=((5, 3),))
    assert _tiles(state, direction="east") == {(4, 3)}
    closed = _state(_skill({"type": "line", "size": 5}), walls=((4, 3),))
    with pytest.raises(IllegalActionError, match="影響範圍為空"):
        _area(closed, direction="east")
    east = UseSkill(unit_id=U1, skill_id=SKILL_ID, direction="east")
    assert east not in legal_actions(closed)
    assert UseSkill(unit_id=U1, skill_id=SKILL_ID, direction="west") in legal_actions(closed)


def test_line_includes_a_sight_blocking_object_then_stops() -> None:
    state = _state(_skill({"type": "line", "size": 5}), objects=((5, 3, "earth_wall"),))
    assert _tiles(state, direction="east") == {(4, 3), (5, 3)}
    # 不阻擋視線的物件（木箱）不會截斷
    crate = _state(_skill({"type": "line", "size": 5}), objects=((4, 3, "crate"),))
    assert _tiles(crate, direction="east") == {(4, 3), (5, 3), (6, 3)}


def test_cone_rows_widen_and_are_cut_by_the_map_edge() -> None:
    state = _state(_skill({"type": "cone", "size": 3}))
    expected = {(3, 2), (2, 1), (3, 1), (4, 1), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)}
    assert _tiles(state, direction="north") == expected
    edge = _state(_skill({"type": "cone", "size": 3}), at=(3, 1))
    assert _tiles(edge, direction="north") == {(3, 0)}  # 其餘排在地圖外
    corner = _state(_skill({"type": "cone", "size": 2}), at=(0, 0))
    assert _tiles(corner, direction="east") == {(1, 0), (2, 0), (2, 1)}


def test_cone_excludes_walls_and_tiles_hidden_behind_them() -> None:
    state = _state(_skill({"type": "cone", "size": 3}), walls=((3, 2),))
    tiles = _tiles(state, direction="north")
    assert (3, 2) not in tiles
    assert (3, 1) not in tiles and (3, 0) not in tiles  # 牆擋住正後方


# ---------------------------------------------------------------------------
# 中心格型：cross／square3／ground_tile
# ---------------------------------------------------------------------------


def test_cross_shape_center_range_and_boundaries() -> None:
    skill = _skill({"type": "cross", "range": 6})
    state = _state(skill)
    assert _tiles(state, target_pos=Pos(x=3, y=5)) == {(3, 5), (3, 4), (3, 6), (2, 5), (4, 5)}
    assert _tiles(state, target_pos=Pos(x=0, y=0)) == {(0, 0), (1, 0), (0, 1)}
    walled = _state(skill, walls=((1, 0),))
    assert _tiles(walled, target_pos=Pos(x=0, y=0)) == {(0, 0), (0, 1)}
    with pytest.raises(IllegalActionError, match="牆壁"):
        _area(walled, target_pos=Pos(x=1, y=0))
    with pytest.raises(IllegalActionError, match="超出地圖"):
        _area(state, target_pos=Pos(x=7, y=3))
    with pytest.raises(IllegalActionError, match="target_pos"):
        _area(state)


def test_cross_range_zero_is_centered_on_the_caster() -> None:
    state = _state(_skill({"type": "cross", "range": 0}))
    assert _tiles(state, target_pos=Pos(x=3, y=3)) == {(3, 3), (3, 2), (3, 4), (2, 3), (4, 3)}
    with pytest.raises(IllegalActionError, match="射程"):
        _area(state, target_pos=Pos(x=4, y=3))
    assert [a for a in legal_actions(state) if isinstance(a, UseSkill)] == [
        UseSkill(unit_id=U1, skill_id=SKILL_ID, target_pos=Pos(x=3, y=3))
    ]


def test_center_shape_needs_sight_only_to_the_center() -> None:
    state = _state(_skill({"type": "cross", "range": 6}), walls=((3, 2),))
    with pytest.raises(IllegalActionError, match="視線"):
        _area(state, target_pos=Pos(x=3, y=1))
    # 中心看得到，擴散到的格子不需要視線：中心 (2, 2) 的右鄰 (3, 2) 是牆，不含；下鄰 (2, 3) 含
    assert _tiles(state, target_pos=Pos(x=2, y=2)) == {(2, 2), (2, 1), (2, 3), (1, 2)}


def test_square3_covers_3x3_and_clips_at_the_corner() -> None:
    skill = _skill({"type": "square3", "range": 6})
    state = _state(skill)
    assert _tiles(state, target_pos=Pos(x=3, y=5)) == _square(3, 5, 1)
    assert _tiles(state, target_pos=Pos(x=0, y=0)) == {(0, 0), (1, 0), (0, 1), (1, 1)}
    walled = _state(skill, walls=((4, 5),))
    assert _tiles(walled, target_pos=Pos(x=3, y=5)) == _square(3, 5, 1) - {(4, 5)}


def test_ground_tile_selects_one_tile_in_range() -> None:
    state = _state(_skill({"type": "ground_tile", "range": 3}))
    assert _area(state, target_pos=Pos(x=5, y=4)).tiles == ((5, 4),)
    with pytest.raises(IllegalActionError, match="射程"):
        _area(state, target_pos=Pos(x=6, y=4))
    walled = _state(_skill({"type": "ground_tile", "range": 3}), walls=((4, 3),))
    with pytest.raises(IllegalActionError, match="牆壁"):
        _area(walled, target_pos=Pos(x=4, y=3))
    with pytest.raises(IllegalActionError, match="視線"):
        _area(walled, target_pos=Pos(x=5, y=3))


# ---------------------------------------------------------------------------
# ring／allies_in_radius
# ---------------------------------------------------------------------------


def test_ring_is_the_chebyshev_shell() -> None:
    one = _state(_skill({"type": "ring", "radius": 1}))
    assert _tiles(one) == _square(3, 3, 1) - {(3, 3)}
    two = _state(_skill({"type": "ring", "radius": 2}))
    assert _tiles(two) == _square(3, 3, 2) - _square(3, 3, 1)
    assert len(_tiles(two)) == 16
    corner = _state(_skill({"type": "ring", "radius": 2}), at=(0, 0))
    assert _tiles(corner) == {(2, 0), (2, 1), (2, 2), (1, 2), (0, 2)}


def test_ring_ignores_sight_but_not_walls() -> None:
    state = _state(_skill({"type": "ring", "radius": 2}), walls=((3, 2), (5, 5)))
    tiles = _tiles(state)
    assert (3, 1) in tiles  # 在牆後面也算
    assert (5, 5) not in tiles


def test_allies_in_radius_is_a_manhattan_diamond_including_the_caster() -> None:
    state = _state(_skill({"type": "allies_in_radius", "radius": 2}))
    diamond = {(x, y) for x in range(7) for y in range(7) if abs(x - 3) + abs(y - 3) <= 2}
    assert _tiles(state) == diamond and len(diamond) == 13
    corner = _state(_skill({"type": "allies_in_radius", "radius": 2}), at=(0, 0))
    assert _tiles(corner) == {(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 2)}


# ---------------------------------------------------------------------------
# chain
# ---------------------------------------------------------------------------

CHAIN = {"type": "chain", "range": 5, "jumps": 2, "jump_range": 2}


def test_chain_jumps_to_the_nearest_unhit_enemy() -> None:
    skill = _skill({**CHAIN, "jump_range": 3}, BOLT)
    # 第一目標 U2 (3, 0)；U3 (3, 2) 距 2；U4 (4, 0) 距 1 → 先跳 U4，再從 (4, 0) 跳 U3（距 3）
    state = _state(skill, at=(0, 0), foes=((3, 0), (3, 2), (4, 0)))
    area = _area(state, target_id=U2)
    assert area.units == (U2, U4, U3)
    assert set(area.tiles) == {(3, 0), (4, 0), (3, 2)}


def test_chain_ties_on_distance_break_by_unit_id() -> None:
    skill = _skill(CHAIN, BOLT)
    # U3 (3, 2) 與 U4 (5, 0) 都距 U2 (3, 0) 兩格 → 選 ID 小的 U3；之後沒有可跳的（距離 4）
    state = _state(skill, at=(0, 0), foes=((3, 0), (3, 2), (5, 0)))
    assert _area(state, target_id=U2).units == (U2, U3)


def test_chain_stops_when_nothing_is_in_reach_or_sight() -> None:
    skill = _skill(CHAIN, BOLT)
    far = _state(skill, at=(0, 0), foes=((3, 0), (6, 6)))
    assert _area(far, target_id=U2).units == (U2,)
    hidden = _state(skill, at=(0, 0), walls=((3, 1),), foes=((3, 0), (3, 2)))
    assert _area(hidden, target_id=U2).units == (U2,)  # 牆擋住 (3, 0) → (3, 2) 的視線


def test_chain_never_hits_a_unit_twice_and_respects_the_jump_limit() -> None:
    skill = _skill({**CHAIN, "jumps": 1}, BOLT)
    state = _state(skill, at=(0, 0), foes=((3, 0), (4, 0), (5, 0)))
    assert _area(state, target_id=U2).units == (U2, U3)
    with pytest.raises(IllegalActionError, match="單位"):
        _area(
            _state(skill, at=(0, 0), objects=((2, 0, "crate"),), foes=((3, 0),)),
            target_object_id="obj_0001",
        )


# ---------------------------------------------------------------------------
# legal_actions 的列舉
# ---------------------------------------------------------------------------


def test_direction_shapes_list_only_non_empty_directions() -> None:
    state = _state(_skill({"type": "line", "size": 3}), at=(0, 0))
    directions = [a.direction for a in legal_actions(state) if isinstance(a, UseSkill)]
    assert directions == ["east", "south"]


def test_center_shapes_list_every_legal_center_in_row_major_order() -> None:
    state = _state(_skill({"type": "ground_tile", "range": 1}))
    centers = [
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.target_pos is not None
    ]
    assert centers == sorted(centers, key=lambda p: (p[1], p[0]))
    assert centers == [(3, 2), (2, 3), (3, 3), (4, 3), (3, 4)]
