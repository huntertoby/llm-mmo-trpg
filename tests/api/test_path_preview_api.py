"""``POST /api/battles/{id}/path-preview``（Phase 6A-4b）：預覽不改變戰鬥，停點與實走一致。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.api.schemas import permille
from trpg.engine.path_preview import preview_path
from trpg.engine.rules.movement import find_path, reachable_tiles
from trpg.engine.state import TrapState, state_to_json
from trpg.shared.types import Attribute, Pos, Surface, Team, UnitId

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
    """6A-4f／#123：連續冰面合成一段（只在第一格檢定），機率與停點與引擎一致，不改變戰鬥。"""
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
    expected = preview_path(state, hero_id, path=tuple(path)).slip_runs[0]
    assert run["status_id"] == "prone"
    assert run["chance_permille"] == permille(expected.chance)
    # #123：失敗時的單一停點與滑行路徑（含起點）
    assert run["fail_stop"] == list(expected.fail_stop)
    assert run["slide_path"] == [list(xy) for xy in expected.slide_path]
    assert run["slide_path"][0] == [path[1].x, path[1].y]
    assert run["stop_reason"] == expected.stop_reason


def test_path_preview_gives_trap_range_after_ice(client: TestClient) -> None:
    """6P-1（6A-4f 待決 1）：冰後的陷阱有傷害範圍（最小～最大）與「可能」的定身，與引擎一致。"""
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    state = session.state
    hero_id = UnitId(battle["hero_id"])
    x, y = _far_tile(client, battle)
    path = find_path(state, hero_id, Pos(x=x, y=y))
    assert path is not None and len(path) >= 5
    ice = path[1]
    state.set_tile(ice.x, ice.y, replace(state.tile(ice.x, ice.y), surface=Surface.ICE))
    owner = next(u for u in state.units.values() if u.team is Team.ENEMY)
    state.traps = [
        TrapState(
            owner_id=owner.id,
            team=Team.ENEMY,
            pos=path[3],
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple((a, 10) for a in Attribute),
            revealed_to=(Team.ALLY,),
        )
    ]
    body = {"path": [{"x": p.x, "y": p.y} for p in path]}
    reply = client.post(f"/api/battles/{battle['battle_id']}/path-preview", json=body)
    assert reply.status_code == 200, reply.text
    data = reply.json()
    events = data["steps"][3]["events"]
    damage = next(e for e in events if e["kind"] == "damage" and e["other_id"] == owner.id)
    root = next(e for e in events if e["kind"] == "status" and e["status_id"] == "root")
    preview = preview_path(state, hero_id, path=tuple(path))
    assert data["stops"] == [list(xy) for xy in preview.stops] and len(data["stops"]) > 1
    assert data["stops"][0] == data["stop"] and data["worst_stop"] in data["stops"]
    expected = preview.steps[3].events
    engine = next(e for e in expected if e.kind == "damage" and e.other_id == owner.id)
    assert (damage["amount_min"], damage["amount_max"]) == (engine.amount_min, engine.amount_max)
    assert damage["amount_min"] < damage["amount_max"]
    assert not root["certain"]
