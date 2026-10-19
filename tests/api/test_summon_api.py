"""召喚（Phase 3D-4a）在網頁 API：主角施放召喚、召喚物出現在視圖與事件中、由 AI 自動行動、
預覽可用。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

SKILL = "skill_raise_skeleton"


def _summon_action(body: dict[str, Any]) -> dict[str, Any]:
    return next(
        a for a in body["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == SKILL
    )


def _open(client: TestClient) -> dict[str, Any]:
    created = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 0, "hero_build": "build_trapper"}
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    assert body["awaiting"] == "action"
    return body


def test_the_hero_summons_and_the_summon_acts_on_its_own(client: TestClient) -> None:
    body = _open(client)
    action = _summon_action(body)
    battle_id, hero = body["battle_id"], body["hero_id"]
    preview = client.post(f"/api/battles/{battle_id}/preview", json=action)
    assert preview.status_code == 200, preview.text
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    events = [e for step in data["steps"] for e in step["events"]]
    [summoned] = [e for e in events if e["type"] == "unit_summoned"]
    assert summoned["owner_id"] == hero and "召喚了" in summoned["text"]
    sid = summoned["unit_id"]
    order = data["steps"][0]["view"]["turn_order"]
    assert order[order.index(hero) + 1] == sid
    unit = next(u for u in data["view"]["units"] if u["id"] == sid)
    assert unit["owner_id"] == hero and unit["summon_expires_round"] is not None
    assert unit["skills"] == [] and unit["dismissed"] is False
    # 主角結束回合後，召喚物由 AI 接著行動（玩家不能操控）
    ended = client.post(
        f"/api/battles/{battle_id}/actions", json={"type": "end_turn", "unit_id": hero}
    )
    assert ended.status_code == 200, ended.text
    later = [e for step in ended.json()["steps"] for e in step["events"]]
    started = [e["unit_id"] for e in later if e["type"] == "turn_started"]
    assert started[0] == sid
    assert any(step["actor_id"] == sid for step in ended.json()["steps"])


def test_summons_take_no_individual_orders(client: TestClient) -> None:
    body = _open(client)
    battle_id = body["battle_id"]
    reply = client.post(f"/api/battles/{battle_id}/actions", json=_summon_action(body)).json()
    sid = next(u["id"] for u in reply["view"]["units"] if u["owner_id"] is not None)
    orders = {"team_orders": [], "unit_orders": {sid: [{"kind": "use_environment"}]}}
    put = client.put(f"/api/battles/{battle_id}/orders", json=orders)
    assert put.status_code == 422, put.text
    assert "由 AI 控制" in put.text
