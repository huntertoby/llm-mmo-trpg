"""季末重置、編年史與沿用上季角色的端點（Phase 5F-5；``docs/phases/Phase5計畫.md`` 40.5）。

測試裡的密碼一律用 ``secrets`` 當場產生。存檔一律在 ``tmp_path``。
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.server_config import ServerSettings
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore

DAY = 24 * 3600
ENDED = NOON + 15 * DAY
START = {
    "name": "阿霧",
    "weapon": "fire_staff",
    "keywords": ["ignite", "marked"],
    "seed": 0,
    "race": "fox",
}
RESET = {"start_date": "2027-01-01"}


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


def _make(library: ContentLibrary, saves: Path, *, dev_mode: bool) -> TestClient:
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


@pytest.fixture
def dev(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _make(calm, tmp_path / "saves", dev_mode=True) as c:
        yield c


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _ok(reply: Any, status: int = 200) -> Any:
    assert reply.status_code == status, reply.text
    return reply.json()


def _login(client: TestClient, name: str, *, admin: bool = False) -> dict[str, str]:
    accounts = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(accounts, AccountStore)
    password = secrets.token_urlsafe(12)
    record = accounts.create(name, password)
    if admin:
        accounts.set_admin(record.account_id, True)
    body = {"username": name, "password": password}
    token = _ok(client.post("/api/auth/login", json=body))["token"]
    return {"Authorization": f"Bearer {token}"}


def _tree(root: Path) -> dict[str, bytes]:
    files = (p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix != ".lock")
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in files}


def test_dry_run_then_execute(dev: TestClient, tmp_path: Path) -> None:
    store = _store(dev)
    cid = _ok(dev.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    store.clock = lambda: ENDED
    before = _tree(tmp_path / "saves")
    preview = _ok(dev.post("/api/world/season/reset", json=RESET))
    assert preview["dry_run"] is True and preview["backup"] is None
    assert (preview["old_season"], preview["new_season"]) == ("s1", "s2")
    assert preview["chronicle"] == ["阿霧：第一季：走過這一季"]
    assert _tree(tmp_path / "saves") == before
    body = {**RESET, "dry_run": False, "confirm_season": "s1"}
    # 真的執行一律要管理者帳號，開發模式沒帶 token 也不行（開發 PM 代決）
    assert dev.post("/api/world/season/reset", json=body).status_code == 403
    assert _tree(tmp_path / "saves") == before
    admin = _login(dev, "boss", admin=True)
    wrong = dev.post("/api/world/season/reset", json={**RESET, "dry_run": False}, headers=admin)
    assert wrong.status_code == 409 and "確認的季 ID 不符" in wrong.json()["detail"]
    done = _ok(dev.post("/api/world/season/reset", json=body, headers=admin))
    assert done["backup"] is not None and Path(done["backup"]).is_dir()
    assert Path(done["backup"]).parent == tmp_path / "saves-backups"
    assert store.current_season() == "s2"
    assert _ok(dev.get("/api/world/characters")) == []
    assert dev.get(f"/api/world/characters/{cid}").status_code == 404
    chronicle = _ok(dev.get("/api/world/chronicle"))
    (s1,) = [s for s in chronicle["seasons"] if s["season_id"] == "s1"]
    assert s1["name_zh"] == "第一季" and s1["heroes"][0]["name"] == "阿霧"
    assert chronicle["current_season"] == "s2"
    (legacy,) = _ok(dev.get("/api/world/legacy"))
    assert (legacy["character_id"], legacy["race"], legacy["season_id"]) == (cid, "fox", "s1")
    again = {**START, "name": "別的名字", "race": None, "legacy_character": cid}
    view = _ok(dev.post("/api/world/characters", json=again), 201)
    new_cid = view["character"]["character_id"]
    assert new_cid != cid
    char = store.character(new_cid)
    assert (char.hero.name_zh, char.hero.race, char.level) == ("阿霧", "fox", 1)
    # 5F-5c：種族不算外觀——沿用時可以免費改種族，名字照沿用
    elf = {**START, "race": "elf", "legacy_character": cid}
    created = _ok(dev.post("/api/world/characters", json=elf), 201)
    changed = store.character(created["character"]["character_id"])
    assert (changed.hero.name_zh, changed.hero.race) == ("阿霧", "elf")
    assert dev.post("/api/world/season/reset", json=RESET).status_code == 409  # s2 還沒結束


def test_reset_needs_admin(calm: ContentLibrary, tmp_path: Path) -> None:
    with _make(calm, tmp_path / "saves", dev_mode=False) as client:
        player = _login(client, "alice")
        admin = _login(client, "boss", admin=True)
        assert client.post("/api/world/season/reset", json=RESET).status_code == 401
        reply = client.post("/api/world/season/reset", json=RESET, headers=player)
        assert reply.status_code == 403
        _ok(client.post("/api/world/characters", json=START, headers=admin), 201)
        status = _ok(client.get("/api/auth/status", headers=admin))
        assert status["account"]["admin"] is True
        assert _ok(client.get("/api/auth/status", headers=player))["account"]["admin"] is False
        _store(client).clock = lambda: ENDED
        preview = _ok(client.post("/api/world/season/reset", json=RESET, headers=admin))
        assert preview["dry_run"] is True


def test_legacy_is_per_account(calm: ContentLibrary, tmp_path: Path) -> None:
    with _make(calm, tmp_path / "saves", dev_mode=False) as client:
        alice = _login(client, "alice", admin=True)
        bob = _login(client, "bobby")
        reply = _ok(client.post("/api/world/characters", json=START, headers=alice), 201)
        cid = reply["character"]["character_id"]
        _store(client).clock = lambda: ENDED
        body = {**RESET, "dry_run": False, "confirm_season": "s1"}
        _ok(client.post("/api/world/season/reset", json=body, headers=alice))
        assert _ok(client.get("/api/world/legacy", headers=bob)) == []
        assert len(_ok(client.get("/api/world/legacy", headers=alice))) == 1
        steal = {**START, "legacy_character": cid}
        reply = client.post("/api/world/characters", json=steal, headers=bob)
        assert reply.status_code == 404
        status = _ok(client.get("/api/auth/status", headers=alice))
        assert status["account"]["can_create"] is True and status["account"]["characters"] == 0
        _ok(client.post("/api/world/characters", json=steal, headers=alice), 201)
        assert (
            _ok(client.get("/api/world/chronicle", headers=bob))["seasons"][0]["season_id"] == "s1"
        )
