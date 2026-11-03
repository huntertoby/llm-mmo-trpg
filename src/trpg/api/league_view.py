"""影子循環賽的畫面資料與事件句子（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.7）。

排行榜是給別人看的：報名地點照看的人套隱藏地點的提示語（5C-3f，
:func:`~trpg.world.narration.location_name_for`）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.api.league_schemas import (
    LeagueEntryView,
    LeagueMatchView,
    LeagueStandingView,
    LeagueStatus,
    LeagueView,
)
from trpg.api.world_party_view import ai_choice_views, ai_zh, shadow_role_zh
from trpg.content.library import ContentLibrary
from trpg.server.league import LeagueMatch, LeagueRecord, LeagueStanding, standings
from trpg.world.actions import WorldEvent
from trpg.world.calendar import season_day
from trpg.world.common import rules_of
from trpg.world.league import league_rules, matches_per_pair, signup_problem
from trpg.world.league_actions import LeagueEnteredEvent, LeagueWithdrawnEvent
from trpg.world.narration import location_name_for
from trpg.world.state import CharacterState, LeagueEntry, WorldState

__all__ = ["league_event_line", "league_view", "match_title"]

_STATUS_ZH: dict[LeagueStatus, str] = {
    "none": "這一季沒有影子循環賽",
    "signup": "報名中",
    "closed": "報名已截止，等待開賽",
    "running": "比賽進行中",
    "done": "比賽已結束",
}


def _map_name(library: ContentLibrary, map_id: str) -> str:
    found = library.maps.get(map_id)
    return map_id if found is None else found.name_zh


def _status(
    library: ContentLibrary,
    world: WorldState,
    record: LeagueRecord | None,
    now: int,
    *,
    running: bool,
) -> LeagueStatus:
    rules = league_rules(library)
    if rules is None:
        return "none"
    if record is not None:
        pending = any(m.status == "pending" for m in record.matches)
        return "running" if pending or running else "done"
    if season_day(library, world, now) <= rules.signup_close_day:
        return "signup"
    return "closed"


def _enter_problem(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    account: str,
    now: int,
) -> str | None:
    problem = signup_problem(library, world, char, now)
    if problem is not None:
        return problem
    mine = next((e for e in world.league_entries if e.account == account), None)
    if mine is not None and mine.character_id != char.character_id:
        return f"這個帳號已經用「{mine.name}」報名了，先取消報名"
    return None


def _standing_rows(
    library: ContentLibrary,
    viewer: CharacterState,
    entries: Sequence[LeagueEntry],
    table: Sequence[LeagueStanding] | None,
    account: str,
) -> tuple[LeagueStandingView, ...]:
    by_account = {e.account: e for e in entries}
    cap = rules_of(library).hero_growth.level_cap
    rows: list[LeagueStandingView] = []
    order: Sequence[LeagueStanding | None] = table if table is not None else [None] * len(entries)
    accounts = [r.account for r in table] if table is not None else [e.account for e in entries]
    for acc, standing in zip(accounts, order, strict=True):
        entry = by_account[acc]
        snap = entry.snapshot
        rows.append(
            LeagueStandingView(
                rank=None if standing is None else standing.rank,
                name=entry.name,
                level=max(cap, snap.level),
                role_zh=shadow_role_zh(library, snap),
                place_zh=location_name_for(library, viewer, snap.region, snap.location),
                wins=0 if standing is None else standing.wins,
                losses=0 if standing is None else standing.losses,
                draws=0 if standing is None else standing.draws,
                played=0 if standing is None else standing.played,
                mine=acc == account,
            )
        )
    return tuple(rows)


def _result_zh(match: LeagueMatch, names: dict[str, str]) -> str:
    if match.status == "pending":
        return "尚未進行"
    if match.status == "error":
        return f"出錯：{match.error or '未知的錯誤'}"
    if match.winner is None:
        return f"和局（{match.rounds} 輪）"
    return f"{names.get(match.winner, match.winner)}勝（{match.rounds} 輪）"


def match_title(library: ContentLibrary, record: LeagueRecord, match: LeagueMatch) -> str:
    """重播畫面的標題，例「m0003：阿霧（先手） vs 小美・開闊平原・種子 1」。"""
    names = {e.account: e.name for e in record.entries}
    ally = names.get(match.ally, match.ally)
    enemy = names.get(match.enemy, match.enemy)
    where = _map_name(library, match.map)
    return f"{match.id}：{ally}（先手） vs {enemy}・{where}・種子 {match.seed_index + 1}"


def _match_rows(
    library: ContentLibrary, record: LeagueRecord, account: str
) -> tuple[LeagueMatchView, ...]:
    names = {e.account: e.name for e in record.entries}
    rows = [
        LeagueMatchView(
            id=m.id,
            ally_name=names.get(m.ally, m.ally),
            enemy_name=names.get(m.enemy, m.enemy),
            map_zh=_map_name(library, m.map),
            seed_index=m.seed_index,
            status=m.status,
            result_zh=_result_zh(m, names),
            mine=account in (m.a, m.b),
            replayable=m.status == "done",
        )
        for m in record.matches
    ]
    rows.sort(key=lambda r: (not r.mine, r.id))
    return tuple(rows)


def _champion(record: LeagueRecord, table: Sequence[LeagueStanding]) -> str | None:
    if any(m.status == "pending" for m in record.matches) or not table:
        return None
    names = {e.account: e.name for e in record.entries}
    top = [names[r.account] for r in table if r.rank == 1]
    return f"冠軍：{'、'.join(top)}"


def league_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    record: LeagueRecord | None,
    now: int,
    *,
    account: str,
    running: bool = False,
) -> LeagueView:
    """``GET …/league`` 的畫面；``account`` 是看的人的帳號（沒有帳號＝角色 ID）。"""
    rules = league_rules(library)
    status = _status(library, world, record, now, running=running)
    mine = next((e for e in world.league_entries if e.account == account), None)
    problem = _enter_problem(library, world, char, account, now) if rules is not None else None
    entries = record.entries if record is not None else world.league_entries
    table = standings(record) if record is not None else None
    entry = None
    if mine is not None:
        entry = LeagueEntryView(
            character_id=mine.character_id,
            name=mine.name,
            ai=mine.ai,
            ai_zh=ai_zh(library, mine.ai, _default_ai(mine)),
            this_character=mine.character_id == char.character_id,
        )
    cap = rules_of(library).hero_growth.level_cap
    return LeagueView(
        status=status,
        status_zh=_STATUS_ZH[status],
        season_day=season_day(library, world, now),
        signup_close_day=0 if rules is None else rules.signup_close_day,
        maps_zh=() if rules is None else tuple(_map_name(library, m) for m in rules.maps),
        per_pair=0 if rules is None else matches_per_pair(rules),
        rules_zh=(
            f"全員拉到 {cap} 級、1 對 1、雙方都由 AI 操作；每對組合在每張地圖用多個種子、"
            "交換先後手各打一場，勝場多的人排前面。"
        ),
        entry=entry,
        can_enter=status == "signup" and problem is None,
        enter_problem_zh=problem if status in ("signup", "closed") else None,
        can_withdraw=(
            status == "signup" and mine is not None and mine.character_id == char.character_id
        ),
        ai_choices=ai_choice_views(library),
        entrants=len(entries),
        standings=_standing_rows(library, char, entries, table, account),
        matches=() if record is None else _match_rows(library, record, account),
        done=0 if record is None else record.done,
        total=0 if record is None else len(record.matches),
        champion_zh=None if record is None or table is None else _champion(record, table),
    )


def _default_ai(entry: LeagueEntry) -> str | None:
    return entry.snapshot.ai_profile or entry.snapshot.hero.ai_profile


def league_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """報名、更新、取消的句子。"""
    if isinstance(event, LeagueEnteredEvent):
        if event.updated:
            return "已更新影子循環賽的報名（用目前的配置）。"
        how = ai_zh(library, event.ai, None)
        return f"已報名影子循環賽（打法：{how}）。"
    if isinstance(event, LeagueWithdrawnEvent):
        return "已取消影子循環賽的報名。"
    return None
