"""產生前端技能特效測試用的資料（Phase 3-12）：隨機組合器的 20 個技能，各自在試玩場施放一次。

每一筆記錄：技能卡、施放那一步的事件、該步的單位位置（沒施放成功時事件為 ``null``）。
輸出 ``client/src/battle/fixtures/vfx_random_skills.json``，給 ``battle/vfx.test.ts`` 使用。

    uv run python scripts/make_vfx_fixture.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.content.library import load_library

OUT = Path(__file__).resolve().parents[1] / "client/src/battle/fixtures/vfx_random_skills.json"
SEEDS = range(1, 21)
TURNS = 8
CREATED = 201


def _distance(a: dict[str, Any], b: dict[str, Any]) -> int:
    return int(abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]))


def _cast_step(client: TestClient, body: dict[str, Any], skill_id: str) -> dict[str, Any] | None:
    """走向敵人，能施放就施放；回傳施放的那一步（找不到時 ``None``）。"""
    battle_id = body["battle_id"]
    for _ in range(TURNS):
        if body["awaiting"] != "action":
            return None
        uses = [
            a
            for a in body["legal_actions"]
            if a["type"] == "use_skill" and a["skill_id"] == skill_id
        ]
        if uses:
            reply = client.post(f"/api/battles/{battle_id}/actions", json=uses[0]).json()
            for step in reply.get("steps", []):
                events = step["events"]
                if any(e["type"] == "skill_used" and e["skill_id"] == skill_id for e in events):
                    return dict(step)
            return None
        enemies = [u["pos"] for u in body["view"]["units"] if u["team"] == "enemy" and u["hp"] > 0]
        moves = [a for a in body["legal_actions"] if a["type"] == "move"]
        if moves and enemies:
            action = min(moves, key=lambda a: min(_distance(a["path"][-1], p) for p in enemies))
        else:
            action = {"type": "end_turn", "unit_id": body["hero_id"]}
        body = client.post(f"/api/battles/{battle_id}/actions", json=action).json()
    return None


def _create(
    client: TestClient, builds: list[dict[str, Any]], skill: dict[str, Any], seed: int
) -> dict[str, Any] | None:
    """依序試各個 build（換掉第一個技能）直到能建立試玩戰鬥（武器需求、欄位上限）。"""
    for build in builds:
        reply = client.post(
            "/api/battles",
            json={
                "map_id": "training_range",
                "seed": seed,
                "hero_build": build["id"],
                "ally_builds": [],
                "custom_skills": [skill],
                "replace_skills": build["skills"][:1],
            },
        )
        if reply.status_code == CREATED:
            data: dict[str, Any] = reply.json()
            return data
    return None


def main() -> None:
    records: list[dict[str, Any]] = []
    with TestClient(create_app(load_library())) as client:
        builds = client.get("/api/builds").json()
        for seed in SEEDS:
            skill = client.post("/api/workshop/random", json={"seed": seed}).json()["skill"]
            body = _create(client, builds, skill, seed)
            if body is None:
                records.append({"seed": seed, "card": None, "events": None, "units": None})
                continue
            params = {"battle_id": body["battle_id"]}
            card = client.get(f"/api/skills/{skill['id']}", params=params).json()
            step = _cast_step(client, body, skill["id"])
            records.append(
                {
                    "seed": seed,
                    "card": card,
                    "events": None if step is None else step["events"],
                    "units": None
                    if step is None
                    else [{"id": u["id"], "pos": u["pos"]} for u in step["view"]["units"]],
                }
            )
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cast = sum(1 for r in records if r["events"] is not None)
    print(f"{len(records)} 個技能，{cast} 個有施放紀錄 → {OUT}")


if __name__ == "__main__":
    main()
