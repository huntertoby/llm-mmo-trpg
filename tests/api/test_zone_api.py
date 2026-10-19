"""持續區域（Phase 3D-5）在網頁 API：主角施放火牆、視圖列出區域與下一輪位置、環境預告帶著區域的
格子與中文、預覽有建立區域的事件。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _open(client: TestClient) -> dict[str, Any]:
    created = client.post(
        "/api/battles", json={"map_id": "swamp", "seed": 0, "hero_build": "build_summoner"}
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    assert body["awaiting"] == "action"
    return body


def test_the_fire_wall_shows_in_the_view_and_the_telegraph(client: TestClient) -> None:
    body = _open(client)
    battle_id, hero = body["battle_id"], body["hero_id"]
    action = next(
        a
        for a in body["legal_actions"]
        if a["type"] == "use_skill"
        and a["skill_id"] == "skill_fire_wall"
        and a["direction"] == "north"
    )
    preview = client.post(f"/api/battles/{battle_id}/preview", json=action)
    assert preview.status_code == 200, preview.text
    created = [e for e in preview.json()["min_events"] if e["type"] == "zone_created"]
    assert created and "展開持續區域「火牆」" in created[0]["text"]
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    [zone] = data["view"]["zones"]
    assert (zone["owner_id"], zone["anchor"], zone["direction"], zone["harmful"]) == (
        hero,
        "moving",
        "north",
        True,
    )
    assert zone["name_zh"] == "火牆" and zone["next_cells"]
    [moved] = [c for c in data["telegraph"]["changes"] if c["kind"] == "zone_moved"]
    assert moved["tiles"] == zone["next_cells"]
    assert moved["text"].startswith("「火牆」區域將向北前進到")
