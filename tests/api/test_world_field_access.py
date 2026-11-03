"""6D-R1：實地地圖靜態地形的存取（``GET /api/world/characters/{id}/fields/{map_id}``）與隱藏門。

權限表格：（自己／別人／未登入）×（目前地點／室內／去過／隱藏未發現／已發現／未解鎖區／不存在）。
看不到的圖和不存在的圖一樣 404、訊息相同（不能列舉地圖 ID）。測試裡的密碼一律用 ``secrets``
當場產生。
"""

from __future__ import annotations

import itertools
import secrets
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, hero
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.api.world_field_view import HIDDEN_DOOR_TERRAIN, field_tiles, field_view
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore
from trpg.world.field import placed
from trpg.world.state import CharacterState, LocationRef
from trpg.world.step import new_character

CHAR = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}
REGION = "cloud_ridge"

_NAMES = itertools.count()


@pytest.fixture
def server(field_library: ContentLibrary, tmp_path: Any) -> Iterator[TestClient]:
    app = create_app(
        field_library, save_dir=tmp_path / "saves", accounts=AccountSettings(dev_mode=False)
    )
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    with TestClient(app) as client:
        yield client


def _login(client: TestClient, name: str) -> dict[str, str]:
    store = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(store, AccountStore)
    username = f"{name}{next(_NAMES)}"
    pw = secrets.token_urlsafe(12)
    store.create(username, pw)
    reply = client.post("/api/auth/login", json={"username": username, "password": pw})
    assert reply.status_code == 200, reply.text
    return {"Authorization": f"Bearer {reply.json()['token']}"}


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _refs(*locations: str) -> tuple[LocationRef, ...]:
    return tuple(LocationRef(region=REGION, location=loc) for loc in sorted(locations))


def _hidden_door(library: ContentLibrary, map_id: str) -> tuple[str, tuple[int, int]]:
    """``map_id`` 上第一扇隱藏門的（通往的隱藏地點, 格子）：從內容推，不寫死座標。"""
    door = next(d for d in library.field_maps[map_id].doors if d.hidden_until == "reveal")
    return door.to, door.at


def _interior_of(library: ContentLibrary, location: str) -> str:
    return next(
        m.id for m in library.field_maps.values() if m.is_interior and m.interior_of == location
    )


def _ashen_map(library: ContentLibrary) -> str:
    return next(m.id for m in library.field_maps.values() if m.region == "ashen_waste")


# 情境：（名稱, 角色的 visited, revealed, 地圖 ID 的取法, 自己看得到）
CASES: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str, bool], ...] = (
    ("current", (), (), "mist_ferry", True),
    ("interior", (), (), "interior:mist_ferry", True),
    ("visited", ("herb_valley",), (), "herb_valley", True),
    ("not_visited", (), (), "herb_valley", False),
    ("hidden_not_revealed", ("herb_valley",), (), "hidden:herb_valley", False),
    ("hidden_revealed", ("herb_valley",), ("hidden:herb_valley",), "hidden:herb_valley", True),
    ("locked_region", (), (), "ashen", False),
    ("missing", (), (), "no_such_map", False),
)


def _resolve(library: ContentLibrary, spec: str) -> str:
    if spec.startswith("interior:"):
        return _interior_of(library, spec.removeprefix("interior:"))
    if spec.startswith("hidden:"):
        return _hidden_door(library, spec.removeprefix("hidden:"))[0]
    if spec == "ashen":
        return _ashen_map(library)
    return spec


