"""賽季日程：換日、世界事件、懸賞板、今日目標（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.6）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    BattleEndedEvent,
    BattleStartedEvent,
    CampAction,
    CampedEvent,
    LocationRevealedEvent,
    QuestStepDoneEvent,
    WorldEvent,
)
from trpg.world.battle import battle_xp, enemy_level
from trpg.world.calendar import day_of
from trpg.world.economy_actions import CurrencyGainedEvent
from trpg.world.encounters import EncounterLineup, LineupMember, roll_lineup
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.season_board import (
    after_season_step,
    daily_goals_for,
    open_bounty_at,
    posted_bounties,
    record_activity,
    roll_season,
)
from trpg.world.season_events import (
    BountyClaimedEvent,
    BountyMissedEvent,
    DailyGoalDoneEvent,
    WorldEventResolvedEvent,
)
from trpg.world.solutions import make_encounter
from trpg.world.state import CharacterState, DailyActivity, WorldState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
DAY = 24 * 3600


def _day(n: int) -> int:
    """賽季第 ``n`` 天的中午。"""
    return NOON + (n - 1) * DAY


def _battle(
    *,
    weather: str = "fog",
    location: str = "ferry_steps",
    lineup: EncounterLineup | None = None,
    won: bool = True,
    xp: int = 100,
    level: int = 1,
) -> list[WorldEvent]:
    lineup = lineup or EncounterLineup(
        region="cloud_ridge",
        location=location,
        group="bandit_raiders",
        members=(LineupMember(unit="bandit"), LineupMember(unit="bandit")),
    )
    started = BattleStartedEvent(
        location=location,
        battle_map="cliff_outpost",
        region="cloud_ridge",
        lineup=lineup,
        enemy_level=level,
        weather=weather,
        hero_hp=40,
        fatigued=False,
    )
    ended = BattleEndedEvent(
        won=won, end_reason=None, rounds=3, hp=30, mana=5, xp_gained=xp, level=1
    )
    return [started, ended]


def _bounty_lineup(bounty: str = "north_wolf_king") -> EncounterLineup:
    return EncounterLineup(
        region="cloud_ridge",
        location="north_slope",
        group="north_wolf_king_pack",
        members=(
            LineupMember(unit="mist_wolf", affix="berserk"),
            *(LineupMember(unit="mist_wolf") for _ in range(3)),
        ),
        bounty=bounty,
    )


def _with_players(world: WorldState, day: int, count: int) -> WorldState:
    actors = tuple(sorted(f"a{i}" for i in range(count)))
    return world.model_copy(update={"activity": (DailyActivity(day=day, actors=actors),)})


# ---------------------------------------------------------------------------
# 換日與世界事件
# ---------------------------------------------------------------------------


def test_first_day_starts_event_with_base_target(library: ContentLibrary) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    state = world.world_event("mist_tide")
    assert state is not None and state.status == "active"
    assert state.target == 30  # 第 1 天沒有前一天：原門檻（代決 5F1-4）
    assert state.adjustments[0].players is None
    assert world.rolled_day == day_of(library, NOON)
    again, events = roll_season(library, world, NOON + 60)
    assert again == world and events == ()


def test_target_follows_yesterdays_players(library: ContentLibrary) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    world = _with_players(world, day_of(library, NOON), 4)
    world, _ = roll_season(library, world, _day(2))
    state = world.world_event("mist_tide")
    assert state is not None and state.target == 15  # 30 × 4 ÷ 8（Q14）
    assert state.adjustments[-1].players == 4 and state.adjustments[-1].day == day_of(
        library, _day(2)
    )


def test_target_without_activity_keeps_base(library: ContentLibrary) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    world, _ = roll_season(library, world, _day(2))  # 第 1 天沒有上線紀錄：原門檻（5F-1b）
    state = world.world_event("mist_tide")
    assert state is not None and state.target == 30 and len(state.adjustments) == 1


def test_target_floor_quarter(library: ContentLibrary) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    world = _with_players(world, day_of(library, NOON), 1)
    world, _ = roll_season(library, world, _day(2))  # 30 × 1 ÷ 8 ＝ 3 → 下限 1/4 ＝ 8（5F-1b）
    state = world.world_event("mist_tide")
    assert state is not None and state.target == 8
    assert state.adjustments[-1].players == 1


def test_progress_reaches_target_and_applies_success(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    world = _with_players(world, day_of(library, NOON), 1)
    world, _ = roll_season(library, world, _day(2))  # 門檻 8（下限 1/4）
    char = make_char()
    events: list[WorldEvent] = []
    for _ in range(8):
        world, char, more = after_season_step(
            library, world, char, _battle(), now=_day(2), actor="alice"
        )
        events += more
    state = world.world_event("mist_tide")
    assert state is not None and state.status == "succeeded" and state.progress == 8
    assert world.has_flag("ashen_waste_open")
    assert world.level_bonus == {}
    resolved = [e for e in events if isinstance(e, WorldEventResolvedEvent)]
    assert len(resolved) == 1 and resolved[0].outcome == "succeeded"


def test_only_matching_battles_count(library: ContentLibrary, make_char: MakeChar) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    char = make_char()
    for events in (_battle(weather="rain"), _battle(won=False)):
        world, char, _ = after_season_step(library, world, char, events, now=NOON, actor="a")
    state = world.world_event("mist_tide")
    assert state is not None and state.progress == 0


def test_failure_raises_region_level(library: ContentLibrary, make_char: MakeChar) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    world, _ = roll_season(library, world, _day(4))  # 補第 2～4 天；第 4 天判失敗
    state = world.world_event("mist_tide")
    assert state is not None and state.status == "failed"
    assert state.resolved_day == day_of(library, _day(4))
    assert world.level_bonus == {"ashen_waste": 1}
    assert world.has_flag("ashen_waste_open")


def test_level_bonus_raises_enemy_level(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world(level_bonus={"cloud_ridge": 1})
    char = make_char(location="ferry_steps")
    place = library.world_maps["cloud_ridge"].location_by_id()["ferry_steps"]
    encounter, _ = make_encounter(library, world, char, place, NOON)
    assert encounter.level_bonus == 1
    plain = encounter.model_copy(update={"level_bonus": 0})
    assert enemy_level(library, encounter) == enemy_level(library, plain) + 1
    lineup = roll_lineup(library, plain)
    assert battle_xp(library, encounter, lineup) > battle_xp(library, plain, lineup)


def test_activity_keeps_two_days(library: ContentLibrary) -> None:
    world = make_world()
    today = day_of(library, NOON)
    world = record_activity(world, "b", today - 2)
    world = record_activity(world, "a", today - 1)
    world = record_activity(world, "a", today)
    world = record_activity(world, "b", today)
    assert [(a.day, a.actors) for a in world.activity] == [
        (today - 1, ("a",)),
        (today, ("a", "b")),
    ]
    assert record_activity(world, "a", today) is world


# ---------------------------------------------------------------------------
# 懸賞
# ---------------------------------------------------------------------------


def test_bounties_posted_daily(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char()
    posted = posted_bounties(library, world, NOON)
    assert [p.bounty.id for p in posted] == ["north_wolf_king", "mist_swordsman", "scarface"]
    assert all(p.claim is None for p in posted)
    found = open_bounty_at(library, world, char, "north_slope", NOON)
    assert found == "north_wolf_king"
    assert open_bounty_at(library, world, char, "ferry_steps", NOON) is None
    assert posted_bounties(library, world, _day(15)) == ()  # 季末後不再貼


def test_bounty_encounter_uses_bounty_lineup(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(location="sword_tomb")
    place = library.world_maps["cloud_ridge"].location_by_id()["sword_tomb"]
    encounter, _ = make_encounter(library, world, char, place, NOON)
    assert encounter.bounty == "mist_swordsman"
    lineup = roll_lineup(library, encounter)
    assert lineup.bounty == "mist_swordsman"
    assert lineup.members[0] == LineupMember(unit="sect_mist_swordsman", affix="mist_veiled")
    # 自己的劇情變化優先（疤面的線頭到期結局）
    fort = library.world_maps["cloud_ridge"].location_by_id()["cliff_gang_fort"]
    at_fort, _ = make_encounter(library, world, char, fort, NOON)
    assert roll_lineup(library, at_fort, ("scarface_rises",)).bounty is None


def test_first_come_first_served(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    alice, bob = make_char("alice"), make_char("bob")
    fight = _battle(lineup=_bounty_lineup(), location="north_slope", level=4)
    world, alice, first = after_season_step(library, world, alice, fight, now=NOON, actor="a")
    claimed = next(e for e in first if isinstance(e, BountyClaimedEvent))
    assert claimed.bounty == "north_wolf_king" and claimed.coins == 3
    xp = library.world_rules.xp.xp_for("bounty", 4)  # type: ignore[union-attr]
    assert claimed.xp == xp - 100  # 補到懸賞份數（代決 5F1-6）
    assert alice.quest_coins >= 3
    # 已被搶下：bob 今天第一場仍是懸賞陣容（大家都打得到，5F-1b）
    assert open_bounty_at(library, world, bob, "north_slope", NOON) is not None
    world, bob, second = after_season_step(library, world, bob, fight, now=NOON + 60, actor="b")
    missed = BountyMissedEvent(bounty="north_wolf_king", claimed_by=alice.hero.name_zh, coins=1)
    assert missed in second  # 小獎（9.6.3）
    gains = [e for e in second if isinstance(e, CurrencyGainedEvent)]
    assert [g.amount for g in gains if g.source == "bounty_consolation:north_wolf_king"] == [1]
    assert not any(isinstance(e, BountyClaimedEvent) for e in second)
    # 兩人今天的第一場都用掉了：之後照一般遭遇
    for char in (alice, bob):
        assert open_bounty_at(library, world, char, "north_slope", NOON) is None
    # 隔天（6 點換日）重新貼出、重新算第一場
    assert open_bounty_at(library, world, alice, "north_slope", _day(2)) is not None


def test_first_bounty_encounter_per_day(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(location="north_slope")
    place = library.world_maps["cloud_ridge"].location_by_id()["north_slope"]
    first, _ = make_encounter(library, world, char, place, NOON)
    assert first.bounty == "north_wolf_king"
    lost = _battle(lineup=_bounty_lineup(), location="north_slope", won=False)
    world, char, events = after_season_step(library, world, char, lost, now=NOON, actor="a")
    assert char.bounty_days == {"north_wolf_king": day_of(library, NOON)}
    assert not any(isinstance(e, (BountyClaimedEvent, BountyMissedEvent)) for e in events)
    second, _ = make_encounter(library, world, char, place, NOON + 600)
    assert second.bounty is None  # 輸了也算用掉今天的第一場
    # 別的懸賞地點不受影響
    tomb = library.world_maps["cloud_ridge"].location_by_id()["sword_tomb"]
    assert make_encounter(library, world, char, tomb, NOON)[0].bounty == "mist_swordsman"
    # 6 點換日前一刻仍是同一天，過了 6 點重新算
    refresh = day_of(library, NOON)
    before = next(t for t in range(NOON, NOON + DAY, 60) if day_of(library, t) != refresh) - 60
    assert make_encounter(library, world, char, place, before)[0].bounty is None
    assert make_encounter(library, world, char, place, before + 60)[0].bounty == "north_wolf_king"


def test_north_slope_bounty_and_daily_lineups(library: ContentLibrary, make_char: MakeChar) -> None:
    """6E-3d：懸賞期間每天第一場＝north_wolf_king_pack（狼王＋3 狼）；之後的日常駐守＝
    north_slope_pack（狼王＋2 狼，6E-3c）。"""
    king = LineupMember(unit="mist_wolf", affix="berserk")
    wolf = LineupMember(unit="mist_wolf")
    world = make_world()
    char = make_char(location="north_slope")
    place = library.world_maps["cloud_ridge"].location_by_id()["north_slope"]
    first, _ = make_encounter(library, world, char, place, NOON)
    bounty = roll_lineup(library, first)
    assert bounty.bounty == "north_wolf_king"
    assert bounty.group == "north_wolf_king_pack"
    assert bounty.members == (king, wolf, wolf, wolf)
    fight = _battle(lineup=bounty, location="north_slope", won=False)
    world, char, _ = after_season_step(library, world, char, fight, now=NOON, actor="a")
    second, _ = make_encounter(library, world, char, place, NOON + 600)
    daily = roll_lineup(library, second)
    assert daily.bounty is None
    assert daily.group == "north_slope_pack"
    assert daily.members == (king, wolf, wolf)


# ---------------------------------------------------------------------------
# 今日目標
# ---------------------------------------------------------------------------


def test_newbie_goals_then_deterministic(library: ContentLibrary) -> None:
    world = make_world()
    first = daily_goals_for(library, world, day_of(library, NOON))
    assert [g.id for g in first] == ["starter_steps", "reveal_hidden", "elite_once"]
    assert daily_goals_for(library, world, day_of(library, _day(2))) == first
    third = daily_goals_for(library, world, day_of(library, _day(3)))
    assert len(third) == 3 and len({g.id for g in third}) == 3
    assert daily_goals_for(library, world, day_of(library, _day(3))) == third
    other = make_world(season_seed=7)
    days = [day_of(library, _day(n)) for n in range(3, 10)]
    assert [daily_goals_for(library, world, d) for d in days] != [
        daily_goals_for(library, other, d) for d in days
    ]


def test_goal_done_pays_coins_and_resets(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char()
    found: list[WorldEvent] = [
        LocationRevealedEvent(location="mist_hollow", method="perception_nearby")
    ]
    world, char, events = after_season_step(library, world, char, found, now=NOON, actor="a")
    assert DailyGoalDoneEvent(goal="reveal_hidden", coins=1) in events
    assert any(
        isinstance(e, CurrencyGainedEvent) and e.source == "daily_goal:reveal_hidden"
        for e in events
    )
    assert char.daily_goals is not None and char.daily_goals.done == ("reveal_hidden",)
    # 同一天不再給
    _, again, more = after_season_step(library, world, char, found, now=NOON + 60, actor="a")
    assert not any(isinstance(e, DailyGoalDoneEvent) for e in more)
    # 新手任務 2 步：第 1 步只記進度、第 2 步完成；其他種類的任務不算
    step = QuestStepDoneEvent(quest="starter_ferry", step="s1", index=1)
    other = QuestStepDoneEvent(quest="main_mist_rift", step="s1", index=1)
    _, half, none = after_season_step(library, world, again, [step, other], now=NOON, actor="a")
    assert none == ()
    assert half.daily_goals is not None and half.daily_goals.progress["starter_steps"] == 1
    _, full, done = after_season_step(library, world, half, [step], now=NOON, actor="a")
    assert DailyGoalDoneEvent(goal="starter_steps", coins=1) in done
    assert full.quest_coins == half.quest_coins + 1
    # 隔天歸零
    _, tomorrow, _ = after_season_step(library, world, again, found, now=_day(2), actor="a")
    assert tomorrow.daily_goals is not None
    assert tomorrow.daily_goals.day == day_of(library, _day(2))


def test_no_progress_leaves_character(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    camped: list[WorldEvent] = [CampedEvent(location="hunter_hut", supplies_left=1, hp=1, mana=1)]
    _, after, events = after_season_step(library, make_world(), char, camped, now=NOON, actor="a")
    assert after is char and events == ()


# ---------------------------------------------------------------------------
# world_step 與重播
# ---------------------------------------------------------------------------


def test_step_records_actor_and_replays(calm: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    alice = make_char("alice", location="hunter_hut", supplies=5)
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id="alice", action=CampAction(), actor="acc1"),
        WorldLogEntry(seq=2, now=_day(2), character_id="alice", action=CampAction(), actor="acc1"),
    ]
    live = world
    char = alice
    for entry in entries:
        result = world_step(calm, live, char, entry.action, entry.now, actor=entry.actor)
        live, char = result.world, result.char
    assert live.activity[-1].actors == ("acc1",)
    state = live.world_event("mist_tide")
    assert state is not None and state.adjustments[-1].players == 1
    replayed = replay(calm, world, {"alice": alice}, entries)
    assert replayed.world == live and replayed.characters["alice"] == char
