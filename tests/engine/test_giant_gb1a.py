"""GB-1a 不動巨型頭目的佔格與基礎（05 5.12.4、``PhaseGB計畫.md`` 5.1、5.5）：實際跑引擎，每列一條
規則句（列名寫 D／T 編號）。合成巨人（``helpers.giant_template``：佔 3×3、帶 ``boss``、**不帶**
``immovable``）只在測試裡。

場地：9×11 平地；巨人（敵方）中心 (4, 4)、佔 x 3～5、y 3～5，正面朝東（``giant_facing``）；
我方英雄 (4, 8)、(0, 8)；巨人身後（北）一名盜賊 (4, 0)。

距離、範圍、出招起點（GB-1b）與部位綁格（GB-1c）不在這一段。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.engine.helpers import (
    giant_template,
    library,
    make_map,
    make_setup,
    make_state,
    spawn,
    spawn_giant,
)
from trpg.content.maps import MapDef
from trpg.engine import BattleState
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    ChangeTileEffect,
    CreateObstacleEffect,
    CreateSurfaceEffect,
    EffectBase,
    InscribeEffect,
    LowerTerrainEffect,
    MoveUnitEffect,
    PushEffect,
    SwapUnitsEffect,
)
from trpg.engine.effects.surface_entry import enter_surface
from trpg.engine.events import (
    EffectFizzled,
    EnteredDeadlyTerrain,
    EventBase,
    MoveBlocked,
    PushResisted,
)
from trpg.engine.ids import PRONE
from trpg.engine.reactions import after_attack
from trpg.engine.rules.facing import face_toward, is_behind
from trpg.engine.rules.footprint import tiles_of
from trpg.engine.rules.geometry import has_line_of_sight
from trpg.engine.rules.landing import LandingBlock, landing_problem, nearest_free
from trpg.engine.rules.movement import available_move_budget, find_path, reachable_tiles
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.setup import BattleSetupError
from trpg.engine.skills.targeting import _trap_site_problem, summon_site_problem
from trpg.engine.state import UnitState, state_from_json, state_to_json
from trpg.shared.types import Element, Pos, Surface, Team, UnitId

FLAT = "\n".join("000000000" for _ in range(11))
TILES = {(x, y) for y in range(3, 6) for x in range(3, 6)}
GIANT_ID = "test_giant"


def board(*, terrain: str | None = None, surfaces: tuple[tuple[int, int, str], ...] = ()) -> MapDef:
    m = make_map(
        FLAT,
        terrain,
        ally=[(4, 8), (0, 8)],
        enemy=[(4, 4), (4, 0)],
        surfaces=surfaces,
    )
    return m.model_copy(update={"giant_facing": {GIANT_ID: "east"}})


def arena(*, giant_team: Team = Team.ENEMY, **kw: object) -> BattleState:
    return make_state(
        board(**kw),  # type: ignore[arg-type]
        [
            spawn_giant(giant_team, (4, 4), giant_template(id=GIANT_ID)),
            spawn(Team.ENEMY, (4, 0)),
            spawn(Team.ALLY, (4, 8)),
            spawn(Team.ALLY, (0, 8)),
        ],
    )


def giant(state: BattleState) -> UnitState:
    return next(u for u in state.units_sorted() if u.footprint == 3)


def at(state: BattleState, xy: tuple[int, int]) -> UnitState:
    found = state.unit_at(*xy)
    assert found is not None
    return found


def run(state: BattleState, *effects: EffectBase) -> tuple[Ctx, list[EventBase]]:
    ctx = Ctx(state.clone())
    execute(ctx, list(effects))
    return ctx, list(ctx.events)


# ---------------------------------------------------------------------------
# 1. 佔格（D3、T3）
# ---------------------------------------------------------------------------


def test_d3_all_nine_tiles_belong_to_the_giant() -> None:
    state = arena()
    g = giant(state)
    assert set(tiles_of(g)) == TILES
    assert all(state.unit_at(*xy) is g for xy in TILES)
    occupancy = state.occupancy()
    assert all(occupancy[xy] is g for xy in TILES)
    assert all(landing_problem(state, xy) is LandingBlock.OCCUPIED for xy in TILES)
    assert nearest_free(state, (4, 4)) not in TILES


def test_d3_paths_go_around_the_giant_even_for_its_allies() -> None:
    for team in (Team.ENEMY, Team.ALLY):
        state = arena(giant_team=team)
        hero = at(state, (4, 8))
        state.units[hero.id].move_points = 30
        assert not {(p.x, p.y) for p in reachable_tiles(state, hero.id)} & TILES
        path = find_path(state, hero.id, Pos(x=4, y=2), unlimited=True)
        assert path is not None and len(path) > 7  # 直走是 6 步，要繞
        assert not {(p.x, p.y) for p in path} & TILES


def test_d3_nothing_can_be_put_on_the_giant_tiles() -> None:
    state = arena()
    hero = at(state, (4, 8))
    ctx, events = run(state, CreateObstacleEffect(pos=(3, 3)))
    assert [e.reason for e in events if isinstance(e, EffectFizzled)] == ["occupied"]
    assert ctx.state.tile(3, 3).object_id is None
    rune = InscribeEffect(source_id=hero.id, team=Team.ALLY, pos=(5, 5), element=Element.FIRE)
    ctx, events = run(state, rune)
    assert [e.reason for e in events if isinstance(e, EffectFizzled)] == ["occupied"]
    assert not ctx.state.runes
    ctx, events = run(state, CreateSurfaceEffect(pos=(3, 4), surface=Surface.FIRE))
    assert events == [] and ctx.state.tile(3, 4).surface is Surface.NONE  # 跳過、不發事件
    assert summon_site_problem(state, (5, 3)) is not None
    assert _trap_site_problem(state, (3, 5)) is not None
    ctx, events = run(state, MoveUnitEffect(unit_id=hero.id, dest=(5, 3), mode="teleport"))
    assert [e.reason for e in events if isinstance(e, MoveBlocked)] == ["occupied"]


def test_d3_giants_are_placed_first_and_others_skip_their_tiles() -> None:
    m = make_map(FLAT, ally=[(4, 8)], enemy=[(4, 3), (4, 4), (4, 0)])
    loose = spawn(Team.ENEMY, (0, 0)).model_copy(update={"position": None})
    big = spawn_giant(Team.ENEMY, None)
    state = make_state(m, [loose, big, spawn(Team.ALLY, (4, 8))])
    assert giant(state).xy == (4, 3)  # 起始區第一格就放得下
    assert at(state, (4, 0)).footprint == 1  # (4, 4) 被巨人佔了，盜賊排到下一格


def test_d3_explicit_positions_cannot_overlap_the_giant() -> None:
    with pytest.raises(BattleSetupError, match="重疊"):
        make_state(
            board(),
            [spawn(Team.ALLY, (3, 3)), spawn_giant(Team.ENEMY, (4, 4)), spawn(Team.ALLY, (4, 8))],
        )


# ---------------------------------------------------------------------------
# 2. 視線（D7、T4）
# ---------------------------------------------------------------------------


def test_d7_the_body_blocks_sight_behind_it_but_not_to_itself() -> None:
    state = arena()
    assert not has_line_of_sight(state, (4, 8), (4, 0))
    assert not has_line_of_sight(state, (4, 8), (4, 0), lob=1)  # 拋射也越不過
    for tile in ((4, 4), (4, 3), (3, 3), (5, 5)):  # 打它自己的任一格（含北排）不擋
        assert has_line_of_sight(state, (4, 8), tile)
    assert has_line_of_sight(state, (4, 8), (4, 0), ignore_unit=giant(state))


def test_d7_one_tile_units_still_do_not_block_sight() -> None:
    state = make_state(
        board(),
        [spawn(Team.ENEMY, (4, 4)), spawn(Team.ENEMY, (4, 0)), spawn(Team.ALLY, (4, 8))],
    )
    assert has_line_of_sight(state, (4, 8), (4, 0))


# ---------------------------------------------------------------------------
# 3. 位移免疫（D8、T6）
# ---------------------------------------------------------------------------


def _hero(state: BattleState) -> UnitId:
    return at(state, (4, 8)).id


DISPLACEMENTS: dict[str, Callable[[BattleState], EffectBase]] = {
    "push": lambda s: PushEffect(
        source_id=_hero(s), target_id=giant(s).id, direction=(0, -1), distance=2
    ),
    "pull": lambda s: PushEffect(
        source_id=_hero(s), target_id=giant(s).id, direction=(0, 1), distance=1, pull=True
    ),
    "swap": lambda s: SwapUnitsEffect(unit_id=_hero(s), other_id=giant(s).id),
    "teleported": lambda s: MoveUnitEffect(
        source_id=_hero(s), unit_id=giant(s).id, dest=(1, 1), mode="teleported"
    ),
    "teleport": lambda s: MoveUnitEffect(unit_id=giant(s).id, dest=(1, 1), mode="teleport"),
    "prone": lambda s: ApplyStatusEffect(target_id=giant(s).id, status_id=PRONE),
    "slide": lambda s: MoveUnitEffect(unit_id=giant(s).id, dest=(4, 6), mode="slide"),
}


@pytest.mark.parametrize("kind", sorted(DISPLACEMENTS))
def test_d8_the_giant_never_moves_or_falls_prone(kind: str) -> None:
    state = arena()
    ctx, events = run(state, DISPLACEMENTS[kind](state))
    g = giant(ctx.state)
    assert g.xy == (4, 4) and not g.has_status(PRONE)
    assert at(ctx.state, (4, 8)).id == _hero(state)  # 換位時英雄也沒動
    reasons = {
        getattr(e, "reason", None)
        for e in events
        if isinstance(e, (MoveBlocked, PushResisted, EffectFizzled))
    }
    assert reasons == {"immovable"}


def test_d8_the_giant_has_no_move_budget() -> None:
    state = arena()
    g = giant(state)
    g.move_points = 5
    assert available_move_budget(state, g) is None


def test_t6_one_tile_immovable_units_keep_todays_rules() -> None:
    """T6：只有佔多格的單位補齊免疫；1 格的 ``immovable``（源晶柱）照現行可以被換位、擊倒。"""
    state = make_state(
        board(),
        [spawn(Team.ENEMY, (4, 4), "rift_pillar_fire"), spawn(Team.ALLY, (4, 8))],
    )
    pillar, hero = at(state, (4, 4)), at(state, (4, 8))
    ctx, _ = run(state, SwapUnitsEffect(unit_id=hero.id, other_id=pillar.id))
    assert ctx.state.units[pillar.id].xy == (4, 8)
    ctx, _ = run(state, ApplyStatusEffect(target_id=pillar.id, status_id=PRONE))
    assert ctx.state.units[pillar.id].has_status(PRONE)


# ---------------------------------------------------------------------------
# 4. 朝向（D9、T8）
# ---------------------------------------------------------------------------


def test_d9_facing_comes_from_the_map_and_never_turns() -> None:
    state = arena()
    g = giant(state)
    assert g.facing == "east"
    face_toward(g, (0, 0))
    assert g.facing == "east"
    hero = at(state, (4, 8))
    ctx = Ctx(state.clone())
    after_attack(
        ctx, ctx.state.units[hero.id], None, ambushed=False, turns=[(giant(ctx.state), (4, 6))]
    )
    assert giant(ctx.state).facing == "east"


def test_t8_behind_is_the_column_outside_the_back_face() -> None:
    g = giant(arena())  # 朝東：背面是西側那一欄 x＝3，背後是 x＝2、y 3～5
    assert [is_behind((2, y), g) for y in (2, 3, 4, 5, 6)] == [False, True, True, True, False]
    assert not is_behind((6, 4), g) and not is_behind((4, 6), g) and not is_behind((1, 4), g)


def test_t8_without_an_entry_the_giant_keeps_the_team_facing() -> None:
    plain = make_map(FLAT, ally=[(4, 8), (0, 8)], enemy=[(4, 4), (4, 0)])
    state = make_state(plain, [spawn_giant(Team.ENEMY, (4, 4)), spawn(Team.ALLY, (4, 8))])
    assert giant(state).facing == "south"  # 敵方面向我方（南）


# ---------------------------------------------------------------------------
# 5. 地形（D10、T10）
# ---------------------------------------------------------------------------


def test_d10_deadly_terrain_under_the_giant_does_nothing() -> None:
    rows = ["." * 9 for _ in range(11)]
    rows[5] = "....." + "~" + "..."  # (5, 5) 是岩漿、在佔格內
    state = arena(terrain="\n".join(rows))
    g = giant(state)
    assert g.alive
    ctx, events = run(state, ChangeTileEffect(pos=(3, 3), terrain="lava"))
    assert events == [] and ctx.state.tile(3, 3).terrain == "stone"  # 佔格的地形不改
    ctx, events = run(state, LowerTerrainEffect(pos=(5, 3)))
    assert events == [] and ctx.state.tile(5, 3).height == 0
    assert not any(isinstance(e, EnteredDeadlyTerrain) for e in events)


def test_d10_surfaces_under_the_giant_are_cleared_and_never_entered() -> None:
    state = arena(surfaces=((3, 4, "fire"), (6, 4, "fire")))
    assert state.tile(3, 4).surface is Surface.NONE  # 佔格上的表面開場清掉
    assert state.tile(6, 4).surface is Surface.FIRE  # 佔格外的照舊
    ctx = Ctx(state.clone())
    t = ctx.state.tile(4, 4)
    ctx.state.set_tile(4, 4, t.__class__(height=t.height, terrain=t.terrain, surface=Surface.FIRE))
    assert enter_surface(ctx, giant(ctx.state)) == []


# ---------------------------------------------------------------------------
# 6. 確定性與序列化
# ---------------------------------------------------------------------------


def test_same_seed_same_battle_and_the_log_replays() -> None:
    setup = make_setup(
        board(),
        [
            spawn_giant(Team.ENEMY, (4, 4), giant_template(id=GIANT_ID)),
            spawn(Team.ENEMY, (4, 0)),
            spawn(Team.ALLY, (4, 8)),
            spawn(Team.ALLY, (0, 8)),
        ],
        max_rounds=4,
    )
    lib_ai = UtilityAI(library().ai_profiles)
    first = run_battle(setup, 5, lib_ai)
    second = run_battle(setup, 5, lib_ai)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
    log = BattleLog.model_validate_json(first.to_log().model_dump_json())
    again = replay(log.setup, log.seed, log.actions)
    assert state_to_json(again.state) == state_to_json(first.state)
    assert giant(again.state).xy == (4, 4)


def test_clone_and_json_keep_the_footprint_and_one_tile_json_is_unchanged() -> None:
    state = arena()
    g = giant(state)
    assert state.clone().units[g.id].footprint == 3
    assert state_from_json(state_to_json(state)).units[g.id].footprint == 3
    hero = at(state, (4, 8))
    assert '"footprint":3' in state_to_json(state).replace(" ", "")
    assert state_to_json(state).count('"footprint"') == 1  # 一格的單位不輸出
    assert hero.footprint == 1
