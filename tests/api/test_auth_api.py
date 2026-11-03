"""``/api/auth`` 與大世界依帳號存取（Phase 5E-1；``docs/phases/Phase5計畫.md`` 28.6）。

測試裡的密碼一律用 ``secrets`` 當場產生。
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.account_config import AccountSettings
from trpg.api.accounts import AccountStore
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


def _make(library: ContentLibrary, saves: Path, *, dev_mode: bool, limit: int = 2) -> TestClient:
    settings = AccountSettings(dev_mode=dev_mode, max_characters=limit)
    app = create_app(library, save_dir=saves, accounts=settings)
    world = app.state.world
    assert isinstance(world, WorldStore)
    world.clock = lambda: NOON
    return TestClient(app)


def _accounts(client: TestClient) -> AccountStore:
    store = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(store, AccountStore)
    return store


@pytest.fixture
def locked(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _make(calm, tmp_path / "saves", dev_mode=False) as c:
        yield c


@pytest.fixture
def dev(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _make(calm, tmp_path / "saves", dev_mode=True) as c:
        yield c


def _login(client: TestClient, name: str) -> dict[str, str]:
    pw = secrets.token_urlsafe(12)
    _accounts(client).create(name, pw)
    reply = client.post("/api/auth/login", json={"username": name, "password": pw})
    assert reply.status_code == 200, reply.text
    body: dict[str, Any] = reply.json()
    assert body["account"]["username"] == name
    return {"Authorization": f"Bearer {body['token']}"}


def _create(client: TestClient, headers: dict[str, str] | None = None) -> str:
    reply = client.post("/api/world/characters", json=START, headers=headers or {})
    assert reply.status_code == 201, reply.text
    cid: str = reply.json()["character"]["character_id"]
    return cid


def test_status_reports_dev_mode(locked: TestClient, dev: TestClient) -> None:
    assert locked.get("/api/auth/status").json() == {"dev_mode": False, "account": None}
    assert dev.get("/api/auth/status").json() == {"dev_mode": True, "account": None}
    headers = _login(locked, "alice")
    account = locked.get("/api/auth/status", headers=headers).json()["account"]
    assert account["username"] == "alice"
    assert (account["characters"], account["max_characters"], account["can_create"]) == (0, 2, True)
    bad = {"Authorization": "Bearer nope"}
    assert locked.get("/api/auth/status", headers=bad).json()["account"] is None


def test_wrong_password_is_401(locked: TestClient) -> None:
    _accounts(locked).create("alice", secrets.token_urlsafe(12))
    reply = locked.post("/api/auth/login", json={"username": "alice", "password": "x" * 12})
    assert reply.status_code == 401
    assert reply.json() == {"detail": "帳號或密碼錯誤"}


def test_locked_world_needs_login(locked: TestClient) -> None:
    assert locked.get("/api/world/characters").status_code == 401
    assert locked.post("/api/world/characters", json=START).status_code == 401
    assert locked.get("/api/world/llm").status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert locked.get("/api/world/characters", headers=bad).status_code == 401


def test_accounts_only_see_own_characters(locked: TestClient) -> None:
    alice = _login(locked, "alice")
    bob = _login(locked, "bob")
    mine = _create(locked, alice)
    theirs = _create(locked, bob)
    listed = locked.get("/api/world/characters", headers=alice).json()
    assert [c["character_id"] for c in listed] == [mine]
    assert locked.get(f"/api/world/characters/{mine}", headers=alice).status_code == 200
    # 別人的角色：讀、動作、開戰都 404（不透露存在）
    assert locked.get(f"/api/world/characters/{theirs}", headers=alice).status_code == 404
    act = locked.post(
        f"/api/world/characters/{theirs}/actions", json={"kind": "rest"}, headers=alice
    )
    assert act.status_code == 404
    assert locked.post(f"/api/world/characters/{theirs}/battle", headers=alice).status_code == 404
    assert _accounts(locked).owner_of(mine) == _accounts(locked).find("alice").account_id  # type: ignore[union-attr]


def test_character_limit(locked: TestClient) -> None:
    alice = _login(locked, "alice")
    _create(locked, alice)
    _create(locked, alice)
    reply = locked.post("/api/world/characters", json=START, headers=alice)
    assert reply.status_code == 409
    assert "上限" in reply.json()["detail"]
    assert len(locked.get("/api/world/characters", headers=alice).json()) == 2
    status = locked.get("/api/auth/status", headers=alice).json()["account"]
    assert status["can_create"] is False


def test_logout_and_disable(locked: TestClient) -> None:
    alice = _login(locked, "alice")
    assert locked.post("/api/auth/logout", headers=alice).status_code == 204
    assert locked.get("/api/world/characters", headers=alice).status_code == 401
    bob = _login(locked, "bob")
    store = _accounts(locked)
    store.set_disabled(store.find("bob").account_id, True)  # type: ignore[union-attr]
    assert locked.get("/api/world/characters", headers=bob).status_code == 401


def test_dev_mode_keeps_open_access(dev: TestClient) -> None:
    open_id = _create(dev)
    alice = _login(dev, "alice")
    mine = _create(dev, alice)
    listed = {c["character_id"] for c in dev.get("/api/world/characters").json()}
    assert listed == {open_id, mine}  # 不帶 token：照 5A-5 列全部
    scoped = dev.get("/api/world/characters", headers=alice).json()
    assert [c["character_id"] for c in scoped] == [mine]  # 帶 token：依帳號
    assert dev.get(f"/api/world/characters/{open_id}", headers=alice).status_code == 404
    assert dev.get(f"/api/world/characters/{open_id}").status_code == 200


def test_llm_switch_needs_admin(locked: TestClient, dev: TestClient) -> None:
    off = {"enabled": False}
    assert locked.post("/api/world/llm", json=off).status_code == 401
    alice = _login(locked, "alice")
    reply = locked.post("/api/world/llm", json=off, headers=alice)
    assert reply.status_code == 403
    assert reply.json() == {"detail": "只有管理者能改 LLM 開關"}
    assert locked.get("/api/world/llm", headers=alice).status_code == 200  # 讀照舊
    root = _login(locked, "root")
    store = _accounts(locked)
    store.set_admin(store.find("root").account_id, True)  # type: ignore[union-attr]
    assert locked.post("/api/world/llm", json=off, headers=root).status_code == 200
    # 開發模式：沒帶 token 照舊可改；帶了非管理者的 token 一樣 403
    assert dev.post("/api/world/llm", json=off).status_code == 200
    bob = _login(dev, "bob")
    assert dev.post("/api/world/llm", json=off, headers=bob).status_code == 403
