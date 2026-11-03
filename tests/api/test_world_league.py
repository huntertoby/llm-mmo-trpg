"""影子循環賽的 API（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.7）。"""

from __future__ import annotations

import dataclasses
import json
import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, make_world, with_rules
from trpg.api.app import create_app
from trpg.api.league_view import league_view
from trpg.api.server_config import ServerSettings
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.engine.runner import LOG_FORMAT
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore
from trpg.server.first_kills import FirstKill
from trpg.world.league_actions import LeagueEnterAction
from trpg.world.step import new_character, reveal_location, world_step

DAY = 24 * 3600
AFTER = NOON + 13 * DAY  # 第 14 天
START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture(scope="module")
def small(library: ContentLibrary) -> ContentLibrary:
    """不遇敵、循環賽只有 1 張地圖 × 1 個種子（每對 2 場）的內容庫。"""
    calm = with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})
    season = calm.world_season
    assert season is not None and season.league is not None
    league = season.league.model_copy(update={"maps": ("open_plain",), "seeds": 1})
    return dataclasses.replace(calm, world_season=season.model_copy(update={"league": league}))


def _client(library: ContentLibrary, saves: Path, *, dev_mode: bool = True) -> TestClient:
    app = create_app(
        library,
        save_dir=saves,
        accounts=AccountSettings(dev_mode=dev_mode),
        server=ServerSettings(llm_health_interval_s=0),
    )
    world = app.state.world
    assert isinstance(world, WorldStore)
    world.clock = lambda: NOON
    return TestClient(app)


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _create(client: TestClient, body: dict[str, Any]) -> str:
    created = _ok(client.post("/api/world/characters", json=body), 201)
    cid: str = created["character"]["character_id"]
    return cid


def _season_boss_killed(store: WorldStore) -> None:
    kill = FirstKill(
        kind="season_boss",
        target="mist_lock_master",
        target_name_zh="霧鎖真人",
        character_id="someone",
        name="某人",
        region="cloud_ridge",
        location="cloud_summit",
        seq=1,
        at=NOON,
        season_id=store.world().season_id,
    )
    body = {"format": "trpg-firstkills/1", "kills": [kill.model_dump(mode="json")]}
    store.first_kills.path.write_text(json.dumps(body), encoding="utf-8")


def test_league_flow(small: ContentLibrary, tmp_path: Path) -> None:
    with _client(small, tmp_path / "saves") as client:
        store = _store(client)
        a = _create(client, START)
        b = _create(client, START | {"name": "小美", "seed": 1})
        view = _ok(client.get(f"/api/world/characters/{a}/league"))
        assert view["status"] == "signup" and view["can_enter"] and view["entry"] is None
        assert view["signup_close_day"] == 13 and view["per_pair"] == 2
        assert view["maps_zh"] == ["開闊平原"]
        assert {c["id"] for c in view["ai_choices"]} >= {"guard", "brute"}
        world = _ok(
            client.post(
                f"/api/world/characters/{a}/actions", json={"kind": "league_enter", "ai": "guard"}
            )
        )
        assert any("已報名影子循環賽" in line for line in world["events"])
        _ok(client.post(f"/api/world/characters/{b}/actions", json={"kind": "league_enter"}))
        view = _ok(client.get(f"/api/world/characters/{a}/league"))
        assert view["entrants"] == 2
        assert view["entry"]["ai"] == "guard" and view["entry"]["this_character"]
        assert view["can_withdraw"]
        assert all(r["rank"] is None and r["level"] == 10 for r in view["standings"])
        # 截止前不能開跑
        assert client.post("/api/world/league/run").status_code == 409
        _season_boss_killed(store)  # 有人首殺：第 14 天不自動開跑，只能管理者開（5F-4b）
        store.clock = lambda: AFTER
        view = _ok(client.get(f"/api/world/characters/{a}/league"))
        assert view["status"] == "closed" and not view["can_enter"]
        assert view["allocation"] is None  # 截止後不給配點畫面
        assert "截止" in view["enter_problem_zh"]
        reply = client.post(f"/api/world/characters/{a}/actions", json={"kind": "league_withdraw"})
        assert reply.status_code == 422
        run = _ok(client.post("/api/world/league/run"))
        assert run["total"] == 2
        store.league_runner.join(120)
        view = _ok(client.get(f"/api/world/characters/{a}/league"))
        assert view["status"] == "done" and view["done"] == view["total"] == 2
        assert sum(r["played"] for r in view["standings"]) == 4
        assert view["champion_zh"].startswith("冠軍：")
        mine = [m for m in view["matches"] if m["mine"]]
        assert len(mine) == 2 and all(m["replayable"] for m in mine)
        match = mine[0]
        replay = _ok(client.post(f"/api/world/characters/{a}/league/matches/{match['id']}/replay"))
        assert replay["verified"] is True
        assert replay["title_zh"].startswith(f"{match['id']}：")
        battle = replay["battle"]
        assert battle["awaiting"] == "ended" and battle["outcome"] is not None
        assert battle["steps"][0]["step"] is None  # 從開場播起
        assert len(battle["steps"]) > 2
        log = client.get(f"/api/world/league/matches/{match['id']}/log")
        assert log.status_code == 200
        assert json.loads(log.text)["format"] == LOG_FORMAT
        assert client.get("/api/world/league/matches/m9999/log").status_code == 404
        # 已經開過：再按只接續（沒有 pending 就不跑）
        again = _ok(client.post("/api/world/league/run"))
        assert again["done"] == again["total"] == 2


