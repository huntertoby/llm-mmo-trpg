"""開發用 Boss 戰入口（Phase 6F-3）：``POST /api/world/characters/{id}/dev-boss``。

- 開發模式＋``TRPG_DEV_ROUTES=1``：雲頂觀的霧鎖真人直接開打（正式的 Boss 陣容與地圖）。
- 不碰世界：角色存檔、世界日誌、進行中的戰鬥都不變（主線限制照舊）。
- 沒設環境變數 404；開發模式關時不掛載。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


def _client(library: ContentLibrary, saves: Path, *, dev_mode: bool) -> TestClient:
    settings = AccountSettings(dev_mode=dev_mode)
    return TestClient(create_app(library, save_dir=saves, accounts=settings))


@pytest.fixture
def dev(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(library, tmp_path / "saves", dev_mode=True) as c:
        yield c


def _create(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/world/characters", json=START)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _names(battle: dict[str, Any]) -> list[str]:
    return [str(u.get("name_zh", "")) for u in battle["view"]["units"]]


def test_dev_boss_opens_the_real_boss_fight_without_touching_the_world(
    dev: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    before = dev.get(f"/api/world/characters/{cid}").json()
    log = tmp_path / "saves" / "world" / "log.jsonl"
    log_before = log.read_text(encoding="utf-8") if log.exists() else ""
    reply = dev.post(f"/api/world/characters/{cid}/dev-boss", params={"level": 6})
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert data["title_zh"] == "開發：雲頂觀"
    assert any("霧鎖真人" in n for n in _names(data["battle"]))
    # 世界不變：日誌、角色的地點與遭遇
    after = dev.get(f"/api/world/characters/{cid}").json()
    assert (log.read_text(encoding="utf-8") if log.exists() else "") == log_before
    assert after["character"] == before["character"]
    assert [loc["id"] for loc in after["map"]["locations"] if loc["current"]] == [
        loc["id"] for loc in before["map"]["locations"] if loc["current"]
    ]
    assert after["encounter"] is None
    # 這場戰鬥照一般的 /api/battles 操作
    bid = data["battle"]["battle_id"]
    assert dev.get(f"/api/battles/{bid}").status_code == 200
    json.dumps(data)  # 可序列化


def test_dev_boss_needs_the_env_flag(dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRPG_DEV_ROUTES", raising=False)
    cid = _create(dev)["character"]["character_id"]
    assert dev.post(f"/api/world/characters/{cid}/dev-boss").status_code == 404


def test_dev_boss_is_not_mounted_outside_dev_mode(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    with _client(library, tmp_path / "saves", dev_mode=False) as locked:
        reply = locked.post("/api/world/characters/c1/dev-boss")
        assert reply.status_code in (401, 403, 404, 405)
        assert reply.status_code != 200


def test_dev_boss_rejects_towns(dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    reply = dev.post(
        f"/api/world/characters/{cid}/dev-boss",
        params={"location": "mist_ferry", "region": "cloud_ridge"},
    )
    assert reply.status_code in (409, 422), reply.text


def test_dev_boss_rehearses_to_the_boss_charge(
    dev: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ai_until=charge``：AI 代打到 Boss 蓄力中、輪到主角（截圖 Boss 大招用）；還是不碰世界。"""
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    reply = dev.post(
        f"/api/world/characters/{cid}/dev-boss", params={"level": 8, "ai_until": "charge"}
    )
    assert reply.status_code == 200, reply.text
    battle = reply.json()["battle"]
    assert battle["awaiting"] == "action"
    boss = next(u for u in battle["view"]["units"] if "霧鎖真人" in u["name_zh"])
    assert "charging" in [s.get("status_id") for s in boss["statuses"]]
    assert dev.get(f"/api/world/characters/{cid}").json()["encounter"] is None
