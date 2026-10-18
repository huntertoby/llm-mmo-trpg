"""掩護系統與牆壁（docs/phases/Phase1C計畫.md 3.1–3.4、4-2、4-3）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from trpg.content.maps import MapDef, check_map
from trpg.engine import Attack, BattleState, Move, legal_actions, preview, resolve
from trpg.engine.effects import DamageObjectEffect, PushEffect, run_effects
from trpg.engine.events import AttackRolled, EventBase, MoveBlocked, UnitMoved
from trpg.engine.rules.combat import half_cover
from trpg.engine.rules.geometry import has_line_of_sight
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import ObjectId, Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
CRATE = ObjectId("obj_0001")


def _attack_roll(events: list[EventBase]) -> AttackRolled:
    return next(e for e in events if isinstance(e, AttackRolled))


def _archery(
    archer_at: tuple[int, int],
    target_at: tuple[int, int],
    *,
    heights: str = "0000000\n0000000\n0000000\n0000000\n0000000",
    objects: tuple[tuple[int, int, str], ...] = ((2, 2, "crate"),),
    archer: str = "hero_archer",
) -> BattleState:
    """弓手對一名不會反應的盜賊（攻擊值 16 對防禦值 16：命中修正 0）。"""
    m = make_map(heights, objects=objects, ally=[archer_at], enemy=[target_at])
    state = make_state(
        m, [spawn(Team.ALLY, archer_at, archer), spawn(Team.ENEMY, target_at, no_reactions())]
    )
    return give_turn(state, U1)


# ---------------------------------------------------------------------------
# 半掩護判定
# ---------------------------------------------------------------------------


def test_ranged_attack_behind_crate_has_minus_two() -> None:
    # 盜賊在 (3, 2)，木箱在 (2, 2)，弓手在 (0, 2)：木箱位於兩者之間
    state = _archery((0, 2), (3, 2))
    cover = half_cover(state, state.units[U1], state.units[U2])
    assert cover is not None
    assert (cover.penalty, cover.object_id, cover.kind, cover.pos) == (2, CRATE, "crate", (2, 2))
    # 實際擲骰：d20=10 → 10 + 0 + 2 − 2 = 10 < 11 → 失手（沒有掩護時 12 會命中）
    result = resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    roll = _attack_roll(result.events)
    assert (roll.cover, roll.cover_object_id, roll.total, roll.hit) == (-2, CRATE, 10, False)
    # 預覽：命中率 = 自然骰 ≥ 11 → 50%（沒有掩護時 60%）
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert p.hit_chance == Fraction(1, 2)
    assert p.cover is not None and p.cover.object_id == CRATE
    assert p.notes == ("半掩護 −2：木箱 (2, 2)",)


@pytest.mark.parametrize(
    ("archer_at", "covered"),
    [
        ((0, 2), True),  # 正後方：木箱在兩者之間
        ((0, 0), True),  # 斜向：木箱在目標朝向攻擊者的一側（內積 3 > 0）
        ((1, 4), True),  # 斜向：內積 2 > 0
        ((3, 0), False),  # 正上方：木箱在側面（內積 0）
        ((3, 4), False),  # 正下方：內積 0
        ((6, 2), False),  # 從另一側射擊：木箱在目標背後（內積 < 0）
        ((6, 0), False),
    ],
)
def test_cover_depends_on_direction(archer_at: tuple[int, int], covered: bool) -> None:
    state = _archery(archer_at, (3, 2))
    assert (half_cover(state, state.units[U1], state.units[U2]) is not None) is covered
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert p.hit_chance == (Fraction(1, 2) if covered else Fraction(3, 5))
    assert (p.cover is not None) is covered


def test_side_attack_has_no_penalty_in_actual_roll() -> None:
    state = _archery((3, 0), (3, 2))
    result = resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    roll = _attack_roll(result.events)
    assert (roll.cover, roll.cover_object_id, roll.total, roll.hit) == (0, None, 12, True)


@pytest.mark.parametrize(
    ("archer_height", "covered", "situational"),
    [
        (1, True, 2),  # 高 1 層：與掩護物（地形 0 ＋ 物件 1 層）同高，仍有掩護；高打低 +2
        (2, False, 2),  # 高 2 層：比掩護物高 1 層 → 無視半掩護
        (3, False, 2),
    ],
)
def test_attacker_above_cover_ignores_it(
    archer_height: int, covered: bool, situational: int
) -> None:
    heights = "\n".join(str(archer_height) + "000000" if y == 2 else "0000000" for y in range(5))
    state = _archery((0, 2), (3, 2), heights=heights)
    assert (half_cover(state, state.units[U1], state.units[U2]) is not None) is covered
    result = resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    roll = _attack_roll(result.events)
    assert roll.situational == situational
    assert roll.cover == (-2 if covered else 0)


def test_cover_height_uses_cover_tile_height() -> None:
    # 木箱放在高度 1 的格子上：攻擊者在高度 2 仍有掩護（2 ≤ 1 + 1），高度 3 才無視
    def heights(h: int) -> str:
        rows = ["0000000"] * 5
        rows[2] = f"{h}01{'0' * 4}"
        return "\n".join(rows)

    covered = _archery((0, 2), (3, 2), heights=heights(2))
    assert half_cover(covered, covered.units[U1], covered.units[U2]) is not None
    exposed = _archery((0, 2), (3, 2), heights=heights(3))
    assert half_cover(exposed, exposed.units[U1], exposed.units[U2]) is None


def test_melee_ignores_half_cover() -> None:
    # 射程 2 的長柄武器隔著木箱攻擊：木箱在兩者之間，但近戰（受近戰高度差限制的武器）無視半掩護
    state = _archery((1, 2), (3, 2), archer="hero_fighter")
    reach = state.clone()
    reach.units[U1].weapon = reach.units[U1].weapon.model_copy(update={"range": 2})
    assert half_cover(reach, reach.units[U1], reach.units[U2]) is None
    p = preview(reach, Attack(unit_id=U1, target_id=U2))
    assert p.cover is None and p.notes == ()
    result = resolve(with_rolls(reach, [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    assert _attack_roll(result.events).cover == 0
    # 同一位置換成弓：有半掩護
    bow = state.clone()
    bow.units[U1].weapon = library().weapons["bow"]
    assert half_cover(bow, bow.units[U1], bow.units[U2]) is not None
    # 相鄰的近戰：唯一可能「在兩者之間」的相鄰格就是攻擊者自己的格子，因此不會有掩護
    m = make_map("000\n000", objects=[(0, 0, "crate")], ally=[(1, 1)], enemy=[(1, 0)])
    melee = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (1, 1), "hero_fighter"), spawn(Team.ENEMY, (1, 0), no_reactions())]
        ),
        U1,
    )
    assert half_cover(melee, melee.units[U1], melee.units[U2]) is None


def test_destroyed_crate_no_longer_covers() -> None:
    state = _archery((0, 2), (3, 2))
    assert half_cover(state, state.units[U1], state.units[U2]) is not None
    broken = run_effects(state, [DamageObjectEffect(object_id=CRATE, flat=99)]).state
    assert broken.objects[CRATE].destroyed
    assert half_cover(broken, broken.units[U1], broken.units[U2]) is None
    assert preview(broken, Attack(unit_id=U1, target_id=U2)).hit_chance == Fraction(3, 5)


def test_half_cover_and_concealment_stack() -> None:
    # 盜賊站在草叢（隱蔽 → 劣勢）中，木箱在弓手與盜賊之間（−2）；隱蔽限制距離 ≤ 2
    state = _archery((1, 2), (3, 2), objects=((2, 2, "crate"), (3, 2, "grass")))
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert p.cover is not None
    # 劣勢：兩顆都要 ≥ 11 → (10/20)² = 1/4
    assert p.hit_chance == Fraction(1, 4)
    result = resolve(with_rolls(state, [(20, 15), (20, 12)]), Attack(unit_id=U1, target_id=U2))
    roll = _attack_roll(result.events)
    assert (roll.advantage, roll.natural, roll.cover, roll.total) == ("disadvantage", 12, -2, 12)


def test_units_do_not_provide_cover() -> None:
    m = make_map("0000000", ally=[(0, 0)], enemy=[(3, 0)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "hero_archer"),
                spawn(Team.ENEMY, (3, 0), no_reactions()),
                spawn(Team.ENEMY, (2, 0), no_reactions()),
            ],
        ),
        U1,
    )
    assert half_cover(state, state.units[U1], state.units[U2]) is None


@pytest.mark.parametrize("kind", ["crate", "low_wall", "oil_barrel", "fallen_log"])
def test_cover_objects_have_half_cover_tag(kind: str) -> None:
    definition = library().ruleset.object_def(kind)
    assert definition.has_tag("half_cover")
    state = _archery((0, 2), (3, 2), objects=((2, 2, kind),))
    cover = half_cover(state, state.units[U1], state.units[U2])
    assert cover is not None and cover.kind == kind


def test_new_object_tags() -> None:
    rs = library().ruleset
    assert set(rs.object_def("crate").tags) >= {
        "breakable",
        "pushable",
        "blocks_move",
        "half_cover",
        "flammable",
    }
    low_wall = rs.object_def("low_wall")
    assert set(low_wall.tags) == {"breakable", "blocks_move", "half_cover"}
    assert low_wall.max_hp is not None and low_wall.max_hp > rs.object_def("crate").max_hp  # type: ignore[operator]
    assert set(rs.object_def("fallen_log").tags) == {
        "breakable",
        "blocks_move",
        "half_cover",
        "flammable",
    }
    assert {"breakable", "flammable", "explosive", "pushable", "half_cover"} <= set(
        rs.object_def("oil_barrel").tags
    )


def test_penalty_comes_from_core_rules() -> None:
    m = make_map(
        "0000000\n0000000\n0000000", objects=[(2, 1, "crate")], ally=[(0, 1)], enemy=[(3, 1)]
    )
    spawns = [spawn(Team.ALLY, (0, 1), "hero_archer"), spawn(Team.ENEMY, (3, 1), no_reactions())]
    three = give_turn(make_state(m, spawns, half_cover_hit_penalty=3), U1)
    cover = half_cover(three, three.units[U1], three.units[U2])
    assert cover is not None and cover.penalty == 3
    assert preview(three, Attack(unit_id=U1, target_id=U2)).hit_chance == Fraction(9, 20)
    zero = give_turn(make_state(m, spawns, half_cover_hit_penalty=0), U1)
    assert half_cover(zero, zero.units[U1], zero.units[U2]) is None


# ---------------------------------------------------------------------------
# 牆壁
# ---------------------------------------------------------------------------


def _walled() -> BattleState:
    """(2, 0)–(2, 2) 是一道牆，(2, 3) 是缺口。"""
    m = make_map(
        "00000\n00000\n00000\n00000",
        "..#..\n..#..\n..#..\n.....",
        ally=[(0, 1)],
        enemy=[(4, 1)],
    )
    state = make_state(
        m, [spawn(Team.ALLY, (0, 1), "hero_archer"), spawn(Team.ENEMY, (4, 1), no_reactions())]
    )
    return give_turn(state, U1)


def test_wall_blocks_movement() -> None:
    state = _walled()
    with pytest.raises(IllegalActionError, match="無法進入牆壁"):
        resolve(state, Move(unit_id=U1, path=(Pos(x=0, y=1), Pos(x=1, y=1), Pos(x=2, y=1))))
    dests = {(a.dest.x, a.dest.y) for a in legal_actions(state) if isinstance(a, Move)}
    assert not dests & {(2, 0), (2, 1), (2, 2)}
    assert (2, 3) in dests


def test_wall_blocks_sight_regardless_of_height() -> None:
    state = _walled()
    assert not has_line_of_sight(state, (0, 1), (4, 1))
    assert not has_line_of_sight(state, (4, 1), (0, 1))
    assert has_line_of_sight(state, (0, 3), (4, 3))
    with pytest.raises(IllegalActionError, match="視線被阻擋"):
        resolve(state, Attack(unit_id=U1, target_id=U2))
    assert Attack(unit_id=U1, target_id=U2) not in legal_actions(state)
    # 站在高度 3 的高台上也看不過牆
    high = make_map("30000\n30000\n30000", "..#..\n..#..\n..#..", ally=[(0, 1)], enemy=[(4, 1)])
    s = make_state(high, [spawn(Team.ALLY, (0, 1), "hero_archer"), spawn(Team.ENEMY, (4, 1))])
    assert not has_line_of_sight(s, (0, 1), (4, 1))


def test_wall_stops_pushed_units_and_objects() -> None:
    m = make_map(
        "0000\n0000", "..#.\n....", objects=[(1, 1, "crate")], ally=[(0, 0)], enemy=[(1, 0)]
    )
    state = make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0))])
    pushed = run_effects(state, [PushEffect(target_id=U2, direction=(1, 0), distance=2)])
    assert pushed.state.units[U2].xy == (1, 0)
    assert any(isinstance(e, MoveBlocked) and e.reason == "obstacle" for e in pushed.events)
    assert not any(isinstance(e, UnitMoved) for e in pushed.events)
    moved = run_effects(state, [PushEffect(object_id=CRATE, direction=(1, 0), distance=1)])
    assert moved.state.objects[CRATE].xy == (2, 1)
    again = run_effects(moved.state, [PushEffect(object_id=CRATE, direction=(0, -1), distance=1)])
    assert again.state.objects[CRATE].xy == (2, 1)


def _map_data(terrain: str, **extra: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "walls",
        "name_zh": "牆",
        "archetype": "test",
        "size": [5, 3],
        "heights": "00000\n00000\n00000",
        "terrain": terrain,
        "legend": {".": "stone", "#": "wall"},
        "start_zones": {"ally": [[0, 1]], "enemy": [[4, 1]]},
    }
    data.update(extra)
    return data


def test_map_legend_hash_is_wall_and_connectivity_considers_walls() -> None:
    lib = library()
    rs = lib.ruleset
    terrain = rs.terrain.by_id()
    objects = rs.objects.by_id()
    open_map = MapDef.model_validate(_map_data("..#..\n..#..\n....."))
    assert open_map.tile_terrain(2, 0) == "wall"
    assert check_map(open_map, terrain, rs.core, objects) == []
    sealed = MapDef.model_validate(_map_data("..#..\n..#..\n..#.."))
    problems = check_map(sealed, terrain, rs.core, objects)
    assert any("連通性檢查失敗" in p for p in problems)
    on_wall = MapDef.model_validate(
        _map_data(
            "..#..\n..#..\n.....",
            objects=[{"at": [2, 0], "kind": "crate"}],
            surfaces=[{"at": [2, 1], "surface": "oil"}],
        )
    )
    problems = check_map(on_wall, terrain, rs.core, objects)
    assert any("objects 的 [2, 0] 位於牆壁" in p for p in problems)
    assert any("surfaces 的 [2, 1] 位於牆壁" in p for p in problems)


def test_wall_terrain_definition() -> None:
    wall = library().ruleset.terrain_def("wall")
    assert (wall.walkable, wall.deadly, wall.blocks_sight) == (False, False, True)
    assert wall.glyph == "@"


def test_battle_log_shows_cover_source() -> None:
    from trpg.cli.render import describe_event  # noqa: PLC0415

    state = _archery((0, 2), (3, 2))
    result = resolve(with_rolls(state, [(20, 15)]), Attack(unit_id=U1, target_id=U2))
    text = describe_event(_attack_roll(result.events), result.state)
    assert text is not None
    assert "半掩護 -2" in text and "命中 −2：木箱掩護" in text
    side = _archery((3, 0), (3, 2))
    result = resolve(with_rolls(side, [(20, 15)]), Attack(unit_id=U1, target_id=U2))
    text = describe_event(_attack_roll(result.events), result.state)
    assert text is not None and "掩護" not in text


# ---------------------------------------------------------------------------
# Phase 2A 決定 #1：站在高台上的目標不被旁邊地面的掩護物掩護
# ---------------------------------------------------------------------------


def test_target_on_high_platform_is_not_covered_by_ground_crate() -> None:
    # 木箱在 (2, 2)（高 0），盜賊站在 (3, 2)（高 2 的高台），弓手在 (0, 2) 也在地面：
    # 木箱 0 + 1 < 目標高度 2 → 不提供半掩護
    heights = "0002000\n0002000\n0002000\n0002000\n0002000"
    state = _archery((0, 2), (3, 2), heights=heights)
    assert half_cover(state, state.units[U1], state.units[U2]) is None
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert p.cover is None and p.notes == ()


def test_target_on_ground_beside_crate_still_covered_and_low_target_on_one_step() -> None:
    # 地面目標：照舊（上面的測試 test_ranged_attack_behind_crate_has_minus_two 已涵蓋）；
    # 目標只高 1 層時，木箱（0 + 1 ≥ 1）仍提供掩護
    heights = "0001000\n0001000\n0001000\n0001000\n0001000"
    state = _archery((0, 2), (3, 2), heights=heights)
    cover = half_cover(state, state.units[U1], state.units[U2])
    assert cover is not None and cover.object_id == CRATE
