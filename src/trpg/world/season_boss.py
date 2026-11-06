"""賽季 Boss：封印鑰匙、解鎖時間、挑戰與通關（Phase 5F-3；``docs/phases/Phase5計畫.md`` 37.6）。

全部在 :func:`~trpg.world.step.world_step` 裡、依世界動作日誌的序號套用，所以「每帳號每天 3 次」
「首殺」都可以從日誌重播出相同結果。純函式：不讀時間、不呼叫 LLM；只有挑戰時從角色的 ``battle``
串流抽戰鬥種子（賽季種子衍生，伺服器保管——客戶端給不了，09 9.7）。

- **封印鑰匙**（19.6.2）：個人每個來源第一次達成給 1 把（:func:`gain_seal_keys`），同時算進全服
  鑰匙（``WorldState.seal_keys``）；世界事件效果 ``seal_keys`` 也加全服。
- **解鎖**（09 9.7）：世界事件「封印共鳴」成功的旗標第一次出現的時間記在 ``seal_full_at``
  （:func:`note_seal_full`）；解鎖時間＝``min(強制日, max(最早日, 集滿 + 公告小時))`` 之後（含）的
  第一個刷新時刻（6 點；5F-3b 對齊），公告時間＝解鎖前 ``announce_hours`` 小時，開放到 ``close_day``
  結束（:func:`boss_schedule`）。
- **挑戰**（:func:`challenge`）：在 ``entry_kinds`` 的地點、只准傭兵（#87）、個人鑰匙夠、帳號今天的
  次數還沒用完（#100）；扣 1 次並產生 Boss 的遭遇（之後照一般遭遇開戰或撤退，撤退不退次數）。
- **通關**（:func:`boss_result`，由 :func:`~trpg.world.battle.fight` 呼叫）：分數（#87）、本季第一筆
  ＝首殺（#101）；勝負都不給經驗、金錢、掉落，HP 等照開戰前（失敗只扣次數，#98）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

from trpg.content.library import ContentLibrary
from trpg.content.world_season import SeasonBossDef
from trpg.world.actions import InsightGainedEvent, WorldEvent
from trpg.world.calendar import day_of, day_start, local_time_zh, next_refresh
from trpg.world.clock import day_phase
from trpg.world.common import world_map_of
from trpg.world.errors import WorldActionError
from trpg.world.party import season_boss_problem
from trpg.world.rng import STREAM_BATTLE, draw
from trpg.world.season_events import (
    BountyClaimedEvent,
    SealKeyGainedEvent,
    SeasonBossChallengedEvent,
    SeasonBossClearedEvent,
    SeasonBossFailedEvent,
)
from trpg.world.state import BossAttempt, BossClear, CharacterState, EncounterResult, WorldState

__all__ = [
    "BOSS_WEATHER",
    "BossSchedule",
    "BossStatus",
    "boss_def",
    "boss_result",
    "boss_schedule",
    "boss_status",
    "challenge",
    "challenge_problem",
    "gain_seal_keys",
    "note_seal_full",
    "seal_keys_of",
    "status_note_zh",
]

BOSS_WEATHER: Final = "clear"
"""裂界門的天氣（Boss 地圖在界域裡，不跟區域的天氣）。"""
HOUR: Final = 3600
BOUNTY_SOURCE: Final = "bounty:"

type BossStatus = Literal["sealed", "announced", "open", "closed"]


def boss_def(library: ContentLibrary) -> SeasonBossDef | None:
    season = library.world_season
    return None if season is None else season.season_boss


# ---------------------------------------------------------------------------
# 封印鑰匙
# ---------------------------------------------------------------------------


def seal_keys_of(char: CharacterState) -> int:
    """個人的封印鑰匙數。"""
    return len(char.seal_key_sources)


def _key_sources(library: ContentLibrary, events: Sequence[WorldEvent]) -> list[tuple[str, str]]:
    """這一步達成的鑰匙來源（來源 ID、中文名；依事件順序）。"""
    season = library.world_season
    if season is None:
        return []
    found: list[tuple[str, str]] = []
    for source in season.seal_keys.sources:
        for event in events:
            if (
                source.kind == "elite_first_kill"
                and isinstance(event, InsightGainedEvent)
                and event.source == f"elite:{source.unit}"
            ):
                found.append((source.id, source.name_zh))
            elif source.kind == "bounty_claimed" and isinstance(event, BountyClaimedEvent):
                found.append((f"{BOUNTY_SOURCE}{event.bounty}", source.name_zh))
    return found


def gain_seal_keys(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Sequence[WorldEvent],
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    """這一步達成、角色還沒拿過的來源各給 1 把鑰匙（個人＋全服）。"""
    out: list[WorldEvent] = []
    owned = set(char.seal_key_sources)
    for source_id, name_zh in _key_sources(library, events):
        if source_id in owned:
            continue
        owned.add(source_id)
        world = world.model_copy(update={"seal_keys": world.seal_keys + 1})
        out.append(
            SealKeyGainedEvent(
                source=source_id, name_zh=name_zh, keys=len(owned), world_keys=world.seal_keys
            )
        )
    if not out:
        return world, char, out
    char = char.model_copy(update={"seal_key_sources": tuple(sorted(owned))})
    return world, char, out


def note_seal_full(library: ContentLibrary, world: WorldState, at: int) -> WorldState:
    """解鎖旗標第一次出現時記下時間（換日中成功＝該刷新日的刷新時刻，動作中成功＝``now``）。"""
    boss = boss_def(library)
    if boss is None or world.seal_full_at is not None or boss.unlock.flag not in world.flags:
        return world
    return world.model_copy(update={"seal_full_at": at})


# ---------------------------------------------------------------------------
# 解鎖時間
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BossSchedule:
    """賽季 Boss 的時間表（UTC 秒）：公告、解鎖、結束；``early``＝封印鑰匙集滿提早解鎖。"""

    announce_at: int
    unlock_at: int
    close_at: int
    early: bool


def _season_day_start(library: ContentLibrary, world: WorldState, day: int) -> int:
    """賽季第 ``day`` 天的刷新時刻。"""
    return day_start(library, day_of(library, world.season_start) + day - 1)


def _at_or_next_refresh(library: ContentLibrary, at: int) -> int:
    """``at`` 本身是刷新時刻（6 點）就是它，否則是之後的第一個刷新時刻（5F-3b）。"""
    return at if day_start(library, day_of(library, at)) == at else next_refresh(library, at)


def boss_schedule(library: ContentLibrary, world: WorldState) -> BossSchedule | None:
    """解鎖、公告、結束的時間（見模組說明）；沒有賽季 Boss 時 ``None``。"""
    boss = boss_def(library)
    if boss is None:
        return None
    unlock = boss.unlock
    forced_at = _season_day_start(library, world, unlock.forced_day)
    unlock_at = forced_at
    if world.seal_full_at is not None:
        earliest_at = _season_day_start(library, world, unlock.earliest_day)
        notice = world.seal_full_at + unlock.announce_hours * HOUR
        unlock_at = min(forced_at, _at_or_next_refresh(library, max(earliest_at, notice)))
    return BossSchedule(
        announce_at=unlock_at - unlock.announce_hours * HOUR,
        unlock_at=unlock_at,
        close_at=_season_day_start(library, world, unlock.close_day + 1),
        early=unlock_at < forced_at,
    )


def boss_status(library: ContentLibrary, world: WorldState, now: int) -> BossStatus | None:
    """封印中、已公告、開放、已結束；沒有賽季 Boss 時 ``None``。"""
    schedule = boss_schedule(library, world)
    if schedule is None:
        return None
    if now < schedule.announce_at:
        return "sealed"
    if now < schedule.unlock_at:
        return "announced"
    return "open" if now < schedule.close_at else "closed"


def status_note_zh(library: ContentLibrary, world: WorldState, now: int) -> str | None:
    """解鎖時間的說明（公告板與 6 點的今日公告共用）：封印中「最晚 … 解鎖（集滿可提早…）」、
    已公告「… 解鎖」、開放「開放到 …」、結束 ``None``。"""
    boss = boss_def(library)
    schedule = boss_schedule(library, world)
    status = boss_status(library, world, now)
    if boss is None or schedule is None or status is None:
        return None
    unlock_zh = local_time_zh(library, schedule.unlock_at)
    if status == "sealed":
        early = boss.unlock.earliest_day
        return f"最晚 {unlock_zh} 解鎖（封印鑰匙集滿可提早，最早第 {early} 天）"
    if status == "announced":
        return f"{unlock_zh} 解鎖"
    if status == "open":
        return f"開放到 {local_time_zh(library, schedule.close_at)}"
    return None


# ---------------------------------------------------------------------------
# 挑戰
# ---------------------------------------------------------------------------


def _status_problem(library: ContentLibrary, world: WorldState, now: int) -> str | None:
    boss = boss_def(library)
    status = boss_status(library, world, now)
    if boss is None or status is None:
        return "這一季沒有賽季頭目"
    if status in ("sealed", "announced"):
        return f"「{boss.name_zh}」還在封印中"
    if status == "closed":
        return f"本季「{boss.name_zh}」的挑戰已經結束"
    return None


def _pending_problem(char: CharacterState) -> str | None:
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if char.pending_event is not None:
        return "還有沒處理的事件"
    if char.pending_loot is not None:
        return "還有戰利品沒有決定"
    return None


def challenge_problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int, *, actor: str
) -> str | None:
    """不能挑戰的原因（繁體中文）；可以時 ``None``。"""
    problem = _status_problem(library, world, now) or _pending_problem(char)
    if problem is not None:
        return problem
    boss = boss_def(library)
    assert boss is not None
    here = world_map_of(library, char.region).location_by_id()[char.location]
    if here.kind not in boss.entry_kinds:
        return "要在城鎮才能出發挑戰賽季頭目"
    shadow = season_boss_problem(char)
    if shadow is not None:
        return shadow
    season = library.world_season
    assert season is not None
    required = season.seal_keys.required
    if seal_keys_of(char) < required:
        return f"需要至少 {required} 把封印鑰匙才能進裂界門"
    if world.boss_attempts_of(day_of(library, now), actor) >= boss.daily_attempts:
        return f"這個帳號今天的 {boss.daily_attempts} 次挑戰已經用完（每天 6 點刷新）"
    return None


def challenge(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int, *, actor: str
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """``season_boss`` 動作：扣 1 次、產生 Boss 的遭遇（見模組說明）；不能時拋
    :class:`WorldActionError`。"""
    problem = challenge_problem(library, world, char, now, actor=actor)
    if problem is not None:
        raise WorldActionError(problem)
    boss = boss_def(library)
    assert boss is not None
    today = day_of(library, now)
    count = world.boss_attempts_of(today, actor) + 1
    kept = [a for a in world.boss_attempts if a.day == today and a.actor != actor]
    kept.append(BossAttempt(day=today, actor=actor, count=count))
    kept.sort(key=lambda a: a.actor)
    world = world.model_copy(update={"boss_attempts": tuple(kept)})
    rng, char = draw(world.season_seed, char, STREAM_BATTLE)
    encounter = EncounterResult(
        region=char.region,
        location=char.location,
        level=boss.level,
        battle_map=boss.battle_map,
        battle_seed=rng.next_u32(),
        weather=BOSS_WEATHER,
        day_phase=day_phase(now),
        at=now,
        from_location=char.location,
        season_boss=boss.id,
    )
    char = char.model_copy(update={"pending_encounter": encounter})
    event = SeasonBossChallengedEvent(
        boss=boss.id, attempt=count, attempts_left=boss.daily_attempts - count
    )
    return world, char, (event,)


# ---------------------------------------------------------------------------
# 通關
# ---------------------------------------------------------------------------


def boss_result(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    *,
    won: bool,
    rounds: int,
    survivors: int,
    allies: int,
    no_down: bool,
    now: int,
) -> tuple[WorldState, WorldEvent]:
    """一場賽季 Boss 戰的結果：打贏記一筆通關（第一筆＝首殺）與分數；打輸只有事件。"""
    boss = boss_def(library)
    assert boss is not None
    if not won:
        return world, SeasonBossFailedEvent(boss=boss.id)
    score = boss.score.score(rounds=rounds, survivors=survivors, no_down=no_down)
    first = not world.boss_clears
    clear = BossClear(
        character_id=char.character_id, name=char.hero.name_zh, at=now, score=score, rounds=rounds
    )
    world = world.model_copy(update={"boss_clears": (*world.boss_clears, clear)})
    event = SeasonBossClearedEvent(
        boss=boss.id,
        name_zh=boss.name_zh,
        first=first,
        score=score,
        rounds=rounds,
        survivors=survivors,
        allies=allies,
        no_down=no_down,
        title_zh=boss.title_zh,
    )
    return world, event
