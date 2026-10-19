"""直線衝撞（Phase 3D-2c）的 API：``charge_through`` 以 ``use_skill`` ＋ ``target_pos``（終點格）
表達，``legal_actions`` 列出每個合法終點，預覽附上路線（``moves`` 的 ``charge``）與沿途敵人的
命中率。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

BULL = "skill_bull_rush"
BODY = {"map_id": "ruined_fort", "seed": 0, "hero_build": "build_charger"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _lined_up(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    """ruined_fort 種子 0：主角走到 (3, 4)，同一列 (4, 4)、(6, 4) 各站著一個敵人，終點 (7, 4)
    是空格。"""
    battle = client.post("/api/battles", json=BODY).json()
    move = next(
        a
        for a in battle["legal_actions"]
        if a["type"] == "move" and (a["path"][-1]["x"], a["path"][-1]["y"]) == (3, 4)
    )
    battle = _post(client, battle["battle_id"], "actions", move)
    action = next(
        a
        for a in battle["legal_actions"]
        if a["type"] == "use_skill"
        and a["skill_id"] == BULL
        and (a["target_pos"]["x"], a["target_pos"]["y"]) == (7, 4)
    )
    return battle, action


def test_legal_actions_list_straight_end_tiles_only(client: TestClient) -> None:
    battle, _ = _lined_up(client)
    hero = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])["pos"]
    acts = [
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == BULL
    ]
    assert acts
    for a in acts:
        assert a["target_id"] is None and a["target_object_id"] is None
        assert a["second_target_id"] is None
        end = a["target_pos"]
        assert end["x"] == hero["x"] or end["y"] == hero["y"]  # 只有同一列或同一行
        assert 1 <= abs(end["x"] - hero["x"]) + abs(end["y"] - hero["y"]) <= 4


def test_the_preview_carries_the_route_and_the_enemies_on_the_way(client: TestClient) -> None:
    battle, action = _lined_up(client)
    preview = _post(client, battle["battle_id"], "preview", action)
    (move,) = preview["moves"]
    assert move["kind"] == "charge" and move["other_id"] is None
    assert move["path"] == [[3, 4], [4, 4], [5, 4], [6, 4], [7, 4]]
    foes = {u["id"] for u in battle["view"]["units"] if u["team"] == "enemy" and u["pos"]["y"] == 4}
    assert {t["unit_id"] for t in preview["targets"]} == foes and len(foes) == 2
    assert all(
        t["hit_permille"] == 600 and t["knock_permille"] is not None for t in preview["targets"]
    )
    assert all(t["damage"] is not None for t in preview["targets"])


def test_posting_the_charge_runs_through_both_enemies(client: TestClient) -> None:
    battle, action = _lined_up(client)
    after = _post(client, battle["battle_id"], "actions", action)
    events = [e for step in after["steps"] for e in step["events"]]
    (charged,) = [e for e in events if e["type"] == "unit_charged"]
    assert "直線衝撞" in charged["text"] and "(3, 4)→(4, 4)→(5, 4)→(6, 4)→(7, 4)" in charged["text"]
    rolled = [e for e in events if e["type"] == "attack_rolled" and e["skill_id"] == BULL]
    assert [e["target_id"] for e in rolled] == [
        u["id"]
        for x in (4, 6)
        for u in battle["view"]["units"]
        if u["team"] == "enemy" and (u["pos"]["x"], u["pos"]["y"]) == (x, 4)
    ]  # 依路徑順序
    hero = next(u for u in after["view"]["units"] if u["id"] == battle["hero_id"])
    assert hero["pos"] == {"x": 7, "y": 4}


def test_an_off_line_end_tile_is_rejected(client: TestClient) -> None:
    battle, action = _lined_up(client)
    crooked = dict(action, target_pos={"x": 6, "y": 5})
    reply = client.post(f"/api/battles/{battle['battle_id']}/actions", json=crooked)
    assert reply.status_code == 400
