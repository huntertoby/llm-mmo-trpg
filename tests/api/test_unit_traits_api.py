"""戰鬥回應的單位卡「特性」欄（Phase 5A-M1b）：每個單位都有欄位，主角不重複列。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_view_units_carry_traits_zh_and_the_hero_has_none(client: TestClient) -> None:
    reply = client.post(
        "/api/battles",
        json={
            "map_id": "open_plain",
            "seed": 7,
            "weapon": "lightning_staff",
            "keywords": ["wet", "charged"],
        },
    )
    assert reply.status_code == 201, reply.text
    data = reply.json()
    units = data["view"]["units"]
    assert all(isinstance(u["traits_zh"], list) for u in units)
    hero = next(u for u in units if u["id"] == data["hero_id"])
    assert hero["traits_zh"] == []