def test_run_needs_admin(small: ContentLibrary, tmp_path: Path) -> None:
    with _client(small, tmp_path / "saves", dev_mode=False) as client:
        accounts = client.app.state.accounts  # type: ignore[attr-defined]
        assert isinstance(accounts, AccountStore)
        password = secrets.token_urlsafe(12)
        accounts.create("alice", password)
        token = _ok(
            client.post("/api/auth/login", json={"username": "alice", "password": password})
        )["token"]
        reply = client.post("/api/world/league/run", headers={"Authorization": f"Bearer {token}"})
        assert reply.status_code == 403
        assert client.post("/api/world/league/run").status_code == 401


def test_league_signup_counts_accounts(small: ContentLibrary, tmp_path: Path) -> None:
    """帳號的第二個角色不能另外報名（#100）。"""
    with _client(small, tmp_path / "saves", dev_mode=False) as client:
        accounts = client.app.state.accounts  # type: ignore[attr-defined]
        assert isinstance(accounts, AccountStore)
        password = secrets.token_urlsafe(12)
        accounts.create("alice", password)
        token = _ok(
            client.post("/api/auth/login", json={"username": "alice", "password": password})
        )["token"]
        headers = {"Authorization": f"Bearer {token}"}
        ids = [
            _ok(
                client.post("/api/world/characters", json=START | {"seed": s}, headers=headers), 201
            )["character"]["character_id"]
            for s in (0, 1)
        ]
        _ok(
            client.post(
                f"/api/world/characters/{ids[0]}/actions",
                json={"kind": "league_enter"},
                headers=headers,
            )
        )
        view = _ok(client.get(f"/api/world/characters/{ids[1]}/league", headers=headers))
        assert not view["can_enter"] and "已經用" in view["enter_problem_zh"]
        assert view["entry"]["this_character"] is False
        reply = client.post(
            f"/api/world/characters/{ids[1]}/actions",
            json={"kind": "league_enter"},
            headers=headers,
        )
        assert reply.status_code == 422


def test_standings_hide_unrevealed_place(small: ContentLibrary) -> None:
    """排行榜的報名地點：看的人還沒發現的隱藏地點用提示語（5C-3f）。"""
    hero = next(b.hero for b in small.builds.builds if b.id == "build_support")
    places = small.world_maps["cloud_ridge"].location_by_id()
    secret = places["elixir_cave"]
    assert secret.hidden
    owner = new_character(small, "alice", hero, region="cloud_ridge")
    world = world_step(small, make_world(), owner, LeagueEnterAction(), NOON, actor="a1").world
    moved = world.league_entries[0]
    snap = moved.snapshot.model_copy(update={"location": "elixir_cave"})
    world = world.model_copy(
        update={"league_entries": (moved.model_copy(update={"snapshot": snap}),)}
    )
    viewer = new_character(small, "bob", hero, region="cloud_ridge")
    view = league_view(small, world, viewer, None, NOON, account="b1")
    (row,) = view.standings
    assert row.place_zh != secret.name_zh
    assert row.place_zh == (secret.hint_zh or row.place_zh)
    seen = reveal_location(viewer, "cloud_ridge", "elixir_cave")
    revealed = league_view(small, world, seen, None, NOON, account="b1")
    assert revealed.standings[0].place_zh == secret.name_zh


