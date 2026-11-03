"""``POST /api/battles/{id}/path-preview``（Phase 6A-4b）：預覽不改變戰鬥，停點與實走一致。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.api.schemas import permille
from trpg.engine.path_preview import preview_path
from trpg.engine.rules.movement import find_path, reachable_tiles
from trpg.engine.state import state_to_json
from trpg.shared.types import Pos, Surface, UnitId

CREATE = {"map_id": "open_plain", "seed": 7, "hero_build": "build_fire"}


def _create(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/battles", json=CREATE)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _far_tile(client: TestClient, battle: dict[str, Any]) -> tuple[int, int]:
    state = store_of(client).get(battle["battle_id"]).state
    tiles = reachable_tiles(state, UnitId(battle["hero_id"]))
    far = max(tiles, key=lambda p: (tiles[p], p.y, p.x))
    return far.x, far.y


def test_path_preview_by_dest_matches_the_walk_and_changes_nothing(client: TestClient) -> None:
    battle = _create(client)
    url = f"/api/battles/{battle['battle_id']}"
    session = store_of(client).get(battle["battle_id"])
    before = state_to_json(session.state)
    x, y = _far_tile(client, battle)
    reply = client.post(f"{url}/path-preview", json={"dest": {"x": x, "y": y}})
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert state_to_json(session.state) == before
    assert data["unit_id"] == battle["hero_id"] and data["reachable"]
    assert data["path"][-1] == [x, y] and len(data["steps"]) == len(data["path"])
    assert {s["reach"] for s in data["steps"]} <= {"certain", "possible", "interrupted"}
    move = {
        "type": "move",
        "unit_id": battle["hero_id"],
        "path": [{"x": px, "y": py} for px, py in data["path"]],
    }
    acted = client.post(f"{url}/actions", json=move)
    assert acted.status_code == 200, acted.text
    hero = session.state.units[UnitId(battle["hero_id"])]
    assert [hero.pos.x, hero.pos.y] in (data["stop"], data["worst_stop"])


def test_path_preview_marks_unreachable_tiles(client: TestClient) -> None:
    battle = _create(client)
    url = f"/api/battles/{battle['battle_id']}"
    hero = store_of(client).get(battle["battle_id"]).state.units[UnitId(battle["hero_id"])]
    path = [{"x": hero.pos.x, "y": hero.pos.y}, {"x": hero.pos.x + 5, "y": hero.pos.y}]
    reply = client.post(f"{url}/path-preview", json={"path": path})
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert not data["reachable"] and data["reason"] and data["legal_length"] == 0
    assert [s["reach"] for s in data["steps"]] == ["certain", "unreachable"]


def test_path_preview_rejects_bad_requests(client: TestClient) -> None:
    battle = _create(client)
    url = f"/api/battles/{battle['battle_id']}/path-preview"
    assert client.post(url, json={}).status_code == 422
    both = {"path": [{"x": 0, "y": 0}], "dest": {"x": 0, "y": 0}}
    assert client.post(url, json=both).status_code == 422
    units = store_of(client).get(battle["battle_id"]).state.units
    other = next(uid for uid in sorted(units) if uid != battle["hero_id"])
    reply = client.post(url, json={"unit_id": other, "dest": {"x": 0, "y": 0}})
    assert reply.status_code == 400
    assert (
        client.post("/api/battles/nope/path-preview", json={"dest": {"x": 0, "y": 0}}).status_code
        == 404
    )


def test_path_preview_merges_consecutive_ice(client: TestClient) -> None:
    """6A-4f：連續冰面合成一段，機率與引擎的精確值一致（‰ 四捨五入），不改變戰鬥。"""
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    state = session.state
    hero_id = UnitId(battle["hero_id"])
    x, y = _far_tile(client, battle)
    path = find_path(state, hero_id, Pos(x=x, y=y))
    assert path is not None and len(path) >= 4
    for p in path[1:3]:
        state.set_tile(p.x, p.y, replace(state.tile(p.x, p.y), surface=Surface.ICE))
    before = state_to_json(state)
    body = {"path": [{"x": p.x, "y": p.y} for p in path]}
    reply = client.post(f"/api/battles/{battle['battle_id']}/path-preview", json=body)
    assert reply.status_code == 200, reply.text
    assert state_to_json(session.state) == before
    runs = reply.json()["slip_runs"]
    assert len(runs) == 1
    run = runs[0]
    assert (run["start"], run["end"], run["tiles"]) == (1, 2, 2)
    assert run["start_pos"] == [path[1].x, path[1].y]
    assert run["end_pos"] == [path[2].x, path[2].y]
    assert run["status_id"] == "prone" and run["fail_stops"]
    expected = preview_path(state, hero_id, path=tuple(path)).slip_runs[0]
    assert run["chance_permille"] == permille(expected.chance)
