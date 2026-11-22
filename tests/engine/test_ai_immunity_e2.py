"""E2：AI 判斷有害格時看雙方的免疫（08 8.29 E2 第 2 點；開關 ``harmful_sees_immunity``，預設開）。

角魔「炎膚」（``burn_immunity_on: [fire]``）與裝備的同種地形規則：自己免疫的格子敢站、不把免疫的
對手推進那種格子、不在對方腳下放他免疫的表面；開關關掉時和 E2 之前相同。另含帶地形規則的戰鬥
重播確定性。
"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.race_helpers import U1, U2, race_state
from tests.engine.test_unit_rules_e2 import FIRE_WALK, loadout, terrain, wear
from trpg.content.environment import AiProfile
from trpg.engine import BattleState, Shove
from trpg.engine.ai.displace import tile_harm
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.engine.ai.utility.position import _harmful, position_value
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.engine.state import state_to_json
from trpg.shared.types import Team


def switch(state: BattleState, *, on: bool) -> BattleState:
    """把 ``heuristics.scoring.harmful_sees_immunity`` 設成 ``on``（規則包的複本）。"""
    scoring = state.ruleset.ai.scoring.model_copy(update={"harmful_sees_immunity": on})
    ai = state.ruleset.ai.model_copy(update={"scoring": scoring})
    state.ruleset = state.ruleset.model_copy(update={"ai": ai})
    return state


def _brute() -> AiProfile:
    return next(p for p in library().ai_profiles.profiles if p.id == "brute")


def test_switch_is_on_by_default() -> None:
    assert library().ruleset.ai.scoring.harmful_sees_immunity is True


def test_fire_is_not_harmful_to_a_fiend_when_the_switch_is_on() -> None:
    state = race_state("fiend", me=(3, 3), surfaces=[(3, 3, "fire"), (4, 4, "poison")])
    fiend = state.units[U1]
    assert not _harmful(state, (3, 3), fiend)
    assert _harmful(state, (3, 3))  # 沒有指定單位：照舊
    assert _harmful(state, (4, 4), fiend)  # 毒的傷害不是燃燒，照樣有害
    switch(state, on=False)
    assert _harmful(state, (3, 3), fiend)


def test_fire_is_still_harmful_to_others() -> None:
    state = race_state(None, me=(3, 3), surfaces=[(3, 3, "fire")])
    assert _harmful(state, (3, 3), state.units[U1])


def test_equipment_fire_walk_counts_too() -> None:
    state = race_state(None, me=(3, 3), surfaces=[(3, 3, "fire")])
    unit = wear(state, {"feet": [terrain(*FIRE_WALK, rule="burn_immunity_on", surfaces=["fire"])]})
    assert not _harmful(state, (3, 3), unit)


def test_fiend_ai_does_not_count_fire_as_a_hazard_for_its_own_tile() -> None:
    w = _brute().weights
    on = race_state("fiend", me=(3, 3), surfaces=[(3, 3, "fire")])
    off = switch(race_state("fiend", me=(3, 3), surfaces=[(3, 3, "fire")]), on=False)
    assert position_value(on, U1, w) - position_value(off, U1, w) == w.hazard


def _shove_into_fire(foe_race: str | None, *, on: bool = True) -> BattleState:
    """U1 在 (3,3)、敵人 U2 在 (4,3)，推過去落在 (5,3) 的火上。"""
    state = race_state(
        None, me=(3, 3), foes=((4, 3),), surfaces=[(5, 3, "fire")], foe_race=foe_race
    )
    return switch(state, on=on)


def _shove_score(state: BattleState) -> object:
    return score_action(state, Shove(unit_id=U1, target_id=U2), _brute()).score


def test_ai_does_not_value_pushing_an_immune_foe_into_fire() -> None:
    """開關打開時，推角魔進火少了「站上有害表面」的收益；推一般人不受影響。（關掉時推角魔的分數本來
    就比較低——預覽是真的引擎，角魔不會燃燒，所以狀態收益沒有——但仍把火算成有害表面。）"""
    human_on = _shove_score(_shove_into_fire(None))
    human_off = _shove_score(_shove_into_fire(None, on=False))
    assert human_on == human_off
    fiend_on = _shove_score(_shove_into_fire("fiend"))
    fiend_off = _shove_score(_shove_into_fire("fiend", on=False))
    assert fiend_on < fiend_off  # type: ignore[operator]


def test_teleport_estimate_sees_the_immunity() -> None:
    state = race_state(None, me=(3, 3), foes=((4, 3),), surfaces=[(5, 3, "fire")], foe_race="fiend")
    foe = state.units[U2]
    assert tile_harm(state, (5, 3), Team.ALLY, _harmful, foe) == 0
    assert tile_harm(state, (5, 3), Team.ALLY, _harmful) > 0
    assert tile_harm(state, (5, 3), Team.ALLY, _harmful, state.units[U1]) > 0


def test_utility_ai_still_ranks_actions_with_immunity() -> None:
    state = _shove_into_fire("fiend")
    ranked = UtilityAI(library().ai_profiles, override="brute").rank(state)
    assert ranked


# ---------------------------------------------------------------------------
# 重播確定性
# ---------------------------------------------------------------------------


def _terrain_setup() -> BattleSetup:
    lib = library()
    setup = build_setup(lib, "lava_crossing", ["hero_fighter"], ["bandit", "bandit"])
    hero = setup.units[0]
    boots = terrain("affix_t_ice_step", "冰上不滑倒", rule="slip_immunity", surfaces=["ice"])
    fire = terrain(*FIRE_WALK, rule="burn_immunity_on", surfaces=["fire"])
    gear = loadout({"feet": [boots], "body": [fire]})
    template = hero.template.model_copy(update={"race": "fiend"})
    hero = hero.model_copy(update={"equipment": gear, "template": template})
    return setup.model_copy(update={"units": (hero, *setup.units[1:])})


def test_battles_with_terrain_rules_replay_identically() -> None:
    setup = _terrain_setup()
    first = run_battle(setup, 5)
    second = run_battle(setup, 5)
    dump = [e.model_dump() for e in first.events]
    assert dump == [e.model_dump() for e in second.events]
    again = replay(setup, 5, first.actions)
    assert [e.model_dump() for e in again.events] == dump
    assert state_to_json(again.state) == state_to_json(first.state)
