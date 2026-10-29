"""環境被動（Phase 3R-2，``docs/design/07-角色成長.md`` 7.7）：10 項被動 × 有／無該種族。

每一項都用同一個場景跑兩次——單位帶該種族與不帶種族（或別的種族）——比較結果；獸人另外測
「被推」的來源（技能推擊、風、基本動作推擊）與路徑上有無岩漿／深淵，以及拉不減距。
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from tests.engine.race_helpers import FLAT7, U1, U2, U3, end_turn, of, race_state
from trpg.content.races import PASSIVE_RULE_SPECS
from trpg.engine import BattleState, Move, Shove, resolve
from trpg.engine.effects import (
    ApplyStatusEffect,
    DamageEffect,
    ElementTouchEffect,
    PushEffect,
    run_effects,
)
from trpg.engine.events import (
    CheckRolled,
    Collided,
    DamageDealt,
    PushResisted,
    TurnStarted,
    UnitFell,
)
from trpg.engine.ids import CONCEALED
from trpg.engine.rules.combat import (
    advantage_state,
    attack_problem,
    concealed_max_distance,
    concealment_problem,
)
from trpg.engine.rules.geometry import has_line_of_sight, sight_range
from trpg.engine.rules.race import passive_active
from trpg.engine.rules.statuses import move_points_for_turn
from trpg.engine.state import TrapState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, Team

WIDE = "\n".join(["0" * 30] * 3)  # 30 × 3 的平地：測試視線距離用


def _wide(
    race: str | None, *, weather: str | None = None, tags: tuple[str, ...] = ()
) -> BattleState:
    return race_state(
        race, me=(0, 1), foes=((29, 1),), heights=WIDE, weather=weather, map_tags=tags
    )


def _sees(state: BattleState, distance: int) -> bool:
    me = state.units[U1]
    return has_line_of_sight(state, me.xy, (distance, 1), viewer=me)


# ---------------------------------------------------------------------------
# 人類：明視（濃霧、夜晚的視線懲罰減半）
# ---------------------------------------------------------------------------


def test_human_clear_eyes_halves_fog_penalty() -> None:
    base = 24  # rules/core.yaml base_sight_range
    fog_plain = _wide(None, weather="fog")
    fog_human = _wide("human", weather="fog")
    assert sight_range(fog_plain, fog_plain.units[U1]) == base // 2
    assert sight_range(fog_human, fog_human.units[U1]) == base // 2 + base // 4
    assert not _sees(fog_plain, 15) and _sees(fog_human, 15)
    assert _sees(fog_plain, 12) and not _sees(fog_human, 19)


def test_human_clear_eyes_does_nothing_in_clear_weather() -> None:
    clear = _wide("human")
    assert sight_range(clear, clear.units[U1]) == 24
    assert passive_active(clear, clear.units[U1]) is False
    assert passive_active(_wide("human", weather="fog"), _wide("human", weather="fog").units[U1])


def test_human_clear_eyes_softens_night_concealment() -> None:
    plain = race_state(None, foes=((5, 3),), weather="night")
    human = race_state("human", foes=((5, 3),), weather="night")
    assert concealed_max_distance(plain, plain.units[U1]) == 1
    assert concealed_max_distance(human, human.units[U1]) == 2  # 夜晚縮短的 1 格回復 500‰（進位）


# ---------------------------------------------------------------------------
# 精靈：林間視野（森林地圖視線 +1）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("tags", "bonus"), [(("forest",), 1), ((), 0)])
def test_elf_forest_sight_bonus_only_on_forest_maps(tags: tuple[str, ...], bonus: int) -> None:
    elf = _wide("elf", tags=tags)
    plain = _wide(None, tags=tags)
    assert sight_range(elf, elf.units[U1]) == 24 + bonus
    assert sight_range(plain, plain.units[U1]) == 24
    assert _sees(elf, 25) is bool(bonus)
    assert passive_active(elf, elf.units[U1]) is bool(bonus)


def test_forest_tag_is_on_dark_forest_only() -> None:

    tagged = sorted(m.id for m in library().maps.values() if "forest" in m.tags)
    assert tagged == ["dark_forest"]


# ---------------------------------------------------------------------------
# 狐族：靈覺（2 格內的敵方陷阱與隱蔽單位）
# ---------------------------------------------------------------------------


def _hidden_foe(race: str | None) -> BattleState:
    state = race_state(race, foes=((5, 3),), weather="night")  # 夜晚：隱蔽目標只能在 1 格內被選取

    return run_effects(
        state, [ApplyStatusEffect(target_id=U2, status_id=CONCEALED, source_id=U2, duration=3)]
    ).state


def test_fox_keen_senses_sees_hidden_units_within_two_tiles() -> None:
    near_plain = _hidden_foe(None)
    near_fox = _hidden_foe("fox")
    plain_problem = concealment_problem(near_plain, near_plain.units[U1], near_plain.units[U2])
    fox_problem = concealment_problem(near_fox, near_fox.units[U1], near_fox.units[U2])
    assert plain_problem is not None and "隱蔽" in plain_problem
    assert fox_problem is None
    assert advantage_state(near_plain, near_plain.units[U1], near_plain.units[U2]) == "disadvantage"
    assert advantage_state(near_fox, near_fox.units[U1], near_fox.units[U2]) != "disadvantage"


def test_fox_keen_senses_does_not_reach_three_tiles() -> None:
    state = _hidden_foe("fox")
    state.units[U2].pos = Pos(x=6, y=3)
    assert concealment_problem(state, state.units[U1], state.units[U2]) is not None


def _trap_state(race: str | None) -> BattleState:

    state = race_state(race, foes=((0, 6),))
    skill_id = next(iter(state.ruleset.skills.skills)).id
    trap = TrapState(
        owner_id=U2,
        team=Team.ENEMY,
        pos=Pos(x=5, y=3),
        skill_id=skill_id,
        remaining=5,
        attributes=(),
    )
    state.traps = [replace(trap)]
    return state


@pytest.mark.parametrize(("race", "seen"), [("fox", True), (None, False), ("human", False)])
def test_fox_reveals_enemy_traps_within_two_tiles_when_moving_near(
    race: str | None, seen: bool
) -> None:
    state = _trap_state(race)
    moved = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=4, y=3)))).state
    (trap,) = moved.traps
    assert (Team.ALLY in trap.revealed_to) is seen


def test_fox_does_not_reveal_traps_three_tiles_away() -> None:
    state = _trap_state("fox")
    moved = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=2, y=3)))).state
    assert Team.ALLY not in moved.traps[0].revealed_to


# ---------------------------------------------------------------------------
# 龍裔：耐火鱗（火焰傷害 −20%）
# ---------------------------------------------------------------------------


def _fire_damage(race: str | None, element: Element) -> int:
    state = race_state(race, foes=((6, 6),))
    effect = DamageEffect(
        target_id=U1,
        element=element,
        flat=100,
        source_id=U2,
        apply_weather=False,
    )
    events = run_effects(state, [effect]).events

    return next(e for e in events if isinstance(e, DamageDealt)).amount


def test_dragonkin_takes_twenty_percent_less_fire_damage_only() -> None:
    plain = _fire_damage(None, Element.FIRE)
    scaled = _fire_damage("dragonkin", Element.FIRE)
    assert scaled == plain * 80 // 100
    assert _fire_damage("dragonkin", Element.ICE) == _fire_damage(None, Element.ICE)
    assert _fire_damage("human", Element.FIRE) == plain


# ---------------------------------------------------------------------------
# 矮人：穩健步伐（冰面不滑倒）／鱗族：流線身形（回合開始站水或冰面移動 +1、冰面不滑倒）
# ---------------------------------------------------------------------------


def _ice_walk(race: str | None, surface: str, seed: int) -> list[CheckRolled]:
    state = race_state(race, foes=((6, 6),), surfaces=[(4, 3, surface)])
    state.rng_state = __import__("trpg.shared.rng", fromlist=["Rng"]).Rng(seed).get_state()
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=4, y=3))))
    return of(result, CheckRolled)


@pytest.mark.parametrize(
    ("race", "checked"), [("dwarf", False), ("scalefolk", False), (None, True)]
)
def test_ice_surface_slip_check_is_skipped_for_dwarf_and_scalefolk(
    race: str | None, checked: bool
) -> None:
    assert bool(_ice_walk(race, "ice", seed=3)) is checked


def test_slip_fall_only_happens_to_others() -> None:
    falls = {
        race: sum(any(not c.success for c in _ice_walk(race, "ice", seed)) for seed in range(30))
        for race in (None, "dwarf", "scalefolk")
    }
    assert falls[None] > 0
    assert falls["dwarf"] == 0 and falls["scalefolk"] == 0


def _start_of_u1_turn(race: str | None, surface: str | None) -> tuple[BattleState, int]:
    """U1 站在 (3,3)（表面 ``surface``）；回傳輪到 U1 時的狀態與 ``TurnStarted.move_points``。"""
    surfaces = [] if surface is None else [(3, 3, surface)]
    s = race_state(race, foes=((6, 6),), surfaces=surfaces)
    for _ in range(8):
        r = end_turn(s)
        s = r.state
        started = [e for e in r.events if isinstance(e, TurnStarted) and e.unit_id == U1]
        if started:
            return s, started[0].move_points
    raise AssertionError("沒有輪到 U1")


@pytest.mark.parametrize("surface", ["water", "ice", None, "oil"])
@pytest.mark.parametrize("race", ["scalefolk", None, "dwarf"])
def test_scalefolk_gets_one_more_move_point_when_the_turn_starts_on_water_or_ice(
    race: str | None, surface: str | None
) -> None:
    """表格：回合開始站水／冰／一般地面 × 鱗族／非鱗族（#68）。"""
    base = _start_of_u1_turn(None, None)[1]
    bonus = 1 if race == "scalefolk" and surface in ("water", "ice") else 0
    assert _start_of_u1_turn(race, surface)[1] == base + bonus


