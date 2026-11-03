"""6C-R3：實地地圖的靜態地形快取（``GET /api/world/fields/{map_id}``）與敵群帶頭單位的外觀。"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, hero, make_world
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.api.world_field_view import field_tiles, field_view
from trpg.content.library import ContentLibrary
from trpg.world.field import placed
from trpg.world.field_enemies import enemy_lineup, field_enemies
from trpg.world.state import CharacterState, LocationRef
from trpg.world.step import new_character

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


@pytest.fixture
def client(field_library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(field_library, save_dir=tmp_path / "saves")
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    with TestClient(app) as c:
        yield c


def _char(library: ContentLibrary, location: str, **updates: Any) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = placed(library, char.model_copy(update={"location": location, "field": None}))
    return char.model_copy(update=updates) if updates else char


# -- 靜態地形 -----------------------------------------------------------------


def test_static_tiles_cached_and_hash_follows_content(field_library: ContentLibrary) -> None:
    """同一個內容庫只算一次；雜湊只看內容（換一個內容一樣的內容庫物件雜湊不變，改一格就變）。"""
    first = field_tiles(field_library, "mist_ferry")
    assert first is not None and field_tiles(field_library, "mist_ferry") is first
    copy = dataclasses.replace(field_library)
    again = field_tiles(copy, "mist_ferry")
    assert again is not None and again is not first and again.hash == first.hash
    found = field_library.field_maps["mist_ferry"]
    first_digit = found.heights.lstrip()[0]
    heights = found.heights.replace(first_digit, "1" if first_digit == "0" else "0", 1)
    changed = found.model_copy(update={"heights": heights})
    maps = {**field_library.field_maps, "mist_ferry": changed}
    other = dataclasses.replace(field_library, field_maps=maps)
    moved = field_tiles(other, "mist_ferry")
    assert moved is not None and moved.hash != first.hash
    assert field_tiles(field_library, "no_such_map") is None


def test_static_tiles_match_char_without_reveals(field_library: ContentLibrary) -> None:
    """沒發現隱藏門的角色：靜態地形＝原本每個角色算的地形，``open_cells`` 為空。"""
    char = _char(field_library, "herb_valley")
    view = field_view(field_library, char)
    static = field_tiles(field_library, "herb_valley")
    assert view is not None and static is not None
    assert view.tiles == static.tiles and view.tiles_hash == static.hash
    assert view.open_cells == ()
    lean = field_view(field_library, char, inline_tiles=False)
    assert lean is not None and lean.tiles == () and lean.tiles_hash == static.hash


def test_revealed_hidden_door_in_open_cells(field_library: ContentLibrary) -> None:
    """發現隱藏門之後：靜態地形不變（不洩漏給沒發現的人），那一格放進 ``open_cells``。"""
    found = field_library.field_maps["herb_valley"]
    door = next(d for d in found.doors if d.hidden_until == "reveal")
    char = _char(
        field_library,
        "herb_valley",
        revealed=(LocationRef(region="cloud_ridge", location=door.to),),
    )
    view = field_view(field_library, char)
    static = field_tiles(field_library, "herb_valley")
    assert view is not None and static is not None
    assert view.open_cells == (door.at,)
    walk = {(t.x, t.y): t.walkable for t in view.tiles}
    assert walk[door.at] is True
    assert {(t.x, t.y): t.walkable for t in static.tiles}[door.at] is False
    patched = {(t.x, t.y): t.walkable or (t.x, t.y) in set(view.open_cells) for t in static.tiles}
    assert patched == walk  # 靜態地形＋open_cells＝原本的地形


def test_tiles_endpoint_and_cache_header(client: TestClient) -> None:
    view = client.post("/api/world/characters", json=START).json()
    field = view["field"]
    assert field["tiles"] == [] and field["tiles_hash"]
    hit = client.get(f"/api/world/fields/{field['map_id']}?h={field['tiles_hash']}")
    assert hit.status_code == 200 and hit.json()["hash"] == field["tiles_hash"]
    assert "immutable" in hit.headers.get("cache-control", "")
    miss = client.get(f"/api/world/fields/{field['map_id']}?h=stale")
    assert miss.status_code == 200 and miss.json()["hash"] == field["tiles_hash"]
    assert "cache-control" not in miss.headers
    assert client.get("/api/world/fields/no_such_map").status_code == 404


def test_world_view_is_smaller_without_tiles(client: TestClient) -> None:
    view = client.post("/api/world/characters", json=START)
    static = client.get(f"/api/world/fields/{view.json()['field']['map_id']}")
    assert len(view.content) < 2 * len(static.content) + 200_000  # 量測見 6C-R3 報告


# -- 敵群外觀 -----------------------------------------------------------------


def test_enemy_leader_look(field_library: ContentLibrary) -> None:
    """``FieldView.enemies`` 帶帶頭單位的外觀：範本、``doll_look``（含 ``creature``）同戰鬥。"""
    world = make_world()
    char = _char(field_library, "ferry_steps")
    view = field_view(field_library, char, world=world, now=NOON)
    assert view is not None and view.enemies
    catalog = field_library.enemy_catalog()
    for shown, enemy in zip(
        view.enemies, field_enemies(field_library, world, char, NOON), strict=True
    ):
        lineup = enemy_lineup(field_library, world, char, enemy, NOON)
        assert lineup is not None and shown.look is not None
        lead = (*lineup.members, *lineup.third)[0]
        template = catalog.template(lead.unit)
        assert shown.look.template_id == template.id
        assert shown.look.doll_look == template.doll
        assert shown.look.weapon_id == template.weapon


def test_enemy_look_creature_passes_through(
    field_library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    """帶頭的是異形（``creature``）時：外觀原樣帶到 ``doll_look.creature``
    （前端照戰鬥的異形畫法）。
    """
    creature = next(
        (t for t in field_library.units.values() if t.doll is not None and t.doll.creature),
        None,
    )
    if creature is None:
        pytest.skip("正式內容沒有異形範本")
    catalog = field_library.enemy_catalog()
    monkeypatch.setattr(type(catalog), "template", lambda _self, _unit: creature)
    view = field_view(
        field_library, _char(field_library, "ferry_steps"), world=make_world(), now=NOON
    )
    assert view is not None and view.enemies
    look = view.enemies[0].look
    assert look is not None and look.doll_look == creature.doll
    assert look.doll_look is not None and look.doll_look.creature is not None
