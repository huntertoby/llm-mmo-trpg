"""一輪的測試模式的 API（Phase 3-39）：開局、標記、存檔列表、讀檔、不合法裝備。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import ContentLibrary

_BODY: dict[str, Any] = {"weapon": "one_handed_sword", "keywords": ["ignite", "prone"], "seed": 3}
_GEAR = {"main_hand": "item_test_sword", "body": "item_test_armor"}


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=tmp_path / "saves")) as c:
        yield c


def _ok(reply: Any) -> Any:
    assert reply.status_code in (200, 201), reply.text
    return reply.json()


def test_test_mode_run_is_marked_listed_and_loadable(client: TestClient) -> None:
    body = {**_BODY, "test_mode": True, "test_equipment": _GEAR}
    run = _ok(client.post("/api/runs", json=body))
    assert run["test_mode"] is True and run["test_equipment"] == _GEAR
    assert [s["test_mode"] for s in _ok(client.get("/api/runs/saves"))] == [True]
    assert _ok(client.get(f"/api/runs/{run['run_id']}"))["test_mode"] is True
    loaded = _ok(client.post("/api/runs/load", json={"run_id": run["run_id"]}))
    assert loaded["test_mode"] is True and loaded["test_equipment"] == _GEAR


def test_test_mode_equipment_reaches_the_battle(client: TestClient) -> None:
    body = {**_BODY, "test_mode": True, "test_equipment": _GEAR}
    run = _ok(client.post("/api/runs", json=body))
    battle = _ok(client.post(f"/api/runs/{run['run_id']}/battle"))["battle"]
    hero = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    assert {e["slot"]: e["item_id"] for e in hero["equipment"]} == _GEAR


def test_normal_run_is_not_test_mode(client: TestClient) -> None:
    run = _ok(client.post("/api/runs", json=_BODY))
    assert run["test_mode"] is False and run["test_equipment"] == {}
    assert [s["test_mode"] for s in _ok(client.get("/api/runs/saves"))] == [False]


@pytest.mark.parametrize(
    ("extra", "text"),
    [
        ({"test_mode": True, "test_equipment": {"head": "item_test_armor"}}, "只能放"),
        ({"test_equipment": {"body": "item_test_armor"}}, "測試模式"),
        ({"test_mode": True, "weapon": None, "keywords": None, "build": "build_push"}, "測試模式"),
    ],
)
def test_test_mode_rejects_bad_requests(
    client: TestClient, extra: dict[str, Any], text: str
) -> None:
    reply = client.post("/api/runs", json={**_BODY, **extra})
    assert reply.status_code == 422 and text in reply.text
