"""復活、技能內的擊殺時效果與定時炸彈（Phase 3D-8b）在網頁 API：技能卡片描述新機制、倒下的友方在
視圖裡標為可復活並出現在復活技能的合法目標、預覽列出復活與炸彈的倒數與範圍、施放後視圖與環境
預告帶著炸彈的倒數與範圍。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.engine.helpers import rng_state_for
from trpg.engine.effects import run_effects
from trpg.engine.effects.models import DamageEffect
from trpg.shared.types import Pos, Team


def _open(client: TestClient, build: str) -> dict[str, Any]:
    created = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 2, "hero_build": build}
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    assert body["awaiting"] == "action"
    return body


def _get(client: TestClient, battle_id: str) -> dict[str, Any]:
    reply = client.get(f"/api/battles/{battle_id}")
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_skill_cards_describe_the_new_mechanics(client: TestClient) -> None:
    revive = client.get("/api/skills/skill_resurrection").json()
    assert "站起來" in revive["effects"][0] and "每個單位每場最多一次" in revive["effects"][0]
    harvest = client.get("/api/skills/skill_ash_harvest").json()
    assert "若這一招讓敵人倒下" in harvest["effects"][0] and "返還 1 AP" in harvest["effects"][0]
    assert "冷卻歸零" in harvest["effects"][0]
    bomb = client.get("/api/skills/skill_time_bomb_rune").json()
    assert "定時炸彈" in bomb["effects"][0] and "環境回合後" in bomb["effects"][0]


@pytest.mark.parametrize(
    ("build", "skill_id"),
    [
        ("build_healer", "skill_resurrection"),
        ("build_bomber", "skill_time_bomb_rune"),
        ("build_bomber", "skill_ash_harvest"),
    ],
)
def test_the_builds_offer_the_demo_skills(client: TestClient, build: str, skill_id: str) -> None:
    battle = _open(client, build)
    heroes = [u for u in battle["view"]["units"] if skill_id in u["skills"]]
    assert heroes and heroes[0]["team"] == "ally"


def test_a_downed_teammate_can_be_revived_through_the_api(client: TestClient) -> None:
    body = _open(client, "build_healer")
    battle_id, hero = body["battle_id"], body["hero_id"]
    session = store_of(client).get(battle_id)
    mate = next(u for u in session.state.units_sorted() if u.team is Team.ALLY and u.id != hero)
    mate.pos = Pos(x=session.state.units[hero].pos.x + 1, y=session.state.units[hero].pos.y)
    session.state = run_effects(
        session.state, [DamageEffect(target_id=mate.id, mode="lethal", apply_element_mod=False)]
    ).state
    now = _get(client, battle_id)
    unit = next(u for u in now["view"]["units"] if u["id"] == mate.id)
    assert unit["downed"] and unit["revivable"]
    revives = [
        a
        for a in now["legal_actions"]
        if a["type"] == "use_skill" and a["skill_id"] == "skill_resurrection"
    ]
    assert [a["target_id"] for a in revives] == [mate.id]
    preview = client.post(f"/api/battles/{battle_id}/preview", json=revives[0])
    assert preview.status_code == 200, preview.text
    [info] = preview.json()["revives"]
    assert info["unit_id"] == mate.id and info["hp"] >= 1
    assert any(e["type"] == "unit_revived" for e in preview.json()["min_events"])
    reply = client.post(f"/api/battles/{battle_id}/actions", json=revives[0])
    assert reply.status_code == 200, reply.text
    data = reply.json()
    events = [e for step in data["steps"] for e in step["events"]]
    [revived] = [e for e in events if e["type"] == "unit_revived"]
    assert revived["unit_id"] == mate.id and "重新站了起來" in revived["text"]
    after = next(u for u in data["view"]["units"] if u["id"] == mate.id)
    assert not after["downed"] and not after["revivable"] and after["hp"] == revived["hp"]


def test_the_time_bomb_shows_in_the_preview_the_view_and_the_telegraph(
    client: TestClient,
) -> None:
    body = _open(client, "build_bomber")
    battle_id, hero = body["battle_id"], body["hero_id"]
    session = store_of(client).get(battle_id)
    foe = next(u for u in session.state.units_sorted() if u.team is Team.ENEMY)
    foe.pos = Pos(x=session.state.units[hero].pos.x + 2, y=session.state.units[hero].pos.y)
    session.state.rng_state = rng_state_for([(20, 19)])  # 第一顆 d20 擲 19：命中
    now = _get(client, battle_id)
    action = next(
        a
        for a in now["legal_actions"]
        if a["type"] == "use_skill"
        and a["skill_id"] == "skill_time_bomb_rune"
        and a["target_id"] == foe.id
    )
    preview = client.post(f"/api/battles/{battle_id}/preview", json=action)
    assert preview.status_code == 200, preview.text
    [bomb] = preview.json()["bombs"]
    assert (bomb["unit_id"], bomb["rounds"], bomb["radius"]) == (foe.id, 2, 1)
    assert len(bomb["tiles"]) >= 3
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    data = reply.json()
    carrier = next(u for u in data["view"]["units"] if u["id"] == foe.id)
    [status] = [s for s in carrier["statuses"] if s["status_id"] == "time_bomb"]
    assert status["remaining"] == 2 and status["blast_radius"] == 1
    [info] = data["telegraph"]["bombs"]
    assert info["unit_id"] == foe.id and info["remaining"] == 2 and info["radius"] == 1
    assert "定時炸彈" in info["text"] and "還要 2 次環境回合爆炸" in info["text"]
