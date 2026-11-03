"""``GET /api/world/characters/{id}/board``：城鎮公告板（Phase 5F-1；``docs/phases/Phase5計畫.md``
35.7）；世界日誌記帳號（Q15）、開賽日設定（35.3）。"""

from __future__ import annotations

import datetime as dt
import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.server_config import ServerConfigError, ServerSettings, load_server_settings
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore
from trpg.world.calendar import season_start_at
from trpg.world.save import loads_log, loads_world

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


def _client(
    library: ContentLibrary, saves: Path, *, dev_mode: bool = True, start: dt.date | None = None
) -> TestClient:
    app = create_app(
        library,
        save_dir=saves,
        accounts=AccountSettings(dev_mode=dev_mode),
        server=ServerSettings(llm_health_interval_s=0, season_start_date=start),
    )
    world = app.state.world
    assert isinstance(world, WorldStore)
    world.clock = lambda: NOON
    return TestClient(app)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_board_lists_season_goals_bounties_events(calm: ContentLibrary, tmp_path: Path) -> None:
    with _client(calm, tmp_path / "saves") as client:
        cid = _ok(client.post("/api/world/characters", json=START), 201)["character"][
            "character_id"
        ]
        board = _ok(client.get(f"/api/world/characters/{cid}/board"))
    season = board["season"]
    assert season["day"] == 1 and season["days"] == 14 and season["status"] == "running"
    assert season["status_zh"] == "賽季第 1 天／共 14 天"
    assert season["phase_zh"].startswith("霧中裂痕")
    assert season["next_refresh_at"] > NOON and season["next_refresh_zh"] == "每天 06:00 刷新"
    assert [g["goal"] for g in board["goals"]] == ["starter_steps", "reveal_hidden", "elite_once"]
    assert board["goals_note_zh"] == "新手期：教學目標"
    assert all(g["progress"] == 0 and not g["done"] for g in board["goals"])
    names = {b["bounty"]: b for b in board["bounties"]}
    assert set(names) == {"north_wolf_king", "mist_swordsman", "scarface"}
    assert all(b["open"] and b["status_zh"] == "懸賞中" for b in board["bounties"])
    (event,) = board["world_events"]
    assert event["name_zh"] == "霧潮入侵" and event["status"] == "active"
    assert event["target"] == 30 and event["permille"] == 0
    assert event["target_note_zh"] == "第 1 天用原門檻"
    # 公告板只算、不寫世界存檔
    world = loads_world((tmp_path / "saves" / "world" / "world.json").read_text(encoding="utf-8"))
    assert world.rolled_day is None


def test_hidden_bounty_location_uses_hint(calm: ContentLibrary, tmp_path: Path) -> None:
    """懸賞地點是還沒發現的隱藏地點時用提示語（5C-3f）。"""
    hidden = {loc.id for loc in calm.world_maps["cloud_ridge"].locations if loc.hidden}
    with _client(calm, tmp_path / "saves") as client:
        cid = _ok(client.post("/api/world/characters", json=START), 201)["character"][
            "character_id"
        ]
        board = _ok(client.get(f"/api/world/characters/{cid}/board"))
    by_location = {b["bounty"]: b["location_zh"] for b in board["bounties"]}
    season = calm.world_season
    assert season is not None
    places = calm.world_maps["cloud_ridge"].location_by_id()
    for bounty in season.bounties:
        name = places[bounty.location].name_zh
        if bounty.location in hidden:
            assert by_location[bounty.id] != name
        else:
            assert by_location[bounty.id] == name


def test_log_records_account_actor(calm: ContentLibrary, tmp_path: Path) -> None:
    with _client(calm, tmp_path / "saves", dev_mode=False) as client:
        accounts = client.app.state.accounts  # type: ignore[attr-defined]
        assert isinstance(accounts, AccountStore)
        password = secrets.token_urlsafe(12)
        accounts.create("alice", password)
        login = client.post("/api/auth/login", json={"username": "alice", "password": password})
        token = _ok(login)["token"]
        headers = {"Authorization": f"Bearer {token}"}
        cid = _ok(client.post("/api/world/characters", json=START, headers=headers), 201)[
            "character"
        ]["character_id"]
        reply = client.post(
            f"/api/world/characters/{cid}/actions",
            json={"kind": "travel", "to": "hunter_hut"},
            headers=headers,
        )
        _ok(reply)
        account_id = accounts.owner_of(cid)
    root = tmp_path / "saves" / "world"
    entries = loads_log((root / "log.jsonl").read_text(encoding="utf-8"))
    assert entries[-1].actor == account_id is not None
    world = loads_world((root / "world.json").read_text(encoding="utf-8"))
    assert world.activity[-1].actors == (account_id,)


def test_season_start_date_setting(calm: ContentLibrary, tmp_path: Path) -> None:
    start = dt.date(2026, 11, 10)
    with _client(calm, tmp_path / "saves", start=start) as client:
        cid = _ok(client.post("/api/world/characters", json=START), 201)["character"][
            "character_id"
        ]
        board = _ok(client.get(f"/api/world/characters/{cid}/board"))
    assert board["season"]["status"] == "upcoming" and board["season"]["status_zh"] == "開賽前"
    world = loads_world((tmp_path / "saves" / "world" / "world.json").read_text(encoding="utf-8"))
    assert world.season_start == season_start_at(calm, start)


def test_season_start_config(tmp_path: Path) -> None:
    path = tmp_path / "server.toml"
    path.write_text('[season]\nstart_date = "2026-11-10"\n', encoding="utf-8")
    assert load_server_settings(path, env={}).season_start_date == dt.date(2026, 11, 10)
    path.write_text('[season]\nstart_date = ""\n', encoding="utf-8")
    assert load_server_settings(path, env={}).season_start_date is None
    env = {"TRPG_SEASON_START": "2026-12-01"}
    assert load_server_settings(path, env=env).season_start_date == dt.date(2026, 12, 1)
    path.write_text('[season]\nstart = "x"\n', encoding="utf-8")
    with pytest.raises(ServerConfigError, match=r"season.start"):
        load_server_settings(path, env={})
