"""召喚物操控（Phase 3-33c）在網頁 API：視圖帶模式、切換模式（0 AP）、指揮選項與指揮（1 AP）、
預覽、不合法的請求。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

SKILL = "skill_raise_skeleton"


def _open_and_summon(client: TestClient) -> tuple[str, str, str, dict[str, Any]]:
    created = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 0, "hero_build": "build_trapper"}
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    action = next(
        a for a in body["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == SKILL
    )
    battle_id, hero = body["battle_id"], body["hero_id"]
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    sid = next(u["id"] for u in data["view"]["units"] if u["owner_id"] == hero)
    return battle_id, hero, sid, data


def _unit(data: dict[str, Any], uid: str) -> dict[str, Any]:
    return next(u for u in data["view"]["units"] if u["id"] == uid)


def test_the_view_carries_the_mode_and_the_command_cost(client: TestClient) -> None:
    _, hero, sid, data = _open_and_summon(client)
    summon = _unit(data, sid)
    assert summon["summon_mode"] == "follow" and summon["commanded"] is False
    assert summon["summon_target_id"] is None
    assert _unit(data, hero)["summon_mode"] is None
    assert data["view"]["summon_command_ap_cost"] == 1


def test_switching_the_mode_costs_no_ap_and_is_logged(client: TestClient) -> None:
    battle_id, hero, sid, data = _open_and_summon(client)
    ap = _unit(data, hero)["ap"]
    action = {"type": "set_summon_mode", "unit_id": hero, "summon_id": sid, "mode": "hold"}
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    out: dict[str, Any] = reply.json()
    assert _unit(out, sid)["summon_mode"] == "hold" and _unit(out, hero)["ap"] == ap
    assert out["awaiting"] == "action"
    events = [e for step in out["steps"] for e in step["events"]]
    [event] = [e for e in events if e["type"] == "summon_mode_set"]
    assert "切換為待命" in event["text"]


def test_focus_needs_a_living_enemy_target(client: TestClient) -> None:
    battle_id, hero, sid, data = _open_and_summon(client)
    foe = next(u["id"] for u in data["view"]["units"] if u["team"] == "enemy")
    bad = {"type": "set_summon_mode", "unit_id": hero, "summon_id": sid, "mode": "focus"}
    assert client.post(f"/api/battles/{battle_id}/actions", json=bad).status_code == 422
    ally = {**bad, "target_id": hero}
    assert client.post(f"/api/battles/{battle_id}/actions", json=ally).status_code == 400
    good = {**bad, "target_id": foe}
    reply = client.post(f"/api/battles/{battle_id}/actions", json=good)
    assert reply.status_code == 200, reply.text
    unit = _unit(reply.json(), sid)
    assert (unit["summon_mode"], unit["summon_target_id"]) == ("focus", foe)


def test_command_options_and_command(client: TestClient) -> None:
    battle_id, hero, sid, data = _open_and_summon(client)
    ap = _unit(data, hero)["ap"]
    options = client.get(f"/api/battles/{battle_id}/summons/{sid}/command-options")
    assert options.status_code == 200, options.text
    body: dict[str, Any] = options.json()
    assert body["summon_id"] == sid and body["ap_cost"] == 1
    stay, *moves = body["options"]
    assert stay["path"] == [stay["dest"]] and moves  # 第一個是原地
    dest = moves[0]
    action = {"type": "command_summon", "unit_id": hero, "summon_id": sid, "path": dest["path"]}
    preview = client.post(f"/api/battles/{battle_id}/preview", json=action)
    assert preview.status_code == 200, preview.text
    assert preview.json()["ap_cost"] == 1
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    out: dict[str, Any] = reply.json()
    assert _unit(out, sid)["pos"] == dest["dest"] and _unit(out, sid)["commanded"] is True
    assert _unit(out, hero)["ap"] == ap - 1
    events = [e for step in out["steps"] for e in step["events"]]
    assert any(e["type"] == "summon_commanded" and "指揮" in e["text"] for e in events)
    # 同一輪不能再指揮；選項端點也拒絕
    again = client.get(f"/api/battles/{battle_id}/summons/{sid}/command-options")
    assert again.status_code == 400 and "已經被指揮過" in again.text
    second = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert second.status_code == 400


def test_command_options_reject_other_units(client: TestClient) -> None:
    battle_id, _, _, data = _open_and_summon(client)
    foe = next(u["id"] for u in data["view"]["units"] if u["team"] == "enemy")
    reply = client.get(f"/api/battles/{battle_id}/summons/{foe}/command-options")
    assert reply.status_code == 400 and "不是你的召喚物" in reply.text


def _exhaust_hero_actions(
    client: TestClient, battle_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """主角一直做 ``end_turn`` 以外的動作（優先花 AP 的），直到只剩 ``end_turn``。"""
    for _ in range(40):
        rest = [a for a in data["legal_actions"] if a["type"] != "end_turn"]
        if not rest:
            return data
        spend = [a for a in rest if a["type"] not in ("move", "end_stance")] or rest
        reply = client.post(f"/api/battles/{battle_id}/actions", json=spend[0])
        assert reply.status_code == 200, reply.text
        data = reply.json()
    raise AssertionError("主角的動作一直用不完")


def test_a_summoner_with_no_ap_left_is_not_auto_ended(client: TestClient) -> None:
    """3-32b：AP 用完、只剩「結束回合」時，有召喚物的主角停下來等玩家（還能切模式），不自動結束。"""
    battle_id, hero, sid, data = _open_and_summon(client)
    data = _exhaust_hero_actions(client, battle_id, data)
    assert data["awaiting"] == "action" and data["view"]["active_unit"] == hero
    assert [a["type"] for a in data["legal_actions"]] == ["end_turn"]
    mode = {"type": "set_summon_mode", "unit_id": hero, "summon_id": sid, "mode": "hold"}
    switched = client.post(f"/api/battles/{battle_id}/actions", json=mode)
    assert switched.status_code == 200, switched.text
    assert switched.json()["awaiting"] == "action"
    end = {"type": "end_turn", "unit_id": hero}
    ended = client.post(f"/api/battles/{battle_id}/actions", json=end)
    assert ended.status_code == 200, ended.text
    out = ended.json()
    assert out["view"]["active_unit"] != hero or out["view"]["round"] > data["view"]["round"]
