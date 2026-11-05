"""獸耳族（#138，6R-1；``docs/design/07-角色成長.md`` 7.7 實作細節第 6 點）：種族技「獸躍」與環境
被動「輕身」的結算，以及 AI 對兩者的估值。

- 獸躍：每場 1 次，跳到 3 格內任一空格（平移、往上最多 2 層、往下不限），不觸發藉機攻擊；落點要
  有一條不經過牆的最短路徑（可以越過單位、矮牆、物件，不能越過牆與石柱）。
- 輕身：墜落不受傷（被推下或自己往下都算）；致命地形照舊致命。
"""

from __future__ import annotations

import re

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.race_helpers import FLAT7, U1, U2, act, of, race_state, use
from trpg.engine import Move, legal_actions, resolve
from trpg.engine.actions import UseRaceSkill
from trpg.engine.ai.race import race_ai_action
from trpg.engine.ai.utility import is_risky_move
from trpg.engine.basics import vault_problem
from trpg.engine.effects import ApplyStatusEffect, PushEffect, run_effects
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EnteredDeadlyTerrain,
    RaceSkillUsed,
    UnitFell,
    UnitMoved,
)
from trpg.engine.race.skills import leap_path_clear
from trpg.engine.rules.race import fall_immune
from trpg.engine.state import BattleState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team

# 一排一排的高度（x 由左到右、y 由上到下）；U1 預設站在 (3, 3)
STEPS = "\n".join(["0000000", "0000000", "0000000", "0000123", "0000000", "0000000", "0000000"])
"""(4, 3)～(6, 3) 依序高 1、2、3。"""
CLIFF = "\n".join(["3330000"] * 7)
"""x = 0～2 高 3 層，其餘 0。"""


def _skill() -> UseRaceSkill:
    return use(pos=(4, 3))


def _numbers(text: str) -> set[int]:
    return {int(n) for n in re.findall(r"\d+", text)}


def _leaps(state: BattleState) -> list[tuple[int, int]]:
    return sorted(
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseRaceSkill) and a.target_pos is not None
    )


# ---------------------------------------------------------------------------
# 資料與卡片
# ---------------------------------------------------------------------------


def test_beast_leap_data_matches_the_card() -> None:
    state = race_state("fox")
    race = state.ruleset.race_def("fox")
    (effect,) = race.skill.effects
    assert (race.name_zh, race.skill.name_zh, race.passive.name_zh) == ("獸耳族", "獸躍", "輕身")
    assert (effect.type, effect.range, effect.max_rise, race.skill.uses_per_battle) == (
        "leap",
        3,
        2,
        1,
    )
    assert {3, 2, 1} <= _numbers(race.skill.description_zh)
    assert race.passive.rule == "fall_immunity"
    assert race.look.beast_ears == "fox"


# ---------------------------------------------------------------------------
# 獸躍：落點
# ---------------------------------------------------------------------------


def test_leap_moves_flat_up_to_three_tiles_without_spending_move_points() -> None:
    state = race_state("fox", foes=((0, 6),))
    before = state.units[U1].move_points
    result = act(state, pos=(5, 4))
    me = result.state.units[U1]
    assert me.xy == (5, 4) and me.move_points == before
    assert me.ap == state.units[U1].ap - 1
    (moved,) = of(result, UnitMoved)
    assert moved.mode == "leap"
    (used,) = of(result, RaceSkillUsed)
    assert used.skill_id == "race_beast_leap" and used.uses_left == 0


def test_leap_reach_is_three_manhattan_tiles() -> None:
    state = race_state("fox", foes=((0, 6),))
    cells = _leaps(state)
    assert all(0 < abs(x - 3) + abs(y - 3) <= 3 for x, y in cells)
    assert (6, 3) in cells and (5, 4) in cells and (5, 5) not in cells
    with pytest.raises(IllegalActionError, match="射程"):
        resolve(state, use(pos=(5, 5)))


def test_leap_rises_at_most_two_levels() -> None:
    state = race_state("fox", foes=((0, 6),), heights=STEPS)
    assert act(state, pos=(5, 3)).state.units[U1].xy == (5, 3)  # 高 2
    with pytest.raises(IllegalActionError, match="太高"):
        resolve(state, use(pos=(6, 3)))  # 高 3


