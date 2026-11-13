"""公告板分頁版的後端欄位（PNL-1b；``docs/art/資訊面板-移植需求.md`` 2.4）：日程與時間點完整表、
時間點種類、世界事件整數天與區域、懸賞狀態與括號說明分欄、刷新時刻。"""

from __future__ import annotations

from typing import Any

from tests.world.helpers import NOON, hero, make_world
from trpg.api.season_view import milestone_kinds, season_board
from trpg.content.library import ContentLibrary
from trpg.content.world_season import Milestone
from trpg.world.calendar import day_of
from trpg.world.state import BountyClaim, CharacterState
from trpg.world.step import new_character

DAY = 24 * 3600


def _day(n: int) -> int:
    return NOON + (n - 1) * DAY


def _char(library: ContentLibrary, cid: str = "alice", **updates: Any) -> CharacterState:
    char = new_character(library, cid, hero(library), region="cloud_ridge")
    return char.model_copy(update=updates)


def test_season_lists_all_phases_and_milestones(library: ContentLibrary) -> None:
    board = season_board(library, make_world(), _char(library), _day(3))
    season = board.season
    assert season.day == 3
    assert [(p.name_zh, p.start_day, p.end_day) for p in season.phases] == [
        ("霧中裂痕", 1, 3),
        ("灰燼之心", 4, 7),
        ("封印", 8, 10),
        ("頭目競賽", 11, 13),
        ("季末", 14, 14),
    ]
    assert season.phase is not None and season.phase.name_zh == "霧中裂痕"
    assert season.phase.text_zh.startswith("主線第 1～2 章")
    assert season.phase_zh == f"霧中裂痕：{season.phase.text_zh}"  # 舊欄位照舊
    # 完整表含已過的（第 2 天）；upcoming 照舊只有今天起
    assert [m.day for m in season.milestones] == [2, 6, 8, 10, 13, 14]
    assert [m.day for m in season.upcoming] == [6, 8, 10, 13, 14]
    kinds = {m.id: m.kinds for m in season.milestones}
    assert kinds == {
        "story_skill_1": ("story_skill",),
        "story_skill_2": ("story_skill",),
        "boss_earliest": ("boss_unlock",),
        "boss_forced": ("boss_unlock", "story_skill"),
        "league_signup_close": ("league",),
        "league": ("league",),
    }
    assert all(m.kind == m.kinds[0] for m in season.milestones)
    assert season.refresh_time_zh == "06:00"


def test_milestone_kind_fallback() -> None:
    assert milestone_kinds(Milestone(id="harvest", day=3, name_zh="豐收祭")) == ("other",)


def test_upcoming_season_has_no_current_phase(library: ContentLibrary) -> None:
    world = make_world().model_copy(update={"season_start": _day(3)})
    season = season_board(library, world, _char(library), NOON).season
    assert season.status == "upcoming"
    assert season.phase is None and len(season.phases) == 5 and len(season.milestones) == 6


def test_world_events_have_integer_days_and_region(library: ContentLibrary) -> None:
    board = season_board(library, make_world(), _char(library), NOON)
    got = {e.event: (e.start_day, e.end_day, e.region, e.days_zh) for e in board.world_events}
    assert got == {
        "mist_tide": (1, 3, "cloud_ridge", "第 1～3 天"),
        "lava_breach": (4, 7, "ashen_waste", "第 4～7 天"),
        "seal_resonance": (7, 10, None, "第 7～10 天"),
    }


def test_bounty_status_note_is_separate(library: ContentLibrary) -> None:
    today = day_of(library, NOON)
    claim = BountyClaim(day=today, bounty="scarface", character_id="bob", name="小美", at=NOON)
    world = make_world(bounty_claims=(claim,))
    by_id = {b.bounty: b for b in season_board(library, world, _char(library), NOON).bounties}
    taken = by_id["scarface"]
    assert taken.status_zh == "已被 小美 搶下" and not taken.open and taken.claimed_by == "小美"
    assert taken.status_note_zh == "今天第一次交手打倒仍有小獎：任務幣 1"
    assert by_id["north_wolf_king"].status_zh == "懸賞中"
    assert by_id["north_wolf_king"].status_note_zh is None
    # 今天已經和這張交手過（拿過小獎）：不再寫說明
    fought = _char(library, bounty_days={"scarface": today})
    again = {b.bounty: b for b in season_board(library, world, fought, NOON).bounties}
    assert again["scarface"].status_zh == "已被 小美 搶下"
    assert again["scarface"].status_note_zh is None
    # 自己搶下的
    mine = BountyClaim(day=today, bounty="scarface", character_id="alice", name="阿霧", at=NOON)
    own = season_board(library, make_world(bounty_claims=(mine,)), _char(library), NOON)
    assert {b.bounty: b.status_zh for b in own.bounties}["scarface"] == "你搶下了"
