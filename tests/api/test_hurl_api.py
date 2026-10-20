"""投擲物件（Phase 3C-5a）的 API：兩段選取（物件 → 落點）以一個完整的 ``use_skill`` 表達——
``target_object_id`` 是被舉起的物件、``target_pos`` 是落點。``legal_actions`` 列出每一組合法的
（物件, 落點），客戶端可以先依 ``target_object_id`` 分組選物件、再選落點（網頁介面在 3C-5b）。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

HURL = "skill_telekinetic_hurl"
BODY = {"map_id": "narrow_halls", "seed": 9, "hero_build": "build_telekinesis"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _hurls(battle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == HURL
    ]


def _to_hurl_turn(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/battles", json=BODY)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    for _ in range(300):
        if battle["awaiting"] == "ended":
            break
        if battle["awaiting"] == "decision":
            battle = _post(client, battle["battle_id"], "decision", {"accept": True})
            continue
        if _hurls(battle):
            return battle
        end = {"type": "end_turn", "unit_id": battle["hero_id"]}
        battle = _post(client, battle["battle_id"], "actions", end)
    pytest.fail("找不到可以投擲物件的回合")


def test_legal_actions_carry_object_and_landing_pairs(client: TestClient) -> None:
    battle = _to_hurl_turn(client)
    hurls = _hurls(battle)
    assert all(a["target_object_id"] and a["target_pos"] for a in hurls)
    assert all(a["target_id"] is None and a["direction"] is None for a in hurls)
    objects = {a["target_object_id"] for a in hurls}
    for obj in objects:  # 每個物件都有多個落點可選（第二段選取）
        assert len([a for a in hurls if a["target_object_id"] == obj]) > 1


def test_posting_a_pair_hurls_the_object(client: TestClient) -> None:
    battle = _to_hurl_turn(client)
    action = _hurls(battle)[0]
    after = _post(client, battle["battle_id"], "actions", action)
    events = [e for step in after["steps"] for e in step["events"]]
    thrown = [e for e in events if e["type"] == "object_hurled"]
    assert len(thrown) == 1
    assert thrown[0]["object_id"] == action["target_object_id"]
    assert thrown[0]["to_pos"] == action["target_pos"]
    assert "丟向" in thrown[0]["text"]
    remaining = {o["id"]: o for o in after["view"]["objects"]}
    if thrown[0]["outcome"] == "placed":
        assert remaining[action["target_object_id"]]["pos"] == thrown[0]["placed_pos"]
    else:  # 爆炸、碎掉或找不到落腳處：物件從戰場上消失
        assert action["target_object_id"] not in remaining


def test_a_pair_with_only_the_object_is_rejected(client: TestClient) -> None:
    battle = _to_hurl_turn(client)
    action = dict(_hurls(battle)[0], target_pos=None)
    reply = client.post(f"/api/battles/{battle['battle_id']}/actions", json=action)
    assert reply.status_code == 400
    assert "同時指定" in reply.text


def test_the_preview_of_a_pair_shows_the_object_and_the_landing(client: TestClient) -> None:
    """網頁的兩段選取：選好（物件, 落點）後預覽給出物件的去向與落地結果（Phase 3C-5b）。"""
    battle = _to_hurl_turn(client)
    action = _hurls(battle)[0]
    preview = _post(client, battle["battle_id"], "preview", action)
    (hurl,) = preview["hurls"]
    assert hurl["object_id"] == action["target_object_id"]
    assert hurl["to_pos"] == [action["target_pos"]["x"], action["target_pos"]["y"]]
    assert hurl["outcome"] in {"exploded", "shattered", "placed", "lost"}
    assert preview["pierce"] is None and preview["topples"] == []
