"""影子循環賽（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36）。"""

from __future__ import annotations

from collections.abc import Callable
from math import comb

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_season import LeagueRules
from trpg.engine.battle import begin_battle
from trpg.engine.events import DamageDealt, StatusRemoved
from trpg.engine.runner import log_replay_problem, replay
from trpg.shared.types import Attribute, Team
from trpg.world.actions import CampAction
from trpg.world.errors import WorldActionError
from trpg.world.league import (
    league_rules,
    league_schedule,
    league_spawns,
    leveled_snapshot,
    match_setup,
    match_winner,
    matches_per_pair,
    play_match,
)
from trpg.world.league_actions import (
    LeagueEnterAction,
    LeagueEnteredEvent,
    LeagueWithdrawAction,
    LeagueWithdrawnEvent,
)
from trpg.world.replay import WorldLogEntry
from trpg.world.replay import replay as replay_world
from trpg.world.shadows import shadow_snapshot
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import new_character, world_step

MakeChar = Callable[..., CharacterState]
DAY = 24 * 3600


def _rules(library: ContentLibrary) -> LeagueRules:
    rules = league_rules(library)
    assert rules is not None
    return rules


def _enter(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    actor: str,
    *,
    ai: str | None = None,
    now: int = NOON,
) -> WorldState:
    return world_step(library, world, char, LeagueEnterAction(ai=ai), now, actor=actor).world


def _build_char(library: ContentLibrary, character_id: str, build: str) -> CharacterState:
    hero = next(b.hero for b in library.builds.builds if b.id == build)
    return new_character(library, character_id, hero, region="cloud_ridge")


@pytest.fixture(scope="module")
def three(library: ContentLibrary) -> WorldState:
    """三個帳號各報名一個角色（輔助、衝陣、雷水）。"""
    world = make_world()
    builds = (("alice", "build_support"), ("bob", "build_charger"), ("cara", "build_storm"))
    for cid, build in builds:
        world = _enter(library, world, _build_char(library, cid, build), f"acc_{cid}")
    return world


# ---------------------------------------------------------------------------
# 內容
# ---------------------------------------------------------------------------


def test_content_league(library: ContentLibrary) -> None:
    rules = _rules(library)
    assert rules.signup_close_day == 13  # #101
    assert len(rules.maps) == 3  # 9.7「3 張事先公布的地圖」
    assert rules.seeds >= 2  # 多個種子
    assert matches_per_pair(rules) == 3 * rules.seeds * 2


# ---------------------------------------------------------------------------
# 報名
# ---------------------------------------------------------------------------


def test_enter_and_update(library: ContentLibrary, make_char: MakeChar) -> None:
    alice = make_char("alice")
    result = world_step(
        library, make_world(), alice, LeagueEnterAction(ai="guard"), NOON, actor="acc1"
    )
    assert LeagueEnteredEvent(ai="guard", updated=False) in result.events
    (entry,) = result.world.league_entries
    assert (entry.account, entry.character_id, entry.name) == ("acc1", "alice", alice.hero.name_zh)
    assert entry.snapshot == shadow_snapshot(alice, NOON)
    assert entry.ai == "guard" and entry.entered_at == NOON
    again = world_step(library, result.world, alice, LeagueEnterAction(), NOON + 60, actor="acc1")
    assert LeagueEnteredEvent(ai=None, updated=True) in again.events
    (updated,) = again.world.league_entries
    assert updated.ai is None and updated.entered_at == NOON  # 報名時間不變
    assert updated.snapshot.saved_at == NOON + 60