def test_leap_down_is_unlimited_and_light_body_takes_no_fall_damage() -> None:
    state = race_state("fox", me=(2, 3), foes=((6, 6),), heights=CLIFF)
    result = act(state, pos=(5, 3))  # 從 3 層跳到 0 層
    me = result.state.units[U1]
    assert me.xy == (5, 3) and me.hp == me.max_hp
    assert not of(result, UnitFell) and not of(result, DamageDealt)


def test_leap_cannot_land_on_a_unit_a_blocker_or_deadly_terrain() -> None:
    terrain = "\n".join(["......."] * 3 + ["....x.."] + ["......."] * 3)
    state = race_state(
        "fox", foes=((4, 2),), terrain=terrain, objects=[(5, 3, "crate")], heights=FLAT7
    )
    for pos, reason in (((4, 2), "已經有單位"), ((5, 3), "不能站立"), ((4, 3), "不能站立")):
        with pytest.raises(IllegalActionError, match=reason):
            resolve(state, use(pos=pos))


# ---------------------------------------------------------------------------
# 獸躍：不能越過牆
# ---------------------------------------------------------------------------


def _walled(column: str) -> str:
    """第 4 欄（x = 4）照 ``column``（由上到下），其餘是石地。"""
    return "\n".join(f"....{c}.." for c in column)


def test_leap_cannot_cross_a_wall_but_can_go_around_it() -> None:
    state = race_state("fox", foes=((0, 6),), terrain=_walled("...#..."))
    with pytest.raises(IllegalActionError, match="牆"):
        resolve(state, use(pos=(5, 3)))  # 唯一的最短路徑經過牆
    assert act(state, pos=(5, 4)).state.units[U1].xy == (5, 4)  # 繞過 (3, 4)／(4, 4)


def test_a_full_wall_blocks_every_shortest_path() -> None:
    state = race_state("fox", foes=((0, 6),), terrain=_walled("#######"))
    assert not any(x > 4 for x, _ in _leaps(state))


@pytest.mark.parametrize("blocker", ["stone_pillar", "earth_wall", "dead_tree", "ice_wall"])
def test_pillars_and_tall_obstacles_block_the_leap(blocker: str) -> None:
    state = race_state("fox", foes=((0, 6),), objects=[(4, 3, blocker)])
    with pytest.raises(IllegalActionError, match="牆"):
        resolve(state, use(pos=(5, 3)))


@pytest.mark.parametrize("obstacle", ["low_wall", "crate", "fallen_log", "oil_barrel"])
def test_low_walls_and_objects_can_be_leapt_over(obstacle: str) -> None:
    state = race_state("fox", foes=((0, 6),), objects=[(4, 3, obstacle)])
    assert act(state, pos=(5, 3)).state.units[U1].xy == (5, 3)


def test_units_and_chasm_gaps_can_be_leapt_over() -> None:
    terrain = "\n".join(["......."] * 3 + ["....x.."] + ["......."] * 3)
    over_gap = race_state("fox", foes=((0, 6),), terrain=terrain)
    assert act(over_gap, pos=(5, 3)).state.units[U1].xy == (5, 3)
    over_unit = race_state("fox", foes=((4, 3),))
    assert act(over_unit, pos=(5, 3)).state.units[U1].xy == (5, 3)


def test_terrain_higher_than_the_leap_can_rise_blocks_like_a_wall() -> None:
    heights = "\n".join(["0000000"] * 3 + ["0000300"] + ["0000000"] * 3)
    state = race_state("fox", foes=((0, 6),), heights=heights)
    assert not leap_path_clear(state, (3, 3), (5, 3), 2)
    with pytest.raises(IllegalActionError, match="牆"):
        resolve(state, use(pos=(5, 3)))


# ---------------------------------------------------------------------------
# 獸躍：藉機攻擊、次數、狀態
# ---------------------------------------------------------------------------


def _opportunity_state() -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter", max_hp=999, race="fox")),
        spawn(Team.ENEMY, (4, 3), template("bandit", max_hp=999)),  # 保留預設反應（藉機攻擊）
    ]
    return give_turn(make_state(m, spawns), U1)


def test_leap_does_not_provoke_opportunity_attacks() -> None:
    walk = Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=2, y=3)))
    assert of(resolve(_opportunity_state(), walk), AttackRolled)  # 走開會被藉機攻擊
    leapt = resolve(_opportunity_state(), use(pos=(0, 3)))
    assert leapt.state.units[U1].xy == (0, 3)
    assert not of(leapt, AttackRolled)


