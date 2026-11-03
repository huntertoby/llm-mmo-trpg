"""「你不在的時候」摘要（Phase 5F-1b）：世界事件成敗、懸賞被誰搶下、新開放的區域；看過不再跳。"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, hero, make_world, with_rules
from trpg.api.absence_view import absence_summary
from trpg.api.app import create_app
from trpg.api.season_view import season_board
from trpg.api.server_config import ServerSettings
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.world.actions import NewsSeenAction
from trpg.world.calendar import day_of
from trpg.world.season_board import roll_season
from trpg.world.state import BountyClaim, CharacterState, LocationRef
from trpg.world.step import new_character, world_step

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}
DAY = 24 * 3600


def _day(n: int) -> int:
    return NOON + (n - 1) * DAY


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


def _char(library: ContentLibrary, cid: str = "alice", **updates: Any) -> CharacterState:
    char = new_character(library, cid, hero(library), region="cloud_ridge")
    return char.model_copy(update=updates)


def test_lava_breach_failure_lists_price_raise(library: ContentLibrary) -> None:
    """5F-5b：熔岩潰堤失敗＝餘燼集商店買價 +20% 到季末（離線摘要與公告板的世界變化都列）。"""
    world, _ = roll_season(library, make_world(), NOON)
    world, _ = roll_season(library, world, _day(9))  # 第 8 天換日：熔岩潰堤失敗
    char = _char(library, news_seen_at=_day(7))
    texts = [i.text_zh for i in absence_summary(library, world, char, _day(9)).items]
    assert (
        "世界事件「熔岩潰堤」失敗（0／24），灰燼荒原建議等級 +1、鐵娘的廢鐵攤買價 +20%。" in texts
    )
    board = season_board(library, world, char, _day(9))
    assert board.level_bonus_zh == ("灰燼荒原：建議等級 +2", "鐵娘的廢鐵攤：買價 +20%")


def _claim(day: int, bounty: str, who: str, at: int) -> BountyClaim:
    return BountyClaim(day=day, bounty=bounty, character_id=who, name=f"{who}名", at=at)


def test_failed_event_opens_gate_and_raises_level(library: ContentLibrary) -> None:
    world, _ = roll_season(library, make_world(), NOON)
    world, _ = roll_season(library, world, _day(5))  # 第 4 天換日：霧潮入侵失敗
    char = _char(library, news_seen_at=NOON)
    view = absence_summary(library, world, char, _day(5))
    assert [i.kind for i in view.items] == ["world_event", "opened"]
    assert view.items[0].text_zh == "世界事件「霧潮入侵」失敗（0／30），灰燼荒原建議等級 +1。"
    assert view.items[1].text_zh == "「往灰燼荒原的渡口」開放了，可以前往灰燼荒原。"
    assert view.since == NOON and view.as_of == _day(5)
    state = world.world_event("mist_tide")
    assert state is not None and state.resolved_at is not None
    assert day_of(library, state.resolved_at) == state.resolved_day
    # 看過之後（news_seen_at 往後）就不再列
    seen = char.model_copy(update={"news_seen_at": _day(5)})
    assert absence_summary(library, world, seen, _day(5) + 60).items == ()


def test_bounty_claims_by_others_since_last_seen(library: ContentLibrary) -> None:
    today = day_of(library, NOON)
    claims = (
        _claim(today, "mist_swordsman", "bob", NOON + 100),
        _claim(today, "north_wolf_king", "alice", NOON + 50),  # 自己搶的不列
        _claim(today, "scarface", "carol", NOON - 100),  # 上次看過之前
    )
    world = make_world(bounty_claims=claims)
    char = _char(library, news_seen_at=NOON)
    (item,) = absence_summary(library, world, char, NOON + 200).items
    assert item.kind == "bounty" and item.at == NOON + 100
    assert item.text_zh == "第 1 天的懸賞「霧中劍客」（劍冢）被 bob名 搶下。"


def test_hidden_location_uses_hint(library: ContentLibrary) -> None:
    """摘要提到看的人還沒發現的隱藏地點時用提示語（5C-3f）。"""
    season = library.world_season
    assert season is not None
    moved = tuple(
        b.model_copy(update={"location": "elixir_cave"}) if b.id == "scarface" else b
        for b in season.bounties
    )
    hidden = dataclasses.replace(
        library, world_season=season.model_copy(update={"bounties": moved})
    )
    world = make_world(bounty_claims=(_claim(day_of(library, NOON), "scarface", "bob", NOON + 9),))
    stranger = _char(library, news_seen_at=NOON)
    (item,) = absence_summary(hidden, world, stranger, NOON + 60).items
    assert "谷底一處隱密的洞窟" in item.text_zh and "丹爐洞" not in item.text_zh
    ref = LocationRef(region="cloud_ridge", location="elixir_cave")
    finder = stranger.model_copy(update={"revealed": (ref,)})
    (item,) = absence_summary(hidden, world, finder, NOON + 60).items
    assert "丹爐洞" in item.text_zh


def test_old_save_counts_from_season_start(library: ContentLibrary) -> None:
    world = make_world(bounty_claims=(_claim(day_of(library, NOON), "scarface", "bob", NOON + 9),))
    view = absence_summary(library, world, _char(library), NOON + 60)  # news_seen_at None
    assert view.since == world.season_start and len(view.items) == 1


def test_news_seen_action_only_moves_forward(library: ContentLibrary) -> None:
    char = _char(library, news_seen_at=NOON)
    world = make_world()
    later = world_step(library, world, char, NewsSeenAction(until=NOON + 500), NOON + 600).char
    assert later.news_seen_at == NOON + 500
    back = world_step(library, world, later, NewsSeenAction(until=NOON), NOON + 700).char
    assert back.news_seen_at == NOON + 500
    future = world_step(library, world, later, NewsSeenAction(until=NOON + 9999), NOON + 800).char
    assert future.news_seen_at == NOON + 800  # 不超過現在


def _client(library: ContentLibrary, saves: Path, clock: list[int]) -> TestClient:
    app = create_app(
        library,
        save_dir=saves,
        accounts=AccountSettings(dev_mode=True),
        server=ServerSettings(llm_health_interval_s=0),
    )
    world = app.state.world
    assert isinstance(world, WorldStore)
    world.clock = lambda: clock[0]
    return TestClient(app)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_endpoint_then_seen(calm: ContentLibrary, tmp_path: Path) -> None:
    clock = [NOON]
    with _client(calm, tmp_path / "saves", clock) as client:
        created = _ok(client.post("/api/world/characters", json=START), 201)
        cid = created["character"]["character_id"]
        url = f"/api/world/characters/{cid}/absence"
        assert _ok(client.get(url))["items"] == []  # 新角色：建立之前的消息不算
        clock[0] = _day(5)
        view = _ok(client.get(url))
        assert [i["kind"] for i in view["items"]] == ["world_event", "opened"]
        assert view["as_of"] == _day(5)
        clock[0] = _day(5) + 30
        seen = {"kind": "news_seen", "until": view["as_of"]}
        _ok(client.post(f"/api/world/characters/{cid}/actions", json=seen))
        assert _ok(client.get(url))["items"] == []
