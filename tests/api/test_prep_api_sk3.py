"""戰前佈置的 API（SK-3，#166，06 6.38 第 11 點）：主角有可放的技能時，建立戰鬥後停在
``awaiting: prep``（``prep`` 列出可放的技能與格子）；``POST /prep`` 放 1 個或跳過，之後照常推進；
戰鬥紀錄可以重播。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory, store_of
from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.engine.runner import replay
from trpg.engine.state import state_to_json

TRAP = "skill_ws_bear_trap"


def _trap() -> dict[str, Any]:
    data = library().skills["skill_bear_trap"].model_dump(mode="json", exclude_none=True)
    return {**data, "id": TRAP, "provenance": {"origin": "workshop"}}


@pytest.fixture
def client(library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    """這個檔的 client 開著戰前佈置（其他 API 測試預設關）。"""
    return make_client(library, prep_placement=True)


def _create(client: TestClient, *, with_trap: bool = True) -> dict[str, Any]:
    body: dict[str, Any] = {"map_id": "open_plain", "seed": 3, "hero_build": "build_charger"}
    if with_trap:
        body |= {"custom_skills": [_trap()], "replace_skills": ["skill_bull_rush"]}
    reply = client.post("/api/battles", json=body)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _prep(client: TestClient, battle_id: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/prep", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _events(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for s in body["steps"] for e in s["events"]]


def test_the_battle_waits_for_prep_and_places_a_trap(client: TestClient) -> None:
    body = _create(client)
    assert body["awaiting"] == "prep"
    assert body["legal_actions"] == []
    prep = body["prep"]
    assert prep["unit_id"] == body["hero_id"]
    (option,) = [o for o in prep["options"] if o["skill_id"] == TRAP]
    assert option["kind"] == "trap" and option["tiles"]
    assert all(tuple(t) in {tuple(z) for z in prep["zone"]} for t in option["tiles"])
    x, y = option["tiles"][0]
    after = _prep(client, body["battle_id"], {"skill_id": TRAP, "target_pos": {"x": x, "y": y}})
    assert after["awaiting"] != "prep" and after["prep"] is None
    kinds = [e["type"] for e in _events(after)]
    assert kinds[:2] == ["prep_placed", "trap_placed"]
    hero = next(u for u in after["view"]["units"] if u["id"] == body["hero_id"])
    assert hero["cooldowns"].get(TRAP, 0) > 0
    session = store_of(client).get(body["battle_id"])
    log = session.to_log()
    replayed = replay(log.setup, log.seed, log.actions)
    assert state_to_json(replayed.state) == state_to_json(session.state)


def test_skipping_starts_the_battle(client: TestClient) -> None:
    body = _create(client)
    after = _prep(client, body["battle_id"], {})
    assert after["awaiting"] in ("action", "ended")
    assert [e["type"] for e in _events(after)][:1] == ["prep_skipped"]
    again = client.post(f"/api/battles/{body['battle_id']}/prep", json={})
    assert again.status_code == 409


def test_an_illegal_tile_is_rejected_and_nothing_changes(client: TestClient) -> None:
    body = _create(client)
    bad = client.post(
        f"/api/battles/{body['battle_id']}/prep",
        json={"skill_id": TRAP, "target_pos": {"x": 99, "y": 99}},
    )
    assert bad.status_code == 400
    still = client.get(f"/api/battles/{body['battle_id']}").json()
    assert still["awaiting"] == "prep"


def test_without_a_placing_skill_there_is_no_prep(client: TestClient) -> None:
    body = _create(client, with_trap=False)
    assert body["awaiting"] != "prep" and body["prep"] is None
