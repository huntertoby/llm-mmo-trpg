"""吸血、聖光雙效、驅散與揭露（Phase 3D-8a）在網頁 API：技能卡片描述新機制，新 build 的主角可以在
戰鬥中選到這些技能。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def _battle(client: TestClient, build: str) -> dict[str, Any]:
    body = {"map_id": "open_plain", "seed": 2, "hero_build": build}
    reply = client.post("/api/battles", json=body)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_skill_cards_describe_the_new_mechanics(client: TestClient) -> None:
    drain = client.get("/api/skills/skill_life_drain").json()
    assert "吸血：你回復造成傷害的 40%" in drain["effects"][0]
    burst = client.get("/api/skills/skill_holy_burst").json()
    assert "友方（含自己）改為治療同樣的骰值" in burst["effects"][0]
    dispel = client.get("/api/skills/skill_dispel_magic").json()
    assert "驅散目標身上的全部增益" in dispel["effects"][0]
    flare = client.get("/api/skills/skill_flare_sight").json()
    assert "揭露範圍內的敵人" in flare["effects"][0] and "敵方陷阱" in flare["effects"][0]


@pytest.mark.parametrize(
    ("build", "skill_id"),
    [
        ("build_support", "skill_life_drain"),
        ("build_healer", "skill_holy_burst"),
        ("build_seer", "skill_dispel_magic"),
        ("build_seer", "skill_flare_sight"),
    ],
)
def test_the_new_builds_offer_the_demo_skills(
    client: TestClient, build: str, skill_id: str
) -> None:
    battle = _battle(client, build)
    heroes = [u for u in battle["view"]["units"] if skill_id in u["skills"]]
    assert heroes and heroes[0]["team"] == "ally"
