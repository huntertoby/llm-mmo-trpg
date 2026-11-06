"""Phase 3-54d：工坊的技能元素與預覽武器下拉的 API。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of

_TERRAIN: dict[str, Any] = {
    "skeleton": "control",
    "kind": "active",
    "category": "spell",
    "weapon_req": "focus",
    "scaling_attr": "int",
    "tier": 2,
    "ap_cost": 2,
    "element": "earth",
    "shape": {"type": "square3", "range": 4},
    "effects": [{"type": "lower_terrain", "affects": "tiles"}],
    "cost": {"mana": 8, "cooldown": 3},
    "rarity": "epic",
}


def test_weapons_endpoint_lists_every_player_weapon(client: TestClient) -> None:
    body = client.get("/api/workshop/weapons").json()
    ids = [w["id"] for w in body]
    assert len(ids) == len(set(ids)) > 5
    assert {w["weapon_class"] for w in body} == {"melee", "ranged", "focus"}
    assert all(w["name_zh"] and w["class_zh"] for w in body)
    library = store_of(client).library
    assert all(not library.weapons[i].summon_only for i in ids)


def test_basics_step_has_the_optional_skill_element(client: TestClient) -> None:
    body = client.post(
        "/api/workshop/options", json={"skill": {"skeleton": "control", "kind": "active"}}
    ).json()
    basics = next(s for s in body["steps"] if s["id"] == "basics")
    element = next(f for f in basics["fields"] if f["field"] == "element")
    assert not element["required"]
    values = [c["value"] for c in element["choices"]]
    assert "earth" in values and "physical" not in values


def test_check_card_shows_the_skill_element_and_the_earth_rule(client: TestClient) -> None:
    check = client.post("/api/workshop/check", json={"skill": _TERRAIN}).json()
    assert check["card"]["element"] == "大地" and check["card"]["element_id"] == "earth"
    assert not [p for p in check["problems"] if "terrain_needs_earth" in p["rule"]]
    burning = {**_TERRAIN, "element": "fire"}
    fire = client.post("/api/workshop/check", json={"skill": burning}).json()
    assert [p for p in fire["problems"] if "terrain_needs_earth" in p["rule"]]


def test_effect_options_grey_out_earth_only_parts_without_the_earth_element(
    client: TestClient,
) -> None:
    def terrain_choice(skill: dict[str, Any]) -> dict[str, Any]:
        body = client.post("/api/workshop/options", json={"skill": skill}).json()
        effects = next(s for s in body["steps"] if s["id"] == "effects")
        field = next(f for f in effects["fields"] if f["field"] == "effects")
        return next(c for c in field["choices"] if c["value"] == "lower_terrain")

    base = {k: v for k, v in _TERRAIN.items() if k not in ("effects", "cost", "rarity")}
    assert "unavailable_zh" not in terrain_choice(base)["info"]
    fire = terrain_choice({**base, "element": "fire"})
    assert "大地" in fire["info"]["unavailable_zh"]
    plain = {k: v for k, v in base.items() if k != "element"}
    assert "unavailable_zh" in terrain_choice(plain)["info"]
