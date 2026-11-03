"""開發用欄位的後端拒絕（Phase 6S-1，使用者「當然擋」）。

表格測試：每個帶開發用欄位的入口 ×（開發模式開／關）×（登入／未登入）。

- 開發模式關：登入了送開發用欄位 → 403，訊息寫「開發模式才能用」與欄位名；未登入 401（先要登入）。
- 開發模式開：照舊（不會 403）。
- 一般玩家的請求（不帶開發用欄位）開發模式關也照常。

「別人」不適用：這些都是建立或檢查用的請求，沒有既有的資源。測試裡的密碼用 ``secrets`` 產生。
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore

BUILD = "build_charger"
KEYWORDS = {"weapon": "fire_staff", "keywords": ["ignite", "marked"]}
TEST_START = {"weapon": "one_handed_sword", "keywords": ["ignite", "prone"], "seed": 3}
MAP = {"map_id": "open_plain", "seed": 7}

DEV_CASES: tuple[tuple[str, str, dict[str, Any], tuple[str, ...]], ...] = (
    ("run_build", "/api/runs", {"seed": 1, "build": BUILD}, ("build",)),
    ("run_dev_pack", "/api/runs", {"seed": 1, "dev_pack": "{pack}"}, ("dev_pack",)),
    ("run_test_mode", "/api/runs", {**TEST_START, "test_mode": True}, ("test_mode",)),
    (
        "run_test_equipment",
        "/api/runs",
        {**TEST_START, "test_mode": True, "test_equipment": {"body": "item_test_armor"}},
        ("test_equipment", "test_mode"),
    ),
    ("battle_hero_build", "/api/battles", {**MAP, "hero_build": BUILD}, ("hero_build",)),
    ("battle_dev_pack", "/api/battles", {**MAP, "dev_pack": "{pack}"}, ("dev_pack",)),
    (
        "battle_ally_builds",
        "/api/battles",
        {**MAP, **KEYWORDS, "ally_builds": [BUILD]},
        ("ally_builds",),
    ),
    (
        "battle_equipment",
        "/api/battles",
        {**MAP, **KEYWORDS, "equipment": {"body": {"item_id": "item_test_armor"}}},
        ("equipment",),
    ),
    ("gear_hero_build", "/api/gear/check", {"hero_build": BUILD}, ("hero_build",)),
    ("gear_dev_pack", "/api/gear/check", {"dev_pack": "{pack}"}, ("dev_pack",)),
    (
        "workshop_allow_illegal",
        "/api/workshop/export",
        {"skill": {}, "allow_illegal": True},
        ("allow_illegal",),
    ),
)
PLAYER_CASES: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("run", "/api/runs", {"seed": 1, **KEYWORDS}),
    ("battle", "/api/battles", {**MAP, **KEYWORDS}),
    ("battle_solo_tryout", "/api/battles", {**MAP, **KEYWORDS, "ally_builds": []}),
    ("gear_check", "/api/gear/check", {**KEYWORDS}),
    ("workshop_export", "/api/workshop/export", {"skill": {}}),
)


@pytest.fixture(scope="module", params=[False, True], ids=["dev_off", "dev_on"])
def server(
    request: pytest.FixtureRequest,
    library: ContentLibrary,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[TestClient, bool, dict[str, str]]]:
    dev = bool(request.param)
    saves = tmp_path_factory.mktemp("saves")
    app = create_app(library, save_dir=Path(saves), accounts=AccountSettings(dev_mode=dev))
    with TestClient(app) as client:
        store = app.state.accounts
        assert isinstance(store, AccountStore)
        pw = secrets.token_urlsafe(12)
        store.create("alice", pw)
        reply = client.post("/api/auth/login", json={"username": "alice", "password": pw})
        assert reply.status_code == 200, reply.text
        yield client, dev, {"Authorization": f"Bearer {reply.json()['token']}"}


def _fill(body: dict[str, Any], library: ContentLibrary) -> dict[str, Any]:
    pack = library.dev_starters.packs[0].id
    return {k: pack if v == "{pack}" else v for k, v in body.items()}


@pytest.mark.parametrize(
    ("path", "body", "fields"), [c[1:] for c in DEV_CASES], ids=[c[0] for c in DEV_CASES]
)
def test_dev_fields_need_dev_mode(
    server: tuple[TestClient, bool, dict[str, str]],
    library: ContentLibrary,
    path: str,
    body: dict[str, Any],
    fields: tuple[str, ...],
) -> None:
    client, dev, token = server
    for logged_in in (False, True):  # 未登入、登入
        reply = client.post(path, json=_fill(body, library), headers=token if logged_in else {})
        if dev:
            assert reply.status_code not in (401, 403), (logged_in, reply.text)
        elif not logged_in:
            assert reply.status_code == 401, reply.text
        else:
            assert reply.status_code == 403, reply.text
            detail = reply.json()["detail"]
            assert "開發模式才能用" in detail
            assert detail.startswith("、".join(fields)), detail


@pytest.mark.parametrize(
    ("path", "body"), [c[1:] for c in PLAYER_CASES], ids=[c[0] for c in PLAYER_CASES]
)
def test_player_requests_still_work(
    server: tuple[TestClient, bool, dict[str, str]], path: str, body: dict[str, Any]
) -> None:
    client, _dev, token = server
    reply = client.post(path, json=body, headers=token)
    assert reply.status_code not in (401, 403), reply.text
    if path != "/api/workshop/export":  # 空技能匯出本來就 422（技能不完整）
        assert reply.status_code in (200, 201), reply.text
