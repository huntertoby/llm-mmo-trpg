"""公告板的賽季 Boss 區塊與賽季 Boss 事件的中文句子（Phase 5F-3；``docs/phases/Phase5計畫.md``
37.7）。

全部由後端算好：封印狀態、解鎖時間、封印鑰匙進度、自己的鑰匙、帳號今天剩幾次、能不能挑戰（原因）、
首殺、評分榜。評分榜是給別人看的：出發地點照看的人套隱藏地點提示語（5C-3f）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.api.account_schemas import TitlesOf, no_titles
from trpg.api.season_schemas import BoardBossEntryView, BoardSeasonBossView
from trpg.content.library import ContentLibrary
from trpg.server.season_boss_board import BossBoardEntry
from trpg.world.actions import WorldEvent
from trpg.world.calendar import day_of
from trpg.world.narration import location_name_for
from trpg.world.opening import opening_limits
from trpg.world.season_boss import (
    boss_def,
    boss_schedule,
    boss_status,
    challenge_problem,
    seal_keys_of,
    status_note_zh,
)
from trpg.world.season_events import (
    SealKeyGainedEvent,
    SeasonBossChallengedEvent,
    SeasonBossClearedEvent,
    SeasonBossFailedEvent,
)
from trpg.world.state import CharacterState, WorldState

__all__ = ["STATUS_ZH", "season_boss_block", "season_boss_event_line"]

STATUS_ZH = {
    "sealed": "封印中",
    "announced": "即將解鎖",
    "open": "已解鎖，挑戰中",
    "closed": "本季挑戰已結束",
}


def _keys_target(world: WorldState, flag_event: str | None) -> int | None:
    if flag_event is None:
        return None
    state = world.world_event(flag_event)
    return None if state is None else state.target


def _unlock_event(library: ContentLibrary) -> str | None:
    """解鎖旗標由哪個世界事件給（封印共鳴）。"""
    season = library.world_season
    boss = boss_def(library)
    if season is None or boss is None:
        return None
    return next((e.id for e in season.world_events if boss.unlock.flag in e.on_success.flags), None)


def _entries(
    library: ContentLibrary,
    viewer: CharacterState,
    entries: Sequence[BossBoardEntry],
    titles: TitlesOf,
) -> tuple[BoardBossEntryView, ...]:
    return tuple(
        BoardBossEntryView(
            rank=index,
            name=e.name,
            score=e.score,
            rounds=e.rounds,
            survivors=e.survivors,
            allies=e.allies,
            no_down=e.no_down,
            location_zh=location_name_for(library, viewer, e.region, e.location),
            mine=e.character_id == viewer.character_id,
            at=e.at,
            titles=titles(e.character_id),
        )
        for index, e in enumerate(entries, start=1)
    )


def season_boss_block(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    actor: str,
    entries: Sequence[BossBoardEntry] = (),
    titles: TitlesOf = no_titles,
) -> BoardSeasonBossView | None:
    """``char``（帳號 ``actor``）看到的賽季 Boss 區塊；沒有賽季 Boss 時 ``None``。``titles``：
    評分榜與首殺玩家的帳號稱號（5F-3c）。"""
    boss = boss_def(library)
    schedule = boss_schedule(library, world)
    status = boss_status(library, world, now)
    season = library.world_season
    if boss is None or schedule is None or status is None or season is None:
        return None
    note = status_note_zh(library, world, now)
    problem = challenge_problem(library, world, char, now, actor=actor)
    problem = opening_limits(char).get("season_boss") or problem  # OB-5：入門期不開放
    used = world.boss_attempts_of(day_of(library, now), actor)
    first = world.boss_clears[0] if world.boss_clears else None
    return BoardSeasonBossView(
        boss=boss.id,
        name_zh=boss.name_zh,
        status=status,
        status_zh=STATUS_ZH[status],
        note_zh=note,
        announce_at=schedule.announce_at,
        unlock_at=schedule.unlock_at,
        close_at=schedule.close_at,
        world_keys=world.seal_keys,
        keys_target=_keys_target(world, _unlock_event(library)),
        my_keys=seal_keys_of(char),
        keys_required=season.seal_keys.required,
        attempts_left=max(0, boss.daily_attempts - used),
        daily_attempts=boss.daily_attempts,
        can_challenge=problem is None,
        problem_zh=problem,
        first_kill_zh=None if first is None else f"本季首殺：{first.name}（{first.rounds} 輪）",
        first_kill_titles=() if first is None else titles(first.character_id),
        title_zh=boss.title_zh,
        board=_entries(library, char, entries, titles),
    )


def season_boss_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """封印鑰匙、挑戰、通關的句子。"""
    boss = boss_def(library)
    name = "賽季頭目" if boss is None else f"「{boss.name_zh}」"
    match event:
        case SealKeyGainedEvent():
            return (
                f"得到 1 把封印鑰匙（{event.name_zh}）：你有 {event.keys} 把、"
                f"全服共 {event.world_keys} 把。"
            )
        case SeasonBossChallengedEvent():
            left = event.attempts_left
            return f"踏進裂界門挑戰{name}（今天第 {event.attempt} 次，還剩 {left} 次）。"
        case SeasonBossClearedEvent():
            head = "本季首殺！" if event.first else ""
            down = "、沒有人倒下" if event.no_down else ""
            return (
                f"{head}打倒了{name}：{event.rounds} 輪、存活 {event.survivors}／{event.allies}"
                f"{down}，評分 {event.score}；得到稱號「{event.title_zh}」。"
            )
        case SeasonBossFailedEvent():
            return f"挑戰{name}失敗（只扣這次的挑戰次數）。"
        case _:
            return None
