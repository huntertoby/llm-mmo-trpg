"""技能變形（Phase 3D-3）的 API：修正規則讓技能轉成別的形狀時，``legal_actions``（選取方式）、預覽
（影響格）與結算（``skill_used`` 的格子）用的是變形後的形狀，網頁的目標選取因此跟著改變。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of

RENEWAL = "skill_renewal"
BODY = {"map_id": "open_plain", "seed": 0, "hero_build": "build_healer"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_a_converted_heal_is_selected_by_direction_and_includes_the_caster(
    client: TestClient,
) -> None:
    battle: dict[str, Any] = client.post("/api/battles", json=BODY).json()
    heals = [
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == RENEWAL
    ]
    # 慈悲光束把單體回春轉成直線：選方向，不選單位
    assert heals and all(a["direction"] is not None for a in heals)
    assert all(a["target_id"] is None and a["target_object_id"] is None for a in heals)
    hero = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    action = heals[0]
    preview = _post(client, battle["battle_id"], "preview", action)
    tiles = {(x, y) for x, y in preview["affected_tiles"]}
    assert (hero["pos"]["x"], hero["pos"]["y"]) in tiles  # 自我療癒：施放者也在範圍內
    assert hero["id"] in preview["affected_units"]
    done = _post(client, battle["battle_id"], "actions", action)
    used = next(e for step in done["steps"] for e in step["events"] if e["type"] == "skill_used")
    assert {(p["x"], p["y"]) for p in used["tiles"]} == tiles  # 預覽與結算的格子一致


def test_the_hero_carries_the_shape_modifiers(client: TestClient) -> None:
    battle: dict[str, Any] = client.post("/api/battles", json=BODY).json()
    hero = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    assert {"skill_beam_of_mercy", "skill_self_mending"} <= set(hero["skills"])
    assert store_of(client).get(battle["battle_id"]).hero_id == battle["hero_id"]
