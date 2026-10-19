"""源力與傳說技能的 API（Phase 3C-4a 6.4）：視圖帶源力與源泉格、技能卡片帶源力成本、源力不足時
施放被拒（400，中文原因）。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.engine.state import state_to_json
from trpg.shared.types import UnitId

LEGEND = "skill_time_surge"


def _create(client: TestClient, map_id: str = "ruined_fort") -> dict[str, Any]:
    body = {"map_id": map_id, "seed": 3, "hero_build": "build_ranged"}
    reply = client.post("/api/battles", json=body)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _hero(battle: dict[str, Any]) -> dict[str, Any]:
    unit: dict[str, Any] = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    return unit


def test_views_carry_source_and_wells(client: TestClient) -> None:
    battle = _create(client)
    hero = _hero(battle)
    assert hero["source_max"] == 3
    assert 0 <= hero["source"] <= 3
    enemies = [u for u in battle["view"]["units"] if u["team"] == "enemy"]
    assert all(u["source"] == 0 for u in enemies)
    wells = {(p["x"], p["y"]) for p in battle["view"]["source_wells"]}
    assert wells <= {(4, 1), (4, 8)}


def test_skill_card_has_the_source_cost(client: TestClient) -> None:
    card = client.get(f"/api/skills/{LEGEND}").json()
    assert card["source_cost"] == 1 and "源力 1" in card["cost"]
    assert client.get("/api/skills/skill_fire_bolt").json()["source_cost"] is None


def test_casting_without_source_is_400_in_chinese(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    hero_id = UnitId(battle["hero_id"])
    session.state.units[hero_id].source = 0
    session.state.units[hero_id].cooldowns.pop(LEGEND, None)
    before = state_to_json(session.state)
    action = {"type": "use_skill", "unit_id": hero_id, "skill_id": LEGEND}
    reply = client.post(f"/api/battles/{battle['battle_id']}/actions", json=action)
    assert reply.status_code == 400
    assert "源力不足：需要 1，目前 0" in reply.json()["detail"]
    assert state_to_json(session.state) == before