def test_one_character_per_account(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _enter(library, make_world(), make_char("alice"), "acc1")
    with pytest.raises(WorldActionError, match="已經用"):
        _enter(library, world, make_char("bob"), "acc1")
    # 別的帳號可以
    world = _enter(library, world, make_char("bob"), "acc2")
    assert [e.account for e in world.league_entries] == ["acc1", "acc2"]


def test_without_account_uses_character_id(library: ContentLibrary, make_char: MakeChar) -> None:
    world = world_step(library, make_world(), make_char("alice"), LeagueEnterAction(), NOON).world
    assert world.league_entries[0].account == "alice"


def test_signup_closes_after_day_13(library: ContentLibrary, make_char: MakeChar) -> None:
    alice = make_char("alice")
    last = NOON + 12 * DAY  # 第 13 天
    world = _enter(library, make_world(), alice, "acc1", now=last)
    with pytest.raises(WorldActionError, match="截止"):
        _enter(library, world, make_char("bob"), "acc2", now=last + DAY)
    with pytest.raises(WorldActionError, match="截止"):
        world_step(library, world, alice, LeagueWithdrawAction(), last + DAY, actor="acc1")


def test_signup_needs_town_and_known_ai(calm: ContentLibrary, make_char: MakeChar) -> None:
    field = make_char("alice", location="hunter_hut", supplies=3)
    with pytest.raises(WorldActionError, match="城鎮"):
        _enter(calm, make_world(), field, "acc1")
    camped = world_step(calm, make_world(), field, CampAction(), NOON).char
    with pytest.raises(WorldActionError, match="城鎮"):
        _enter(calm, make_world(), camped, "acc1")
    with pytest.raises(WorldActionError, match="打法"):
        _enter(calm, make_world(), make_char("alice"), "acc1", ai="idle")


def test_withdraw(library: ContentLibrary, make_char: MakeChar) -> None:
    alice = make_char("alice")
    world = _enter(library, make_world(), alice, "acc1")
    result = world_step(library, world, alice, LeagueWithdrawAction(), NOON, actor="acc1")
    assert LeagueWithdrawnEvent() in result.events
    assert result.world.league_entries == ()
    with pytest.raises(WorldActionError, match="沒有報名"):
        world_step(library, result.world, alice, LeagueWithdrawAction(), NOON, actor="acc1")


def test_world_log_replay_with_entries(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    chars = {c: make_char(c) for c in ("alice", "bob")}
    log = [
        WorldLogEntry(
            seq=1, now=NOON, character_id="alice", action=LeagueEnterAction(ai="guard"), actor="a1"
        ),
        WorldLogEntry(
            seq=2, now=NOON + 5, character_id="bob", action=LeagueEnterAction(), actor="b1"
        ),
        WorldLogEntry(
            seq=3, now=NOON + 9, character_id="alice", action=LeagueWithdrawAction(), actor="a1"
        ),
    ]
    first = replay_world(library, world, chars, log)
    second = replay_world(library, world, chars, log)
    assert first == second
    assert [e.account for e in first.world.league_entries] == ["b1"]


# ---------------------------------------------------------------------------
# 拉到等級上限
# ---------------------------------------------------------------------------


def test_leveled_snapshot(library: ContentLibrary, three: WorldState) -> None:
    entry = three.league_entries[0]  # alice：輔助（祝禱、智慧）
    snap = entry.snapshot
    leveled = leveled_snapshot(library, snap)
    assert snap.level == 1
    assert leveled.level == 10 and leveled.skill_tier == 3
    added = 9 * library.roguelite.attribute_points_per_level
    gained = {a: leveled.hero.attributes[a] - snap.hero.attributes.get(a, 0) for a in Attribute}
    assert sum(gained.values()) == added
    assert leveled.attribute_points == 0
    assert sum(leveled.attribute_spent.values()) == added
    assert gained[Attribute.WIS] == added  # 主屬性（技能最常用的縮放屬性）
    assert all(s.endswith("_t3") for s in leveled.hero.skills)
    assert len(leveled.hero.skills) == len(snap.hero.skills)
    assert {s.id for s in leveled.skills} == set(leveled.hero.skills)
    assert all(s.tier == 3 for s in leveled.skills)
    assert leveled_snapshot(library, leveled) == leveled


# ---------------------------------------------------------------------------
# 賽程與對戰
# ---------------------------------------------------------------------------


def test_schedule(library: ContentLibrary, three: WorldState) -> None:
    rules = _rules(library)
    schedule = league_schedule(rules, three.season_seed, three.league_entries)
    assert len(schedule) == comb(3, 2) * matches_per_pair(rules)
    assert [s.id for s in schedule[:3]] == ["m0001", "m0002", "m0003"]
    assert len({s.id for s in schedule}) == len(schedule)
    first, swapped = schedule[0], schedule[1]
    assert (first.a, first.b, first.map) == ("acc_alice", "acc_bob", rules.maps[0])
    assert first.seed == swapped.seed and first.ally == "acc_alice" and swapped.ally == "acc_bob"
    assert league_schedule(rules, three.season_seed, three.league_entries) == schedule
    assert league_schedule(rules, three.season_seed + 1, three.league_entries)[0].seed != first.seed
    pairs = {(s.a, s.b) for s in schedule}
    assert pairs == {("acc_alice", "acc_bob"), ("acc_alice", "acc_cara"), ("acc_bob", "acc_cara")}


def test_match_setup_and_replay(library: ContentLibrary, three: WorldState) -> None:
    rules = _rules(library)
    schedule = league_schedule(rules, three.season_seed, three.league_entries)
    spawns = league_spawns(library, three.league_entries)
    spec = schedule[1]  # bob 先手
    setup = match_setup(library, rules, spawns, spec)
    ally, enemy = setup.units
    assert (ally.team, enemy.team) == (Team.ALLY, Team.ENEMY)
    assert ally.template.name_zh == three.league_entries[1].name
    assert ally.template.id == "shadow_bob" and enemy.template.id == "shadow_alice"
    assert ally.template.level == enemy.template.level == 10
    assert setup.first_team is Team.ALLY and setup.max_rounds == rules.max_rounds
    assert setup.map.id == spec.map
    for skill in (*ally.template.skills, *enemy.template.skills):
        assert skill in {s.id for s in setup.ruleset.skills.skills}
    run = play_match(library, setup, spec.seed)
    assert run.state.ended
    again = play_match(library, setup, spec.seed)
    assert again.actions == run.actions
    winner = match_winner(run.state, spec)
    assert winner in (spec.a, spec.b, None)
    log = run.to_log()
    assert log_replay_problem(log) is None
    assert replay(log.setup, log.seed, log.actions).state == run.state


# ---------------------------------------------------------------------------
# 5F-4b：循環賽的平衡規則（開場 HP ×2、第 1 輪休戰）
# ---------------------------------------------------------------------------


def test_balance_rules_only_in_league(library: ContentLibrary, three: WorldState) -> None:
    """開場 HP ×2、雙方掛上休戰；不套在一般戰鬥（同一個影子 spawn 原樣）。"""
    rules = _rules(library)
    assert rules.hp_permille == 2000
    assert rules.opening_statuses == ("league_truce",)
    spawns = league_spawns(library, three.league_entries)
    spec = league_schedule(rules, three.season_seed, three.league_entries)[0]
    setup = match_setup(library, rules, spawns, spec)
    plain_rules = rules.model_copy(update={"hp_permille": 1000, "opening_statuses": ()})
    plain = match_setup(library, plain_rules, spawns, spec)
    state = begin_battle(setup, spec.seed).state
    base = begin_battle(plain, spec.seed).state
    for uid, unit in state.units.items():
        assert unit.max_hp == unit.hp == base.units[uid].max_hp * 2
        assert "league_truce" in {s.status_id for s in unit.statuses}
        assert "league_truce" not in {s.status_id for s in base.units[uid].statuses}
    raw, _ = spawns[spec.ally]
    assert "league_truce" not in raw.opening_statuses  # 影子本身的出場設定不變


@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5])
def test_truce_blocks_round_one_damage(
    library: ContentLibrary, three: WorldState, index: int
) -> None:
    """第 1 輪沒有任何傷害事件、休戰在第 1 輪結束時移除；第 2 輪起照常；重播一致。"""
    rules = _rules(library)
    spawns = league_spawns(library, three.league_entries)
    spec = league_schedule(rules, three.season_seed, three.league_entries)[index]
    run = play_match(library, match_setup(library, rules, spawns, spec), spec.seed)
    first_round = [e for e in run.events if e.round == 1]
    assert not [e for e in first_round if isinstance(e, DamageDealt)]
    removed = [
        e for e in first_round if isinstance(e, StatusRemoved) and e.status_id == "league_truce"
    ]
    assert len(removed) == 2  # 兩人都在第 1 輪結束時移除
    log = run.to_log()
    assert replay(log.setup, log.seed, log.actions).state == run.state