# ---------------------------------------------------------------------------
# 5F-4b
# ---------------------------------------------------------------------------


def test_auto_start_reallocation_paging_and_stale(small: ContentLibrary, tmp_path: Path) -> None:
    """第 14 天沒有人首殺賽季 Boss → 看循環賽就自動開跑；報名可以重新配點；場次分頁；
    規則改了的賽程不能重播、管理者再開跑就整個重跑。"""
    with _client(small, tmp_path / "saves") as client:
        store = _store(client)
        ids = [_create(client, START | {"name": n, "seed": s}) for s, n in enumerate("甲乙丙")]
        view = _ok(client.get(f"/api/world/characters/{ids[0]}/league"))
        alloc = view["allocation"]
        assert alloc is not None and alloc["points"] > 0
        assert sum(alloc["auto"].values()) == alloc["points"]
        custom = {"con": alloc["points"]}
        _ok(
            client.post(
                f"/api/world/characters/{ids[0]}/actions",
                json={"kind": "league_enter", "allocation": custom},
            )
        )
        bad = client.post(
            f"/api/world/characters/{ids[1]}/actions",
            json={"kind": "league_enter", "allocation": {"con": alloc["points"] + 1}},
        )
        assert bad.status_code == 422
        for cid in ids[1:]:
            _ok(client.post(f"/api/world/characters/{cid}/actions", json={"kind": "league_enter"}))
        view = _ok(client.get(f"/api/world/characters/{ids[0]}/league"))
        assert view["entry"]["allocation"] == custom
        assert "HP ×2" in view["rules_zh"] and "開場休戰" in view["rules_zh"]
        store.clock = lambda: AFTER
        view = _ok(client.get(f"/api/world/characters/{ids[0]}/league", params={"page_size": 4}))
        assert view["status"] in ("running", "done")  # 自動開跑
        store.league_runner.join(120)
        view = _ok(client.get(f"/api/world/characters/{ids[0]}/league", params={"page_size": 4}))
        assert view["status"] == "done" and view["total"] == 6
        assert view["pages"] == 2 and view["page"] == 1 and len(view["matches"]) == 4
        assert all(m["mine"] for m in view["matches"])  # 自己的在前
        last = _ok(
            client.get(f"/api/world/characters/{ids[0]}/league", params={"page_size": 4, "page": 9})
        )
        assert last["page"] == 2 and len(last["matches"]) == 2
        assert all(" 勝（" in m["result_zh"] or "和局" in m["result_zh"] for m in view["matches"])
        season = store.league.chronicle.season(store.world().season_id)
        assert season is not None and len(season.ranks) == 3
        match_id = view["matches"][0]["id"]
        _ok(client.post(f"/api/world/characters/{ids[0]}/league/matches/{match_id}/replay"))
        # 規則改了：標示不能重播、重播 409；管理者再開跑＝整個重跑
        record = store.league.record()
        assert record is not None
        store.league._save(record.model_copy(update={"rules_key": "old"}))
        view = _ok(client.get(f"/api/world/characters/{ids[0]}/league"))
        assert view["stale_zh"] is not None and "規則已變" in view["stale_zh"]
        assert not any(m["replayable"] for m in view["matches"])
        assert {m["replay_problem_zh"] for m in view["matches"]} == {"規則已變、不能重播"}
        reply = client.post(f"/api/world/characters/{ids[0]}/league/matches/{match_id}/replay")
        assert reply.status_code == 409
        run = _ok(client.post("/api/world/league/run"))
        assert run["done"] == 0 and run["total"] == 6
        store.league_runner.join(120)
        view = _ok(client.get(f"/api/world/characters/{ids[0]}/league"))
        assert view["status"] == "done" and view["stale_zh"] is None and view["reruns"] == 1
