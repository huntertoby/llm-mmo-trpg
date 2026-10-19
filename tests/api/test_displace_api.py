"""位移他人（Phase 3D-2b）的 API：``teleport_target`` 與 ``swap_any`` 的兩段選取各以一個完整的
``use_skill`` 表達——``target_id`` ＋ ``target_pos``（傳送）、``target_id`` ＋ ``second_target_id``
（互換）。``legal_actions`` 列出每一組合法的組合，預覽附上抵抗判定的成功率。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

BANISH = "skill_banish"
VOID = "skill_void_swap"
BODY = {"map_id": "lava_crossing", "seed": 1, "hero_build": "build_banisher"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _skill(battle: dict[str, Any], skill_id: str) -> list[dict[str, Any]]:
    return [
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == skill_id
    ]


def _to_turn(client: TestClient, skill_id: str) -> dict[str, Any]:
    """主角第 1 輪先走到離敵人最近的格子，這樣敵人才進得了射程。"""
    reply = client.post("/api/battles", json=BODY)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    foes = [(u["pos"]["x"], u["pos"]["y"]) for u in battle["view"]["units"] if u["team"] == "enemy"]

    def gap(action: dict[str, Any]) -> int:
        end = action["path"][-1]
        return min(abs(end["x"] - x) + abs(end["y"] - y) for x, y in foes)

    moves = [a for a in battle["legal_actions"] if a["type"] == "move"]
    battle = _post(client, battle["battle_id"], "actions", min(moves, key=gap))
    assert _skill(battle, skill_id), "移動後應該有可以施放的目標"
    return battle


def test_banish_legal_actions_carry_unit_and_landing_pairs(client: TestClient) -> None:
    battle = _to_turn(client, BANISH)
    acts = _skill(battle, BANISH)
    assert all(a["target_id"] and a["target_pos"] for a in acts)
    assert all(a["target_object_id"] is None and a["second_target_id"] is None for a in acts)
    units = {a["target_id"] for a in acts}
    assert battle["hero_id"] not in units  # 不能傳送自己
    for unit in units:  # 每個單位都有多個落點可選（第二段選取）
        assert len([a for a in acts if a["target_id"] == unit]) > 1


def test_posting_a_banish_pair_moves_or_resists(client: TestClient) -> None:
    battle = _to_turn(client, BANISH)
    action = _skill(battle, BANISH)[0]
    after = _post(client, battle["battle_id"], "actions", action)
    events = [e for step in after["steps"] for e in step["events"]]
    moved = [e for e in events if e["type"] == "unit_moved" and e["mode"] == "teleported"]
    rolls = [e for e in events if e["type"] == "maneuver_rolled" and e["maneuver"] == "teleport"]
    friendly = bool(
        [
            u
            for u in battle["view"]["units"]
            if u["id"] == action["target_id"] and u["team"] == "ally"
        ]
    )
    assert friendly or len(rolls) == 1  # 友方不檢定，敵方擲一次對抗
    assert bool(moved) == (friendly or rolls[0]["success"])
    assert all("被傳送到" in e["text"] for e in moved)


def test_a_banish_with_only_the_unit_is_rejected(client: TestClient) -> None:
    battle = _to_turn(client, BANISH)
    action = dict(_skill(battle, BANISH)[0], target_pos=None)
    reply = client.post(f"/api/battles/{battle['battle_id']}/actions", json=action)
    assert reply.status_code == 400
    assert "同時指定" in reply.text


def test_void_swap_legal_actions_are_distinct_unit_pairs(client: TestClient) -> None:
    battle = _to_turn(client, VOID)
    acts = _skill(battle, VOID)
    assert acts and all(a["target_id"] and a["second_target_id"] for a in acts)
    assert all(a["target_id"] < a["second_target_id"] for a in acts)  # 每組只列一次
    assert len({(a["target_id"], a["second_target_id"]) for a in acts}) == len(acts)


def test_the_preview_carries_the_success_chances(client: TestClient) -> None:
    battle = _to_turn(client, BANISH)
    enemies = {u["id"] for u in battle["view"]["units"] if u["team"] == "enemy"}
    action = next(a for a in _skill(battle, BANISH) if a["target_id"] in enemies)
    reply = client.post(f"/api/battles/{battle['battle_id']}/preview", json=action)
    assert reply.status_code == 200, reply.text
    data = reply.json()
    (check,) = data["displace_checks"]
    assert check["unit_id"] == action["target_id"]
    assert check["resist_bonus"] >= 2 and 0 < check["success_permille"] < 1000
    assert data["displace_permille"] == check["success_permille"]
    assert [m["kind"] for m in data["moves"]] == ["teleport"]
