"""朝向與瞬步（Phase 3D-8d）的 API：視圖的 ``facing``、一般瞬步（``landing: choose``）的兩段選取
以 ``target_id`` ＋ ``target_pos`` 表達、預覽的 ``backstab`` 與 ``moves``（``shadowstep``）。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

AMBUSH = "skill_shadow_ambush"
BACKSTAB = "skill_shadow_backstab"
BODY = {"map_id": "open_plain", "seed": 2, "hero_build": "build_assassin"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _skill(battle: dict[str, Any], skill_id: str) -> list[dict[str, Any]]:
    return [
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == skill_id
    ]


def _start(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/battles", json=BODY)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    return battle


def _to_turn(client: TestClient) -> dict[str, Any]:
    """主角第 1 輪先走到離敵人最近的格子，讓敵人進入瞬步的射程。"""
    battle = _start(client)
    foes = [(u["pos"]["x"], u["pos"]["y"]) for u in battle["view"]["units"] if u["team"] == "enemy"]

    def gap(action: dict[str, Any]) -> int:
        end = action["path"][-1]
        return int(min(abs(end["x"] - x) + abs(end["y"] - y) for x, y in foes))

    moves = [a for a in battle["legal_actions"] if a["type"] == "move"]
    battle = _post(client, battle["battle_id"], "actions", min(moves, key=gap))
    assert _skill(battle, AMBUSH), "移動後應該有可以瞬步的敵人"
    return battle


def test_the_view_has_every_units_facing(client: TestClient) -> None:
    battle = _start(client)
    facings = {u["team"]: u["facing"] for u in battle["view"]["units"]}
    assert facings["ally"] in {"north", "east", "south", "west"}
    assert facings["ally"] != facings["enemy"]


def test_choose_lists_enemy_and_adjacent_landing_pairs(client: TestClient) -> None:
    battle = _to_turn(client)
    acts = _skill(battle, AMBUSH)
    assert all(a["target_id"] and a["target_pos"] for a in acts)
    enemies = {u["id"]: u for u in battle["view"]["units"] if u["team"] == "enemy"}
    for action in acts:
        foe = enemies[action["target_id"]]["pos"]
        land = action["target_pos"]
        assert abs(foe["x"] - land["x"]) + abs(foe["y"] - land["y"]) == 1


def test_posting_a_choose_pair_lands_there_and_previews_the_move(client: TestClient) -> None:
    battle = _to_turn(client)
    action = _skill(battle, AMBUSH)[0]
    shown = _post(client, battle["battle_id"], "preview", action)
    assert [m["kind"] for m in shown["moves"]] == ["shadowstep"]
    assert "backstab" in shown
    after = _post(client, battle["battle_id"], "actions", action)
    events = [e for step in after["steps"] for e in step["events"]]
    moved = [e for e in events if e["type"] == "unit_moved" and e["mode"] == "shadowstep"]
    assert [(e["to_pos"]["x"], e["to_pos"]["y"]) for e in moved] == [
        (action["target_pos"]["x"], action["target_pos"]["y"])
    ]
    assert all("瞬步到" in e["text"] for e in moved)


def test_a_choose_with_only_the_enemy_is_rejected(client: TestClient) -> None:
    battle = _to_turn(client)
    action = dict(_skill(battle, AMBUSH)[0], target_pos=None)
    reply = client.post(f"/api/battles/{battle['battle_id']}/actions", json=action)
    assert reply.status_code == 400


def test_behind_needs_only_the_enemy(client: TestClient) -> None:
    battle = _to_turn(client)
    acts = _skill(battle, BACKSTAB)
    assert acts and all(a["target_id"] and a["target_pos"] is None for a in acts)
