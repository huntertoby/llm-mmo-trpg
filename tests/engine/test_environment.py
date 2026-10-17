"""環境互動的情境測試（docs/phases/Phase1計畫.md 6.2-2）：物件、表面、互動表、推擊、連鎖。

全部以資料驅動：測試只建構小地圖、放置物件與表面，再執行動作或直接把效果放進佇列。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.engine import Attack, BattleState, EndTurn, Move, Shove, legal_actions, resolve
from trpg.engine.effects import (
    CreateSurfaceEffect,
    DamageEffect,
    DamageObjectEffect,
    ElementTouchEffect,
    LowerTerrainEffect,
    PushEffect,
    RaiseTerrainEffect,
    run_effects,
)
from trpg.engine.events import (
    ChainLimitReached,
    CheckRolled,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    ObjectDestroyed,
    ObjectExploded,
    PushResisted,
    StatusApplied,
    UnitFell,
)
from trpg.shared.types import Element, ObjectId, Pos, Surface, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
O1, O2, O3, O4 = (ObjectId(f"obj_000{i}") for i in range(1, 5))


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def surfaces(state: BattleState) -> dict[tuple[int, int], Surface]:
    return {
        (x, y): state.tile(x, y).surface
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is not Surface.NONE
    }


# ---------------------------------------------------------------------------
# 火焰 × 油桶
# ---------------------------------------------------------------------------


def _depot() -> BattleState:
    """5×5：油桶在 (2, 2)，周圍有油；盜賊在 (1, 2)、(3, 2)；法師在 (2, 0)（爆炸範圍外）。"""
    m = make_map(
        "00000\n00000\n00000\n00000\n00000",
        objects=[(2, 2, "oil_barrel")],
        surfaces=[(1, 1, "oil"), (3, 3, "oil"), (2, 3, "oil"), (2, 2, "oil"), (4, 4, "oil")],
        ally=[(2, 0)],
        enemy=[(1, 2)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 0), "hero_mage"),
            spawn(Team.ENEMY, (1, 2), template("bandit", max_hp=200)),
            spawn(Team.ENEMY, (3, 2), template("bandit", max_hp=200)),
        ],
    )
    return give_turn(state, U1)


def test_fire_attack_on_oil_barrel_explodes() -> None:
    state = _depot()
    action = Attack(unit_id=U1, target_object_id=O1)
    assert action in legal_actions(state)
    result = resolve(state, action)
    events = result.events
    exploded = [e for e in events if isinstance(e, ObjectExploded)]
    assert len(exploded) == 1 and exploded[0].object_id == O1 and exploded[0].radius == 1
    destroyed = [e for e in events if isinstance(e, ObjectDestroyed)]
    assert [(d.object_id, d.cause) for d in destroyed] == [(O1, "explosion")]
    assert result.state.objects[O1].destroyed
    assert result.state.tile(2, 2).object_id is None
    # 3×3 範圍內的兩名盜賊受到爆炸火焰傷害
    blast = [e for e in events if isinstance(e, DamageDealt) and e.cause == "explosion"]
    assert {e.target_id for e in blast} == {U2, U3}
    assert all(e.element is Element.FIRE and e.source_id == U1 for e in blast)
    # 範圍內的油著火，範圍外 (4, 4) 的油不變
    after = surfaces(result.state)
    for xy in [(1, 1), (3, 3), (2, 3), (2, 2)]:
        assert after[xy] is Surface.FIRE, xy
    assert after[(4, 4)] is Surface.OIL


def test_physical_attack_destroys_barrel_without_explosion() -> None:
    m = make_map("000\n000", objects=[(1, 0, "oil_barrel")], surfaces=[(1, 1, "oil")])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (2, 1))]), U1
    )
    result = run_effects(state, [DamageObjectEffect(object_id=O1, flat=100, source_id=U1)])
    assert [type(e) for e in result.events if isinstance(e, ObjectExploded)] == []
    assert result.state.objects[O1].destroyed
    assert surfaces(result.state) == {(1, 1): Surface.OIL}


def test_chain_reaction_stops_at_depth_limit() -> None:
    """一排油桶：攻擊 (0) → 爆炸 (1) → (2) → (3) → 第 4 個油桶的爆炸超過深度 3，不發生。"""
    m = make_map(
        "000000\n000000",
        objects=[
            (1, 0, "oil_barrel"),
            (2, 0, "oil_barrel"),
            (3, 0, "oil_barrel"),
            (4, 0, "oil_barrel"),
        ],
        ally=[(0, 1)],
        enemy=[(5, 1)],
    )
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 1), "hero_mage"), spawn(Team.ENEMY, (5, 1))]), U1
    )
    result = resolve(state, Attack(unit_id=U1, target_object_id=O1))
    exploded = [e.object_id for e in result.events if isinstance(e, ObjectExploded)]
    assert exploded == [O1, O2, O3]
    limits = [e for e in result.events if isinstance(e, ChainLimitReached)]
    assert any(e.effect_kind == "explode" and e.depth == 4 for e in limits)
    assert not result.state.objects[O4].destroyed


# ---------------------------------------------------------------------------
# 木橋與深淵
# ---------------------------------------------------------------------------


def _bridge(victim: str) -> BattleState:
    """深淵 (1, 0..2) 上架了一座木橋 (1, 1)；受害者站在橋上，英雄在 (0, 1)。"""
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
            spawn(Team.ENEMY, (1, 1), victim),
            spawn(Team.ENEMY, (2, 2)),
        ],
    )
    return give_turn(state, U1)


def test_breaking_bridge_drops_normal_unit() -> None:
    state = _bridge("bandit")
    result = run_effects(state, [DamageObjectEffect(object_id=O1, flat=100, source_id=U1)])
    types = [type(e) for e in result.events]
    assert ObjectDestroyed in types and EnteredDeadlyTerrain in types
    assert result.state.units[U2].downed


def test_breaking_bridge_boss_takes_30_percent_and_moves_to_safe_tile() -> None:
    state = _bridge("bandit_boss")
    result = run_effects(state, [DamageObjectEffect(object_id=O1, flat=100, source_id=U1)])
    boss = result.state.units[U2]
    assert not boss.downed and boss.hp == 80 - 24
    # 最近的安全格：距離 1 的 (1, 0)、(0, 1)、(2, 1)、(1, 2) 中，(1, 0) 與 (1, 2) 是深淵、
    # (0, 1) 有英雄 → (2, 1)
    assert boss.pos == P(2, 1)


def test_attacking_bridge_until_it_breaks() -> None:
    state = _bridge("bandit")
    action = Attack(unit_id=U1, target_object_id=O1)
    assert action in legal_actions(state)
    hp = []
    for _ in range(3):
        if state.objects[O1].destroyed:
            break
        state = resolve(state, action).state
        hp.append(state.objects[O1].hp)
    assert state.objects[O1].destroyed and state.units[U2].downed
    assert hp[-1] == 0


def test_bridge_makes_chasm_walkable() -> None:
    m = make_map(
        "000\n000\n000", ".x.\n.x.\n.x.", objects=[(1, 1, "wooden_bridge")], enemy=[(2, 2)]
    )
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 1), "hero_fighter"), spawn(Team.ENEMY, (2, 2))]), U1
    )
    s = resolve(state, Move(unit_id=U1, path=(P(0, 1), P(1, 1), P(2, 1)))).state
    assert s.units[U1].pos == P(2, 1) and not s.units[U1].downed


def test_burning_bridge_collapses_at_environment_turn() -> None:
    """火焰點燃木橋 → 下一次環境回合摧毀 → 橋上的單位墜落。"""
    state = _bridge("bandit")
    s = run_effects(
        state,
        [ElementTouchEffect(pos=(1, 1), element=Element.FIRE, source_id=U1)],
    ).state
    assert s.objects[O1].burning == 1 and s.tile(1, 1).surface is Surface.FIRE
    # 跑完這一輪（三個單位結束回合）→ 環境回合
    events: list[EventBase] = []
    for _ in range(4):
        if s.round > 1 or s.ended:
            break
        assert s.active_unit is not None
        r = resolve(s, EndTurn(unit_id=s.active_unit))
        s, events = r.state, events + r.events
    destroyed = [e for e in events if isinstance(e, ObjectDestroyed)]
    assert destroyed and destroyed[0].cause == "burned"
    assert s.units[U2].downed


# ---------------------------------------------------------------------------
# 雷電 × 水、冰霜 × 水
# ---------------------------------------------------------------------------


def _swamp() -> BattleState:
    """水 (0..2, 1) 相連；目標在 (0, 1)，同一片水裡的 (2, 1)，水外的 (2, 2)。"""
    m = make_map(
        "0000\n0000\n0000",
        surfaces=[(0, 1, "water"), (1, 1, "water"), (2, 1, "water")],
        ally=[(3, 0)],
        enemy=[(0, 1)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 0), "hero_mage", weapon="lightning_staff"),
            spawn(Team.ENEMY, (0, 1), template("bandit", max_hp=200)),
            spawn(Team.ENEMY, (2, 1), template("bandit", max_hp=200)),
            spawn(Team.ENEMY, (2, 2), template("bandit", max_hp=200)),
        ],
    )
    return give_turn(state, U1)


def test_lightning_conducts_through_connected_water() -> None:
    state = with_rolls(_swamp(), [(20, 15), (6, 4)])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    damage = [e for e in result.events if isinstance(e, DamageDealt)]
    direct = [e for e in damage if e.cause == "attack"]
    conducted = [e for e in damage if e.cause == "conduct"]
    assert [e.target_id for e in direct] == [U2]
    assert [e.target_id for e in conducted] == [U3]  # (2, 2) 不在水裡
    assert conducted[0].element is Element.LIGHTNING
    assert conducted[0].amount == direct[0].amount  # damage_permille 1000


def test_ice_freezes_water_then_slip_check() -> None:
    state = _swamp()
    s = run_effects(
        state, [DamageEffect(target_id=U2, element=Element.ICE, flat=1, source_id=U1)]
    ).state
    assert s.tile(0, 1).surface is Surface.ICE
    assert s.tile(1, 1).surface is Surface.WATER  # 只有被命中的那一格
    # 盜賊 (2, 1) 走進冰面：d20 + 敏捷修正 (14 → +2) ≥ 12；擲 3 → 失敗 → 倒地並停止移動
    s = give_turn(s, U3)
    s.units[U2].pos = P(0, 2)  # 讓出冰面
    # 第一步 (1, 1) 是水，不檢定；第二步 (0, 1) 是冰
    s2 = with_rolls(give_turn(s, U3), [(20, 3)])
    result = resolve(s2, Move(unit_id=U3, path=(P(2, 1), P(1, 1), P(0, 1), P(0, 0))))
    checks = [e for e in result.events if isinstance(e, CheckRolled)]
    assert len(checks) == 1 and checks[0].total == 5 and not checks[0].success
    assert result.state.units[U3].has_status("prone")
    assert result.state.units[U3].pos == P(0, 1)  # 滑倒後停下
    # 擲 10 → 10 + 2 = 12 通過
    s3 = with_rolls(give_turn(s, U3), [(20, 10)])
    ok = resolve(s3, Move(unit_id=U3, path=(P(2, 1), P(1, 1), P(0, 1), P(0, 0))))
    assert not ok.state.units[U3].has_status("prone") and ok.state.units[U3].pos == P(0, 0)


def test_fire_melts_ice_and_water_extinguishes_fire() -> None:
    m = make_map(
        "000\n000", surfaces=[(0, 0, "ice"), (1, 0, "fire"), (2, 0, "water")], enemy=[(2, 1)]
    )
    state = make_state(m, [spawn(Team.ALLY, (0, 1)), spawn(Team.ENEMY, (2, 1))])
    s = run_effects(
        state,
        [
            ElementTouchEffect(pos=(0, 0), element=Element.FIRE),
            CreateSurfaceEffect(pos=(1, 0), surface=Surface.WATER),
            CreateSurfaceEffect(pos=(2, 0), surface=Surface.FIRE),
        ],
    ).state
    assert surfaces(s) == {(0, 0): Surface.WATER, (2, 0): Surface.WATER}


# ---------------------------------------------------------------------------
# 推擊、墜落
# ---------------------------------------------------------------------------


def test_push_boss_two_tiles_moves_only_one() -> None:
    m = make_map("00000")
    state = make_state(
        m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0), "bandit_boss")]
    )
    result = run_effects(
        state, [PushEffect(target_id=U2, direction=(1, 0), distance=2, source_id=U1)]
    )
    resisted = [e for e in result.events if isinstance(e, PushResisted)]
    assert resisted and (resisted[0].requested, resisted[0].distance) == (2, 1)
    assert result.state.units[U2].pos == P(2, 0)
    # 一般盜賊推 2 格就是 2 格
    m2 = make_map("00000")
    s2 = make_state(m2, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0))])
    r2 = run_effects(s2, [PushEffect(target_id=U2, direction=(1, 0), distance=2)])
    assert r2.state.units[U2].pos == P(3, 0)


def test_shove_action_pushes_into_chasm() -> None:
    m = make_map("000", "..x", enemy=[(1, 0)])
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0), "bandit")]
        ),
        U1,
    )
    shove = Shove(unit_id=U1, target_id=U2)
    assert shove in legal_actions(state)
    result = resolve(with_rolls(state, [(20, 15)]), shove)
    assert result.state.units[U2].downed
    assert any(isinstance(e, EnteredDeadlyTerrain) for e in result.events)
    assert result.state.units[U1].ap == state.units[U1].ap - 1


def test_shove_blocked_by_obstacle_and_height() -> None:
    m = make_map("0010", objects=[(3, 0, "crate")])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (1, 0))])
    r = run_effects(state, [PushEffect(target_id=U2, direction=(1, 0), distance=3)])
    assert r.state.units[U2].pos == P(1, 0)  # (2, 0) 比較高 → 推不上去


def test_fall_damage_from_push_is_capped() -> None:
    m = make_map("3300\n0000")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), "hero_fighter"),
            spawn(Team.ENEMY, (1, 0), template("bandit", max_hp=100)),
        ],
        fall_damage_permille_per_level=200,
    )
    result = run_effects(state, [PushEffect(target_id=U2, direction=(1, 0), distance=1)])
    fell = next(e for e in result.events if isinstance(e, UnitFell))
    assert (fell.drop, fell.levels) == (3, 2)
    damage = next(e for e in result.events if isinstance(e, DamageDealt))
    assert damage.cause == "fall" and damage.amount == 30  # 40% → 上限 30%


# ---------------------------------------------------------------------------
# 風、神聖、大地
# ---------------------------------------------------------------------------


def _open(surface_list: list[tuple[int, int, str]], **kw: object) -> BattleState:
    m = make_map("0000\n0000\n0000", surfaces=surface_list, enemy=[(3, 2)], **kw)  # type: ignore[arg-type]
    return make_state(m, [spawn(Team.ALLY, (0, 2)), spawn(Team.ENEMY, (3, 2))])


def test_wind_spreads_fire_along_direction_and_disperses_poison() -> None:
    state = _open([(1, 0, "fire"), (1, 1, "poison")])
    s = run_effects(
        state,
        [
            ElementTouchEffect(pos=(1, 0), element=Element.WIND, direction=(1, 0), push_distance=1),
            ElementTouchEffect(pos=(1, 1), element=Element.WIND, direction=(1, 0), push_distance=1),
        ],
    ).state
    assert surfaces(s) == {(1, 0): Surface.FIRE, (2, 0): Surface.FIRE}


def test_wind_pushes_pushable_object() -> None:
    state = _open([], objects=[(1, 0, "crate")])
    s = run_effects(
        state,
        [ElementTouchEffect(pos=(1, 0), element=Element.WIND, direction=(1, 0), push_distance=2)],
    ).state
    assert s.objects[O1].pos == P(3, 0) and s.tile(3, 0).object_id == O1


def test_holy_purifies_poison_and_dispels_darkness() -> None:
    state = _open([(0, 0, "poison"), (1, 0, "darkness")])
    s = run_effects(
        state,
        [
            ElementTouchEffect(pos=(0, 0), element=Element.HOLY),
            ElementTouchEffect(pos=(1, 0), element=Element.HOLY),
        ],
    ).state
    assert surfaces(s) == {}


def test_earth_raises_and_lowers_terrain() -> None:
    m = make_map("3000\n0000", enemy=[(3, 1)])
    state = make_state(m, [spawn(Team.ALLY, (1, 0)), spawn(Team.ENEMY, (3, 1))])
    s = run_effects(
        state,
        [
            RaiseTerrainEffect(pos=(0, 0)),  # 已是 3 → 不變
            RaiseTerrainEffect(pos=(1, 0)),  # 單位跟著升高
            LowerTerrainEffect(pos=(2, 0)),  # 已是 0 → 不變
        ],
    ).state
    assert [s.tile(x, 0).height for x in range(3)] == [3, 1, 0]
    s = run_effects(s, [LowerTerrainEffect(pos=(0, 0)), LowerTerrainEffect(pos=(1, 0))]).state
    assert [s.tile(x, 0).height for x in range(3)] == [2, 0, 0]


def test_earth_fills_chasm_under_bridge() -> None:
    m = make_map("000", ".x.", objects=[(1, 0, "wooden_bridge")], enemy=[(2, 0)])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 0))])
    s = run_effects(state, [ElementTouchEffect(pos=(1, 0), element=Element.EARTH)]).state
    assert s.objects[O1].destroyed and s.tile(1, 0).terrain == "dirt"


# ---------------------------------------------------------------------------
# 表面的回合開始效果
# ---------------------------------------------------------------------------


def _turn_start_on(
    surface: str, victim: str = "bandit", tags: list[str] | None = None
) -> list[object]:
    m = make_map("000", surfaces=[(1, 0, surface)], enemy=[(1, 0)])
    t = template(victim, max_hp=100, tags=tags or ["humanoid"])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (1, 0), t)])
    state = give_turn(state, U1)
    state.units[U2].hp = 50
    result = resolve(state, EndTurn(unit_id=U1))
    return list(result.events)


def test_poison_surface_damages_at_turn_start() -> None:
    events = _turn_start_on("poison")
    dmg = [e for e in events if isinstance(e, DamageDealt) and e.target_id == U2]
    assert len(dmg) == 1 and dmg[0].element is Element.POISON and dmg[0].cause == "surface"
    assert 1 <= dmg[0].rolls[0] <= 4


def test_holy_surface_heals_living_and_hurts_undead() -> None:
    from trpg.engine.events import Healed  # noqa: PLC0415

    events = _turn_start_on("holy")
    assert any(isinstance(e, Healed) and e.target_id == U2 for e in events)
    assert not any(isinstance(e, DamageDealt) and e.target_id == U2 for e in events)
    undead = _turn_start_on("holy", tags=["undead"])
    assert not any(isinstance(e, Healed) and e.target_id == U2 for e in undead)
    hurt = [e for e in undead if isinstance(e, DamageDealt) and e.target_id == U2]
    assert hurt and hurt[0].element is Element.HOLY


def test_fire_surface_burns_on_enter() -> None:
    m = make_map("000", surfaces=[(1, 0, "fire")])
    state = give_turn(make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 0))]), U1)
    result = resolve(state, Move(unit_id=U1, path=(P(0, 0), P(1, 0))))
    assert any(isinstance(e, StatusApplied) and e.status_id == "burning" for e in result.events)


# ---------------------------------------------------------------------------
# 視線、隱蔽
# ---------------------------------------------------------------------------


def test_pillar_and_darkness_block_sight() -> None:
    from trpg.engine.rules.geometry import has_line_of_sight  # noqa: PLC0415

    m = make_map("00000\n00000", objects=[(2, 0, "stone_pillar")], surfaces=[(2, 1, "darkness")])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (4, 1))])
    assert not has_line_of_sight(state, (0, 0), (4, 0))
    assert not has_line_of_sight(state, (0, 1), (4, 1))
    assert has_line_of_sight(state, (0, 1), (2, 1))  # 終點在黑暗裡不算阻擋


@pytest.mark.parametrize(
    ("hiding", "distance", "weather", "targetable"),
    [
        ("darkness", 2, None, True),
        ("darkness", 3, None, False),
        ("grass", 3, None, False),
        (None, 3, None, True),
        ("grass", 2, "night", False),  # 夜晚：超過 1 格就無法選為目標
    ],
)
def test_concealment_limits_ranged_targeting(
    hiding: str | None, distance: int, weather: str | None, targetable: bool
) -> None:
    objects = [(distance, 0, "grass")] if hiding == "grass" else []
    surfs = [(distance, 0, "darkness")] if hiding == "darkness" else []
    m = make_map("00000\n00000", objects=objects, surfaces=surfs, enemy=[(distance, 0)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "hero_archer"),
                spawn(Team.ENEMY, (distance, 0), no_reactions()),
            ],
            weather=weather,
        ),
        U1,
    )
    attack = Attack(unit_id=U1, target_id=U2)
    assert (attack in legal_actions(state)) is targetable
    if targetable and hiding is not None:
        rolled = resolve(state, attack).events
        assert any(getattr(e, "advantage", None) == "disadvantage" for e in rolled)


def test_fog_halves_sight_and_gives_ranged_disadvantage() -> None:
    from trpg.engine.rules.combat import advantage_state  # noqa: PLC0415
    from trpg.engine.rules.geometry import has_line_of_sight, sight_range  # noqa: PLC0415

    m = make_map("0" * 14, enemy=[(13, 0)])
    state = make_state(
        m, [spawn(Team.ALLY, (0, 0), "hero_archer"), spawn(Team.ENEMY, (5, 0))], weather="fog"
    )
    assert sight_range(state) == 12
    assert has_line_of_sight(state, (0, 0), (12, 0)) and not has_line_of_sight(
        state, (0, 0), (13, 0)
    )
    assert advantage_state(state, state.units[U1], state.units[U2]) == "disadvantage"  # 5 > 4
    state.units[U2].pos = P(4, 0)
    assert advantage_state(state, state.units[U1], state.units[U2]) == "none"


def test_rain_modifies_fire_and_lightning_damage() -> None:
    m = make_map("000")
    for weather, element, expected in (
        ("rain", Element.FIRE, 7),
        ("rain", Element.LIGHTNING, 12),
        ("rain", Element.PHYSICAL, 10),
        (None, Element.FIRE, 10),
    ):
        state = make_state(
            m,
            [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 0), template("bandit", max_hp=99))],
            weather=weather,
        )
        r = run_effects(state, [DamageEffect(target_id=U2, element=element, flat=10)])
        dmg = next(e for e in r.events if isinstance(e, DamageDealt))
        assert dmg.amount == expected, (weather, element)
