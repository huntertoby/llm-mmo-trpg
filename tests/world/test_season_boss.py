"""賽季 Boss：封印鑰匙、解鎖時間、挑戰、通關（Phase 5F-3；``docs/phases/Phase5計畫.md`` 37.6）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    BattleEndedEvent,
    FightAction,
    InsightGainedEvent,
    RetreatAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.calendar import day_of, day_start
from trpg.world.errors import WorldActionError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.rng import STREAM_BATTLE, draw
from trpg.world.season_board import roll_season
from trpg.world.season_boss import (
    boss_result,
    boss_schedule,
    boss_status,
    challenge,
    challenge_problem,
    gain_seal_keys,
)
from trpg.world.season_events import (
    BountyClaimedEvent,
    SeasonBossAction,
    SeasonBossChallengedEvent,
    SeasonBossClearedEvent,
)
from trpg.world.state import CharacterState, DailyActivity, ShadowSnapshot, WorldState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
DAY = 24 * 3600
HOUR = 3600
KEY = ("summit_boss",)


def _day(n: int) -> int:
    """賽季第 ``n`` 天的中午（開賽＝第 1 天中午）。"""
    return NOON + (n - 1) * DAY


def _start(library: ContentLibrary, world: WorldState, n: int) -> int:
    """賽季第 ``n`` 天的刷新時刻。"""
    return day_start(library, day_of(library, world.season_start) + n - 1)


def _ready(make_char: MakeChar, character_id: str = "alice") -> CharacterState:
    return make_char(character_id, level=10, mercenaries=PARTY, seal_key_sources=KEY)


# ---------------------------------------------------------------------------
# 封印鑰匙
# ---------------------------------------------------------------------------


def test_first_summit_kill_and_bounty_give_keys(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world, char = make_world(), make_char()
    kill = InsightGainedEvent(source="elite:sect_mist_lock_master", amount=1, insight=1)
    world, char, events = gain_seal_keys(library, world, char, [kill])
    assert char.seal_key_sources == ("summit_boss",) and world.seal_keys == 1
    assert [e.kind for e in events] == ["seal_key_gained"]
    again = gain_seal_keys(library, world, char, [kill])  # 同一來源只給一次
    assert again[0] == world and again[1] == char and again[2] == []
    claim = BountyClaimedEvent(bounty="scarface", coins=3)
    world, char, _ = gain_seal_keys(library, world, char, [claim])
    assert char.seal_key_sources == ("bounty:scarface", "summit_boss") and world.seal_keys == 2
    other = InsightGainedEvent(source="elite:mist_wolf+berserk", amount=1, insight=2)
    assert gain_seal_keys(library, world, char, [other])[2] == []


def test_seal_resonance_starts_with_world_keys(library: ContentLibrary) -> None:
    actors = tuple(f"a{i}" for i in range(8))  # 前一天 8 人上線：門檻照原值 12
    yesterday = DailyActivity(day=day_of(library, _day(6)), actors=actors)
    world = make_world(seal_keys=5, rolled_day=day_of(library, _day(6)), activity=(yesterday,))
    world, _ = roll_season(library, world, _day(7))
    state = world.world_event("seal_resonance")
    assert state is not None and state.status == "active" and state.progress == 5
    assert state.target == 12


def test_seal_resonance_full_records_time(library: ContentLibrary) -> None:
    world, _ = roll_season(library, make_world(seal_keys=30), _day(7))  # 開始時就超過門檻
    state = world.world_event("seal_resonance")
    assert state is not None and state.status == "succeeded"
    assert world.seal_full_at == _start(library, world, 7)


# ---------------------------------------------------------------------------
# 解鎖時間與狀態
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("full_day", "full_hour", "unlock_day", "unlock_hour"),
    [
        (None, 0, 10, 0),  # 沒集滿：第 10 天強制
        (5, 6, 8, 0),  # 第 5 天集滿：最早第 8 天
        (8, 6, 9, 6),  # 第 8 天中午集滿：至少 24 小時後
        (9, 6, 10, 0),  # 第 9 天中午集滿：24 小時後已超過強制日 → 強制日
    ],
)
def test_unlock_time(
    library: ContentLibrary,
    full_day: int | None,
    full_hour: int,
    unlock_day: int,
    unlock_hour: int,
) -> None:
    world = make_world()
    full = None if full_day is None else _start(library, world, full_day) + full_hour * HOUR
    world = world.model_copy(update={"seal_full_at": full})
    schedule = boss_schedule(library, world)
    assert schedule is not None
    assert schedule.unlock_at == _start(library, world, unlock_day) + unlock_hour * HOUR
    assert schedule.announce_at == schedule.unlock_at - 24 * HOUR
    assert schedule.close_at == _start(library, world, 14)
    assert schedule.early == (full_day is not None and unlock_day < 10)


def test_status_follows_the_schedule(library: ContentLibrary) -> None:
    world = make_world()
    assert boss_status(library, world, _day(8)) == "sealed"
    assert boss_status(library, world, _day(9)) == "announced"  # 第 9 天 06:00 起公告
    assert boss_status(library, world, _day(10)) == "open"
    assert boss_status(library, world, _day(13)) == "open"
    assert boss_status(library, world, _day(14)) == "closed"


# ---------------------------------------------------------------------------
# 挑戰
# ---------------------------------------------------------------------------


def test_challenge_problems(library: ContentLibrary, make_char: MakeChar) -> None:
    world, now = make_world(), _day(10)
    ready = _ready(make_char)
    assert challenge_problem(library, world, ready, now, actor="acc") is None
    assert "封印中" in (challenge_problem(library, world, ready, _day(9), actor="acc") or "")
    assert "結束" in (challenge_problem(library, world, ready, _day(14), actor="acc") or "")
    away = ready.model_copy(update={"location": "ferry_steps"})
    assert "城鎮" in (challenge_problem(library, world, away, now, actor="acc") or "")
    nokey = ready.model_copy(update={"seal_key_sources": ()})
    assert "封印鑰匙" in (challenge_problem(library, world, nokey, now, actor="acc") or "")
    shadow = ShadowSnapshot(
        owner="bob",
        hero=ready.hero,
        level=10,
        region="cloud_ridge",
        location="mist_ferry",
        saved_at=NOON,
    )
    shadowed = ready.model_copy(update={"shadows": (shadow,)})
    assert "傭兵" in (challenge_problem(library, world, shadowed, now, actor="acc") or "")


def test_three_attempts_per_account_per_day(library: ContentLibrary, make_char: MakeChar) -> None:
    world, now = make_world(), _day(10)
    alice, bob = _ready(make_char, "alice"), _ready(make_char, "bob")
    for n in range(3):  # 同帳號的兩個角色共用次數
        char = alice if n % 2 == 0 else bob
        world, char, events = challenge(library, world, char, now, actor="acc")
        (event,) = events
        assert isinstance(event, SeasonBossChallengedEvent) and event.attempts_left == 2 - n
    with pytest.raises(WorldActionError, match="用完"):
        challenge(library, world, alice, now, actor="acc")
    challenge(library, world, alice, now, actor="other")  # 別的帳號照算
    challenge(library, world, alice, _day(11), actor="acc")  # 隔天刷新
    assert world.boss_attempts_of(day_of(library, now), "acc") == 3


def test_challenge_uses_server_seed_and_boss_encounter(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world, char, now = make_world(), _ready(make_char), _day(10)
    expected = draw(world.season_seed, char, STREAM_BATTLE)[0].next_u32()
    result = world_step(library, world, char, SeasonBossAction(), now, actor="acc")
    encounter = result.char.pending_encounter
    assert encounter is not None
    assert encounter.season_boss == "rift_shard_lord" and encounter.battle_seed == expected
    assert encounter.battle_map == "rift_gate" and encounter.level == 10
    assert result.world.boss_attempts_of(day_of(library, now), "acc") == 1
    prepared = prepare_battle(library, result.char)
    assert prepared.setup.map.id == "rift_gate" and prepared.enemy_level == 10
    allies = [u for u in prepared.setup.units if u.team.value == "ally"]
    assert len(allies) == 1 + len(PARTY)  # 主角＋傭兵（只准傭兵，#87）
    assert prepared.lineup.members[0].unit == "rift_shard_lord"


def test_retreat_does_not_refund(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char, now = make_world(), _ready(make_char), _day(10)
    step = world_step(library, world, char, SeasonBossAction(), now, actor="acc")
    back = world_step(library, step.world, step.char, RetreatAction(), now + 60, actor="acc")
    assert back.char.pending_encounter is None
    assert back.world.boss_attempts_of(day_of(library, now), "acc") == 1


def test_fight_only_costs_the_attempt(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char, now = make_world(), _ready(make_char), _day(10)
    char = char.model_copy(update={"hp": 50})
    step = world_step(library, world, char, SeasonBossAction(), now, actor="acc")
    steps = auto_steps(library, step.char)
    done = world_step(
        library, step.world, step.char, FightAction(steps=steps), now + 60, actor="acc"
    )
    after = done.char
    assert after.pending_encounter is None and not after.fatigued
    assert (after.hp, after.mana, after.xp, after.gold) == (50, char.mana, char.xp, char.gold)
    assert after.location == char.location and after.bag == char.bag
    ended = next(e for e in done.events if isinstance(e, BattleEndedEvent))
    assert ended.xp_gained == 0
    kinds = {e.kind for e in done.events}
    assert kinds & {"season_boss_cleared", "season_boss_failed"}
    # 世界日誌重播：同樣的結果
    entries = [
        WorldLogEntry(seq=1, now=now, character_id="alice", action=SeasonBossAction(), actor="acc"),
        WorldLogEntry(
            seq=2, now=now + 60, character_id="alice", action=FightAction(steps=steps), actor="acc"
        ),
    ]
    replayed = replay(library, world, {"alice": char}, entries)
    assert replayed.world == done.world and replayed.characters["alice"] == after


def test_first_clear_and_score(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char = make_world(), _ready(make_char)
    world, event = boss_result(
        library, world, char, won=True, rounds=8, survivors=3, allies=3, no_down=True, now=NOON
    )
    assert isinstance(event, SeasonBossClearedEvent) and event.first
    assert event.score == 1000 - 20 * 8 + 100 * 3 + 200
    assert event.title_zh == "碎晶的終結者"
    world, second = boss_result(
        library, world, char, won=True, rounds=20, survivors=1, allies=3, no_down=False, now=NOON
    )
    assert isinstance(second, SeasonBossClearedEvent) and not second.first
    assert second.score == 1000 - 400 + 100
    assert [c.score for c in world.boss_clears] == [event.score, second.score]
    lost_world, lost = boss_result(
        library, world, char, won=False, rounds=30, survivors=0, allies=3, no_down=False, now=NOON
    )
    assert lost.kind == "season_boss_failed" and lost_world == world
