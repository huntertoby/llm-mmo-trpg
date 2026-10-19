"""賭博型技能（Phase 3D-7a）在網頁 API：預覽附上賭注兩個分支的機率與結果、失手反噬的說明，
技能卡片列出賭注與反噬，戰鬥紀錄帶中文的擲骰與反噬文字。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

SACRIFICE = "skill_blood_sacrifice"
ALL_IN = "skill_all_in"
BODY = {"map_id": "open_plain", "seed": 2, "hero_build": "build_gambler"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _skill(battle: dict[str, Any], skill_id: str) -> list[dict[str, Any]]:
    return [
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == skill_id
    ]


def _to_turn(client: TestClient) -> dict[str, Any]:
    """主角第 1 輪先走到離敵人最近的格子，兩個近戰賭博技能才有目標。"""
    reply = client.post("/api/battles", json=BODY)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    foes = [(u["pos"]["x"], u["pos"]["y"]) for u in battle["view"]["units"] if u["team"] == "enemy"]

    def gap(action: dict[str, Any]) -> int:
        end = action["path"][-1]
        return int(min(abs(end["x"] - x) + abs(end["y"] - y) for x, y in foes))

    moves = [a for a in battle["legal_actions"] if a["type"] == "move"]
    battle = _post(client, battle["battle_id"], "actions", min(moves, key=gap))
    assert _skill(battle, SACRIFICE) and _skill(battle, ALL_IN)
    return battle


def test_the_preview_lists_both_gamble_branches(client: TestClient) -> None:
    battle = _to_turn(client)
    action = _skill(battle, SACRIFICE)[0]
    preview = _post(client, battle["battle_id"], "preview", action)
    gamble = preview["gamble"]
    assert gamble["chance_permille"] == 600
    win, lose = gamble["branches"]
    assert (win["kind"], win["permille"], win["multiplier_permille"]) == ("win", 600, 2000)
    assert (lose["kind"], lose["permille"], lose["multiplier_permille"]) == ("lose", 400, 1000)
    assert win["self_damage_max"] == 0 and lose["self_damage_max"] > 0
    assert win["targets"][0]["damage"]["maximum"] > lose["targets"][0]["damage"]["maximum"]
    assert preview["miss_notes"] == []


def test_the_preview_of_a_plain_skill_has_no_gamble_and_the_miss_backlash_is_noted(
    client: TestClient,
) -> None:
    battle = _to_turn(client)
    preview = _post(client, battle["battle_id"], "preview", _skill(battle, ALL_IN)[0])
    assert preview["gamble"] is None
    assert preview["miss_notes"] == ["失手時：你獲得「倒地」"]


def test_skill_cards_list_the_gamble_and_the_miss_backlash(client: TestClient) -> None:
    sacrifice = client.get(f"/api/skills/{SACRIFICE}").json()
    assert sacrifice["effects"][1].startswith("賭注（命中後擲 d1000）——60%：本次傷害 ×2")
    assert "gamble" in sacrifice["tags"]
    all_in = client.get(f"/api/skills/{ALL_IN}").json()
    assert all_in["cost"][-1] == "失手（含自然 1）時：你獲得「倒地」"


def test_casting_a_gamble_logs_the_roll(client: TestClient) -> None:
    battle = _to_turn(client)
    data = _post(client, battle["battle_id"], "actions", _skill(battle, SACRIFICE)[0])
    events = [e for step in data["steps"] for e in step["events"]]
    rolled = [e for e in events if e["type"] == "gamble_rolled"]
    missed = not any(e["type"] == "attack_rolled" and e["hit"] for e in events)
    if missed:  # 未命中：整個賭注不結算
        assert not rolled
        return
    assert len(rolled) == 1 and "賭上了「血祭重擊」" in rolled[0]["text"]
    assert 1 <= rolled[0]["roll"] <= 1000
