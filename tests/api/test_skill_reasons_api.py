"""灰掉的技能的原因、工坊試玩 Boss 地圖、`/api/builds` 法力上限、`/api/skills/{id}?battle_id=`
（Phase 3-5c-2 驗收 1、3、4）。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.api.test_workshop_api import CHARGE
from trpg.shared.types import Pos
from trpg.skillgen.draft import build_skill


def _create(client: TestClient, **extra: Any) -> dict[str, Any]:
    body = {"map_id": "open_plain", "seed": 7, "hero_build": "build_fire", **extra}
    reply = client.post("/api/battles", json=body)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _reasons(client: TestClient, battle: dict[str, Any]) -> dict[str, str]:
    reply = client.get(f"/api/battles/{battle['battle_id']}/skill-reasons")
    assert reply.status_code == 200, reply.text
    reasons: dict[str, str] = reply.json()["reasons"]
    return reasons


def test_every_gray_skill_has_a_reason_and_legal_ones_have_none(client: TestClient) -> None:
    battle = _create(client)
    reasons = _reasons(client, battle)
    legal = {a["skill_id"] for a in battle["legal_actions"] if a["type"] == "use_skill"}
    hero = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    assert set(reasons) == set(hero["skills"]) - legal
    assert all(text for text in reasons.values())


def test_reasons_name_the_missing_resource(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    hero = session.state.units[session.hero_id]
    usable = [
        s
        for s in hero.skills
        if s in {a["skill_id"] for a in battle["legal_actions"] if a["type"] == "use_skill"}
    ]
    target = usable[0]
    hero.cooldowns[target] = 2
    assert "冷卻" in _reasons(client, battle)[target]
    del hero.cooldowns[target]
    hero.mana = 0
    assert any("法力不足" in text for text in _reasons(client, battle).values())
    hero.ap = 0
    assert "AP 不足" in _reasons(client, battle)[target]


def test_out_of_reach_target_is_explained(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    state = session.state
    hero = state.units[session.hero_id]
    for unit in state.living_units():
        if unit.team is not hero.team:
            unit.pos = Pos(x=0 if hero.pos.x > 10 else 25, y=0 if hero.pos.y > 10 else 25)
    reasons = _reasons(client, battle)
    assert any("超出射程" in text or "視線" in text for text in reasons.values()), reasons


def test_reasons_are_empty_when_it_is_not_the_heros_turn(client: TestClient) -> None:
    battle = _create(client)
    end = {"type": "end_turn", "unit_id": battle["hero_id"]}
    done = client.post(f"/api/battles/{battle['battle_id']}/actions", json=end).json()
    session = store_of(client).get(battle["battle_id"])
    session.state.ended = True
    assert _reasons(client, done) == {}
    assert client.get("/api/battles/nope/skill-reasons").status_code == 404


def test_builds_report_max_mana(client: TestClient, library: Any) -> None:
    builds = {b["id"]: b for b in client.get("/api/builds").json()}
    assert builds
    for built in library.builds.builds:
        assert builds[built.id]["max_mana"] == built.hero.max_mana
    assert any(b["max_mana"] > 0 for b in builds.values())


def test_battle_skill_card_lookup_finds_custom_skills(client: TestClient) -> None:
    custom_id = build_skill(CHARGE).id
    assert client.get(f"/api/skills/{custom_id}").status_code == 404
    battle = _create(
        client,
        map_id="training_range",
        hero_build="build_charger",
        ally_builds=[],
        custom_skills=[CHARGE],
        replace_skills=["skill_bull_rush"],
    )
    card = client.get(f"/api/skills/{custom_id}", params={"battle_id": battle["battle_id"]})
    assert card.status_code == 200 and card.json()["name_zh"] == "衝鋒擊退"
    other = client.get(f"/api/skills/{custom_id}", params={"battle_id": "nope"})
    assert other.status_code == 404
    known = client.get("/api/skills/skill_bull_rush", params={"battle_id": battle["battle_id"]})
    assert known.status_code == 200


def test_workshop_arena_offers_the_boss_map(client: TestClient) -> None:
    arena = client.get("/api/workshop/arena").json()
    ids = [m["id"] for m in arena["maps"]]
    assert "bandit_lair" in ids
    assert "bandit_lair" not in [m["id"] for m in client.get("/api/maps").json()]
    battle = client.post(
        "/api/battles",
        json={
            "map_id": "bandit_lair",
            "seed": 3,
            "hero_build": "build_charger",
            "ally_builds": [],
            "custom_skills": [CHARGE],
            "replace_skills": ["skill_bull_rush"],
        },
    )
    assert battle.status_code == 201, battle.text
