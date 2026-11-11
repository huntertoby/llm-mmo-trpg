"""影子循環賽的畫面資料與事件句子（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.7）。

排行榜是給別人看的：報名地點照看的人套隱藏地點的提示語（5C-3f，
:func:`~trpg.world.narration.location_name_for`）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.api.league_schemas import (
    LeagueAllocationView,
    LeagueEntryView,
    LeagueMatchView,
    LeagueStandingView,
    LeagueStatus,
    LeagueView,
)
from trpg.api.world_party_view import ai_choice_views, ai_zh, shadow_role_zh
from trpg.content.library import ContentLibrary
from trpg.content.world_season import LeagueRules
from trpg.server.league import STALE_ZH, LeagueMatch, LeagueRecord, LeagueStanding, standings
from trpg.world.actions import WorldEvent
from trpg.world.calendar import season_day
from trpg.world.common import rules_of
from trpg.world.league import (
    league_auto_allocation,
    league_base_attributes,
    league_point_pool,
    league_rules,
    matches_per_pair,
    signup_problem,
)
from trpg.world.league_actions import LeagueEnteredEvent, LeagueWithdrawnEvent
from trpg.world.narration import location_name_for
from trpg.world.opening import opening_limits
from trpg.world.shadows import shadow_snapshot
from trpg.world.state import CharacterState, LeagueEntry, WorldState

PERMILLE = 1000

__all__ = [
    "PAGE_SIZE",
    "league_event_line",
    "league_view",
    "match_outcome_zh",
    "match_title",
    "result_zh",
]

PAGE_SIZE = 20
"""場次列表每頁幾場（5F-4b）。"""
STALE_NOTE_ZH = f"{STALE_ZH}：這份賽程是用舊規則跑的，管理者重新開跑時會用同一份報名整個重跑。"

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
                hp_permille_total=0 if standing is None else standing.hp_permille_total,
                rounds_total=0 if standing is None else standing.rounds_total,
                tied=False if standing is None else standing.tied,
            )
        )
    return tuple(rows)


def result_zh(match: LeagueMatch, names: dict[str, str]) -> str:
    """一場的結果文字（中性，5F-4b）：「某某 勝（N 輪）」「和局（N 輪）」。"""
    if match.status == "pending":
        return "尚未進行"
    if match.status == "error":
        return f"出錯：{match.error or '未知的錯誤'}"
    if match.winner is None:
        return f"和局（{match.rounds} 輪）"
    return f"{names.get(match.winner, match.winner)} 勝（{match.rounds} 輪）"


def match_outcome_zh(record: LeagueRecord, match: LeagueMatch) -> str:
    """重播結束面板的中性勝負文字（5F-4b）：「某某 勝」或「和局」（不從先手視角寫勝利／敗北）。"""
    if match.winner is None:
        return "和局"
    names = {e.account: e.name for e in record.entries}
    return f"{names.get(match.winner, match.winner)} 勝"


def match_title(library: ContentLibrary, record: LeagueRecord, match: LeagueMatch) -> str:
    """重播畫面的標題，例「m0003：阿霧（先手） vs 小美・開闊平原・種子 1」。"""
    names = {e.account: e.name for e in record.entries}
    ally = names.get(match.ally, match.ally)
    enemy = names.get(match.enemy, match.enemy)
    where = _map_name(library, match.map)
    return f"{match.id}：{ally}（先手） vs {enemy}・{where}・種子 {match.seed_index + 1}"


def _match_rows(
    library: ContentLibrary, record: LeagueRecord, account: str, *, stale: bool
) -> list[LeagueMatchView]:
    names = {e.account: e.name for e in record.entries}
    rows = [
        LeagueMatchView(
            id=m.id,
            ally_name=names.get(m.ally, m.ally),
            enemy_name=names.get(m.enemy, m.enemy),
            map_zh=_map_name(library, m.map),
            seed_index=m.seed_index,
            status=m.status,
            result_zh=result_zh(m, names),
            mine=account in (m.a, m.b),
            replayable=m.status == "done" and not stale,
            replay_problem_zh=STALE_ZH if stale and m.status == "done" else None,
        )
        for m in record.matches
    ]
    rows.sort(key=lambda r: (not r.mine, r.id))
    return rows


def _page(
    rows: Sequence[LeagueMatchView], page: int, size: int
) -> tuple[tuple[LeagueMatchView, ...], int, int]:
    """（這一頁的場次, 第幾頁〔超過範圍時夾到最後一頁〕, 共幾頁）。"""
    pages = max(1, -(-len(rows) // size))
    current = min(max(1, page), pages)
    start = (current - 1) * size
    return tuple(rows[start : start + size]), current, pages


def _allocation(
    library: ContentLibrary, char: CharacterState, now: int
) -> LeagueAllocationView | None:
    """這個角色報名時可以重新配點的資料（以目前的 build 算，報名時存的就是這份快照）。"""
    try:
        snap = shadow_snapshot(char, now)
        return LeagueAllocationView(
            base={a.value: v for a, v in league_base_attributes(snap).items()},
            points=league_point_pool(library, snap),
            auto={a.value: v for a, v in league_auto_allocation(library, snap).items()},
        )
    except (KeyError, ValueError):  # 舊存檔的武器或技能不在內容庫：不給配點畫面
        return None


def _rules_zh(library: ContentLibrary, rules: LeagueRules | None, cap: int) -> str:
    """一行規則說明（開場 HP 倍率、開場狀態照內容寫，5F-4b）。"""
    extra: list[str] = []
    if rules is not None and rules.hp_permille != PERMILLE:
        extra.append(f"開場 HP ×{rules.hp_permille / PERMILLE:g}")
    statuses = () if rules is None else (*rules.opening_statuses, *rules.first_opening_statuses)
    both = () if rules is None else rules.opening_statuses
    for status_id in dict.fromkeys(statuses):
        found = library.ruleset.status_def(status_id)  # 載入時已檢查存在
        who = "" if status_id in both else "先手"
        extra.append(f"{who}開場「{found.name_zh}」：{found.description_zh}")
    head = f"全員拉到 {cap} 級（報名時可以免費重新配點）、1 對 1、雙方都由 AI 操作。"
    middle = "".join(f"{line}。" if not line.endswith("。") else line for line in extra)
    tail = (
        "每對組合在每張地圖用多個種子、交換先後手各打一場；勝場多的人排前面，同勝場比剩餘 HP "
        "比例合計、再比總輪數（少的勝），都一樣就同名次。"
    )
    return head + middle + tail


def _champion(record: LeagueRecord, table: Sequence[LeagueStanding]) -> str | None:
    if any(m.status == "pending" for m in record.matches) or not table:
        return None
    names = {e.account: e.name for e in record.entries}
    top = [names[r.account] for r in table if r.rank == 1]
    tie = "（同分，平分獎金）" if len(top) > 1 else ""
    return f"冠軍：{'、'.join(top)}{tie}"


def league_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    record: LeagueRecord | None,
    now: int,
    *,
    account: str,
    running: bool = False,
    stale: bool = False,
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> LeagueView:
    """``GET …/league`` 的畫面；``account`` 是看的人的帳號（沒有帳號＝角色 ID）。``stale``：賽程是用
    舊規則跑的（5F-4b）。``page``／``page_size``：場次列表分頁。"""
    rules = league_rules(library)
    status = _status(library, world, record, now, running=running)
    mine = next((e for e in world.league_entries if e.account == account), None)
    problem = _enter_problem(library, world, char, account, now) if rules is not None else None
    # OB-5（#150 第 9 點）：入門期不開放——面板先標成不能報名，原因和送出動作被拒的同一句
    problem = opening_limits(char).get("league") or problem
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
            allocation=(
                None
                if mine.allocation is None
                else {a.value: v for a, v in mine.allocation.items()}
            ),
        )
    cap = rules_of(library).hero_growth.level_cap
    rows = [] if record is None else _match_rows(library, record, account, stale=stale)
    shown, current, pages = _page(rows, page, page_size)
    return LeagueView(
        status=status,
        status_zh=_STATUS_ZH[status],
        season_day=season_day(library, world, now),
        signup_close_day=0 if rules is None else rules.signup_close_day,
        maps_zh=() if rules is None else tuple(_map_name(library, m) for m in rules.maps),
        per_pair=0 if rules is None else matches_per_pair(rules),
        rules_zh=_rules_zh(library, rules, cap),
        entry=entry,
        can_enter=status == "signup" and problem is None,
        enter_problem_zh=problem if status in ("signup", "closed") else None,
        can_withdraw=(
            status == "signup" and mine is not None and mine.character_id == char.character_id
        ),
        ai_choices=ai_choice_views(library),
        entrants=len(entries),
        standings=_standing_rows(library, char, entries, table, account),
        matches=shown,
        done=0 if record is None else record.done,
        total=0 if record is None else len(record.matches),
        champion_zh=None if record is None or table is None else _champion(record, table),
        page=current,
        pages=pages,
        page_size=page_size,
        allocation=_allocation(library, char, now) if status == "signup" else None,
        stale_zh=STALE_NOTE_ZH if record is not None and stale else None,
        reruns=0 if record is None else record.reruns,
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
