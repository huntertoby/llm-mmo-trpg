"""撥開的 API 層測試（Phase 3C-1）：合法動作列表、互動選項（含不合法原因）、送出撥開。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.engine.helpers import give_turn, make_map, make_state, no_reactions, spawn
from trpg.engine.state import BattleState
from trpg.shared.types import Team

CREATE = {"map_id": "open_plain", "seed": 7, "hero_build": "build_fire"}


def _field() -> BattleState:
    """主角 (2, 2)；箱子 (3, 2)；牆 (3, 1)（往左撥會被擋住）。"""
    terrain = ".....\n...#.\n.....\n.....\n....."
    m = make_map(
        "00000\n00000\n00000\n00000\n00000",
        terrain,
        objects=[(3, 2, "crate")],
        ally=[(2, 2)],
        enemy=[(4, 4)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (2, 2), no_reactions("hero_fighter", max_hp=500)),
            spawn(Team.ENEMY, (4, 4), no_reactions("bandit", max_hp=500)),
        ],
    )
    return give_turn(state, "unit_0001")


def _inject(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/battles", json=CREATE)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    session = store_of(client).get(battle["battle_id"])
    session.state = _field()
    session.pending = None
    session.hero_id = session.state.units_sorted()[0].id
    return battle


def test_response_lists_push_and_shove_aside_options_with_reasons(client: TestClient) -> None:
    battle = _inject(client)
    got = client.get(f"/api/battles/{battle['battle_id']}").json()
    assert got["awaiting"] == "action"
    legal = [
        (a.get("mode"), a.get("side")) for a in got["legal_actions"] if a["type"] == "interact"
    ]
    assert legal == [("push", None), ("shove_aside", "right")]
    options = {(o["mode"], o["side"]): o for o in got["interact_options"]}
    assert set(options) == {("push", None), ("shove_aside", "left"), ("shove_aside", "right")}
    left = options[("shove_aside", "left")]
    assert (
        left["legal"] is False and "撥不動" in left["reason"] and left["to_pos"] == {"x": 3, "y": 1}
    )
    right = options[("shove_aside", "right")]
    assert (
        right["legal"] is True and right["reason"] is None and right["to_pos"] == {"x": 3, "y": 3}
    )


def test_posting_a_shove_aside_moves_the_object(client: TestClient) -> None:
    battle = _inject(client)
    url = f"/api/battles/{battle['battle_id']}/actions"
    body = {
        "type": "interact",
        "unit_id": "unit_0001",
        "object_id": "obj_0001",
        "mode": "shove_aside",
        "side": "right",
    }
    reply = client.post(url, json=body)
    assert reply.status_code == 200, reply.text
    moved = next(
        e for s in reply.json()["steps"] for e in s["events"] if e["type"] == "object_moved"
    )
    assert moved["how"] == "shove_aside" and moved["to_pos"] == {"x": 3, "y": 3}
    assert "撥到" in moved["text"]


def test_posting_an_illegal_shove_aside_is_rejected_in_chinese(client: TestClient) -> None:
    battle = _inject(client)
    url = f"/api/battles/{battle['battle_id']}/actions"
    body = {
        "type": "interact",
        "unit_id": "unit_0001",
        "object_id": "obj_0001",
        "mode": "shove_aside",
        "side": "left",
    }
    reply = client.post(url, json=body)
    assert reply.status_code in (400, 409, 422)
    assert "撥不動" in reply.text


def test_options_for_an_object_at_the_map_edge_do_not_crash(client: TestClient) -> None:
    """箱子貼著左緣、主角在它右邊：往左推會出界，選項仍要回得來（``to_pos`` 為 ``None``）。"""
    battle = _inject(client)
    m = make_map(
        "00000\n00000\n00000\n00000\n00000",
        ".....\n.....\n.....\n.....\n.....",
        objects=[(0, 2, "crate")],
        ally=[(1, 2)],
        enemy=[(4, 4)],
    )
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 2), no_reactions("hero_fighter", max_hp=500)),
            spawn(Team.ENEMY, (4, 4), no_reactions("bandit", max_hp=500)),
        ],
    )
    session = store_of(client).get(battle["battle_id"])
    session.state = give_turn(state, "unit_0001")
    reply = client.get(f"/api/battles/{battle['battle_id']}")
    assert reply.status_code == 200, reply.text
    push = [o for o in reply.json()["interact_options"] if o["mode"] == "push"]
    assert len(push) == 1
    assert push[0]["legal"] is False and "推不動" in push[0]["reason"] and push[0]["to_pos"] is None
