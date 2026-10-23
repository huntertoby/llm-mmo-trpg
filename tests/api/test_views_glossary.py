"""Phase 3-4a：``initial_view``、``steps[i].view``（逐步播放用）與 ``/api/glossary``。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.content.library import ContentLibrary
from trpg.engine.runner import replay
from trpg.engine.view import project_for
from trpg.shared.types import Attribute, Element, Surface, Team


def _view_json(state: Any) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(project_for(state, Team.ALLY).model_dump_json())
    return data


def _check_steps(
    client: TestClient, battle: dict[str, Any], steps_before: int, response: dict[str, Any]
) -> None:
    session = store_of(client).get(battle["battle_id"])
    for i, step in enumerate(response["steps"]):
        # 建立戰鬥時 steps[0] 是開場（沒有 step），之後第 i 項是第 i 個步驟；
        # 之後的請求 steps[i] 是第 steps_before + i 個步驟（結算後 ＝ 前 steps_before + i + 1 個）。
        count = steps_before + i if steps_before == 0 else steps_before + i + 1
        expected = _view_json(replay(session.setup, session.seed, session.steps[:count]).state)
        assert step["view"] == expected, i
    assert response["steps"][-1]["view"] == response["view"]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_create_has_initial_view_and_per_step_views(client: TestClient, seed: int) -> None:
    body = {"map_id": "open_plain", "seed": seed, "hero_build": "build_fire"}
    reply = client.post("/api/battles", json=body)
    assert reply.status_code == 201
    data = reply.json()
    session = store_of(client).get(data["battle_id"])
    opening = _view_json(replay(session.setup, seed, []).state)
    assert data["initial_view"] == opening
    assert data["steps"][0]["step"] is None
    assert data["steps"][0]["view"] == opening
    _check_steps(client, data, 0, data)


def test_action_initial_view_is_the_view_before(client: TestClient) -> None:
    body = {"map_id": "open_plain", "seed": 5, "hero_build": "build_fire"}
    first = client.post("/api/battles", json=body).json()
    url = f"/api/battles/{first['battle_id']}"
    before = len(store_of(client).get(first["battle_id"]).steps)
    reply = client.post(
        f"{url}/actions", json={"type": "end_turn", "unit_id": first["hero_id"]}
    ).json()
    assert reply["initial_view"] == first["view"]
    assert len(reply["steps"]) >= 1
    _check_steps(client, first, before, reply)


def test_get_has_no_steps_and_equal_views(client: TestClient) -> None:
    body = {"map_id": "open_plain", "seed": 5, "hero_build": "build_fire"}
    first = client.post("/api/battles", json=body).json()
    again = client.get(f"/api/battles/{first['battle_id']}").json()
    assert again["steps"] == []
    assert again["initial_view"] == again["view"] == first["view"]


def test_glossary_covers_every_content_id(client: TestClient) -> None:
    store = store_of(client)
    rules = store.library.ruleset
    data = client.get("/api/glossary").json()

    def ids(key: str) -> set[str]:
        entries = data[key]
        assert all(e["name_zh"] for e in entries)
        return {e["id"] for e in entries}

    assert ids("terrain") == {t.id for t in rules.terrain.terrain}
    assert ids("surfaces") == {s.value for s in Surface if s is not Surface.NONE}
    assert ids("objects") == {o.id for o in rules.objects.objects}
    assert ids("statuses") == {s.id for s in rules.statuses.statuses}
    assert ids("stacks") == {k.id for k in rules.stacks.stacks}
    assert ids("reactions") == {r.id for r in rules.reactions.reactions}
    assert ids("elements") == {e.value for e in Element}
    assert ids("attributes") == {a.value for a in Attribute}
    flags = {e["id"]: e["tags"] for e in data["terrain"]}
    assert "deadly" in flags["chasm"]
    assert "blocked" in flags["wall"]


def test_glossary_has_static_rules_for_tiles(client: TestClient) -> None:
    data = client.get("/api/glossary").json()
    for key in ("terrain", "surfaces", "objects"):
        assert all(e["rules_zh"] for e in data[key]), key
    by_id = {e["id"]: e for e in data["objects"]}
    assert any("半掩護" in line for line in by_id["crate"]["rules_zh"])


def test_glossary_status_look_covers_all_statuses(
    client: TestClient, library: ContentLibrary
) -> None:
    """Phase 3-36a：statuses 每一項都帶 ``status_look``，欄位與 statuses.yaml 一致。"""
    lib = library
    glossary = client.get("/api/glossary").json()
    by_id = {e["id"]: e for e in glossary["statuses"]}
    assert set(by_id) == {s.id for s in lib.ruleset.statuses.statuses}
    for s in lib.ruleset.statuses.statuses:
        look = by_id[s.id]["status_look"]
        assert look["polarity"] == s.polarity
        assert look["control_group"] == s.control_group
        assert look["skip_turn"] is s.skip_turn
        assert look["absorbs_damage"] is s.absorbs_damage
        assert look["prevents_move"] is s.prevents_move
        assert look["removed_by_element"] == sorted(e.value for e in s.removed_by_element)
        dot = None if s.on_turn_start_damage is None else s.on_turn_start_damage.element.value
        assert look["dot_element"] == dot
    assert by_id["frozen"]["status_look"]["removed_by_element"] == ["fire"]
    assert by_id["stun"]["status_look"]["skip_turn"] is True
    assert by_id["poison"]["status_look"]["dot_element"] == "poison"
    assert glossary["terrain"][0]["status_look"] is None
