"""``/api/world`` 的實地地圖：``WorldView.field``、``walk``、``use_teleport_stone``（6B-2）。"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, hero, with_rules
from trpg.api.world_field_view import field_view
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.layout import LOG_FILE
from trpg.world.save import loads_char, read_log
from trpg.world.state import FieldPos
from trpg.world.step import new_character

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _act(client: TestClient, cid: str, **action: Any) -> Any:
    return client.post(f"/api/world/characters/{cid}/actions", json=action)


def test_view_has_field(client: TestClient, field_library: ContentLibrary) -> None:
    """畫面的 ``field`` 照內容資料投影（座標、高度都從地圖定義算，不寫死正式內容的數字）。"""
    found = field_library.field_maps["mist_ferry"]
    view = _ok(client.post("/api/world/characters", json=START), 201)
    field = view["field"]
    assert field["map_id"] == "mist_ferry"
    assert field["name_zh"] == found.name_zh
    assert (field["width"], field["height"]) == (found.width, found.height)
    assert field["tiles"] == []  # 6C-R3：地形另外取，依雜湊快取
    assert field["walk_max_steps"] == 30  # 6P-2：規則 field.walk_max_steps，前端照這個分段送
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/fields/mist_ferry?h={field['tiles_hash']}"
    static = _ok(client.get(url))
    assert static["hash"] == field["tiles_hash"]
    assert len(static["tiles"]) == found.width * found.height
    grid = found.grid()
    assert [(t["x"], t["y"], t["height"], t["terrain"]) for t in static["tiles"]] == [
        (x, y, h, terrain) for y, row in enumerate(grid) for x, (h, terrain) in enumerate(row)
    ]
    tiles = {(t["x"], t["y"]): t for t in static["tiles"]}
    walls = [(t["x"], t["y"]) for t in static["tiles"] if t["terrain"] == "wall"]
    assert walls and all(tiles[c]["walkable"] is False for c in walls)  # 牆（建築）
    assert all(tiles[npc.at]["walkable"] is False for npc in found.npcs)  # NPC 站的格子
    assert tiles[found.entry]["walkable"] is True
    assert field["max_climb"] == field_library.ruleset.core.max_climb_height
    assert field["hero"]["weapon_id"] == "fire_staff"
    assert field["hero"]["weapon_class"] == "focus"
    assert (field["me"]["x"], field["me"]["y"]) == found.entry
    assert {e["id"] for e in field["exits"]} == {e.id for e in found.exits}
    assert {d["id"] for d in field["doors"]} == {
        d.id for d in found.doors if d.hidden_until != "reveal"
    }
    assert field["stones"] == [
        {"id": s.id, "x": s.at[0], "y": s.at[1], "unlocked": False} for s in found.teleport_stones
    ]
    assert [(n["id"], n["x"], n["y"]) for n in field["npcs"]] == [
        (n.id, n.at[0], n.at[1]) for n in found.npcs
    ]
    assert all(n["name_zh"] != n["id"] for n in field["npcs"])  # 名字來自人設卡
    assert {f["kind"] for f in field["facilities"]} == {f.id for f in found.facilities}


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
    assert reply.status_code == 422  # 超過規則的 30 格（6P-2：處理時檢查，訊息說清楚）
    assert "一次最多走 30 格（這次送了 31 格" in reply.json()["detail"]
    view = _ok(_act(client, cid, kind="walk", path=[[x, 8] for x in range(13, 24)]))
    assert view["here"]["location"] == "ferry_steps"
    assert view["field"]["map_id"] == "ferry_steps"
    assert view["field"]["me"] == {"x": 1, "y": 8, "facing": "e"}
    assert any("渡口石階" in e for e in view["events"])
    # 日誌記整串路徑（不合法的動作不寫）；角色存檔有位置與解鎖的傳送石
    root = tmp_path / "saves" / "world"
    log = read_log((root / LOG_FILE).read_text(encoding="utf-8"))
    assert log.stale_through is None
    # 進渡口石階時可能擲出地點事件（角色 ID 每次不同，亂數跟著變），說書紀錄 `narrate` 不在這裡比
    walks = [e for e in log.entries if e.action.kind != "narrate"]
    assert [e.action.kind for e in walks] == ["walk", "walk"]
    assert len(getattr(walks[1].action, "path", ())) == 11
    saved = loads_char((root / "chars" / f"{cid}.json").read_text(encoding="utf-8"))
    assert saved.format == "trpg-char/14"
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
