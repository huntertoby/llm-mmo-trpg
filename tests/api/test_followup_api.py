"""複合技能第二段選目標（Phase 3F-4a）的 API：送出沒有 ``followup_target`` 的「回馬斬」
（動作 → 位移）→ 第一段結算後伺服器暫停（``awaiting: decision``、``pending.kind: followup``、
``followup_options``）→ ``/decision`` 帶 ``followup_target`` 繼續（或放棄第二段）；戰鬥紀錄
可以重播。

在靶場以「裝上試玩」把回馬斬（換一個 ID）裝到衝鋒流主角身上（換下蠻牛衝陣），對木樁施放。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.engine.helpers import library
from trpg.cli.battle import cmd_replay
from trpg.engine.runner import BattleLog, replay
from trpg.engine.state import state_from_json, state_to_json

SLASH = "skill_ws_retreating_slash"


def _slash() -> dict[str, Any]:
    data = library().skills["skill_retreating_slash"].model_dump(mode="json", exclude_none=True)
    return {**data, "id": SLASH, "provenance": {"origin": "workshop"}}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _units(body: dict[str, Any], team: str) -> list[dict[str, Any]]:
    return [u for u in body["view"]["units"] if u["team"] == team and u["hp"] > 0]


def _distance(a: dict[str, Any], b: dict[str, Any]) -> int:
    return int(abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]))


def _hits(client: TestClient, battle_id: str, action: dict[str, Any]) -> int:
    p = client.post(f"/api/battles/{battle_id}/preview", json=action).json()
    return sum(1 for t in p["targets"] if not t["ally"])


def _paused_slash(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    """建立試玩戰鬥、走到木樁旁邊施放回馬斬（不帶第二段）；回傳（施放前、暫停後）的回應。"""
    reply = client.post(
        "/api/battles",
        json={
            "map_id": "training_range",
            "seed": 3,
            "hero_build": "build_charger",
            "ally_builds": [],
            "custom_skills": [_slash()],
            "replace_skills": ["skill_bull_rush"],
        },
    )
    assert reply.status_code == 201, reply.text
    body: dict[str, Any] = reply.json()
    battle_id = body["battle_id"]
    for _ in range(6):
        slashes = [
            a
            for a in body["legal_actions"]
            if a["type"] == "use_skill" and a["skill_id"] == SLASH and a["followup_target"] is None
        ]
        best = max(slashes, key=lambda a: _hits(client, battle_id, a), default=None)
        if best is not None and _hits(client, battle_id, best) > 0:
            return body, _post(client, battle_id, "actions", best)
        dummies = _units(body, "enemy")
        moves = [a for a in body["legal_actions"] if a["type"] == "move"]
        if moves:
            move = min(
                moves, key=lambda a: min(_distance(a["path"][-1], d["pos"]) for d in dummies)
            )
            body = _post(client, battle_id, "actions", move)
            continue
        end = {"type": "end_turn", "unit_id": body["hero_id"]}
        body = _post(client, battle_id, "actions", end)
    pytest.fail("走不到木樁旁邊")


def test_the_slash_pauses_after_the_first_part_and_lists_the_landings(client: TestClient) -> None:
    before, paused = _paused_slash(client)
    battle_id = paused["battle_id"]
    assert paused["awaiting"] == "decision" and paused["legal_actions"] == []
    pending = paused["pending"]
    assert pending["kind"] == "followup" and pending["skill_id"] == SLASH
    assert pending["unit_id"] == paused["hero_id"]
    options = paused["followup_options"]
    assert options and all(o["followup_target"]["target_pos"] for o in options)
    assert all(len(o["tiles"]) == 1 for o in options)  # 跳躍只影響落點
    events = [e for step in paused["steps"] for e in step["events"]]
    assert any(e["type"] == "damage_dealt" for e in events)  # 錐形斬擊已結算
    assert not any(e["type"] == "skill_followup" for e in events)
    again = client.get(f"/api/battles/{battle_id}").json()
    assert again["awaiting"] == "decision" and again["followup_options"] == options
    state = store_of(client).get(battle_id).state
    assert state_from_json(state_to_json(state)).pending == state.pending
    end = {"type": "end_turn", "unit_id": paused["hero_id"]}
    assert client.post(f"/api/battles/{battle_id}/actions", json=end).status_code == 409
    # 不合法的第二段：400，暫停不變
    bad = {"accept": True, "followup_target": {"target_pos": {"x": 0, "y": 0}}}
    reply = client.post(f"/api/battles/{battle_id}/decision", json=bad)
    assert reply.status_code == 400 and "第二段" in reply.text
    assert client.get(f"/api/battles/{battle_id}").json()["awaiting"] == "decision"
    assert before["awaiting"] == "action"


def test_the_decision_completes_the_slash_and_the_log_replays(
    client: TestClient, tmp_path: Path
) -> None:
    _, paused = _paused_slash(client)
    battle_id = paused["battle_id"]
    pick = paused["followup_options"][-1]["followup_target"]
    done = _post(client, battle_id, "decision", {"accept": True, "followup_target": pick})
    assert done["pending"] is None and done["followup_options"] == []
    events = [e for step in done["steps"] for e in step["events"]]
    follow = [e for e in events if e["type"] == "skill_followup"]
    assert [f["when"] for f in follow] == ["after_action"]
    assert any("接著施展" in e.get("text", "") for e in events)
    hero = next(u for u in done["view"]["units"] if u["id"] == done["hero_id"])
    assert hero["pos"] == pick["target_pos"]
    raw = client.get(f"/api/battles/{battle_id}/log").text
    log = BattleLog.model_validate_json(raw)
    assert any(s.type == "decision" and s.followup_target is not None for s in log.actions)
    run = replay(log.setup, log.seed, log.actions)
    assert state_to_json(run.state) == state_to_json(log.final_state)
    path = tmp_path / "slash.json"
    path.write_text(raw, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0 and "重播驗證通過" in out.getvalue()


def test_declining_skips_only_the_second_part(client: TestClient) -> None:
    _, paused = _paused_slash(client)
    hero_before = next(u for u in paused["view"]["units"] if u["id"] == paused["hero_id"])
    back = _post(client, paused["battle_id"], "decision", {"accept": False})
    assert back["pending"] is None
    events = [e for step in back["steps"] for e in step["events"]]
    assert any(e.get("reason") == "followup_declined" for e in events)
    assert any("放棄了第二段" in e.get("text", "") for e in events)
    hero = next(u for u in back["view"]["units"] if u["id"] == back["hero_id"])
    assert hero["pos"] == hero_before["pos"]
