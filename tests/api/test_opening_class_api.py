"""#150 選大類的 API（Phase OB-1）：``opening_class`` 動作、``RangeView`` 帶階段、舊流程建角只留
開發模式。"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.routes.world import LEGACY_CREATE_ENV
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore

pytestmark = pytest.mark.capital_spawn

NEW = {"name": "小靶", "seed": 7, "race": "human"}
OLD_FLOW = {**NEW, "weapon": "dagger", "keywords": ["frozen", "concealed"]}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _store(client: TestClient) -> WorldStore:
    app: Any = client.app
    store = app.state.world
    assert isinstance(store, WorldStore)
    return store


def test_conftest_switch_matches_route_constant() -> None:
    assert LEGACY_CREATE_ENV == "TRPG_LEGACY_CREATE"


def test_range_view_carries_stage_and_starters(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    opening = view["opening"]
    assert opening["stage"] == "pick_class" and opening["weapon_class"] is None
    assert {r["weapon_class"]: r["starter_weapon"] for r in opening["racks"]} == {
        "melee": "one_handed_sword",
        "ranged": "bow",
        "focus": "fire_staff",
    }
    assert all(r["starter_weapon_zh"] for r in opening["racks"])


def test_opening_class_action(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    after = _ok(client.post(url, json={"kind": "opening_class", "weapon_class": "ranged"}))
    assert after["opening"]["stage"] == "starter"
    assert after["opening"]["weapon_class"] == "ranged"
    char = _store(client).character(cid)
    assert char.hero.weapon == "bow" and len(char.hero.skills) == 2
    # 入門期黑名單：換種族 422；傳送不被閘門擋
    refused = client.post(url, json={"kind": "change_race", "race": "elf"})
    assert refused.status_code == 422 and "入門期" in refused.text
    bad = client.post(url, json={"kind": "opening_class", "weapon_class": "melee"})
    assert bad.status_code == 422 and "大類已經選好" in bad.text


def test_opening_class_rejects_unknown_class(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=NEW), 201)
    url = f"/api/world/characters/{view['character']['character_id']}/actions"
    assert client.post(url, json={"kind": "opening_class", "weapon_class": "x"}).status_code == 422


def _server(
    library: ContentLibrary, tmp_path: Path, *, dev: bool
) -> tuple[TestClient, dict[str, str]]:
    app = create_app(library, save_dir=tmp_path, accounts=AccountSettings(dev_mode=dev))
    client = TestClient(app)
    client.__enter__()
    store = app.state.accounts
    assert isinstance(store, AccountStore)
    password = secrets.token_urlsafe(12)
    store.create("alice", password)
    reply = client.post("/api/auth/login", json={"username": "alice", "password": password})
    assert reply.status_code == 200, reply.text
    return client, {"Authorization": f"Bearer {reply.json()['token']}"}


@pytest.mark.parametrize(("dev", "status"), [(False, 403), (True, 201)])
def test_old_flow_create_needs_dev_mode(
    library: ContentLibrary,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dev: bool,
    status: int,
) -> None:
    monkeypatch.delenv(LEGACY_CREATE_ENV)
    client, token = _server(library, tmp_path, dev=dev)
    try:
        reply = client.post("/api/world/characters", json=OLD_FLOW, headers=token)
        assert reply.status_code == status, reply.text
        if status == 403:
            assert "開發模式才能用" in reply.text
        # 正式流程（不給武器與關鍵字）開發模式關也照常
        assert client.post("/api/world/characters", json=NEW, headers=token).status_code == 201
    finally:
        client.__exit__(None, None, None)


def test_old_flow_create_allowed_with_test_switch(library: ContentLibrary, tmp_path: Path) -> None:
    client, token = _server(library, tmp_path, dev=False)
    try:
        assert client.post("/api/world/characters", json=OLD_FLOW, headers=token).status_code == 201
    finally:
        client.__exit__(None, None, None)
