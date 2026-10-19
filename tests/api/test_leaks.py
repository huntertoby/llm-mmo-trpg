"""不洩漏（Phase 3-2 4.4「不可洩漏」、4.5）：隨機內部狀態、暫停結算的內部欄位、敵方隱藏陷阱。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.api.helpers import Played, play, utility_chooser
from trpg.api.presenter import step_view
from trpg.content.library import ContentLibrary
from trpg.engine.actions import ACTION_ADAPTER, Move, UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import resolve
from trpg.engine.event_filter import filter_events
from trpg.engine.events import TrapPlaced, TrapTriggered
from trpg.engine.state import BattleState, TrapState
from trpg.shared.types import Attribute, Team

FORBIDDEN_WORDS = ("rng_state", "base_state_json", "action_json", "events_emitted", '"seed"')
BEAR = "skill_bear_trap"


def _assert_clean(texts: list[str]) -> None:
    for text in texts:
        for word in FORBIDDEN_WORDS:
            assert word not in text, word


def _trap_first(ai: UtilityAI) -> Any:
    """主角能放陷阱時就放（第一個合法的陷阱技能），否則交給效用 AI。"""
    fallback = utility_chooser(ai)

    def choose(response: dict[str, Any], state: BattleState) -> dict[str, Any]:
        for action in response["legal_actions"]:
            if action["type"] == "use_skill" and state.ruleset.skill_def(action["skill_id"]).trap:
                data: dict[str, Any] = action
                return data
        return fallback(response, state)

    return choose


@pytest.fixture
def trapper_battle(client: TestClient, library: ContentLibrary) -> Played:
    return play(
        client,
        store_of(client),
        {"map_id": "open_plain", "seed": 7, "hero_build": "build_trapper"},
        _trap_first(UtilityAI(library.ai_profiles)),
    )


def test_no_response_contains_random_or_paused_internals(
    trapper_battle: Played, prompt_client: TestClient, prompt_library: ContentLibrary
) -> None:
    _assert_clean(trapper_battle.texts)
    prompted = play(
        prompt_client,
        store_of(prompt_client),
        {"map_id": "ruined_fort", "seed": 5, "hero_build": "build_tank"},
        utility_chooser(UtilityAI(prompt_library.ai_profiles)),
    )
    assert prompted.decisions > 0  # 含暫停中的回應
    _assert_clean(prompted.texts)


def test_the_hero_trap_is_hidden_from_the_enemy_view(
    client: TestClient, trapper_battle: Played
) -> None:
    session = store_of(client).get(trapper_battle.battle_id)
    placed = [e for e in session.events if isinstance(e, TrapPlaced)]
    assert placed, "主角應該放過陷阱"
    # 我方回應看得到自己的陷阱放置事件
    assert any('"type":"trap_placed"' in t for t in trapper_battle.texts)
    # 以敵方視角過濾工作階段的事件：沒有陷阱放置，放陷阱的技能不給目標格
    enemy_events = filter_events(session.events, session.state, Team.ENEMY)
    assert not any(isinstance(e, TrapPlaced) for e in enemy_events)
    trap_steps = [
        s
        for s in session.steps
        if isinstance(s, UseSkill) and session.state.ruleset.skill_def(s.skill_id).trap
    ]
    assert trap_steps
    for step in trap_steps:
        hidden = step_view(step, session.state, Team.ENEMY)
        assert isinstance(hidden, UseSkill) and hidden.target_pos is None
        assert step_view(step, session.state, Team.ALLY) == step


def _enemy_trap_session(client: TestClient) -> tuple[dict[str, Any], Move, TrapState]:
    """測試專用狀態：在主角第一個可走到的格子放一個敵方的捕獸夾。"""
    battle = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 7, "hero_build": "build_fire"}
    ).json()
    session = store_of(client).get(battle["battle_id"])
    move = next(
        ACTION_ADAPTER.validate_python(a) for a in battle["legal_actions"] if a["type"] == "move"
    )
    assert isinstance(move, Move)
    enemy = next(u for u in session.state.units_sorted() if u.team is Team.ENEMY)
    trap = TrapState(
        owner_id=enemy.id,
        team=Team.ENEMY,
        pos=move.dest,
        skill_id=BEAR,
        remaining=3,
        attributes=((Attribute.DEX, 14),),
    )
    session.state.traps = [*session.state.traps, trap]
    return battle, move, trap


def test_an_enemy_trap_never_reaches_the_ally_responses(client: TestClient) -> None:
    battle, _move, _trap = _enemy_trap_session(client)
    url = f"/api/battles/{battle['battle_id']}"
    text = client.get(url).text
    view = json.loads(text)["view"]
    assert view["traps"] == []
    assert BEAR not in text
    _assert_clean([text])


def test_preview_does_not_reveal_an_enemy_trap(client: TestClient) -> None:
    battle, move, trap = _enemy_trap_session(client)
    session = store_of(client).get(battle["battle_id"])
    # 實際結算會踩到（確認測試狀態有效）
    real = resolve(session.state, move)
    assert any(isinstance(e, TrapTriggered) for e in real.events)
    body = json.loads(ACTION_ADAPTER.dump_json(move))
    reply = client.post(f"/api/battles/{battle['battle_id']}/preview", json=body)
    assert reply.status_code == 200
    text = reply.text
    assert "trap" not in text
    assert BEAR not in text
    data = reply.json()
    assert not [o for o in data["certain"] + data["possible"] if o["kind"].startswith("trap")]
    assert session.state.traps[-1] == trap  # 預覽沒有改變工作階段
