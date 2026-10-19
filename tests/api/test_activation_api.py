"""常駐類傳說（Phase 3D-6）在網頁 API：修正型傳說從技能列啟動、視圖列出生效中的傳說、技能卡片帶
啟動方式與規則改變的描述、生效中不能再啟動。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

AVATAR = "skill_war_avatar"


def _open(client: TestClient) -> dict[str, Any]:
    created = client.post(
        "/api/battles", json={"map_id": "swamp", "seed": 0, "hero_build": "build_charger"}
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    assert body["awaiting"] == "action"
    return body


def test_the_hero_activates_a_modifier_legendary_from_the_skill_bar(client: TestClient) -> None:
    body = _open(client)
    battle_id, hero_id = body["battle_id"], body["hero_id"]
    action = next(
        a for a in body["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == AVATAR
    )
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    events = [e for step in data["steps"] for e in step["events"]]
    activated = [e for e in events if e["type"] == "skill_activated"]
    assert activated and "啟動了傳說「戰神降臨」" in activated[0]["text"]
    hero = next(u for u in data["view"]["units"] if u["id"] == hero_id)
    [active] = hero["activations"]
    assert (active["skill_id"], active["activation"], active["rule_name_zh"]) == (
        AVATAR,
        "timed",
        None,
    )
    assert active["expires_round"] == data["view"]["round"] + 3
    assert not any(
        a["type"] == "use_skill" and a["skill_id"] == AVATAR for a in data["legal_actions"]
    )
    again = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert again.status_code == 400 and "已經啟動" in again.json()["detail"]


def test_skill_cards_describe_the_activation_and_the_rule_change(client: TestClient) -> None:
    avatar = client.get(f"/api/skills/{AVATAR}").json()
    assert avatar["activation"] == "限時：花 AP 1 ＋ 源力 1 啟動，持續 3 輪"
    assert avatar["activation_id"] == "timed" and avatar["ap_cost"] == 1
    flame = client.get("/api/skills/skill_kindred_flame").json()
    assert flame["activation"] == "整場：花 AP 1 ＋ 源力 1 啟動，本場剩餘時間有效"
    assert flame["effects"] == [
        "規則改變「慈焰」：你造成的火焰傷害打到友方（不含自己）時，改為治療（原本傷害的 100%）"
    ]
