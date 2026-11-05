"""這一季的免費換種族（Phase 6R-1，#138）：走一般的動作端點 ``change_race``；世界畫面的角色欄
帶 ``race``、``free_race_change``、``free_race_change_zh``。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary

START = {
    "name": "阿霧",
    "weapon": "dagger",
    "keywords": ["frozen", "concealed"],
    "seed": 0,
    "race": "fox",
}


@pytest.fixture
def client(field_library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    app = create_app(calm, save_dir=tmp_path / "saves")
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    with TestClient(app) as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_free_race_change_through_the_action_endpoint(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    me = view["character"]
    assert (me["race"], me["race_name_zh"]) == ("fox", "獸耳族")
    assert me["free_race_change"] is True
    url = f"/api/world/characters/{me['character_id']}/actions"
    if me["free_race_change_zh"] is not None:  # 測試內容庫的新角色出生在霧渡鎮：先傳回主城
        assert me["free_race_change_zh"] == "只有在主城能換種族"
        refused = client.post(url, json={"kind": "change_race", "race": "elf"})
        assert refused.status_code >= 400 and "主城" in refused.text
        moved = _ok(client.post(url, json={"kind": "teleport", "region": "capital"}))
        assert moved["character"]["free_race_change_zh"] is None
    changed = _ok(client.post(url, json={"kind": "change_race", "race": "elf"}))
    assert changed["character"]["race"] == "elf"
    assert changed["character"]["free_race_change"] is False
    assert any("換成精靈" in line for line in changed["events"])
    again = client.post(url, json={"kind": "change_race", "race": "fox"})
    assert again.status_code >= 400 and "已經用過" in again.text
