"""外觀選項的 API（Phase 6R-2，#137）：建角收 ``look``（在種族清單內才收）、``change_look`` 動作、
世界畫面角色欄的 ``look``／``look_change_zh``。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.content.library import ContentLibrary

START = {
    "name": "小美",
    "weapon": "dagger",
    "keywords": ["frozen", "concealed"],
    "seed": 0,
    "race": "fox",
    "look": {"hair": "twin", "beast_ears": "rabbit", "lashes": True, "eye_style": "big"},
}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_create_with_look_and_change_in_capital(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    me = view["character"]
    assert me["look"]["hair"] == "twin" and me["look"]["beast_ears"] == "rabbit"
    url = f"/api/world/characters/{me['character_id']}/actions"
    if me["look_change_zh"] is not None:
        assert "主城" in me["look_change_zh"]
        refused = client.post(url, json={"kind": "change_look", "look": {"hair": "long"}})
        assert refused.status_code >= 400 and "主城" in refused.text
        _ok(client.post(url, json={"kind": "teleport", "region": "capital"}))
    changed = _ok(client.post(url, json={"kind": "change_look", "look": {"hair": "long"}}))
    assert changed["character"]["look"] == {
        k: (v if k == "hair" else None) for k, v in changed["character"]["look"].items()
    } | {"hair": "long"}
    assert any("外觀" in line for line in changed["events"])
    reset = _ok(client.post(url, json={"kind": "change_look"}))
    assert reset["character"]["look"] is None


def test_create_rejects_look_outside_race(client: TestClient) -> None:
    bad = {**START, "race": "elf", "look": {"beard": "full"}}
    reply = client.post("/api/world/characters", json=bad)
    assert reply.status_code == 422 and "鬍子" in reply.text
    unknown = {**START, "look": {"gender": "f"}}
    assert client.post("/api/world/characters", json=unknown).status_code == 422