@pytest.mark.parametrize("case", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_field_tiles_access_table(
    server: TestClient,
    field_library: ContentLibrary,
    case: tuple[tuple[str, ...], tuple[str, ...], str, bool],
) -> None:
    visited, revealed, spec, visible = case
    alice, bob = _login(server, "alice"), _login(server, "bob")
    made = server.post("/api/world/characters", json=CHAR, headers=alice)
    assert made.status_code == 201, made.text
    cid = made.json()["character"]["character_id"]
    store = _store(server)
    char = store.character(cid)
    assert (char.region, char.location) == (REGION, "mist_ferry")
    hidden = tuple(_resolve(field_library, r) for r in revealed)
    store._save_char(
        char.model_copy(update={"visited_locations": _refs(*visited), "revealed": _refs(*hidden)})
    )
    map_id = _resolve(field_library, spec)
    url = f"/api/world/characters/{cid}/fields/{map_id}"

    mine = server.get(url, headers=alice)
    if visible:
        assert mine.status_code == 200, mine.text
        assert mine.json()["map_id"] == map_id
    else:
        assert mine.status_code == 404, mine.text
        assert mine.json()["detail"] == f"找不到實地地圖 {map_id}"  # 和不存在的一樣
    other = server.get(url, headers=bob)
    assert other.status_code == 404 and other.json()["detail"] == f"找不到角色 {cid}"
    assert server.get(url).status_code == 401


def test_old_route_is_gone(server: TestClient) -> None:
    """舊的 ``GET /api/world/fields/{map_id}``（只檢查登入）不在了。"""
    alice = _login(server, "alice")
    assert server.get("/api/world/fields/mist_ferry", headers=alice).status_code == 404


# -- 隱藏門在靜態地形分不出來 ---------------------------------------------------


def _hidden_doors(library: ContentLibrary) -> list[tuple[str, tuple[int, int]]]:
    return sorted(
        (m.id, d.at)
        for m in library.field_maps.values()
        for d in m.doors
        if d.hidden_until == "reveal"
    )


def test_hidden_doors_look_like_walls_in_static_tiles(field_library: ContentLibrary) -> None:
    """每一扇隱藏門（正式內容的 herb_valley、north_slope、tar_pits 等，從內容推）：靜態地形畫成
    牆、沒有表面、不可站，和同一張圖上真的牆只差座標與高度；那一格沒有物件。"""
    doors = _hidden_doors(field_library)
    assert {m for m, _ in doors} >= {"herb_valley", "north_slope", "tar_pits"}
    terrain = field_library.ruleset.terrain.by_id()
    assert terrain[HIDDEN_DOOR_TERRAIN].walkable is False
    for map_id, at in doors:
        static = field_tiles(field_library, map_id)
        assert static is not None
        tile = next(t for t in static.tiles if (t.x, t.y) == at)
        assert (tile.terrain, tile.surface, tile.walkable) == (HIDDEN_DOOR_TERRAIN, "none", False)
        assert all(o.at != at for o in field_library.field_maps[map_id].objects)


def _herb_char(library: ContentLibrary, *, revealed: bool) -> CharacterState:
    char = new_character(library, "alice", hero(library), region=REGION)
    update: dict[str, Any] = {"location": "herb_valley", "field": None}
    if revealed:
        update["revealed"] = _refs(_hidden_door(library, "herb_valley")[0])
    return placed(library, char.model_copy(update=update))


def test_inline_tiles_also_hide_undiscovered_doors(field_library: ContentLibrary) -> None:
    """``with_tiles``（世界畫面直接帶地形）也一樣：沒發現＝牆；發現後＝真地形、站得上去。"""
    _to, at = _hidden_door(field_library, "herb_valley")
    raw = field_library.field_maps["herb_valley"].grid()[at[1]][at[0]]
    before = field_view(field_library, _herb_char(field_library, revealed=False))
    after = field_view(field_library, _herb_char(field_library, revealed=True))
    assert before is not None and after is not None
    hidden = next(t for t in before.tiles if (t.x, t.y) == at)
    assert hidden.terrain == HIDDEN_DOOR_TERRAIN and not hidden.walkable
    shown = next(t for t in after.tiles if (t.x, t.y) == at)
    assert (shown.height, shown.terrain) == raw and shown.walkable
    assert after.open_cells == (shown,) and before.open_cells == ()


def test_with_tiles_query_brings_tiles(server: TestClient) -> None:
    alice = _login(server, "alice")
    cid = server.post("/api/world/characters", json=CHAR, headers=alice).json()["character"][
        "character_id"
    ]
    lean = server.get(f"/api/world/characters/{cid}", headers=alice).json()["field"]
    full = server.get(f"/api/world/characters/{cid}?with_tiles=1", headers=alice).json()["field"]
    assert lean["tiles"] == [] and len(full["tiles"]) == full["width"] * full["height"]
    assert full["tiles_hash"] == lean["tiles_hash"]
