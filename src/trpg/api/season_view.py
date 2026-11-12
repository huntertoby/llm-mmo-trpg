"""城鎮公告板的畫面資料與賽季事件的中文句子（Phase 5F-1；``docs/phases/Phase5計畫.md`` 35.7）。

公告板用「換日後」的世界算（:meth:`~trpg.api.world.WorldStore.season_world`，只算不寫檔）；地點名
照看的人套隱藏地點的提示語（5C-3f）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.api.account_schemas import TitlesOf, no_titles
from trpg.api.season_boss_view import season_boss_block
from trpg.api.season_schemas import (
    BoardBountyView,
    BoardClearedView,
    BoardGoalView,
    BoardMilestoneView,
    BoardPhaseView,
    BoardWorldEventView,
    MilestoneKind,
    SeasonBoardView,
    SeasonInfoView,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_season import Milestone, SchedulePhase
from trpg.server.announce import region_name
from trpg.server.season_boss_board import BossBoardEntry
from trpg.world.actions import WorldEvent
from trpg.world.calendar import (
    calendar_of,
    day_of,
    next_refresh,
    season_day,
    season_status,
)
from trpg.world.economy import shop_price_zh
from trpg.world.narration import location_name_for
from trpg.world.season_board import daily_goals_for, players_on, posted_bounties
from trpg.world.season_events import (
    BountyClaimedEvent,
    BountyMissedEvent,
    DailyGoalDoneEvent,
    WorldEventProgressEvent,
    WorldEventResolvedEvent,
)
from trpg.world.state import CharacterState, WorldState

__all__ = ["season_board", "season_event_line"]

_STATUS_ZH = {"upcoming": "開賽前", "ended": "本季已結束"}
_EVENT_STATUS_ZH = {
    "pending": "尚未開始",
    "active": "進行中",
    "succeeded": "成功",
    "failed": "失敗",
}


_KIND_PREFIX: tuple[tuple[str, MilestoneKind], ...] = (
    ("story_skill", "story_skill"),
    ("boss", "boss_unlock"),
    ("league", "league"),
)
_STORY_SKILL_ZH = "劇情技能"


def milestone_kinds(milestone: Milestone) -> tuple[MilestoneKind, ...]:
    """時間點的種類（PNL-1b；時間軸釘的圖示）。``season.yaml`` 的時間點沒有種類欄位
    （內容檔不在本段），依 ID 前綴判斷（``story_skill*``＝劇情技能、``boss*``＝頭目解鎖、
    ``league*``＝循環賽，其他＝other）；名稱另寫到劇情技能的（第 10 天「頭目強制解鎖；
    主線第 3 章的劇情技能」）再加一個劇情技能。"""
    kinds: list[MilestoneKind] = [
        next((k for p, k in _KIND_PREFIX if milestone.id.startswith(p)), "other")
    ]
    if _STORY_SKILL_ZH in milestone.name_zh and "story_skill" not in kinds:
        kinds.append("story_skill")
    return tuple(kinds)


def _milestone_view(milestone: Milestone) -> BoardMilestoneView:
    kinds = milestone_kinds(milestone)
    return BoardMilestoneView(
        day=milestone.day, name_zh=milestone.name_zh, id=milestone.id, kind=kinds[0], kinds=kinds
    )


def _phase_view(phase: SchedulePhase) -> BoardPhaseView:
    return BoardPhaseView(
        id=phase.id,
        name_zh=phase.name_zh,
        text_zh=phase.text_zh,
        start_day=phase.days[0],
        end_day=phase.days[1],
    )


def _season_info(library: ContentLibrary, world: WorldState, now: int) -> SeasonInfoView:
    season = library.world_season
    days = 0 if season is None else season.days
    day = season_day(library, world, now)
    status = season_status(library, world, now)
    phase = None if season is None else season.phase_on(day)
    phase_zh = None
    if phase is not None and status == "running":
        phase_zh = f"{phase.name_zh}：{phase.text_zh}" if phase.text_zh else phase.name_zh
    milestones = () if season is None else tuple(sorted(season.milestones, key=lambda m: m.day))
    cal = calendar_of(library)
    return SeasonInfoView(
        day=day,
        days=days,
        status=status,
        status_zh=_STATUS_ZH.get(status, f"賽季第 {day} 天／共 {days} 天"),
        phase_zh=phase_zh,
        phase=_phase_view(phase) if phase is not None and status == "running" else None,
        phases=() if season is None else tuple(_phase_view(p) for p in season.schedule),
        upcoming=tuple(_milestone_view(m) for m in milestones if m.day >= day),
        milestones=tuple(_milestone_view(m) for m in milestones),
        next_refresh_at=next_refresh(library, now),
        next_refresh_zh=f"每天 {cal.refresh_hour:02d}:00 刷新",
        refresh_time_zh=f"{cal.refresh_hour:02d}:00",
    )


def _goals(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[tuple[BoardGoalView, ...], str | None]:
    season = library.world_season
    rules = None if season is None else season.daily_goals
    if rules is None:
        return (), None
    today = day_of(library, now)
    progress = char.daily_goals if char.daily_goals and char.daily_goals.day == today else None
    views = tuple(
        BoardGoalView(
            goal=g.id,
            text_zh=g.text_zh,
            progress=0 if progress is None else progress.progress.get(g.id, 0),
            count=g.goal.count,
            done=progress is not None and g.id in progress.done,
            coins=rules.coins,
        )
        for g in daily_goals_for(library, world, today)
    )
    newbie = season_day(library, world, now) <= rules.newbie_days
    return views, "新手期：教學目標" if newbie else None


def _bounties(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[BoardBountyView, ...]:
    views: list[BoardBountyView] = []
    today = day_of(library, now)
    for posted in posted_bounties(library, world, now):
        bounty, claim = posted.bounty, posted.claim
        note = None
        if claim is None:
            status = "懸賞中"
        elif claim.character_id == char.character_id:
            status = "你搶下了"
        else:
            status = f"已被 {claim.name} 搶下"
            if bounty.consolation_coins and char.bounty_days.get(bounty.id) != today:
                note = f"今天第一次交手打倒仍有小獎：任務幣 {bounty.consolation_coins}"
        views.append(
            BoardBountyView(
                bounty=bounty.id,
                name_zh=bounty.name_zh,
                location_zh=location_name_for(library, char, bounty.region, bounty.location),
                level=bounty.level,
                coins=bounty.coins,
                open=claim is None,
                claimed_by=None if claim is None else claim.name,
                status_zh=status,
                status_note_zh=note,
            )
        )
    return tuple(views)


def _world_events(
    library: ContentLibrary, world: WorldState, now: int
) -> tuple[BoardWorldEventView, ...]:
    season = library.world_season
    if season is None:
        return ()
    views: list[BoardWorldEventView] = []
    for event in season.world_events:
        state = world.world_event(event.id)
        target = event.goal.count if state is None else state.target
        progress = 0 if state is None else state.progress
        note = None
        if state is not None and state.adjustments:
            last = state.adjustments[-1]
            note = (
                "沒有前一天的上線紀錄，用原門檻"
                if last.players is None
                else f"依前一天 {last.players} 位冒險者調整"
            )
        status = "pending" if state is None else state.status
        views.append(
            BoardWorldEventView(
                event=event.id,
                name_zh=event.name_zh,
                text_zh=event.text_zh,
                status=status,
                status_zh=_EVENT_STATUS_ZH[status],
                progress=progress,
                target=target,
                permille=min(1000, progress * 1000 // max(1, target)),
                days_zh=f"第 {event.days[0]}～{event.days[1]} 天",
                start_day=event.days[0],
                end_day=event.days[1],
                region=event.goal.region,
                target_note_zh=note,
            )
        )
    return tuple(views)


def season_board(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    actor: str | None = None,
    boss_board: Sequence[BossBoardEntry] = (),
    titles: TitlesOf = no_titles,
) -> SeasonBoardView:
    """``char`` 看到的公告板（``world`` 是換日後的世界）。``actor`` 是看的人的帳號（賽季 Boss 的
    剩餘次數，5F-3；``None``＝角色 ID）；``boss_board`` 是這一季的評分榜。"""
    goals, goals_note = _goals(library, world, char, now)
    cleared = tuple(
        BoardClearedView(
            location_zh=location_name_for(library, char, c.region, c.location),
            respawn_at=c.respawn_at,
        )
        for c in world.cleared
        if now < c.respawn_at
    )
    bonus = tuple(
        f"{region_name(library, region)}：建議等級 +{amount}"
        for region, amount in world.level_bonus.items()
    ) + tuple(shop_price_zh(library, shop, p) for shop, p in world.shop_price.items())
    return SeasonBoardView(
        season=_season_info(library, world, now),
        goals=goals,
        goals_note_zh=goals_note,
        bounties=_bounties(library, world, char, now),
        world_events=_world_events(library, world, now),
        cleared=cleared,
        level_bonus_zh=bonus,
        season_boss=season_boss_block(
            library,
            world,
            char,
            now,
            actor=char.character_id if actor is None else actor,
            entries=boss_board,
            titles=titles,
        ),
    )


def active_yesterday(library: ContentLibrary, world: WorldState, now: int) -> int:
    """昨天有動作的帳號數（世界狀態的上線紀錄）。"""
    return players_on(world, day_of(library, now) - 1)


def season_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """懸賞、世界事件進度、今日目標的句子。"""
    season = library.world_season
    if season is None:
        return None
    bounties = season.bounty_by_id()
    events = season.event_by_id()
    goals = {} if season.daily_goals is None else season.daily_goals.goal_by_id()
    line: str | None = None
    match event:
        case BountyClaimedEvent():
            name = bounties[event.bounty].name_zh if event.bounty in bounties else event.bounty
            extra = f"、多得 {event.xp} 經驗" if event.xp else ""
            line = f"搶下懸賞「{name}」（任務幣 +{event.coins}{extra}）！"
        case BountyMissedEvent():
            name = bounties[event.bounty].name_zh if event.bounty in bounties else event.bounty
            small = f"拿到小獎（任務幣 +{event.coins}）" if event.coins else "沒有懸賞獎勵"
            line = f"懸賞「{name}」今天已經被 {event.claimed_by} 搶先了，{small}。"
        case WorldEventProgressEvent():
            name = events[event.event].name_zh if event.event in events else event.event
            line = f"世界事件「{name}」進度 +{event.added}（{event.progress}／{event.target}）。"
        case WorldEventResolvedEvent():
            name = events[event.event].name_zh if event.event in events else event.event
            result = "成功" if event.outcome == "succeeded" else "失敗"
            line = f"世界事件「{name}」{result}！"
        case DailyGoalDoneEvent():
            text = goals[event.goal].text_zh if event.goal in goals else event.goal
            line = f"完成今日目標「{text}」（任務幣 +{event.coins}）。"
        case _:
            pass
    return line
