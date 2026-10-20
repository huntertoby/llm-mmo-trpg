"""複合技能（Phase 3F-3a）的 API：合法動作帶 ``followup_target``、預覽回傳落點與動作段範圍、施放後
事件有 ``skill_followup``，戰鬥紀錄可以重播。以「裝上試玩」把示範技能「瞬影旋斬」換進衝鋒流。"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from trpg.cli.battle import cmd_replay

DEMO = "skill_shadow_whirl"


def _demo() -> dict[str, Any]:
    data = library().skills[DEMO].model_dump(mode="json", exclude_none=True)
    data.pop("id")
    return data


def _post(client: TestClient, path: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(path, json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_cast_a_composite_through_the_api_and_replay_it(client: TestClient, tmp_path: Path) -> None:
    reply = client.post(
        "/api/battles",
        json={
            "map_id": "training_range",
            "seed": 3,
            "hero_build": "build_charger",
            "ally_builds": [],
            "custom_skills": [_demo()],
            "replace_skills": ["skill_guard_swap"],
        },
    )
    assert reply.status_code == 201, reply.text
    battle = reply.json()
    battle_id = battle["battle_id"]
    # 先走向木樁 (6, 4)，讓落點的錐形打得到
    moves = [a for a in battle["legal_actions"] if a["type"] == "move"]
    move = min(moves, key=lambda a: abs(a["path"][-1]["x"] - 6) + abs(a["path"][-1]["y"] - 4))
    battle = _post(client, f"/api/battles/{battle_id}/actions", move)
    combos = [
        a
        for a in battle["legal_actions"]
        if a["type"] == "use_skill" and a.get("followup_target") is not None
    ]
    assert combos and all(a["followup_target"]["direction"] for a in combos)
    best: tuple[int, dict[str, Any], dict[str, Any]] | None = None
    for action in combos:
        p = _post(client, f"/api/battles/{battle_id}/preview", action)
        hits = len(p["targets"])
        if best is None or hits > best[0]:
            best = (hits, action, p)
    assert best is not None and best[0] > 0
    _, action, p = best
    landing = [action["target_pos"]["x"], action["target_pos"]["y"]]
    assert p["landing"] == landing
    assert p["followup_tiles"] and all(t in p["affected_tiles"] for t in p["followup_tiles"])
    body = _post(client, f"/api/battles/{battle_id}/actions", action)
    events = [e for step in body["steps"] for e in step["events"]]
    follow = [e for e in events if e["type"] == "skill_followup"]
    assert follow and [follow[0]["origin"]["x"], follow[0]["origin"]["y"]] == landing
    assert "第二段" in follow[0]["text"]
    log = tmp_path / "combo.json"
    log.write_text(client.get(f"/api/battles/{battle_id}/log").text, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(log, out) == 0 and "重播驗證通過" in out.getvalue()


def test_followup_target_on_a_plain_skill_is_rejected(client: TestClient) -> None:
    reply = client.post(
        "/api/battles", json={"map_id": "training_range", "seed": 3, "hero_build": "build_charger"}
    )
    battle = reply.json()
    plain = next(a for a in battle["legal_actions"] if a["type"] == "use_skill")
    bad = {**plain, "followup_target": {"direction": "east"}}
    reply = client.post(f"/api/battles/{battle['battle_id']}/preview", json=bad)
    assert reply.status_code == 400 and "只有複合技能" in reply.text