def test_scalefolk_move_bonus_is_kept_after_leaving_the_water() -> None:
    state, points = _start_of_u1_turn("scalefolk", "water")
    plain = _start_of_u1_turn("scalefolk", None)[1]
    assert points == plain + 1
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=3, y=4))))
    assert result.state.units[U1].move_points == points - 1  # 離開水面不收回


def test_scalefolk_bonus_is_not_given_again_next_turn_when_off_the_water() -> None:
    state, points = _start_of_u1_turn("scalefolk", "water")
    moved = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=3, y=4)))).state
    for _ in range(8):
        r = end_turn(moved)
        moved = r.state
        started = [e for e in r.events if isinstance(e, TurnStarted) and e.unit_id == U1]
        if started:
            assert started[0].move_points == points - 1  # 這回合開始站在一般地面：沒有加值
            return
    raise AssertionError("沒有輪到 U1")


def test_water_has_no_slip_check_for_anyone() -> None:
    assert not _ice_walk(None, "water", seed=3)


# ---------------------------------------------------------------------------
# 晶能義體人：絕緣（站在水上不被雷電導電）
# ---------------------------------------------------------------------------


def _conduct(race: str | None, standing_on: str) -> list[DamageDealt]:
    m = make_map(
        FLAT7,
        ally=[(0, 0)],
        enemy=[(6, 6)],
        surfaces=[(2, 3, "water"), (3, 3, "water"), (4, 3, "water")],
    )
    spawns = [
        spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter", max_hp=999, race=None)),
        spawn(Team.ENEMY, (2, 3), no_reactions("bandit", max_hp=999)),
        spawn(
            Team.ENEMY,
            (3, 3) if standing_on == "water" else (3, 5),
            no_reactions("bandit", max_hp=999, race=race),
        ),
    ]
    state = give_turn(make_state(m, spawns), U1)
    hit = DamageEffect(target_id=U2, element=Element.LIGHTNING, flat=10, source_id=U1)
    events = run_effects(state, [hit]).events

    return [e for e in events if isinstance(e, DamageDealt) and e.cause == "conduct"]


