"""``dev_mode=false`` 時的端點保護（Phase 5D-R2，保守代決，待使用者確認）。

- runs／battles／workshop／gear 要登入（沒 token 401）；開發模式開照舊不用登入。
- 開發用端點（``/api/runs/dev-packs``、``/api/runs/{id}/dev-advance``）與存檔列表、讀檔
  （``/api/runs/saves``、``/api/runs/load``）開發模式關時不掛載。
- ``/api/maps`` 等內容端點與 ``/api/auth`` 不受影響。

測試裡的密碼一律用 ``secrets`` 當場產生。
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore

RUN = {"seed": 1, "weapon": "fire_staff", "keywords": ["ignite", "marked"]}

GUARDED = (
    ("GET", "/api/runs/start-options"),
    ("GET", "/api/runs/rules"),
    ("POST", "/api/runs"),
    ("GET", "/api/runs/r123"),
    ("GET", "/api/battles/b123"),
    ("GET", "/api/workshop/weapons"),
    ("GET", "/api/gear/catalog"),
)


def _make(library: ContentLibrary, saves: Path, *, dev_mode: bool) -> TestClient:
    app = create_app(library, save_dir=saves, accounts=AccountSettings(dev_mode=dev_mode))
    return TestClient(app)


@pytest.fixture
def locked(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _make(library, tmp_path / "saves", dev_mode=False) as c:
        yield c


@pytest.fixture
def dev(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _make(library, tmp_path / "saves", dev_mode=True) as c:
        yield c


def _login(client: TestClient) -> dict[str, str]:
    pw = secrets.token_urlsafe(12)
    store = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(store, AccountStore)
    store.create("alice", pw)
    reply = client.post("/api/auth/login", json={"username": "alice", "password": pw})
    assert reply.status_code == 200, reply.text
    return {"Authorization": f"Bearer {reply.json()['token']}"}


@pytest.mark.parametrize(("method", "path"), GUARDED)
def test_guarded_routes_need_login_when_dev_mode_off(
    locked: TestClient, method: str, path: str
) -> None:
    reply = locked.request(method, path, json=RUN if method == "POST" else None)
    assert reply.status_code == 401, reply.text
    assert reply.json()["detail"] == "請先登入"
    bad = locked.request(method, path, headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


def test_logged_in_player_can_play_a_run(locked: TestClient) -> None:
    headers = _login(locked)
    assert locked.get("/api/runs/start-options", headers=headers).status_code == 200
    created = locked.post("/api/runs", json=RUN, headers=headers)
    assert created.status_code == 201, created.text
    run_id = created.json()["run_id"]
    assert locked.get(f"/api/runs/{run_id}", headers=headers).status_code == 200
    assert locked.post(f"/api/runs/{run_id}/save", headers=headers).status_code == 200
    assert locked.get("/api/gear/catalog", headers=headers).status_code == 200


def test_dev_and_save_routes_not_mounted_when_dev_mode_off(locked: TestClient) -> None:
    headers = _login(locked)
    paths = set(locked.app.openapi()["paths"])  # type: ignore[attr-defined]
    for path in (
        "/api/runs/dev-packs",
        "/api/runs/saves",
        "/api/runs/load",
        "/api/runs/{run_id}/dev-advance",
    ):
        assert path not in paths
    created = locked.post("/api/runs", json=RUN, headers=headers).json()
    run_id = created["run_id"]
    # /saves 落到 /{run_id}：沒有這一輪（404）；/load 沒有 POST 路由（405）
    assert locked.get("/api/runs/saves", headers=headers).status_code == 404
    assert locked.get("/api/runs/dev-packs", headers=headers).status_code == 404
    load = locked.post("/api/runs/load", json={"run_id": run_id}, headers=headers)
    assert load.status_code == 405
    advance = locked.post(f"/api/runs/{run_id}/dev-advance?to=ended", headers=headers)
    assert advance.status_code in {404, 405}


def test_dev_mode_on_keeps_old_behaviour(dev: TestClient) -> None:
    for method, path in GUARDED:
        reply = dev.request(method, path, json=RUN if method == "POST" else None)
        assert reply.status_code != 401, (path, reply.text)
    assert dev.get("/api/runs/saves").status_code == 200
    assert dev.get("/api/runs/dev-packs").status_code == 200
    paths = set(dev.app.openapi()["paths"])  # type: ignore[attr-defined]
    assert "/api/runs/load" in paths and "/api/runs/{run_id}/dev-advance" in paths


def test_content_and_auth_routes_stay_open(locked: TestClient) -> None:
    assert locked.get("/api/maps").status_code == 200
    assert locked.get("/api/glossary").status_code == 200
    assert locked.get("/api/auth/status").status_code == 200
