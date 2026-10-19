"""Phase 3D-3 的四個新反應事件在網頁詢問模式（``prompt``）下被詢問：``awaiting: decision``、
``pending`` 帶出反應與觸發者、``/decision`` 接受或拒絕後繼續。

情境由引擎測試的世界建立、結算到暫停，再把暫停的狀態放回 API 的工作階段（狀態本身就是完整的
引擎狀態），所以這裡測的是 API 對新事件的暫停與回應，不是 AI 的行為。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.engine.helpers import give_turn
from tests.engine.skill_helpers import U1, U2, U3
from tests.engine.test_passive_triggers import always
from tests.engine.test_reaction_events_3d3 import (
    AMBUSH,
    COUNTERSPELL,
    COVERING_FIRE,
    FIRE_BOLT,
    GRIEF_RAGE,
    ambush_world,
    downed_world,
    prompt_state,
    targeted_world,
    walk,
)
from trpg.engine import Action, Attack, BattleState, ResolveResult, UseSkill, resolve


def _prompting(state: BattleState) -> BattleState:
    """持有者（U1）的反應規則全部改為 ``prompt``。"""
    unit = state.units[U1]
    unit.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in unit.reactions)
    return state


def _scenarios() -> list[tuple[str, BattleState, Action, str]]:
    return [
        (
            "hit_by_spell",
            prompt_state("hit_by_spell", COUNTERSPELL),
            UseSkill(unit_id=U2, skill_id=FIRE_BOLT, target_id=U1),
            COUNTERSPELL,
        ),
        (
            "ally_downed",
            _prompting(downed_world()),
            Attack(unit_id=U2, target_id=U3),
            GRIEF_RAGE,
        ),
        (
            "enemy_enters_adjacent",
            _prompting(ambush_world()),
            walk((6, 3), (5, 3), (4, 3)),
            AMBUSH,
        ),
        (
            "ally_targeted",
            _prompting(targeted_world()),
            Attack(unit_id=U2, target_id=U3),
            COVERING_FIRE,
        ),
    ]


def _open(client: TestClient, paused: ResolveResult) -> str:
    """建立一場戰鬥，再把暫停中的狀態放進它的工作階段。"""
    created = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 0, "hero_build": "build_tank"}
    )
    assert created.status_code == 201, created.text
    battle_id: str = created.json()["battle_id"]
    session = store_of(client).get(battle_id)
    assert session.hero_id == U1
    session.state = paused.state
    session.pending = paused.pending
    return battle_id


@pytest.mark.parametrize(("event", "state", "action", "skill_id"), _scenarios())
def test_the_web_asks_about_the_new_reactions(
    event: str,
    state: BattleState,
    action: Action,
    skill_id: str,
    *,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    paused = resolve(give_turn(state, action.unit_id), action)
    assert paused.pending is not None, event
    battle_id = _open(client, paused)
    got = client.get(f"/api/battles/{battle_id}")
    assert got.status_code == 200, got.text
    body: dict[str, Any] = got.json()
    assert body["awaiting"] == "decision" and body["legal_actions"] == []
    pending = body["pending"]
    assert (pending["kind"], pending["unit_id"], pending["skill_id"]) == ("reaction", U1, skill_id)
    assert pending["reaction"] == skill_id and pending["trigger_unit_id"] in (U2, U3)
    hero = next(u for u in body["view"]["units"] if u["id"] == U1)
    (rule,) = hero["reaction_rules"]
    assert (rule["reaction"], rule["event"], rule["mode"]) == (skill_id, event, "prompt")
    assert rule["trigger_zh"]  # 規則的觸發時機有中文說明（view.REACTION_TRIGGER_TEXT）


@pytest.mark.parametrize(("event", "state", "action", "skill_id"), _scenarios())
def test_accepting_and_declining_continue_the_battle(
    event: str,
    state: BattleState,
    action: Action,
    skill_id: str,
    *,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    for accept in (True, False):
        paused = resolve(give_turn(state, action.unit_id), action)
        battle_id = _open(client, paused)
        reply = client.post(f"/api/battles/{battle_id}/decision", json={"accept": accept})
        assert reply.status_code == 200, reply.text
        data: dict[str, Any] = reply.json()
        events = [e for step in data["steps"] for e in step["events"]]
        kinds = [e["type"] for e in events]
        assert ("reaction_triggered" in kinds) is accept, event
        assert ("reaction_declined" in kinds) is not accept, event
        assert data["pending"] is None
