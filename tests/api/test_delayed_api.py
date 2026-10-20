"""延遲段與第二段暫停中的預覽（Phase 3F-4b）的 API。

- 延遲段：施放「蓄力斬」後，預覽有預計範圍（``landing``／``followup_tiles``）、視圖的狀態有
  ``charging``（技能、釋放時機、預計範圍），環境預告有 ``charges``（倒數、範圍、中文說明）；
- 「動作 → 位移」暫停中：``/preview`` 帶 ``followup_target`` 會預覽第二段（與 ``/decision`` 的
  結果一致），其他動作 400。
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.test_followup_api import SLASH, _paused_slash
from trpg.shared.types import Team


def _open(client: TestClient) -> dict[str, Any]:
    created = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 2, "hero_build": "build_push"}
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


def test_the_charge_shows_in_the_preview_the_view_and_the_telegraph(client: TestClient) -> None:
    body = _open(client)
    battle_id, hero = body["battle_id"], body["hero_id"]
    action = {"type": "use_skill", "unit_id": hero, "skill_id": "skill_charged_cleave"}
    assert action | {"followup_target": None} in [
        {k: a.get(k) for k in (*action, "followup_target")} for a in body["legal_actions"]
    ]
    preview = client.post(f"/api/battles/{battle_id}/preview", json=action)
    assert preview.status_code == 200, preview.text
    p = preview.json()
    tiles = len(p["followup_tiles"])
    assert p["landing"] is not None and tiles >= 4  # 以主角為中心的方陣（地圖邊緣會少幾格）
    reply = client.post(f"/api/battles/{battle_id}/actions", json=action)
    assert reply.status_code == 200, reply.text
    data = reply.json()
    me = next(u for u in data["view"]["units"] if u["id"] == hero)
    [status] = [s for s in me["statuses"] if s["status_id"] == "charging"]
    assert status["skill_id"] == "skill_charged_cleave" and status["release"] == "next_turn"
    assert status["remaining"] == 1 and len(status["charge_tiles"]) == tiles
    [charge] = data["telegraph"]["charges"]
    assert charge["unit_id"] == hero and charge["remaining"] == 1 and len(charge["tiles"]) == tiles
    assert "正在蓄力「蓄力斬」" in charge["text"] and "下回合開始時釋放" in charge["text"]
    events = [e for step in data["steps"] for e in step["events"]]
    assert any(e["type"] == "followup_charged" and "開始蓄力" in e["text"] for e in events)
    assert Team.ALLY.value == me["team"]


def test_the_paused_second_part_can_be_previewed(client: TestClient) -> None:
    _, paused = _paused_slash(client)
    battle_id, hero = paused["battle_id"], paused["hero_id"]
    pick = paused["followup_options"][-1]["followup_target"]
    action = {"type": "use_skill", "unit_id": hero, "skill_id": SLASH, "followup_target": pick}
    reply = client.post(f"/api/battles/{battle_id}/preview", json=action)
    assert reply.status_code == 200, reply.text
    p = reply.json()
    landing = pick["target_pos"]
    assert p["followup_tiles"] == [[landing["x"], landing["y"]]]  # 第二段（跳躍）只影響落點
    bad = client.post(
        f"/api/battles/{battle_id}/preview",
        json={"type": "end_turn", "unit_id": hero},
    )
    assert bad.status_code == 400 and "第二段的預覽" in bad.text
    assert client.get(f"/api/battles/{battle_id}").json()["awaiting"] == "decision"


def _workshop(skill_id: str, new_id: str) -> dict[str, Any]:
    from tests.engine.helpers import library  # noqa: PLC0415

    data = library().skills[skill_id].model_dump(mode="json", exclude_none=True)
    return {**data, "id": new_id, "provenance": {"origin": "workshop"}}


def test_a_workshop_delayed_skill_can_be_tried_out_and_charged(client: TestClient) -> None:
    """工坊的延遲段技能裝上試玩（靶場、木樁）：施放後開始蓄力，環境預告列出倒數。"""
    custom = _workshop("skill_parry_riposte", "skill_ws_parry")
    reply = client.post(
        "/api/battles",
        json={
            "map_id": "training_range",
            "seed": 3,
            "hero_build": "build_charger",
            "ally_builds": [],
            "custom_skills": [custom],
            "replace_skills": ["skill_bull_rush"],
        },
    )
    assert reply.status_code == 201, reply.text
    body = reply.json()
    hero = body["hero_id"]
    action = {"type": "use_skill", "unit_id": hero, "skill_id": "skill_ws_parry"}
    data = client.post(f"/api/battles/{body['battle_id']}/actions", json=action).json()
    [charge] = data["telegraph"]["charges"]
    assert charge["skill_id"] == "skill_ws_parry" and charge["release"] == "attacked"
    assert "被敵人攻擊就釋放" in charge["text"]
