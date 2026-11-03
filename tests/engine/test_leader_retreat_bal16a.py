"""BAL-16a（#86，05 5.8）：Boss 戰頭目倒下時，其餘護衛撤退，戰鬥直接勝利。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, make_map, make_state, no_reactions, spawn
from trpg.content.maps import Objective
from trpg.engine import BattleState, build_setup, start_battle
from trpg.engine.effects import DamageEffect, run_effects
from trpg.engine.events import BattleEnded, GuardsRetreated, UnitDowned
from trpg.engine.ids import BOSS_TAG
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.types import Team, UnitId

HERO, BOSS, GUARD, BOSS2 = (UnitId(f"unit_000{i}") for i in range(1, 5))


def _state(*, retreat: bool, two_bosses: bool = False) -> BattleState:
    enemies = [(4, 0), (5, 0)] + ([(5, 1)] if two_bosses else [])
    objective = {"kind": "eliminate", "leader_retreat": True} if retreat else None
    m = make_map("000000\n000000", ally=[(0, 0)], enemy=enemies, objective=objective)
    spawns = [
        spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
        spawn(Team.ENEMY, (4, 0), no_reactions("bandit_warlord")),
        spawn(Team.ENEMY, (5, 0), no_reactions("bandit_guard")),
    ]
    if two_bosses:
        spawns.append(spawn(Team.ENEMY, (5, 1), no_reactions("bandit_boss")))
    return make_state(m, spawns)


def _kill(state: BattleState, uid: UnitId) -> tuple[BattleState, list[object]]:
    result = run_effects(state, [DamageEffect(target_id=uid, mode="lethal")])
    return result.state, list(result.events)


def test_leader_down_ends_the_battle_with_a_victory() -> None:
    state = _state(retreat=True)
    assert state.units[BOSS].has_tag(BOSS_TAG)
    s, events = _kill(state, BOSS)
    assert s.ended and s.winner is Team.ALLY and s.end_reason == "leader_defeated"
    # 撤退的護衛沒有倒下（不給擊殺、不掉落）
    guard = s.units[GUARD]
    assert not guard.downed and guard.hp == guard.max_hp
    assert not any(isinstance(e, UnitDowned) and e.unit_id == GUARD for e in events)
    ended = [e for e in events if isinstance(e, BattleEnded)]
    assert len(ended) == 1 and ended[0].reason == "leader_defeated"
    # BAL-16b2：獨立的撤退事件，緊接在 battle_ended 之前
    (retreat,) = [e for e in events if isinstance(e, GuardsRetreated)]
    assert retreat.leader_ids == (BOSS,) and retreat.unit_ids == (GUARD,)
    assert events.index(retreat) + 1 == events.index(ended[0])
    line = describe_event(retreat, s)
    assert line is not None and line.startswith("  頭目倒下，") and line.endswith(" 撤退了")
    assert s.units[GUARD].name_zh in line


def test_without_the_flag_the_guards_keep_fighting() -> None:
    s, _ = _kill(_state(retreat=False), BOSS)
    assert not s.ended


def test_killing_a_guard_first_does_not_end_the_battle() -> None:
    s, _ = _kill(_state(retreat=True), GUARD)
    assert not s.ended


def test_every_leader_must_be_down() -> None:
    s, _ = _kill(_state(retreat=True, two_bosses=True), BOSS)
    assert not s.ended
    s, _ = _kill(s, BOSS2)
    assert s.ended and s.end_reason == "leader_defeated"


def test_no_leader_on_the_field_never_triggers() -> None:
    m = make_map(
        "000000",
        ally=[(0, 0)],
        enemy=[(4, 0), (5, 0)],
        objective={"kind": "eliminate", "leader_retreat": True},
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (4, 0), no_reactions()),
            spawn(Team.ENEMY, (5, 0), no_reactions()),
        ],
    )
    s, _ = _kill(state, BOSS)  # 第二個單位只是一般盜賊
    assert not s.ended


def test_leader_retreat_only_with_eliminate() -> None:
    with pytest.raises(ValueError, match="leader_retreat"):
        Objective(kind="defend", rounds=2, tiles=((1, 1),), leader_retreat=True)


def test_boss_map_carries_the_rule_and_normal_maps_do_not() -> None:
    lib = library()
    boss_map = lib.map(lib.roguelite.boss.map)
    assert boss_map.objective.leader_retreat
    assert boss_map.objective_for("eliminate").leader_retreat
    for map_id in lib.roguelite.map_pool:
        assert not lib.map(map_id).objective_for("eliminate").leader_retreat


BOSS_SEED = 0  # 靠種子：這個種子的 Boss 戰以「頭目倒下、護衛撤退」結束
HEROES = ("hero_fighter", "hero_archer", "hero_mage", "hero_fighter")


def test_boss_battle_ends_by_retreat_and_replays() -> None:
    lib = library()
    rules = lib.roguelite
    setup = build_setup(lib, rules.boss.map, HEROES, rules.boss.enemies)
    assert start_battle(setup, BOSS_SEED).objective.leader_retreat
    run = run_battle(setup, BOSS_SEED)
    assert run.state.end_reason == "leader_defeated" and run.state.winner is Team.ALLY
    assert any(u.alive for u in run.state.units.values() if u.team is Team.ENEMY)
    again = replay(run.setup, run.seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
