"""Phase 1B 驗收後的 PM 決定（docs/phases/Phase1C計畫.md 2.5）：#2、#3、#5、#6、#10。

#1（AI 效能）見 ``test_ai_utility.py`` 與 ``scripts/bench_battle.py``；#4、#7 見
``tests/cli/test_demo_maps.py`` 與 ``tests/sim``；#8、#9 為接受現狀（不需修改）。
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
    with_conduct_permille,
    with_rolls,
)
from trpg.engine import Attack, BattleState, EndTurn, Interact, Shove, legal_actions, resolve
from trpg.engine.effects import (
    CreateSurfaceEffect,
    DamageEffect,
    DamageObjectEffect,
    ElementTouchEffect,
    PushEffect,
    run_effects,
)
from trpg.engine.environment import telegraph
from trpg.engine.events import (
    CheckRolled,
    Collided,
    DamageDealt,
    EnvironmentStarted,
    EventBase,
    ObjectDestroyed,
    ObjectExploded,
    PushResisted,
    StatusApplied,
    SurfaceChanged,
    SurfaceEntered,
    UnitMoved,
)
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, ObjectId, Pos, Surface, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
O1, O2 = ObjectId("obj_0001"), ObjectId("obj_0002")


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _surfaces(state: BattleState) -> dict[tuple[int, int], Surface]:
    return {
        (x, y): state.tile(x, y).surface
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is not Surface.NONE
    }


# ---------------------------------------------------------------------------
# #2 steadfast：推擊距離減半後為 0 → Shove 不合法；技能的推擊只是不移動
# ---------------------------------------------------------------------------


def _shove_scene(enemy: str = "bandit_boss", shove_distance: int = 1) -> BattleState:
    m = make_map("00000")
    state = make_state(
        m,
        [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0), enemy)],
        shove_distance=shove_distance,
    )
    return give_turn(state, U1)


def test_shove_on_steadfast_boss_is_illegal() -> None:
    state = _shove_scene()
    shove = Shove(unit_id=U1, target_id=U2)
    assert shove not in legal_actions(state)
    with pytest.raises(IllegalActionError, match="推不動：盜賊頭目 不為所動"):
        resolve(state, shove)
    # 絆倒、攻擊不受影響
    assert any(a.type == "trip" for a in legal_actions(state))
    # 一般盜賊可以推
    assert shove in legal_actions(_shove_scene("bandit"))
    # 推擊距離改為 2 時，減半後 1 格 → 合法
    assert shove in legal_actions(_shove_scene(shove_distance=2))


def test_skill_push_of_zero_tiles_just_does_not_move() -> None:
    state = _shove_scene()
    result = run_effects(state, [PushEffect(target_id=U2, direction=(1, 0), distance=1)])
    resisted = [e for e in result.events if isinstance(e, PushResisted)]
    assert [(e.requested, e.distance) for e in resisted] == [(1, 0)]
    assert result.state.units[U2].pos == P(1, 0)
    assert not any(isinstance(e, UnitMoved) for e in result.events)


# ---------------------------------------------------------------------------
# #10 推不動時 Shove／Interact 不合法；Interact 高度差 ≤ 1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("heights", "terrain", "objects", "extra_enemy", "obstacle"),
    [
        ("000", None, [(2, 0, "crate")], None, "object"),
        ("000", "..#", [], None, "wall"),
        ("001", None, [], None, "wall"),
        ("000", None, [], (2, 0), "unit"),
        ("00", None, [], None, "edge"),
    ],
)
def test_blocked_shove_is_legal_and_collides(
    heights: str,
    terrain: str | None,
    objects: list[tuple[int, int, str]],
    extra_enemy: tuple[int, int] | None,
    obstacle: str,
) -> None:
    """Phase 3C-3b 5.4（取代 Phase 1C #10 的「推不動不合法」）：目標身後第一格被擋時推擊仍合法，
    對抗成功則目標不移動、撞擊 1 次。"""
    m = make_map(heights, terrain, objects=objects, enemy=[(1, 0)])
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0))]
    if extra_enemy is not None:
        spawns.append(spawn(Team.ENEMY, extra_enemy))
    state = give_turn(make_state(m, spawns), U1)
    shove = Shove(unit_id=U1, target_id=U2)
    assert shove in legal_actions(state)
    result = resolve(with_rolls(state, [(20, 20)]), shove)
    (hit,) = [e for e in result.events if isinstance(e, Collided)]
    assert (hit.obstacle, hit.shortfall) == (obstacle, 1)
    assert result.state.units[U2].pos == P(1, 0)


def test_shove_into_chasm_is_still_legal() -> None:
    m = make_map("000", "..x", enemy=[(1, 0)])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (1, 0))]), U1
    )
    assert Shove(unit_id=U1, target_id=U2) in legal_actions(state)


@pytest.mark.parametrize(
    ("heights", "terrain", "objects", "fragment"),
    [
        ("0000", None, [(1, 0, "crate"), (2, 0, "crate")], "另一側被擋住"),
        ("0000", "..#.", [(1, 0, "crate")], "另一側被擋住"),
        ("0010", None, [(1, 0, "crate")], "另一側比較高"),
        ("00", None, [(1, 0, "crate")], "會被推出地圖"),
        ("0220", None, [(1, 0, "crate")], "高度差過大：相差 2 層"),
    ],
)
def test_blocked_interact_is_illegal(
    heights: str, terrain: str | None, objects: list[tuple[int, int, str]], fragment: str
) -> None:
    w = len(heights)
    m = make_map(
        heights + "\n" + "0" * w,
        None if terrain is None else terrain + "\n" + "." * w,
        objects=objects,
        enemy=[(w - 1, 1)],
    )
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (w - 1, 1))]),
        U1,
    )
    interact = Interact(unit_id=U1, object_id=O1)
    assert interact not in legal_actions(state)
    with pytest.raises(IllegalActionError, match=fragment):
        resolve(state, interact)


def test_interact_height_difference_of_one_is_allowed() -> None:
    m = make_map("0110\n0000", objects=[(1, 0, "crate")], enemy=[(3, 1)])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (3, 1))]), U1
    )
    interact = Interact(unit_id=U1, object_id=O1)
    assert interact in legal_actions(state)
    assert resolve(state, interact).state.objects[O1].pos == P(2, 0)


# ---------------------------------------------------------------------------
# #3 雷電擴散：基準為主要目標套用自身抗性與格擋之前的傷害；範圍含友方與攻擊者
# ---------------------------------------------------------------------------


def _conduct_scene(weather: str | None = None) -> BattleState:
    """一整排水 (0..4, 0)：主要目標（元素抗性 50%）在 (0, 0)、一般盜賊 (1, 0)、
    雷電弱點的盜賊 (2, 0)、我方戰士 (3, 0)、站在水中的施法者 (4, 0)。"""
    m = make_map(
        "00000\n00000",
        surfaces=[(x, 0, "water") for x in range(5)],
        ally=[(4, 0)],
        enemy=[(0, 0)],
    )
    return give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (4, 0), template("hero_mage", max_hp=200), "lightning_staff"),
                spawn(Team.ENEMY, (0, 0), no_reactions(max_hp=200, resist={"elemental": 500})),
                spawn(Team.ENEMY, (1, 0), no_reactions(max_hp=200)),
                spawn(
                    Team.ENEMY, (2, 0), no_reactions(max_hp=200, element_mods={"lightning": 500})
                ),
                spawn(Team.ALLY, (3, 0), template("hero_fighter", max_hp=200)),
            ],
            weather=weather,
        ),
        U1,
    )


def _damage_by_target(events: list[EventBase]) -> dict[str, int]:
    return {e.target_id: e.amount for e in events if isinstance(e, DamageDealt)}


def test_conduct_base_is_damage_before_primary_resistance() -> None:
    state = with_conduct_permille(_conduct_scene())  # 1000‰：擴散 ＝ 基準（內容 500‰）
    result = run_effects(
        state,
        [
            DamageEffect(
                target_id=U2, source_id=U1, cause="attack", element=Element.LIGHTNING, flat=10
            )
        ],
    )
    dealt = _damage_by_target(result.events)
    primary = next(e for e in result.events if isinstance(e, DamageDealt) and e.cause == "attack")
    assert (primary.amount, primary.base_amount) == (5, 10)  # 元素抗性 50%
    # 擴散：基準 10，各自套用元素修正；友方戰士與施法者自己也受到傷害
    assert dealt[U3] == 10
    assert dealt[U4] == 15  # 雷電弱點 +50%
    fighter = UnitId("unit_0005")
    assert dealt[fighter] == 10
    assert dealt[U1] == 8  # 施法者自己：元素抗性 15% → 8.5 無條件捨去
    conducted = [e for e in result.events if isinstance(e, DamageDealt) and e.cause == "conduct"]
    assert {e.target_id for e in conducted} == {U1, U3, U4, fighter}
    assert all(e.weather_permille == 1000 for e in conducted)


def test_conduct_base_ignores_block_multiplier_and_includes_weather() -> None:
    state = with_conduct_permille(_conduct_scene())  # 擴散倍率 1000‰（BAL-13c 起內容 500‰）
    blocked = run_effects(
        state,
        [
            DamageEffect(
                target_id=U3,
                source_id=U1,
                cause="attack",
                element=Element.LIGHTNING,
                flat=10,
                multiplier_permille=500,  # 格擋：傷害減半
            )
        ],
    )
    dealt = _damage_by_target(blocked.events)
    assert dealt[U3] == 5
    assert dealt[U2] == 5  # 基準 10 × 元素抗性 50%
    assert dealt[U4] == 15
    wet = run_effects(
        with_conduct_permille(_conduct_scene("rain")),
        [
            DamageEffect(
                target_id=U3, source_id=U1, cause="attack", element=Element.LIGHTNING, flat=10
            )
        ],
    )
    dealt = _damage_by_target(wet.events)
    assert dealt[U3] == 12
    assert dealt[UnitId("unit_0005")] == 12  # 下雨 +20% 只算一次
    assert dealt[U2] == 6


# ---------------------------------------------------------------------------
# #5 油桶：火焰觸及即爆炸；非火焰傷害打破時漏油（該格與四方向相鄰格）
# ---------------------------------------------------------------------------


def _barrel_scene() -> BattleState:
    m = make_map(
        "00000\n00000\n00000",
        objects=[(2, 1, "oil_barrel")],
        surfaces=[(3, 1, "fire")],
        ally=[(0, 0)],
        enemy=[(4, 2)],
    )
    return give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "hero_archer"),
                spawn(Team.ALLY, (1, 0), "hero_mage"),
                spawn(Team.ENEMY, (4, 2), no_reactions(max_hp=200)),
            ],
        ),
        U1,
    )


def test_non_fire_damage_breaking_barrel_spills_oil() -> None:
    state = _barrel_scene()
    state.objects[O1].hp = 1
    result = resolve(state, Attack(unit_id=U1, target_object_id=O1))
    assert not any(isinstance(e, ObjectExploded) for e in result.events)
    destroyed = [e for e in result.events if isinstance(e, ObjectDestroyed)]
    assert [(e.object_id, e.cause) for e in destroyed] == [(O1, "damage")]
    after = _surfaces(result.state)
    for xy in [(2, 1), (2, 0), (1, 1), (2, 2)]:
        assert after[xy] is Surface.OIL, xy
    assert after[(3, 1)] is Surface.FIRE  # 漏到火上：繼續燃燒（oil_on_fire_burns）
    # 漏出的油之後可被點燃
    lit = run_effects(result.state, [ElementTouchEffect(pos=(2, 1), element=Element.FIRE)])
    assert lit.state.tile(2, 1).surface is Surface.FIRE


def test_fire_touching_barrel_still_explodes() -> None:
    state = give_turn(_barrel_scene(), U2)
    result = resolve(with_rolls(state, [(6, 1)]), Attack(unit_id=U2, target_object_id=O1))
    assert any(isinstance(e, ObjectExploded) for e in result.events)
    destroyed = [e for e in result.events if isinstance(e, ObjectDestroyed)]
    assert [(e.object_id, e.cause) for e in destroyed] == [(O1, "explosion")]
    assert result.state.tile(2, 0).surface is Surface.NONE  # 爆炸不漏油


def test_barrel_falling_into_chasm_does_not_spill() -> None:
    m = make_map("000\n000", "..x\n...", objects=[(1, 0, "oil_barrel")], enemy=[(2, 1)])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 1))])
    result = run_effects(state, [PushEffect(object_id=O1, direction=(1, 0), distance=1)])
    assert result.state.objects[O1].destroyed
    assert _surfaces(result.state) == {}


# ---------------------------------------------------------------------------
# #6 表面出現在單位腳下時立即生效（依單位 ID）
# ---------------------------------------------------------------------------


def test_explosion_ignites_oil_under_unit_and_burns_immediately() -> None:
    m = make_map(
        "00000\n00000\n00000",
        objects=[(2, 1, "oil_barrel")],
        surfaces=[(3, 1, "oil")],
        ally=[(0, 0)],
        enemy=[(3, 1)],
    )
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (0, 0), "hero_mage"),
                spawn(Team.ENEMY, (3, 1), no_reactions(max_hp=200)),
            ],
        ),
        U1,
    )
    result = resolve(state, Attack(unit_id=U1, target_object_id=O1))
    assert result.state.tile(3, 1).surface is Surface.FIRE
    entered = [e for e in result.events if isinstance(e, SurfaceEntered)]
    assert [(e.unit_id, e.surface) for e in entered] == [(U2, Surface.FIRE)]
    assert result.state.units[U2].has_status("burning")
    # 進入效果在表面改變之後
    seqs = {type(e).__name__: e.seq for e in result.events if isinstance(e, SurfaceChanged)}
    assert entered[0].seq > min(seqs.values())


def test_freezing_water_under_unit_triggers_slip_check() -> None:
    m = make_map("000\n000", surfaces=[(1, 0, "water")], ally=[(0, 1)], enemy=[(1, 0)])
    state = make_state(
        m, [spawn(Team.ALLY, (0, 1), "hero_mage"), spawn(Team.ENEMY, (1, 0), no_reactions())]
    )
    fail = run_effects(
        with_rolls(state, [(20, 2)]),
        [DamageEffect(target_id=U2, source_id=U1, element=Element.ICE, flat=1)],
    )
    checks = [e for e in fail.events if isinstance(e, CheckRolled)]
    assert len(checks) == 1 and checks[0].unit_id == U2 and not checks[0].success
    assert fail.state.tile(1, 0).surface is Surface.ICE
    assert fail.state.units[U2].has_status("prone")
    ok = run_effects(
        with_rolls(state, [(20, 15)]),
        [DamageEffect(target_id=U2, source_id=U1, element=Element.ICE, flat=1)],
    )
    assert not ok.state.units[U2].has_status("prone")


def test_surface_entries_resolve_in_unit_id_order() -> None:
    # 格子順序 (0, 0) → (2, 0)，但 (0, 0) 上的是 unit_0003、(2, 0) 上的是 unit_0002
    m = make_map("000\n000", ally=[(1, 1)], enemy=[(2, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 1), "hero_mage"),
            spawn(Team.ENEMY, (2, 0), no_reactions()),
            spawn(Team.ENEMY, (0, 0), no_reactions()),
        ],
    )
    result = run_effects(
        state,
        [
            CreateSurfaceEffect(pos=(0, 0), surface=Surface.ICE),
            CreateSurfaceEffect(pos=(2, 0), surface=Surface.ICE),
        ],
    )
    changed = [e.pos for e in result.events if isinstance(e, SurfaceChanged)]
    assert changed == [P(0, 0), P(2, 0)]
    checks = [e.unit_id for e in result.events if isinstance(e, CheckRolled)]
    assert checks == [U2, U3]


def test_fire_spreading_onto_unit_at_environment_turn_burns_and_is_telegraphed() -> None:
    m = make_map(
        "0000\n0000", surfaces=[(1, 0, "fire"), (2, 0, "oil")], ally=[(0, 1)], enemy=[(2, 0)]
    )
    state = make_state(
        m,
        [spawn(Team.ALLY, (0, 1), "hero_fighter"), spawn(Team.ENEMY, (2, 0), no_reactions())],
    )
    forecast = telegraph(state)
    # 結束全員回合，進入環境回合
    s = state
    events: list[EventBase] = []
    while not any(isinstance(e, EnvironmentStarted) for e in events):
        assert s.active_unit is not None
        r = resolve(s, EndTurn(unit_id=s.active_unit))
        events.extend(r.events)
        s = r.state
    env = [e for e in events if e.round == 1]
    start = next(i for i, e in enumerate(env) if isinstance(e, EnvironmentStarted))
    env_events = env[start:]
    burned = [e for e in env_events if isinstance(e, StatusApplied) and e.target_id == U2]
    assert burned and burned[0].status_id == "burning"
    assert [e.model_dump(exclude={"seq"}) for e in forecast.events] == [
        e.model_dump(exclude={"seq"}) for e in env_events[: len(forecast.events)]
    ]


def test_spill_and_surfaces_never_land_on_walls() -> None:
    from trpg.engine.events import EffectFizzled  # noqa: PLC0415

    m = make_map("000\n000", "..#\n...", objects=[(1, 0, "oil_barrel")], enemy=[(2, 1)])
    state = make_state(m, [spawn(Team.ALLY, (0, 1)), spawn(Team.ENEMY, (2, 1))])
    broken = run_effects(state, [DamageObjectEffect(object_id=O1, flat=99)])
    assert broken.state.tile(2, 0).surface is Surface.NONE  # 牆壁上沒有油
    assert broken.state.tile(1, 0).surface is Surface.OIL
    fizzled = [e for e in broken.events if isinstance(e, EffectFizzled)]
    assert [(e.pos, e.reason) for e in fizzled] == [(P(2, 0), "solid_terrain")]