def test_cyborg_insulated_is_not_conducted_while_standing_on_water() -> None:
    assert [e.target_id for e in _conduct(None, "water")] == [U3]
    assert _conduct("cyborg", "water") == []
    assert [e.target_id for e in _conduct("human", "water")] == [U3]


def test_cyborg_insulation_needs_water_underfoot() -> None:
    """不站在水裡的義體人本來就不會被導電：行為與沒有種族相同（不吃額外好處也不吃額外壞處）。"""
    assert _conduct("cyborg", "dry") == _conduct(None, "dry") == []


# ---------------------------------------------------------------------------
# 獸人：沉穩重心（被推時，路徑上有岩漿或深淵少推 1 格）
# ---------------------------------------------------------------------------

_LAVA_AT_6 = "\n".join(["......~"] * 7)  # (6, y) 是岩漿
_CHASM_AT_6 = "\n".join(["......x"] * 7)
_PLAIN_ROWS = "\n".join(["......."] * 7)


def _push_result(
    race: str | None, terrain: str, *, distance: int = 3, pull: bool = False
) -> tuple[tuple[int, int], list[PushResisted]]:
    state = race_state(race, me=(3, 3), foes=((5, 6),), terrain=terrain)
    direction = (-1, 0) if pull else (1, 0)
    effect = PushEffect(
        target_id=U1, direction=direction, distance=distance, source_id=U2, pull=pull
    )
    result = run_effects(state, [effect])
    return result.state.units[U1].xy, of(result, PushResisted)


