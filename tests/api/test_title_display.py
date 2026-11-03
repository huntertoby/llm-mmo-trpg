"""帳號紀念稱號「碎晶的終結者」的顯示位置（Phase 5F-3c；19.7 的 5F-3b 代決）：玩家名片（雇用清單的
影子）、主城排行榜與 Boss 擊殺紀錄（評分榜、首殺）、編年史。戰鬥畫面不顯示。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import START, _client
from tests.world.helpers import NOON
from trpg.api.chronicle_schemas import ChronicleTitles, chronicle_view
from trpg.api.season_view import season_board
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.accounts import AccountStore, AccountTitle
from trpg.server.chronicle import (
    ChronicleHero,
    LeagueChronicleRank,
    LeagueChronicleSeason,
    SeasonChronicleEntry,
)
from trpg.server.first_kills import FirstKill
from trpg.server.season_boss_board import BossBoardEntry
from trpg.world.state import BossClear

SLAYER = "碎晶的終結者（s1）"
DAY10 = NOON + 9 * 24 * 3600


def _title(character_id: str) -> AccountTitle:
    return AccountTitle(
        id="season_boss:rift_shard_lord",
        name_zh="碎晶的終結者",
        season_id="s1",
        character_id=character_id,
        at=NOON,
    )


def _titles(owner: str) -> tuple[str, ...]:
    return (SLAYER,) if owner in {"char_a", "acc_a"} else ()


def test_account_store_titles_of(tmp_path: Path) -> None:
    store = AccountStore(tmp_path / "acc")
    record = store.create("slayer", "password-123")
    assert store.titles_of(record.account_id) == ()
    store.grant_title(record.account_id, _title("char_a"))
    assert store.titles_of(record.account_id) == (SLAYER,)
    assert store.titles_of("missing") == ()


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(library, tmp_path / "saves") as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_name_card_of_a_friends_shadow_shows_titles(client: TestClient) -> None:
    """玩家名片：城裡的雇用清單點開朋友的影子（看 build）時，名字旁帶帳號稱號。"""
    a = _ok(client.post("/api/world/characters", json={**START, "name": "阿霧"}), 201)
    b = _ok(client.post("/api/world/characters", json={**START, "name": "小美"}), 201)
    a_id, b_id = a["character"]["character_id"], b["character"]["character_id"]
    _ok(client.post(f"/api/world/characters/{a_id}/actions", json={"kind": "rest"}))
    accounts = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(accounts, AccountStore)
    (shadow,) = _ok(client.get(f"/api/world/characters/{b_id}"))["party"]["shadows"]
    assert shadow["titles"] == []  # 開發模式的角色沒有帳號
    record = accounts.create("slayer", "password-123")
    accounts.attach_character(record.account_id, a_id)
    accounts.grant_title(record.account_id, _title(a_id))
    (shadow,) = _ok(client.get(f"/api/world/characters/{b_id}"))["party"]["shadows"]
    assert shadow["owner"] == a_id and shadow["titles"] == [SLAYER]
    # 自己的世界畫面（含戰鬥前的畫面）沒有稱號欄位；稱號只在名片、榜、編年史
    assert "titles" not in _ok(client.get(f"/api/world/characters/{a_id}"))["character"]


def _entry(character_id: str, account_id: str, name: str, score: int) -> BossBoardEntry:
    return BossBoardEntry(
        season_id="s1",
        boss="rift_shard_lord",
        character_id=character_id,
        account_id=account_id,
        name=name,
        score=score,
        rounds=12,
        survivors=3,
        allies=3,
        no_down=True,
        title_zh="碎晶的終結者",
        region="cloud_ridge",
        location="mistford",
        seq=1,
        at=NOON,
    )


def test_board_and_first_kill_show_titles(library: ContentLibrary, tmp_path: Path) -> None:
    store = WorldStore(library, SessionStore(library), tmp_path / "w", prefetch=False)
    store.season_start = NOON
    char = store.create("阿霧", "fire_staff", ("ignite", "marked"), seed=0)
    world = store.world().model_copy(
        update={
            "boss_clears": (
                BossClear(character_id="char_a", name="甲", at=NOON, score=1, rounds=12),
            )
        }
    )
    entries = (_entry("char_a", "acc_a", "甲", 1500), _entry("char_b", "acc_b", "乙", 1400))
    board = season_board(library, world, char, DAY10, boss_board=entries, titles=_titles)
    boss = board.season_boss
    assert boss is not None
    assert [e.titles for e in boss.board] == [(SLAYER,), ()]
    assert boss.first_kill_titles == (SLAYER,)
    plain = season_board(library, world, char, DAY10, boss_board=entries).season_boss
    assert plain is not None and plain.first_kill_titles == () and plain.board[0].titles == ()


def test_chronicle_shows_titles_next_to_names() -> None:
    hero = ChronicleHero(
        character_id="char_x", account_id="acc_a", name="甲", text_zh="甲打過霧鎖真人。"
    )
    season = SeasonChronicleEntry(
        season_id="s1",
        name_zh="第一季",
        next_season_id="s2",
        started_at=NOON,
        reset_at=DAY10,
        heroes=(hero,),
    )
    league = LeagueChronicleSeason(
        season_id="s1",
        finished_at=DAY10,
        matches=0,
        ranks=(
            LeagueChronicleRank(
                rank=1,
                account="acc_a",
                name="甲",
                build_zh="火焰法杖・人類",
                wins=3,
                losses=0,
                draws=0,
                hp_permille_total=0,
                rounds_total=0,
            ),
        ),
    )
    kill = FirstKill(
        kind="season_boss",
        target="rift_shard_lord",
        target_name_zh="碎晶之主",
        character_id="char_a",
        name="甲",
        region="cloud_ridge",
        location="mistford",
        seq=1,
        at=NOON,
    )
    view = chronicle_view(
        "s2",
        (season,),
        (league,),
        (kill,),
        (_entry("char_a", "acc_a", "甲", 1500),),
        titles=ChronicleTitles(of_character=_titles, of_account=_titles),
    )
    (s1,) = view.seasons
    assert s1.heroes[0].titles == [SLAYER]  # 有帳號時照帳號查
    assert s1.league[0].titles == [SLAYER]
    assert s1.first_kills[0].titles == [SLAYER]
    assert s1.boss_board[0].titles == [SLAYER]
    (plain,) = chronicle_view("s2", (season,), (league,), (kill,), ()).seasons
    assert plain.heroes[0].titles == [] and plain.first_kills[0].titles == []
