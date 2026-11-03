"""賽季日程：換日、世界事件、懸賞板、今日目標（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.6）。

全部在 :func:`~trpg.world.step.world_step` 裡、依世界動作日誌的序號套用（單一寫入佇列，2.4），所以
「先搶先贏」、全服進度與門檻調整都可以從日誌重播出相同結果。純函式：不讀時間、不呼叫 LLM、不取用
亂數串流（今日目標的抽選用 ``fnv1a64`` 從賽季種子衍生）。

- **換日**（:func:`roll_season`，每個動作之前）：從上次處理到的刷新日補到今天；每天依序 ① 結束日
  已過、還沒成功的世界事件判失敗並套 ``on_failure``；② 當天開始的世界事件建立；③ 進行中的世界
  事件依前一天的上線帳號數重算門檻（Q14），記下調整；門檻降到進度以下就成功。
- **上線紀錄**：每個成功的動作之後把 ``actor``（帳號 ID；沒有帳號時用角色 ID，Q15）記進今天的
  ``activity``，只留今天與昨天。
- **懸賞**（09 9.7「先搶先贏」、9.6.3「先打倒的人拿大獎，其他人拿小獎」）：每天貼出 ``from_day``
  起的全部懸賞；每個角色每天在該地點的**第一場**遭遇是懸賞陣容，之後照一般遭遇（:func:`open_bounty_at`，
  由 ``make_encounter`` 記進遭遇；開戰時記進 ``CharacterState.bounty_days``，5F-1b）。打贏懸賞陣容時
  當天還沒被搶 → 記下、給任務幣、經驗補到懸賞份數（大獎）；已被搶 → ``bounty_missed``＋小獎任務幣。
- **世界事件進度**：每一步的事件符合目標就累加；達到門檻立刻成功並套 ``on_success``。
- **今日目標**（#99）：第 1～``newbie_days`` 天用固定的教學目標，之後每天從清單確定性抽；角色
  進度跨日歸零，完成一條給任務幣。
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.world_season import (
    BountyDef,
    DailyGoalDef,
    GoalSpec,
    SeasonContent,
    WorldEventDef,
    WorldEventEffect,
)
from trpg.shared.rng import Rng, fnv1a64
from trpg.world.actions import (
    BattleEndedEvent,
    BattleStartedEvent,
    CampedEvent,
    LocationRevealedEvent,
    QuestStepDoneEvent,
    SituationResultEvent,
    TalkedEvent,
    WorldEvent,
)
from trpg.world.calendar import day_of, day_start, season_day
from trpg.world.common import rules_of, world_map_of
from trpg.world.economy_actions import CurrencyGainedEvent
from trpg.world.encounters import elite_kinds
from trpg.world.growth import gain_xp
from trpg.world.season_events import (
    BountyClaimedEvent,
    BountyMissedEvent,
    DailyGoalDoneEvent,
    WorldEventProgressEvent,
    WorldEventResolvedEvent,
    WorldEventStartedEvent,
    WorldEventTargetEvent,
)
from trpg.world.state import (
    BountyClaim,
    CharacterState,
    DailyActivity,
    DailyGoalProgress,
    TargetAdjustment,
    WorldEventState,
    WorldState,
)

__all__ = [
    "PostedBounty",
    "after_season_step",
    "daily_goals_for",
    "open_bounty_at",
    "players_on",
    "posted_bounties",
    "record_activity",
    "roll_season",
]


# ---------------------------------------------------------------------------
# 換日與世界事件
# ---------------------------------------------------------------------------


def players_on(world: WorldState, day: int) -> int:
    """刷新日 ``day`` 有成功世界動作的帳號數（沒有紀錄＝0）。"""
    found = next((a for a in world.activity if a.day == day), None)
    return 0 if found is None else len(found.actors)


def _with_event(world: WorldState, state: WorldEventState) -> WorldState:
    kept = [e for e in world.world_events if e.id != state.id]
    kept.append(state)
    kept.sort(key=lambda e: e.id)
    return world.model_copy(update={"world_events": tuple(kept)})


def _apply_effect(world: WorldState, effect: WorldEventEffect) -> WorldState:
    flags = tuple(sorted({*world.flags, *effect.flags}))
    bonus = dict(world.level_bonus)
    for row in effect.level_bonus:
        bonus[row.region] = bonus.get(row.region, 0) + row.amount
    return world.model_copy(update={"flags": flags, "level_bonus": bonus})


def _resolve(
    world: WorldState,
    event: WorldEventDef,
    state: WorldEventState,
    day: int,
    at: int,
    *,
    success: bool,
) -> tuple[WorldState, WorldEvent]:
    effect = event.on_success if success else event.on_failure
    outcome: Literal["succeeded", "failed"] = "succeeded" if success else "failed"
    update = {"status": outcome, "resolved_day": day, "resolved_at": at}
    state = state.model_copy(update=update)
    world = _apply_effect(_with_event(world, state), effect)
    resolved = WorldEventResolvedEvent(
        event=event.id,
        outcome=outcome,
        progress=state.progress,
        target=state.target,
        flags=effect.flags,
        level_bonus={b.region: b.amount for b in effect.level_bonus},
    )
    return world, resolved


def _roll_day(
    season: SeasonContent, world: WorldState, day: int, start_day: int, at: int
) -> tuple[WorldState, list[WorldEvent]]:
    """刷新日 ``day``（賽季第 ``day − start_day + 1`` 天，從 UTC 秒 ``at`` 開始）的換日。"""
    sday = day - start_day + 1
    players = None if sday <= 1 else (players_on(world, day - 1) or None)  # 沒有紀錄＝None
    events: list[WorldEvent] = []
    for event in season.world_events:
        state = world.world_event(event.id)
        if state is not None and state.status == "active" and event.days[1] < sday:
            world, resolved = _resolve(world, event, state, day, at, success=False)
            events.append(resolved)
            continue
        if not event.days[0] <= sday <= event.days[1]:
            continue
        target = event.target_for(players)
        if state is None:
            adjustment = TargetAdjustment(day=day, players=players, target=target)
            state = WorldEventState(id=event.id, target=target, adjustments=(adjustment,))
            world = _with_event(world, state)
            events.append(WorldEventStartedEvent(event=event.id, day=day, target=target))
        elif state.status == "active" and target != state.target:
            adjustment = TargetAdjustment(day=day, players=players, target=target)
            state = state.model_copy(
                update={"target": target, "adjustments": (*state.adjustments, adjustment)}
            )
            world = _with_event(world, state)
            events.append(
                WorldEventTargetEvent(event=event.id, day=day, players=players, target=target)
            )
        if state.status == "active" and state.progress >= state.target:
            world, resolved = _resolve(world, event, state, day, at, success=True)
            events.append(resolved)
    return world, events


def roll_season(
    library: ContentLibrary, world: WorldState, now: int
) -> tuple[WorldState, tuple[WorldEvent, ...]]:
    """從上次處理到的刷新日補到今天（見模組說明）；沒有賽季資料或還沒開賽時不變。"""
    season = library.world_season
    if season is None:
        return world, ()
    today = day_of(library, now)
    start_day = day_of(library, world.season_start)
    first = start_day if world.rolled_day is None else world.rolled_day + 1
    if first > today:
        return world, ()
    last = min(today, start_day + season.days)  # 季末之後沒有要處理的（多處理結束隔天的失敗）
    events: list[WorldEvent] = []
    for day in range(first, last + 1):
        world, more = _roll_day(season, world, day, start_day, day_start(library, day))
        events += more
    return world.model_copy(update={"rolled_day": today}), tuple(events)


def record_activity(world: WorldState, actor: str, today: int) -> WorldState:
    """把 ``actor`` 記進今天的上線紀錄（只留今天與昨天；已在就不變）。"""
    rows = {a.day: a for a in world.activity if a.day >= today - 1}
    row = rows.get(today)
    if row is not None and actor in row.actors and len(rows) == len(world.activity):
        return world
    actors = () if row is None else row.actors
    rows[today] = DailyActivity(day=today, actors=tuple(sorted({*actors, actor})))
    return world.model_copy(update={"activity": tuple(rows[d] for d in sorted(rows))})


# ---------------------------------------------------------------------------
# 目標的判定（今日目標與世界事件共用）
# ---------------------------------------------------------------------------


def _battles(events: Sequence[WorldEvent]) -> Iterator[BattleStartedEvent]:
    """這一步打贏的戰鬥（``battle_started`` 後面接 ``battle_ended`` 且勝利）。"""
    started: BattleStartedEvent | None = None
    for event in events:
        if isinstance(event, BattleStartedEvent):
            started = event
        elif isinstance(event, BattleEndedEvent):
            if event.won and started is not None:
                yield started
            started = None


def _quest_kind(library: ContentLibrary, quest: str) -> str | None:
    for table in library.world_quests.quests.values():
        found = table.quest_by_id().get(quest)
        if found is not None:
            return found.kind
    return None


def _battle_matches(library: ContentLibrary, goal: GoalSpec, battle: BattleStartedEvent) -> bool:
    if goal.region is not None and battle.region != goal.region:
        return False
    if goal.weather and battle.weather not in goal.weather:
        return False
    if goal.elite and not elite_kinds(library, battle.lineup):
        return False
    if goal.location_kinds:
        place = world_map_of(library, battle.region).location_by_id().get(battle.location)
        if place is None or place.kind not in goal.location_kinds:
            return False
    return True


def _quest_matches(library: ContentLibrary, goal: GoalSpec, event: QuestStepDoneEvent) -> bool:
    if goal.quest is not None and event.quest != goal.quest:
        return False
    return goal.quest_kind is None or _quest_kind(library, event.quest) == goal.quest_kind


def goal_count(library: ContentLibrary, goal: GoalSpec, events: Sequence[WorldEvent]) -> int:
    """這一步的事件裡符合 ``goal`` 的次數。"""
    if goal.kind == "battle_won":
        return sum(1 for b in _battles(events) if _battle_matches(library, goal, b))
    count = 0
    for event in events:
        match event:
            case QuestStepDoneEvent() if goal.kind == "quest_step":
                count += _quest_matches(library, goal, event)
            case LocationRevealedEvent() if goal.kind == "location_revealed":
                count += 1
            case SituationResultEvent() if goal.kind == "situation_success":
                count += event.outcome == "success"
            case TalkedEvent() if goal.kind == "talked":
                count += 1
            case CampedEvent() if goal.kind == "camped":
                count += 1
            case BountyClaimedEvent() if goal.kind == "bounty_claimed":
                count += 1
            case _:
                pass
    return count


def _advance_events(
    library: ContentLibrary,
    season: SeasonContent,
    world: WorldState,
    events: Sequence[WorldEvent],
    now: int,
) -> tuple[WorldState, list[WorldEvent]]:
    """世界事件的全服進度（只算進行中的）。"""
    out: list[WorldEvent] = []
    today = day_of(library, now)
    for event in season.world_events:
        state = world.world_event(event.id)
        if state is None or state.status != "active":
            continue
        added = goal_count(library, event.goal, events)
        if added <= 0:
            continue
        state = state.model_copy(update={"progress": state.progress + added})
        world = _with_event(world, state)
        out.append(
            WorldEventProgressEvent(
                event=event.id, added=added, progress=state.progress, target=state.target
            )
        )
        if state.progress >= state.target:
            world, resolved = _resolve(world, event, state, today, now, success=True)
            out.append(resolved)
    return world, out


# ---------------------------------------------------------------------------
# 懸賞板
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PostedBounty:
    """今天貼出的一張懸賞；``claim`` 不是 ``None``＝已被搶下。"""

    bounty: BountyDef
    claim: BountyClaim | None


def posted_bounties(
    library: ContentLibrary, world: WorldState, now: int
) -> tuple[PostedBounty, ...]:
    """今天貼出的懸賞（依內容順序）；賽季結束後不再貼。"""
    season = library.world_season
    if season is None:
        return ()
    sday = season_day(library, world, now)
    if sday > season.days:
        return ()
    today = day_of(library, now)
    return tuple(
        PostedBounty(bounty=b, claim=world.claim_of(today, b.id))
        for b in season.bounties
        if b.from_day <= sday
    )


def open_bounty_at(
    library: ContentLibrary, world: WorldState, char: CharacterState, location: str, now: int
) -> str | None:
    """``char`` 所在區域的 ``location`` 今天貼出、``char`` 今天還沒打過的懸賞 ID（已被別人搶下也
    照樣遇到，打倒拿小獎；5F-1b）。"""
    region = char.region
    today = day_of(library, now)
    for posted in posted_bounties(library, world, now):
        bounty = posted.bounty
        if (bounty.region, bounty.location) != (region, location):
            continue
        if char.bounty_days.get(bounty.id) != today:
            return bounty.id
    return None


def _mark_bounty_fights(
    library: ContentLibrary, char: CharacterState, events: Sequence[WorldEvent], now: int
) -> CharacterState:
    """這一步開打的懸賞陣容記進 ``bounty_days``（今天在該地點的第一場已用掉）。"""
    fought = {
        e.lineup.bounty
        for e in events
        if isinstance(e, BattleStartedEvent) and e.lineup.bounty is not None
    }
    if not fought:
        return char
    today = day_of(library, now)
    days = {**char.bounty_days, **dict.fromkeys(sorted(fought), today)}
    return char.model_copy(update={"bounty_days": days})


def _won_bounties(events: Sequence[WorldEvent]) -> Iterator[tuple[str, BattleStartedEvent, int]]:
    started: BattleStartedEvent | None = None
    for event in events:
        if isinstance(event, BattleStartedEvent):
            started = event
        elif isinstance(event, BattleEndedEvent):
            if event.won and started is not None and started.lineup.bounty is not None:
                yield started.lineup.bounty, started, event.xp_gained
            started = None


def _claim_bounties(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Sequence[WorldEvent],
    now: int,
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    season = library.world_season
    if season is None:
        return world, char, []
    out: list[WorldEvent] = []
    today = day_of(library, now)
    bounties = season.bounty_by_id()
    for bounty_id, started, xp_gained in _won_bounties(events):
        bounty = bounties.get(bounty_id)
        if bounty is None:
            continue
        claim = world.claim_of(today, bounty_id)
        if claim is not None:  # 小獎（9.6.3）
            small = bounty.consolation_coins
            out.append(BountyMissedEvent(bounty=bounty_id, claimed_by=claim.name, coins=small))
            if small > 0:
                char, coins = _coins(char, small, f"bounty_consolation:{bounty_id}")
                out.append(coins)
            continue
        record = BountyClaim(
            day=today,
            bounty=bounty_id,
            character_id=char.character_id,
            name=char.hero.name_zh,
            at=now,
        )
        claims = sorted((*world.bounty_claims, record), key=lambda c: (c.day, c.bounty))
        world = world.model_copy(update={"bounty_claims": tuple(claims)})
        bounty_xp = rules_of(library).xp.xp_for("bounty", started.enemy_level)
        extra_xp = max(0, bounty_xp - xp_gained)
        out.append(BountyClaimedEvent(bounty=bounty_id, coins=bounty.coins, xp=extra_xp))
        if extra_xp > 0:
            char, leveled = gain_xp(library, world, char, extra_xp)
            out += leveled
        if bounty.coins > 0:
            char, coins = _coins(char, bounty.coins, f"bounty:{bounty_id}")
            out.append(coins)
    return world, char, out


def _coins(char: CharacterState, amount: int, source: str) -> tuple[CharacterState, WorldEvent]:
    char = char.model_copy(update={"quest_coins": char.quest_coins + amount})
    event = CurrencyGainedEvent(
        currency="quest_coins", amount=amount, total=char.quest_coins, source=source
    )
    return char, event


# ---------------------------------------------------------------------------
# 今日目標
# ---------------------------------------------------------------------------


def daily_goals_for(
    library: ContentLibrary, world: WorldState, day: int
) -> tuple[DailyGoalDef, ...]:
    """刷新日 ``day`` 的今日目標（全服同一組，代決 5F1-3）。"""
    season = library.world_season
    rules = None if season is None else season.daily_goals
    if rules is None:
        return ()
    by_id = rules.goal_by_id()
    sday = day - day_of(library, world.season_start) + 1
    if sday <= rules.newbie_days:
        return tuple(by_id[g] for g in rules.newbie)
    rng = Rng(fnv1a64(f"{world.season_seed}:daily_goals:{day}".encode()))
    pool = sorted(rules.goals, key=lambda g: g.id)
    return tuple(rng.shuffled(pool)[: rules.count])


def _advance_goals(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Sequence[WorldEvent],
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    season = library.world_season
    rules = None if season is None else season.daily_goals
    if rules is None:
        return char, []
    today = day_of(library, now)
    progress = char.daily_goals
    if progress is None or progress.day != today:
        progress = DailyGoalProgress(day=today)
    counts = dict(progress.progress)
    done = set(progress.done)
    out: list[WorldEvent] = []
    for goal in daily_goals_for(library, world, today):
        if goal.id in done:
            continue
        added = goal_count(library, goal.goal, events)
        if added <= 0:
            continue
        counts[goal.id] = min(goal.goal.count, counts.get(goal.id, 0) + added)
        if counts[goal.id] >= goal.goal.count:
            done.add(goal.id)
            out.append(DailyGoalDoneEvent(goal=goal.id, coins=rules.coins))
            if rules.coins > 0:
                char, coins = _coins(char, rules.coins, f"daily_goal:{goal.id}")
                out.append(coins)
    if counts == progress.progress:
        return char, out  # 沒有前進：不動角色（跨日的歸零等到第一次前進時再寫）
    updated = DailyGoalProgress(day=today, progress=counts, done=tuple(sorted(done)))
    return char.model_copy(update={"daily_goals": updated}), out


# ---------------------------------------------------------------------------
# 入口（動作之後）
# ---------------------------------------------------------------------------


def after_season_step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Sequence[WorldEvent],
    *,
    now: int,
    actor: str,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """動作之後：懸賞搶先、世界事件進度、今日目標、上線紀錄（依序；見模組說明）。"""
    season = library.world_season
    if season is None:
        return world, char, ()
    char = _mark_bounty_fights(library, char, events, now)
    world, char, claimed = _claim_bounties(library, world, char, events, now)
    seen = (*events, *claimed)
    world, progressed = _advance_events(library, season, world, seen, now)
    char, goals = _advance_goals(library, world, char, seen, now)
    world = record_activity(world, actor, day_of(library, now))
    return world, char, (*claimed, *progressed, *goals)