@pytest.mark.parametrize("terrain", [_LAVA_AT_6, _CHASM_AT_6])
def test_orc_is_pushed_one_less_when_the_path_ends_in_lava_or_chasm(terrain: str) -> None:
    plain_xy, plain_events = _push_result(None, terrain)
    assert not plain_events
    orc_xy, events = _push_result("orc", terrain)
    assert orc_xy == (5, 3)  # 推 3 格 −1 ＝ 2 格，停在危險地形前
    assert [(e.requested, e.distance, e.reason) for e in events] == [(3, 2, "race_heavy")]
    state = race_state(None, me=(3, 3), foes=((5, 6),), terrain=terrain)
    fell = run_effects(
        state, [PushEffect(target_id=U1, direction=(1, 0), distance=3, source_id=U2)]
    )
    assert not fell.state.units[U1].alive, "沒有種族時推 3 格會掉進去"
    assert plain_xy != orc_xy


def test_orc_reduction_counts_hazards_anywhere_on_the_path() -> None:
    middle = "\n".join(["....~.."] * 7)  # (4, y) 是岩漿：推 3 格的路徑第一格
    _, events = _push_result("orc", middle)
    assert [(e.requested, e.distance) for e in events] == [(3, 2)]


def test_orc_is_not_reduced_without_hazard_on_the_path() -> None:
    xy, events = _push_result("orc", _PLAIN_ROWS)
    assert xy == (6, 3) and not events
    behind = "\n".join(["~......"] * 7)  # 岩漿在推的反方向
    xy, events = _push_result("orc", behind)
    assert xy == (6, 3) and not events


def test_orc_reduction_is_at_least_zero() -> None:
    lava_next = "\n".join(["....~.."] * 7)
    xy, events = _push_result("orc", lava_next, distance=1)
    assert xy == (3, 3)  # 1 − 1 ＝ 0 格：不移動
    assert [(e.requested, e.distance) for e in events] == [(1, 0)]


def test_orc_is_not_helped_when_pulled() -> None:
    toward_lava = "\n".join(["~......"] * 7)  # 往左拉 3 格正好是岩漿
    assert _push_result("orc", toward_lava, pull=True) == _push_result(None, toward_lava, pull=True)
    assert not _push_result("orc", toward_lava, pull=True)[1]


def _orc_next_to_lava() -> BattleState:
    terrain = "\n".join(["....~.."] * 7)
    m = make_map(FLAT7, terrain, ally=[(2, 3)], enemy=[(3, 3)])
    spawns = [
        spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", max_hp=999)),
        spawn(Team.ENEMY, (3, 3), no_reactions("bandit", max_hp=999, race="orc")),
    ]
    return give_turn(make_state(m, spawns), U1)


def test_orc_shove_action_is_illegal_when_reduction_leaves_zero() -> None:

    with pytest.raises(IllegalActionError, match="推不動"):
        resolve(_orc_next_to_lava(), Shove(unit_id=U1, target_id=U2))


def test_orc_reduction_applies_to_wind_pushes() -> None:
    terrain = "\n".join([".....~."] * 7)  # 風推 2 格：路徑 (4,3)、(5,3) 岩漿
    m = make_map(FLAT7, terrain, ally=[(2, 3)], enemy=[(3, 3)])
    for race, expected in ((None, False), ("orc", True)):
        spawns = [
            spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", max_hp=999)),
            spawn(Team.ENEMY, (3, 3), no_reactions("bandit", max_hp=999, race=race)),
        ]
        state = give_turn(make_state(m, spawns), U1)
        wind = ElementTouchEffect(
            pos=(3, 3), element=Element.WIND, direction=(1, 0), push_distance=2, source_id=U1
        )
        result = run_effects(state, [wind])
        assert bool(of(result, PushResisted)) is expected, race
        assert result.state.units[U2].alive is expected  # 沒有種族掉進岩漿；獸人停在 (4,3)
        if expected:
            assert result.state.units[U2].xy == (4, 3)


