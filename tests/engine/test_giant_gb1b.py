"""GB-1b 巨型頭目的距離、範圍與出招起點（05 5.12.4 第 2、4 點、``PhaseGB計畫.md`` 5.2、5.5 第 2～5、
14 列；R1、R2、T5、T7、T9）：實際跑引擎，每列一條規則句（列名寫 D／R／T 編號）。合成巨人
（``helpers.giant_template``）只在測試裡，不進 ``content/``。

場地：13×13 平地；巨人（敵方）中心 (6, 6)、佔 x 5～7、y 5～7。
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import cache
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import (
    caster_template,
    giant_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    spawn_giant,
    template,
    with_rolls,
)
from tests.engine.test_footprint_gb1a import unit_at
from tests.engine.test_pending_serialization import PROMPT_BLOCK
from trpg.content.skills import SkillDef
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    Move,
    UseSkill,
    preview,
    resolve,
    resume,
    state_from_json,
    state_to_json,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    EVENT_LIST_ADAPTER,
    AttackRolled,
    DamageDealt,
    PartDamaged,
    UnitMoved,
)
from trpg.engine.rules.combat import attack_problem
from trpg.engine.rules.footprint import (
    adjacent,
    chebyshev_to,
    dist_to,
    face_tile,
    strike_tiles,
    tiles_of,
    touches,
    unit_dist,
)
from trpg.engine.rules.geometry import chebyshev, manhattan
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.skills.shapes import (
    around_tiles,
    caster_center_candidates,
    center_candidates,
    cross_tiles,
    radius_tiles,
    ring_tiles,
    square3_tiles,
)
from trpg.engine.skills.targeting import _hit_tiles, checked_area
from trpg.engine.state import UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

DMG = [{"type": "damage", "dice": "1d4", "element": "physical"}]
FLAT13 = "\n".join("0" * 13 for _ in range(13))
GIANT_ID = "test_giant"
BOX = {(x, y) for y in range(5, 8) for x in range(5, 8)}
SIDES = [
    *((x, 4) for x in range(5, 8)),
    *((8, y) for y in range(5, 8)),
    *((x, 8) for x in range(5, 8)),
    *((4, y) for y in range(5, 8)),
]
CORNERS = [(4, 4), (8, 4), (4, 8), (8, 8)]


def board(
    allies: Sequence[tuple[int, int]],
    enemies: Sequence[tuple[int, int]] = (),
    *,
    objects: tuple[tuple[int, int, str], ...] = (),
) -> Any:
    m = make_map(FLAT13, ally=list(allies), enemy=[(6, 6), *enemies], objects=objects)
    return m.model_copy(update={"giant_facing": {GIANT_ID: "south"}})


def arena(
    allies: Sequence[tuple[int, int, Any]],
    enemies: Sequence[tuple[int, int]] = (),
    *,
    skills: Sequence[SkillDef] = (),
    giant_skills: Sequence[str] = (),
    objects: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    tmpl = giant_template(id=GIANT_ID, skills=tuple(giant_skills), max_mana=99)
    spawns = [spawn_giant(Team.ENEMY, (6, 6), tmpl)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in enemies]
    spawns += [spawn(Team.ALLY, (x, y), t) for x, y, t in allies]
    m = board([(x, y) for x, y, _ in allies], enemies, objects=objects)
    return make_state(m, spawns, skills=skills)


def giant(state: BattleState) -> UnitState:
    return next(u for u in state.units_sorted() if u.footprint == 3)


def at(state: BattleState, xy: tuple[int, int]) -> UnitState:
    found = state.unit_at(*xy)
    assert found is not None
    return found


def moved(state: BattleState, unit_id: str, xy: tuple[int, int]) -> BattleState:
    s = state.clone()
    s.units[UnitId(unit_id)].pos = Pos(x=xy[0], y=xy[1])
    return s


def always_19(monkeypatch: pytest.MonkeyPatch) -> None:
    """每顆骰都擲 19（d20 命中不暴擊；小骰取上限）。"""
    monkeypatch.setattr(Rng, "roll", lambda _self, sides: min(sides, 19))


def skill(sid: str, shape: dict[str, Any], effects: list[dict[str, Any]]) -> SkillDef:
    return make_skill(sid, shape, effects, weapon_req="any")


# ---------------------------------------------------------------------------
# 2. 相鄰與距離（D4、T2）
# ---------------------------------------------------------------------------


def test_d4_the_twelve_side_tiles_are_adjacent_and_the_corners_are_not() -> None:
    hero = template("hero_fighter", reactions=[])
    state = arena([(6, 10, hero)])
    g, uid = giant(state), at(state, (6, 10)).id
    for xy in SIDES:
        s = moved(state, uid, xy)
        h = s.units[uid]
        assert adjacent(h, s.units[g.id]) and unit_dist(h, g) == 1, xy
        assert attack_problem(s, h, s.units[g.id]) is None, xy  # 近戰貼著任何一格都打得到
    for xy in CORNERS:
        s = moved(state, uid, xy)
        h = s.units[uid]
        assert not adjacent(h, g) and unit_dist(h, g) == 2, xy
        problem = attack_problem(s, h, s.units[g.id])
        assert problem is not None and "射程" in problem, xy


def test_d4_range_is_measured_to_the_nearest_tile() -> None:
    """規格 5.5 第 2 列：射程 5 的火球從 (5, 9) 打中心 (5, 3) 的頭目＝距離 5（不是 6）。"""
    bolt = skill(
        "skill_t_gb1b_bolt",
        {"type": "single", "range": 5},
        DMG,
    )
    short = skill(
        "skill_t_gb1b_shrt",
        {"type": "single", "range": 4},
        DMG,
    )
    m = make_map(FLAT13, ally=[(5, 9)], enemy=[(5, 3)])
    caster = caster_template([bolt, short])
    state = make_state(
        m,
        [spawn_giant(Team.ENEMY, (5, 3)), spawn(Team.ALLY, (5, 9), caster)],
        skills=[bolt, short],
    )
    g, me = giant(state), at(state, (5, 9))
    assert dist_to(g, me.xy) == 5
    area = checked_area(state, me, bolt, UseSkill(unit_id=me.id, skill_id=bolt.id, target_id=g.id))
    assert area.units == (g.id,) and area.tiles == ((5, 4),)  # 打中的那一格是離施放者最近的佔格
    with pytest.raises(IllegalActionError, match="距離 5，射程 4"):
        checked_area(state, me, short, UseSkill(unit_id=me.id, skill_id=short.id, target_id=g.id))


def test_d4_leaving_any_side_triggers_the_opportunity_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """藉機攻擊以佔格計：從南排外側 (6, 8) 走開，巨人（盜賊的藉機攻擊規則）出手；一格時那裡離中心
    2 格、不會觸發。走進相鄰不觸發藉機攻擊。"""
    always_19(monkeypatch)
    hero = template("hero_fighter", reactions=[], max_hp=99)
    state = arena([(6, 8, hero)])
    g, me = giant(state), at(state, (6, 8))
    leave = resolve(
        give_turn(state, me.id), Move(unit_id=me.id, path=(Pos(x=6, y=8), Pos(x=6, y=9)))
    )
    rolls = [e for e in leave.events if isinstance(e, AttackRolled)]
    assert [(e.attacker_id, e.target_id) for e in rolls] == [(g.id, me.id)]
    assert rolls[0].hit_tile is None  # 目標是一格的單位
    far = moved(state, me.id, (6, 9))
    enter = resolve(give_turn(far, me.id), Move(unit_id=me.id, path=(Pos(x=6, y=9), Pos(x=6, y=8))))
    assert not [e for e in enter.events if isinstance(e, AttackRolled)]


# ---------------------------------------------------------------------------
# 3. 範圍只打一次、打中的那一格（R1、T5、D6）
# ---------------------------------------------------------------------------

SQUARE = skill(
    "skill_t_gb1b_sqre",
    {"type": "square3", "range": 6},
    DMG,
)


def test_r1_an_area_covering_four_tiles_hits_once_at_the_nearest_tile() -> None:
    state = arena([(6, 11, caster_template([SQUARE]))], skills=[SQUARE])
    g, me = giant(state), at(state, (6, 11))
    action = UseSkill(unit_id=me.id, skill_id=SQUARE.id, target_pos=Pos(x=7, y=7))
    area = checked_area(state, me, SQUARE, action)
    assert sorted(xy for xy in area.tiles if xy in BOX) == [(6, 6), (6, 7), (7, 6), (7, 7)]
    assert area.units == (g.id,) and area.hit_tiles == ((g.id, (7, 7)),)
    result = resolve(with_rolls(give_turn(state, me.id), [(20, 19), (4, 3)]), action)
    rolled = [e for e in result.events if isinstance(e, AttackRolled) and e.target_id == g.id]
    damage = [e for e in result.events if isinstance(e, DamageDealt) and e.target_id == g.id]
    assert len(rolled) == 1 and rolled[0].hit_tile == Pos(x=7, y=7)
    assert len(damage) == 1 and not [e for e in result.events if isinstance(e, PartDamaged)]
    assert result.state.units[g.id].hp == g.hp - damage[0].amount


def test_r1_ties_go_to_the_smaller_y_then_x() -> None:
    state = arena([(6, 11, caster_template([SQUARE]))], skills=[SQUARE])
    g = giant(state)
    assert _hit_tiles(state, (g.id,), ((7, 7), (5, 7)), (6, 9)) == ((g.id, (5, 7)),)
    assert _hit_tiles(state, (g.id,), ((7, 5), (7, 7)), (9, 6)) == ((g.id, (7, 5)),)


def test_r1_cover_is_judged_at_the_hit_tile() -> None:
    """掩護看打中的那一格：方陣中心 (7, 7)（角落）時，(7, 8) 的木箱擋在那一格朝施放者那一側。"""
    state = arena([(7, 11, caster_template([SQUARE]))], skills=[SQUARE], objects=((7, 8, "crate"),))
    g, me = giant(state), at(state, (7, 11))
    action = UseSkill(unit_id=me.id, skill_id=SQUARE.id, target_pos=Pos(x=7, y=7))
    result = resolve(with_rolls(give_turn(state, me.id), [(20, 19), (4, 3)]), action)
    (rolled,) = [e for e in result.events if isinstance(e, AttackRolled) and e.target_id == g.id]
    assert rolled.hit_tile == Pos(x=7, y=7) and rolled.cover < 0


def test_t5_a_chain_jumps_through_the_giant_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    always_19(monkeypatch)
    chain = skill(
        "skill_t_gb1b_chan",
        {"type": "chain", "range": 6, "jumps": 3, "jump_range": 2},
        DMG,
    )
    state = arena([(6, 11, caster_template([chain]))], [(6, 9), (9, 6)], skills=[chain])
    g, me = giant(state), at(state, (6, 11))
    first, last = at(state, (6, 9)), at(state, (9, 6))
    action = UseSkill(unit_id=me.id, skill_id=chain.id, target_id=first.id)
    area = checked_area(state, me, chain, action)
    assert area.units == (
        first.id,
        g.id,
        last.id,
    )  # 從 (6, 9) 跳到南排 (6, 7)，再從東欄 (7, 6) 跳出
    assert area.hit_tiles == ((g.id, (6, 7)),)
    result = resolve(give_turn(state, me.id), action)
    targets = [e.target_id for e in result.events if isinstance(e, AttackRolled)]
    assert sorted(targets) == sorted([first.id, g.id, last.id])


def test_area_units_are_unique() -> None:
    """``_tiles_to_units`` 依單位去重（T5）：範圍光環蓋到 9 格也只有一個巨人。"""
    burst = skill(
        "skill_t_gb1b_brst",
        {"type": "allies_in_radius", "radius": 3},
        DMG,
    )
    state = arena([(6, 9, caster_template([burst]))], skills=[burst])
    me = at(state, (6, 9))
    area = checked_area(state, me, burst, UseSkill(unit_id=me.id, skill_id=burst.id))
    assert area.units.count(giant(state).id) == 1
    assert len(area.units) == len(set(area.units))


# ---------------------------------------------------------------------------
# 4. 以自己為中心的形狀（R2）
# ---------------------------------------------------------------------------

RING2 = [(x, y) for y in range(3, 10) for x in range(3, 10) if max(abs(x - 6), abs(y - 6)) == 3]
# 「整個 3×3 當中心」的環形 2＝7×7 方框的外圈（切比雪夫距離恰為 2）
SQUARE_AROUND = [
    (4, 4), (5, 4), (6, 4), (7, 4), (8, 4),
    (4, 5), (8, 5),
    (4, 6), (8, 6),
    (4, 7), (8, 7),
    (4, 8), (5, 8), (6, 8), (7, 8), (8, 8),
]  # fmt: skip
CROSS_ARM2 = [
    (5, 3), (6, 3), (7, 3),
    (5, 4), (6, 4), (7, 4),
    (3, 5), (4, 5), (8, 5), (9, 5),
    (3, 6), (4, 6), (8, 6), (9, 6),
    (3, 7), (4, 7), (8, 7), (9, 7),
    (5, 8), (6, 8), (7, 8),
    (5, 9), (6, 9), (7, 9),
]  # fmt: skip
CONE3_SOUTH = [(6, 8), (5, 9), (6, 9), (7, 9), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10)]
LINE3_EAST = [(8, 6), (9, 6), (10, 6)]

SELF_SHAPES: list[tuple[str, dict[str, Any], dict[str, Any], list[tuple[int, int]] | int]] = [
    ("ring2", {"type": "ring", "radius": 2}, {}, sorted(RING2, key=lambda p: (p[1], p[0]))),
    ("radius3", {"type": "allies_in_radius", "radius": 3}, {}, 48),
    ("square", {"type": "square3", "range": 0}, {"target_pos": Pos(x=6, y=6)}, SQUARE_AROUND),
    ("cross2", {"type": "cross", "range": 0, "arm": 2}, {"target_pos": Pos(x=6, y=6)}, CROSS_ARM2),
    ("cone3", {"type": "cone", "size": 3}, {"direction": "south"}, CONE3_SOUTH),
    ("line3", {"type": "line", "size": 3}, {"direction": "east"}, LINE3_EAST),
]


@pytest.mark.parametrize(("name", "shape", "pick", "expected"), SELF_SHAPES)
def test_r2_self_centred_shapes_measure_from_the_whole_body(
    name: str, shape: dict[str, Any], pick: dict[str, Any], expected: list[tuple[int, int]] | int
) -> None:
    sk = skill(f"skill_t_gb1b_{name}", shape, DMG)
    state = arena([(0, 12, template("hero_fighter"))], skills=[sk], giant_skills=[sk.id])
    g = giant(state)
    area = checked_area(state, g, sk, UseSkill(unit_id=g.id, skill_id=sk.id, **pick))
    assert not set(area.tiles) & BOX  # 佔格本身永遠不在範圍內
    if isinstance(expected, int):
        assert len(area.tiles) == expected
        assert all(1 <= dist_to(g, xy) <= 3 for xy in area.tiles)
    else:
        assert list(area.tiles) == sorted(expected, key=lambda p: (p[1], p[0]))


def test_r2_counts_from_the_plan() -> None:
    """規格 0.2 R2 的格數：環形 2、十字臂長 2 各 24 格，方陣 16 格，範圍光環 4 是 72 格。"""
    state = arena([(0, 12, template("hero_fighter"))])
    g = giant(state)
    assert len(around_tiles(state, g, "ring", 2)) == 24
    assert len(around_tiles(state, g, "cross", 2)) == 24
    assert len(around_tiles(state, g, "square3", 1)) == 16
    assert len(around_tiles(state, g, "allies_in_radius", 4)) == 72


def test_r2_one_tile_casters_keep_the_old_shapes() -> None:
    state = arena([(2, 10, template("hero_fighter"))])
    me = at(state, (2, 10))
    assert len(around_tiles(state, me, "ring", 2)) == 16
    assert (2, 10) in around_tiles(state, me, "square3", 1)  # 一格時方陣照舊含自己
    assert len(around_tiles(state, me, "cross", 2)) == 9


def test_r2_the_giant_lists_its_own_body_once_as_a_centre() -> None:
    state = arena([(0, 12, template("hero_fighter"))])
    cells = caster_center_candidates(state, giant(state), 1)
    assert [c for c in cells if c in BOX] == [(6, 6)]
    assert (6, 8) in cells and (6, 9) not in cells  # 射程從最近的佔格量


# ---------------------------------------------------------------------------
# 5. 出招起點（T9）、拉人方向（T7）
# ---------------------------------------------------------------------------


def test_t9_the_giant_strikes_from_the_tile_facing_the_target() -> None:
    fighter = template("hero_fighter", reactions=[])
    state = arena([(6, 8, fighter), (8, 6, fighter), (6, 10, fighter)])
    g = giant(state)
    south, east, far = at(state, (6, 8)), at(state, (8, 6)), at(state, (6, 10))
    assert strike_tiles(g, south) == ((6, 7), (6, 8))
    assert strike_tiles(g, east) == ((7, 6), (8, 6))
    assert attack_problem(state, g, south) is None and attack_problem(state, g, east) is None
    assert attack_problem(state, g, far) is not None
    bolt = skill(
        "skill_t_gb1b_gblt",
        {"type": "single", "range": 3},
        DMG,
    )
    s2 = arena([(6, 10, fighter)], skills=[bolt], giant_skills=[bolt.id])
    g2, target = giant(s2), at(s2, (6, 10))
    area = checked_area(
        s2, g2, bolt, UseSkill(unit_id=g2.id, skill_id=bolt.id, target_id=target.id)
    )
    assert area.units == (target.id,)  # 從南排 (6, 7) 起算＝3 格；從中心算會是 4 格


def _pull_result(
    monkeypatch: pytest.MonkeyPatch, shape: dict[str, Any], heroes: list[tuple[int, int]]
) -> Any:
    always_19(monkeypatch)
    pull = skill("skill_t_gb1b_pull", shape, [{"type": "pull", "distance": 1}])
    fighter = template("hero_fighter", reactions=[], max_hp=99)
    state = arena([(x, y, fighter) for x, y in heroes], skills=[pull], giant_skills=[pull.id])
    g = giant(state)
    result = resolve(give_turn(state, g.id), UseSkill(unit_id=g.id, skill_id=pull.id))
    return state, result


def test_t7_the_giant_pulls_toward_its_nearest_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    state, result = _pull_result(monkeypatch, {"type": "ring", "radius": 2}, [(6, 9), (9, 9)])
    south, corner = at(state, (6, 9)).id, at(state, (9, 9)).id
    after = result.state.units
    assert after[south].xy == (6, 8)
    assert after[corner].xy == (8, 9)  # 斜向同距離取 x 軸（最近的佔格是 (7, 7)）


def test_t7_already_adjacent_units_are_not_pulled(monkeypatch: pytest.MonkeyPatch) -> None:
    state, result = _pull_result(
        monkeypatch, {"type": "allies_in_radius", "radius": 3}, [(6, 8), (6, 10)]
    )
    near, far = at(state, (6, 8)).id, at(state, (6, 10)).id
    assert result.state.units[near].xy == (6, 8)
    assert result.state.units[far].xy == (6, 9)
    assert not [e for e in result.events if isinstance(e, UnitMoved) and e.unit_id == near]


# ---------------------------------------------------------------------------
# AI 與預覽（5.2 第 6、7 點）
# ---------------------------------------------------------------------------


def test_ai_walks_next_to_any_tile_and_attacks_the_giant() -> None:
    fighter = template("hero_fighter", reactions=[])
    base = arena([(6, 11, fighter)])
    me = at(base, (6, 11))
    s = give_turn(base, me.id)
    ai = UtilityAI(library().ai_profiles)
    attacked = False
    for _ in range(6):
        action = ai(s)
        if isinstance(action, (Attack, UseSkill)):  # 普攻或武器技（hero_fighter 選撕裂斬）
            assert action.target_id == giant(s).id
            assert unit_dist(s.units[me.id], giant(s)) == 1
            attacked = True
            break
        if not isinstance(action, Move):
            break
        s = resolve(s, action).state
    assert attacked


def test_preview_of_an_attack_on_the_giant_has_no_side_effects() -> None:
    fighter = template("hero_fighter", reactions=[])
    base = arena([(6, 8, fighter)])
    me = at(base, (6, 8))
    state = give_turn(base, me.id)
    before = state_to_json(state)
    shown = preview(state, Attack(unit_id=me.id, target_id=giant(state).id))
    assert shown is not None
    assert state_to_json(state) == before


# ---------------------------------------------------------------------------
# 14. 確定性
# ---------------------------------------------------------------------------


def _battle_spawns() -> Iterator[Any]:
    yield spawn_giant(Team.ENEMY, (6, 6), giant_template(id=GIANT_ID))
    yield spawn(Team.ALLY, (6, 10), "hero_fighter")
    yield spawn(Team.ALLY, (3, 11), "hero_archer")


def test_same_seed_same_battle_and_the_log_replays() -> None:
    setup = make_setup(board([(6, 10), (3, 11)]), list(_battle_spawns()), max_rounds=5)
    ai = UtilityAI(library().ai_profiles)
    first = run_battle(setup, 3, ai)
    second = run_battle(setup, 3, ai)
    assert EVENT_LIST_ADAPTER.dump_json(first.events) == EVENT_LIST_ADAPTER.dump_json(second.events)  # type: ignore[arg-type]
    assert any(
        isinstance(e, AttackRolled) and e.target_id == giant(first.state).id for e in first.events
    )
    log = BattleLog.model_validate_json(first.to_log().model_dump_json())
    again = replay(log.setup, log.seed, log.actions)
    assert state_to_json(again.state) == state_to_json(first.state)


@pytest.mark.parametrize("accept", [True, False])
def test_a_pause_while_the_giant_attacks_resumes_like_a_round_trip(accept: bool) -> None:
    guard = template("hero_fighter", reactions=PROMPT_BLOCK)
    state = arena([(6, 8, guard)])
    g, me = giant(state), at(state, (6, 8))
    paused = resolve(give_turn(state, g.id), Attack(unit_id=g.id, target_id=me.id))
    assert paused.pending is not None and paused.pending.reaction == "block"
    direct = resume(paused.state, Decision(unit_id=me.id, accept=accept))
    restored = state_from_json(state_to_json(paused.state))
    again = resume(restored, Decision(unit_id=me.id, accept=accept))
    assert state_to_json(again.state) == state_to_json(direct.state)
    assert EVENT_LIST_ADAPTER.dump_json(again.events) == EVENT_LIST_ADAPTER.dump_json(direct.events)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# T2：新加的查詢在一格時退化成原本的算法（不變比對成立的前提）
# ---------------------------------------------------------------------------

coords = st.tuples(st.integers(0, 30), st.integers(0, 30))
cells = st.tuples(st.integers(0, 12), st.integers(0, 12))


@settings(deadline=None)
@given(coords, coords, st.sampled_from([(0, -1), (1, 0), (0, 1), (-1, 0)]))
def test_one_tile_helpers_match_the_old_ones(
    a: tuple[int, int], b: tuple[int, int], step: tuple[int, int]
) -> None:
    unit, other = unit_at(a), unit_at(b)
    assert strike_tiles(unit, other) == (a, b)
    assert chebyshev_to(unit, b) == chebyshev(a, b)
    assert face_tile(unit, step) == a
    assert touches(unit, {b}) == (a == b)


@settings(deadline=None)
@given(coords, coords)
def test_giant_strike_tiles_are_a_nearest_pair(c: tuple[int, int], xy: tuple[int, int]) -> None:
    g, other = unit_at(c, 3), unit_at(xy)
    origin, aim = strike_tiles(g, other)
    assert aim == xy and origin in tiles_of(g)
    assert manhattan(origin, aim) == min(manhattan(t, xy) for t in tiles_of(g))
    assert strike_tiles(other, g) == (xy, origin)


@settings(deadline=None, max_examples=40)
@given(cells, st.integers(1, 3))
def test_one_tile_self_shapes_and_centres_are_unchanged(xy: tuple[int, int], size: int) -> None:
    state = moved(_shape_state(), _HERO, xy)
    if state.unit_at(*xy) is not state.units[_HERO]:
        return  # 那一格是巨人
    hero = state.units[_HERO]
    assert around_tiles(state, hero, "ring", size) == ring_tiles(state, xy, size)
    assert around_tiles(state, hero, "allies_in_radius", size) == radius_tiles(state, xy, size)
    assert around_tiles(state, hero, "cross", size) == cross_tiles(state, xy, size)
    assert around_tiles(state, hero, "square3", size) == square3_tiles(state, xy)
    assert caster_center_candidates(state, hero, size) == center_candidates(state, xy, size)


_HERO = UnitId("unit_0002")


@cache
def _shape_state() -> BattleState:
    state = arena([(0, 12, template("hero_fighter"))])
    assert state.unit_at(0, 12) is state.units[_HERO]
    return state
