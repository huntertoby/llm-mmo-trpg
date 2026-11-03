"""``/api/world`` 的實地地圖：``WorldView.field``、``walk``、``use_teleport_stone``（6B-2）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, hero, with_rules
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.api.world_field_view import field_view
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.layout import LOG_FILE
from trpg.world.save import loads_char, read_log
from trpg.world.state import FieldPos
from trpg.world.step import new_character

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


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


def _act(client: TestClient, cid: str, **action: Any) -> Any:
    return client.post(f"/api/world/characters/{cid}/actions", json=action)


def test_view_has_field(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    field = view["field"]
    assert field["map_id"] == "mist_ferry"
    assert field["name_zh"] == "霧渡鎮"
    assert (field["width"], field["height"]) == (24, 18)
    assert len(field["tiles"]) == 24 * 18
    assert field["tiles"][0] == {
        "x": 0,
        "y": 0,
        "height": 1,
        "terrain": "grass",
        "surface": "none",
        "walkable": True,
    }
    tiles = {(t["x"], t["y"]): t for t in field["tiles"]}
    assert tiles[(1, 2)]["walkable"] is False  # 牆（建築）
    assert tiles[(13, 7)]["walkable"] is False  # NPC 站的格子
    assert field["max_climb"] >= 1
    assert field["hero"]["weapon_id"] == "fire_staff"
    assert field["hero"]["weapon_class"] == "focus"
    assert field["me"] == {"x": 11, "y": 9, "facing": "s"}
    assert {e["id"] for e in field["exits"]} == {
        "to_hunter_hut",
        "to_ferry_steps",
        "to_ashen_ferry",
    }
    assert {d["to_name_zh"] for d in field["doors"]} == {"霧渡鎮酒館", "石記鐵鋪"}
    assert field["stones"] == [{"id": "stone_mist_ferry", "x": 12, "y": 8, "unlocked": False}]
    assert [(n["name_zh"], n["x"], n["y"]) for n in field["npcs"]] == [
        ("渡婆婆", 13, 7),
        ("柳掌櫃", 15, 12),
    ]
    assert {f["kind"] for f in field["facilities"]} == {"shop", "notice_board", "mentor"}


def test_walk_and_stone_actions(client: TestClient, tmp_path: Path) -> None:
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    view = _ok(_act(client, cid, kind="walk", path=[[11, 8], [12, 8]]))
    assert view["field"]["me"] == {"x": 12, "y": 8, "facing": "e"}
    assert view["field"]["stones"][0]["unlocked"] is True
    assert any("傳送石" in e for e in view["events"])
    reply = _act(client, cid, kind="use_teleport_stone", to="stone_mist_ferry")
    assert reply.status_code == 422 and "已經在" in reply.json()["detail"]
    reply = _act(client, cid, kind="travel", to="hunter_hut")
    assert reply.status_code == 422 and "請走到出口" in reply.json()["detail"]
    reply = _act(client, cid, kind="walk", path=[[x, 8] for x in range(13, 13 + 31)])
    assert reply.status_code == 422  # 超過 30 格：請求格式不合法
    view = _ok(_act(client, cid, kind="walk", path=[[x, 8] for x in range(13, 24)]))
    assert view["here"]["location"] == "ferry_steps"
    assert view["field"]["map_id"] == "ferry_steps"
    assert view["field"]["me"] == {"x": 1, "y": 8, "facing": "e"}
    assert any("渡口石階" in e for e in view["events"])
    # 日誌記整串路徑（不合法的動作不寫）；角色存檔有位置與解鎖的傳送石
    root = tmp_path / "saves" / "world"
    log = read_log((root / LOG_FILE).read_text(encoding="utf-8"))
    assert log.stale_through is None
    assert [e.action.kind for e in log.entries] == ["walk", "walk"]
    assert len(getattr(log.entries[1].action, "path", ())) == 11
    saved = loads_char((root / "chars" / f"{cid}.json").read_text(encoding="utf-8"))
    assert saved.format == "trpg-char/2"
    assert saved.field is not None and (saved.field.map, saved.field.x) == ("ferry_steps", 1)
    assert saved.teleport_stones == ("stone_mist_ferry",)


def test_old_log_marked_stale(client: TestClient, tmp_path: Path) -> None:
    """``trpg-wlog/1`` 的舊日誌：照讀、寫回時標頭記下「規則已變、不能重播」到哪一筆。"""
    cid = _ok(client.post("/api/world/characters", json=START), 201)["character"]["character_id"]
    _ok(_act(client, cid, kind="walk", path=[[12, 9]]))
    path = tmp_path / "saves" / "world" / LOG_FILE
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(['{"format": "trpg-wlog/1"}', *lines[1:]]) + "\n", encoding="utf-8")
    store = client.app.state.world  # type: ignore[attr-defined]
    store._forget()  # 重新讀檔（同伺服器重啟）
    _ok(_act(client, cid, kind="walk", path=[[13, 9]]))
    log = read_log(path.read_text(encoding="utf-8"))
    assert log.stale_through == 1
    assert log.stale_zh == "規則已變、不能重播"
    assert [e.seq for e in log.entries] == [1, 2]


def test_field_view_stone_targets(field_library: ContentLibrary) -> None:
    """站在傳送石上時列出其他已解鎖的傳送石（6B-3 的「傳送」按鈕用）；不在石上＝空。"""
    herb = FieldMapDef.model_validate(
        {
            "id": "herb_valley",
            "region": "cloud_ridge",
            "location": "herb_valley",
            "size": [4, 4],
            "heights": "0000\n" * 4,
            "terrain": "....\n" * 4,
            "legend": {".": "stone"},
            "entry": [1, 2],
            "teleport_stones": [{"id": "stone_herb", "at": [1, 1]}],
        }
    )
    library = dataclasses.replace(
        field_library, field_maps={**field_library.field_maps, "herb_valley": herb}
    )
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    stones = ("stone_herb", "stone_mist_ferry")
    on_stone = char.model_copy(
        update={"field": FieldPos(map="mist_ferry", x=12, y=8), "teleport_stones": stones}
    )
    view = field_view(library, on_stone)
    assert view is not None
    assert [(t.id, t.name_zh) for t in view.stone_targets] == [("stone_herb", "藥師谷")]
    off = on_stone.model_copy(update={"field": FieldPos(map="mist_ferry", x=11, y=9)})
    off_view = field_view(library, off)
    assert off_view is not None
    assert off_view.stone_targets == ()