def test_orc_push_resisted_event_explains_the_reduction() -> None:
    state = race_state("orc", me=(3, 3), foes=((5, 6),), terrain=_LAVA_AT_6)
    result = run_effects(
        state, [PushEffect(target_id=U1, direction=(1, 0), distance=3, source_id=U2)]
    )
    (resisted,) = of(result, PushResisted)
    assert (resisted.requested, resisted.distance, resisted.reason) == (3, 2, "race_heavy")
    assert not of(result, UnitFell) and not of(result, Collided)


# ---------------------------------------------------------------------------
# 角魔：炎膚（走在火焰表面上不會燃燒）
# ---------------------------------------------------------------------------


def _burning_after_walking_into_fire(race: str | None) -> bool:
    state = race_state(race, foes=((6, 6),), surfaces=[(4, 3, "fire")])
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=4, y=3))))
    return result.state.units[U1].has_status("burning")


def test_fiend_ember_skin_does_not_burn_on_fire_surface() -> None:
    assert _burning_after_walking_into_fire(None) is True
    assert _burning_after_walking_into_fire("human") is True
    assert _burning_after_walking_into_fire("fiend") is False


def test_fiend_ember_skin_also_protects_at_turn_start_but_not_from_fire_damage() -> None:
    for race, burns in ((None, True), ("fiend", False)):
        state = race_state(race, foes=((6, 6),), surfaces=[(3, 3, "fire")])
        s = state
        for _ in range(6):  # 走到下一輪輪到 U1：回合開始時站在火上
            s = end_turn(s).state
            if s.active_unit == U1 and s.round > 1:
                break
        assert s.units[U1].has_status("burning") is burns, race
    # 炎膚只擋「走在火焰表面上」造成的燃燒；被火焰傷害打到照樣受傷
    hit = _fire_damage("fiend", Element.FIRE)
    assert hit == _fire_damage(None, Element.FIRE)


# ---------------------------------------------------------------------------
# 海民：雨中海步（下雨時移動 +1）
# ---------------------------------------------------------------------------


def test_seafolk_gets_one_more_move_point_in_rain_only() -> None:
    rules = race_state("seafolk").ruleset
    for weather, bonus in (("rain", 1), ("clear", 0), (None, 0), ("fog", 0)):
        sea = race_state("seafolk", weather=None if weather in (None, "clear") else weather)
        plain = race_state(None, weather=None if weather in (None, "clear") else weather)
        assert move_points_for_turn(rules, sea.units[U1], weather) == (
            move_points_for_turn(rules, plain.units[U1], weather) + bonus
        )


def _turn_start_move_points(race: str | None, weather: str | None) -> int:
    s = race_state(race, weather=weather)
    for _ in range(8):
        r = end_turn(s)
        s = r.state
        started = [e for e in r.events if isinstance(e, TurnStarted) and e.unit_id == U1]
        if started:
            return started[0].move_points
    raise AssertionError("沒有輪到 U1")


def test_rain_bonus_shows_up_in_the_real_turn_start() -> None:
    assert _turn_start_move_points("seafolk", "rain") == _turn_start_move_points(None, "rain") + 1
    assert _turn_start_move_points("seafolk", None) == _turn_start_move_points(None, None)


# ---------------------------------------------------------------------------
# 共通：沒有種族的單位完全不受影響；被動不給數值
# ---------------------------------------------------------------------------


def test_units_without_race_are_unaffected_everywhere() -> None:
    state = race_state(None, weather="fog")
    me = state.units[U1]
    assert me.race is None
    assert sight_range(state, me) == sight_range(state)
    assert attack_problem(state, me, state.units[U2]) == attack_problem(
        race_state(None, weather="fog"), me, state.units[U2]
    )


def test_every_passive_rule_has_a_behaviour_test() -> None:
    """封閉清單裡的每一條被動規則都有結算點：新增規則時要同時新增結算與測試。"""

    covered = {
        "sight_penalty_reduction",
        "sight_bonus_on_map_tag",
        "detect_hidden_nearby",
        "damage_taken_permille",
        "slip_immunity",
        "conduction_immunity",
        "knockback_reduction_at_hazard",
        "burn_immunity_on",
        "surface_move_bonus",
        "weather_move_bonus",
    }
    assert set(PASSIVE_RULE_SPECS) == covered
