"""以腳本客戶端透過 API 打完一場戰鬥（``docs/phases/Phase3計畫.md`` 4.5）。"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

from trpg.api.sessions import SessionStore
from trpg.engine.actions import ACTION_ADAPTER, Action
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.state import BattleState

type Chooser = Callable[[dict[str, Any], BattleState], dict[str, Any]]
"""``(回應 JSON, 伺服器內部狀態) -> 動作 JSON``。"""

MAX_REQUESTS = 3000


def first_non_end_turn(response: dict[str, Any], _state: BattleState) -> dict[str, Any]:
    """固定選第一個非 ``end_turn`` 的合法動作（都沒有時結束回合）。"""
    actions: list[dict[str, Any]] = response["legal_actions"]
    return next((a for a in actions if a["type"] != "end_turn"), actions[-1])


def utility_chooser(ai: UtilityAI) -> Chooser:
    """主角也用效用 AI（對伺服器內部的狀態）選動作。"""

    def choose(_response: dict[str, Any], state: BattleState) -> dict[str, Any]:
        action: Action = ai(state)
        data: dict[str, Any] = json.loads(ACTION_ADAPTER.dump_json(action))
        return data

    return choose


@dataclass
class Played:
    battle_id: str
    final: dict[str, Any]
    texts: list[str] = field(default_factory=list)
    """每個回應的原始 JSON 文字（依序；檢查洩漏用）。"""
    requests: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    """送出的請求：``("action", 動作)`` 或 ``("decision", {"accept": ...})``（確定性測試重送）。"""
    decisions: int = 0


def _record(played: Played, raw: str) -> dict[str, Any]:
    played.texts.append(raw)
    data: dict[str, Any] = json.loads(raw)
    return data


def play(
    client: TestClient,
    store: SessionStore,
    create: dict[str, Any],
    chooser: Chooser,
    *,
    decision_offset: int = 0,
) -> Played:
    """建立戰鬥並打到結束；反應詢問交替接受與拒絕（``decision_offset`` 為偶數時第一次接受）。"""
    created = client.post("/api/battles", json=create)
    assert created.status_code == 201, created.text
    played = Played(battle_id=created.json()["battle_id"], final={})
    response = _record(played, created.text)
    url = f"/api/battles/{played.battle_id}"
    for _ in range(MAX_REQUESTS):
        if response["awaiting"] == "ended":
            break
        if response["awaiting"] == "decision":
            body = {"accept": (decision_offset + played.decisions) % 2 == 0}
            played.decisions += 1
            played.requests.append(("decision", body))
            reply = client.post(f"{url}/decision", json=body)
        else:
            assert response["awaiting"] == "action", response["awaiting"]
            action = chooser(response, store.get(played.battle_id).state)
            played.requests.append(("action", action))
            reply = client.post(f"{url}/actions", json=action)
        assert reply.status_code == 200, reply.text
        response = _record(played, reply.text)
    else:  # pragma: no cover
        raise AssertionError("戰鬥沒有在請求上限內結束")
    played.final = response
    return played
