"""複製技能（Phase 3C-4b）的 API：兩段選取。送出沒有 ``copy_cast`` 的 ``use_skill`` → 伺服器暫停
（``awaiting: decision``、``pending.kind: copy_skill``、``copy_options``）→ ``/decision`` 帶
``copy_cast`` 繼續（或放棄）。存讀 ``pending`` 與重播由引擎測試與這裡的紀錄重播涵蓋。"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.cli.battle import cmd_replay
from trpg.engine.runner import BattleLog, replay
from trpg.engine.state import state_from_json, state_to_json

COPY = "skill_mirror_cast"
BODY = {"map_id": "oil_depot", "seed": 4, "hero_build": "build_support"}


def _post(client: TestClient, battle_id: str, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
    reply = client.post(f"/api/battles/{battle_id}/{suffix}", json=body)
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _end_turn(battle: dict[str, Any]) -> dict[str, Any]:
    return {"type": "end_turn", "unit_id": battle["hero_id"]}


def _to_copyable_turn(client: TestClient) -> dict[str, Any]:
    """打到主角能施放鏡像施法的回合（本輪有別人施放過技能）。"""
    reply = client.post("/api/battles", json=BODY)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    for _ in range(300):
        if battle["awaiting"] == "ended":
            break
        if battle["awaiting"] == "decision":  # 反應詢問：接受
            battle = _post(client, battle["battle_id"], "decision", {"accept": True})
            continue
        if any(a["type"] == "use_skill" and a["skill_id"] == COPY for a in battle["legal_actions"]):
            return battle
        battle = _post(client, battle["battle_id"], "actions", _end_turn(battle))
    pytest.fail("找不到可以複製技能的回合")


def _cast_copy(client: TestClient, battle: dict[str, Any]) -> dict[str, Any]:
    bare = next(
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == COPY
    )
    assert bare["copy_cast"] is None  # legal_actions 只列一個沒有 copy_cast 的動作
    return _post(client, battle["battle_id"], "actions", bare)


def test_the_first_step_pauses_and_lists_the_copy_options(client: TestClient) -> None:
    battle = _to_copyable_turn(client)
    paused = _cast_copy(client, battle)
    assert paused["awaiting"] == "decision" and paused["legal_actions"] == []
    pending = paused["pending"]
    assert pending["kind"] == "copy_skill" and pending["unit_id"] == battle["hero_id"]
    assert pending["skill_id"] == COPY and pending["copy_skill_id"]
    options = paused["copy_options"]
    assert options and all(o["skill_id"] == pending["copy_skill_id"] for o in options)
    assert all(o["unit_id"] == battle["hero_id"] and o["copy_cast"] is None for o in options)
    # 暫停的狀態讀得回來（GET 與工作階段）：存讀 pending 序列化正確
    again = client.get(f"/api/battles/{battle['battle_id']}").json()
    assert again["awaiting"] == "decision" and again["copy_options"] == options
    state = store_of(client).get(battle["battle_id"]).state
    assert state_from_json(state_to_json(state)).pending == state.pending
    # 還沒付代價：施放者的 AP 與源力不變
    hero = next(u for u in paused["view"]["units"] if u["id"] == battle["hero_id"])
    before = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    assert (hero["ap"], hero["source"]) == (before["ap"], before["source"])
    # 暫停時不收一般動作
    reply = client.post(f"/api/battles/{battle['battle_id']}/actions", json=_end_turn(battle))
    assert reply.status_code == 409


def test_the_second_step_completes_the_copy(client: TestClient, tmp_path: Path) -> None:
    battle = _to_copyable_turn(client)
    paused = _cast_copy(client, battle)
    pick = paused["copy_options"][0]
    done = _post(client, battle["battle_id"], "decision", {"accept": True, "copy_cast": pick})
    assert done["pending"] is None and done["awaiting"] in ("action", "ended")
    texts = [e.get("text", "") for step in done["steps"] for e in step["events"]]
    assert any("複製了" in t for t in texts)
    assert any(e["type"] == "skill_copied" for step in done["steps"] for e in step["events"])
    hero = next(u for u in done["view"]["units"] if u["id"] == battle["hero_id"])
    before = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    assert hero["source"] == before["source"] - 1  # 花了鏡像施法自己的 1 點源力
    # 戰鬥紀錄（含暫停、帶 copy_cast 的決定）可以重播
    raw = client.get(f"/api/battles/{battle['battle_id']}/log").text
    log = BattleLog.model_validate_json(raw)
    assert any(s.type == "decision" and s.copy_cast is not None for s in log.actions)
    run = replay(log.setup, log.seed, log.actions)
    assert state_to_json(run.state) == state_to_json(log.final_state)
    path = tmp_path / "copy.json"
    path.write_text(raw, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0 and "重播驗證通過" in out.getvalue()


def test_declining_the_second_step_costs_nothing(client: TestClient) -> None:
    battle = _to_copyable_turn(client)
    paused = _cast_copy(client, battle)
    assert paused["awaiting"] == "decision"
    back = _post(client, battle["battle_id"], "decision", {"accept": False})
    assert back["awaiting"] == "action" and back["pending"] is None
    assert back["copy_options"] == []
    hero = next(u for u in back["view"]["units"] if u["id"] == battle["hero_id"])
    before = next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])
    assert (hero["ap"], hero["source"]) == (before["ap"], before["source"])
    assert any(a["type"] == "use_skill" and a["skill_id"] == COPY for a in back["legal_actions"])


def test_a_bad_second_step_is_400_and_keeps_the_pause(client: TestClient) -> None:
    battle = _to_copyable_turn(client)
    paused = _cast_copy(client, battle)
    url = f"/api/battles/{battle['battle_id']}/decision"
    missing = client.post(url, json={"accept": True})
    assert missing.status_code == 400 and "必須指定" in missing.json()["detail"]
    wrong = {**paused["copy_options"][0], "skill_id": "skill_fire_bolt"}
    reply = client.post(url, json={"accept": True, "copy_cast": wrong})
    assert reply.status_code == 400
    still = client.get(f"/api/battles/{battle['battle_id']}").json()
    assert still["awaiting"] == "decision" and still["copy_options"] == paused["copy_options"]


def test_a_complete_copy_action_works_in_one_request(client: TestClient) -> None:
    """玩家端也可以一次送完整動作（AI 與紀錄用的形式）。"""
    battle = _to_copyable_turn(client)
    paused = _cast_copy(client, battle)
    pick = paused["copy_options"][0]
    _post(client, battle["battle_id"], "decision", {"accept": False})
    bare = next(
        a for a in battle["legal_actions"] if a["type"] == "use_skill" and a["skill_id"] == COPY
    )
    done = _post(client, battle["battle_id"], "actions", {**bare, "copy_cast": pick})
    assert any(e["type"] == "skill_copied" for step in done["steps"] for e in step["events"])