def test_leap_is_once_per_battle() -> None:
    state = act(race_state("fox", foes=((0, 6),)), pos=(4, 3)).state
    again = give_turn(state, U1)
    with pytest.raises(IllegalActionError, match="已用完"):
        resolve(again, use(pos=(3, 3)))
    assert not _leaps(again)


def test_rooted_unit_cannot_leap() -> None:
    state = race_state("fox", foes=((0, 6),))
    rooted = run_effects(
        state, [ApplyStatusEffect(target_id=U1, status_id="root", source_id=U2, duration=2)]
    ).state
    with pytest.raises(IllegalActionError, match="定身"):
        resolve(give_turn(rooted, U1), use(pos=(4, 3)))


# ---------------------------------------------------------------------------
# 輕身
# ---------------------------------------------------------------------------


def _push_off_cliff(race: str | None) -> tuple[BattleState, list[object]]:
    state = race_state(race, me=(2, 3), foes=((1, 3),), heights=CLIFF)
    push = PushEffect(source_id=U2, target_id=U1, direction=(1, 0), distance=1)
    result = run_effects(state, [push])
    return result.state, list(result.events)


def test_light_body_takes_no_damage_when_pushed_off_a_ledge() -> None:
    plain, plain_events = _push_off_cliff("human")
    assert any(isinstance(e, UnitFell) for e in plain_events)
    assert plain.units[U1].hp < plain.units[U1].max_hp
    beast, beast_events = _push_off_cliff("fox")
    assert beast.units[U1].xy == (3, 3)
    assert not any(isinstance(e, UnitFell | DamageDealt) for e in beast_events)
    assert beast.units[U1].hp == beast.units[U1].max_hp


def test_light_body_walks_down_a_ledge_without_falling() -> None:
    state = race_state("fox", me=(2, 3), foes=((6, 6),), heights=CLIFF)
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=2, y=3), Pos(x=3, y=3))))
    assert result.state.units[U1].xy == (3, 3)
    assert not of(result, UnitFell) and not of(result, DamageDealt)


def test_light_body_still_dies_in_deadly_terrain() -> None:
    terrain = "\n".join(["...x..."] * 7)
    state = race_state("fox", me=(2, 3), foes=((1, 3),), terrain=terrain)
    push = PushEffect(source_id=U2, target_id=U1, direction=(1, 0), distance=1)
    result = run_effects(state, [push])
    assert any(isinstance(e, EnteredDeadlyTerrain) for e in result.events)
    assert not result.state.units[U1].alive or result.state.units[U1].hp <= 0


def test_light_body_can_vault_down_a_ledge() -> None:
    """攀跳的「跳下去會摔傷」不適用於輕身（不會摔傷）。"""
    terrain = "\n".join(["...x..."] * 7)
    heights = "\n".join(["3330000"] * 7)
    beast = race_state("fox", me=(2, 3), foes=((6, 6),), heights=heights, terrain=terrain)
    plain = race_state("human", me=(2, 3), foes=((6, 6),), heights=heights, terrain=terrain)
    assert vault_problem(plain, plain.units[U1], (4, 3)) == "落點太低，跳下去會摔傷"
    assert vault_problem(beast, beast.units[U1], (4, 3)) is None


def test_fall_immune_only_for_light_body() -> None:
    for race, immune in (("fox", True), ("human", False), (None, False)):
        state = race_state(race)
        assert fall_immune(state.ruleset, state.units[U1]) is immune


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_ai_does_not_count_a_drop_as_risk_for_light_body() -> None:
    path = (Pos(x=2, y=3), Pos(x=3, y=3))
    for race, risky in (("fox", False), ("human", True)):
        state = race_state(race, me=(2, 3), foes=((6, 6),), heights=CLIFF)
        assert is_risky_move(state, state.units[U1], Move(unit_id=U1, path=path), []) is risky


def test_ai_leaps_up_to_the_highest_ledge_it_can_attack_from() -> None:
    state = race_state("fox", foes=((6, 3),), heights=STEPS)
    action = race_ai_action(state, state.units[U1])
    assert action is not None and action.target_pos == Pos(x=5, y=3)  # 高 2、打得到高 3 的 (6, 3)


def test_ai_does_not_leap_on_flat_ground() -> None:
    state = race_state("fox", foes=((5, 3),))
    assert race_ai_action(state, state.units[U1]) is None


def test_every_ai_profile_values_height_for_light_body() -> None:
    profiles = library().ai_profiles.profiles
    assert all(p.weights.light_body_height == 4 for p in profiles)
