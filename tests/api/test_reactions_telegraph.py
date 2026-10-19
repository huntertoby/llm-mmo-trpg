"""反應設定、環境預告、隊友指令顯示與連鎖預覽的 API 層測試（Phase 3-4b）。"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.api.helpers import MAX_REQUESTS, Played, utility_chooser
from tests.engine.helpers import make_map, make_state, no_reactions, spawn
from trpg.cli.battle import cmd_replay
from trpg.content.library import ContentLibrary
from trpg.engine import EndTurn, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.environment import telegraph
from trpg.engine.events import EVENT_LIST_ADAPTER
from trpg.engine.runner import BattleLog, replay
from trpg.engine.state import BattleState, state_to_json
from trpg.shared.types import Team

CREATE = {"map_id": "open_plain", "seed": 7, "hero_build": "build_fire"}


def _create(client: TestClient, **kw: Any) -> dict[str, Any]:
    reply = client.post("/api/battles", json={**CREATE, **kw})
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _url(battle: dict[str, Any], suffix: str = "") -> str:
    return f"/api/battles/{battle['battle_id']}{suffix}"


def _hero(response: dict[str, Any]) -> dict[str, Any]:
    return next(u for u in response["view"]["units"] if u["id"] == response["hero_id"])


def _set_mode(client: TestClient, battle: dict[str, Any], reaction: str, mode: str) -> Any:
    body = {
        "type": "set_reaction_mode",
        "unit_id": battle["hero_id"],
        "reaction": reaction,
        "mode": mode,
    }
    return client.post(_url(battle, "/actions"), json=body)


# ---------------------------------------------------------------------------
# 反應設定
# ---------------------------------------------------------------------------


def test_view_lists_the_heros_reaction_rules_only(client: TestClient) -> None:
    battle = _create(client)
    hero = _hero(battle)
    assert hero["reaction_rules"] and all(r["mode"] == "auto" for r in hero["reaction_rules"])
    rule = hero["reaction_rules"][0]
    assert {"reaction", "name_zh", "trigger_zh", "mode", "stamina_cost"} <= set(rule)
    enemies = [u for u in battle["view"]["units"] if u["team"] == "enemy"]
    assert enemies and all(u["reaction_rules"] == [] for u in enemies)
    assert "set_reaction_mode" not in {a["type"] for a in battle["legal_actions"]}


def test_set_reaction_mode_is_one_step_and_does_not_advance(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    reaction = _hero(battle)["reaction_rules"][0]["reaction"]
    reply = _set_mode(client, battle, reaction, "prompt")
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert len(data["steps"]) == 1 and data["steps"][0]["step"]["type"] == "set_reaction_mode"
    assert data["steps"][0]["events"][0]["type"] == "reaction_mode_set"
    assert "每次詢問" in data["steps"][0]["events"][0]["text"]
    assert data["awaiting"] == "action" and data["view"]["active_unit"] == battle["hero_id"]
    after = {r["reaction"]: r["mode"] for r in _hero(data)["reaction_rules"]}
    assert after[reaction] == "prompt"
    assert _hero(data)["ap"] == _hero(battle)["ap"]
    assert session.steps[-1].type == "set_reaction_mode"
    # 再切回自動、關閉
    for mode in ("off", "auto"):
        again = _set_mode(client, battle, reaction, mode).json()
        assert {r["reaction"]: r["mode"] for r in _hero(again)["reaction_rules"]}[reaction] == mode


def test_set_reaction_mode_rejections(client: TestClient) -> None:
    battle = _create(client)
    unknown = _set_mode(client, battle, "no_such_reaction", "off")
    assert unknown.status_code == 400 and "沒有反應規則" in unknown.json()["detail"]
    reaction = _hero(battle)["reaction_rules"][0]["reaction"]
    assert _set_mode(client, battle, reaction, "sometimes").status_code == 422
    other = next(u["id"] for u in battle["view"]["units"] if u["id"] != battle["hero_id"])
    body = {"type": "set_reaction_mode", "unit_id": other, "reaction": reaction, "mode": "off"}
    assert client.post(_url(battle, "/actions"), json=body).status_code == 400


def _play_with_modes(
    client: TestClient, library: ContentLibrary, create: dict[str, Any], mode: str
) -> tuple[Played, int]:
    """開局先把主角所有反應規則設為 ``mode``，再用效用 AI 打完；詢問時交替接受與拒絕。"""
    store = store_of(client)
    chooser = utility_chooser(UtilityAI(library.ai_profiles))
    first = client.post("/api/battles", json=create).json()
    played = Played(battle_id=first["battle_id"], final={})
    url = f"/api/battles/{played.battle_id}"
    response = first
    for rule in _hero(first)["reaction_rules"]:
        body = {
            "type": "set_reaction_mode",
            "unit_id": first["hero_id"],
            "reaction": rule["reaction"],
            "mode": mode,
        }
        response = client.post(f"{url}/actions", json=body).json()
        played.requests.append(("action", body))
    for _ in range(MAX_REQUESTS):
        if response["awaiting"] == "ended":
            break
        if response["awaiting"] == "decision":
            body = {"accept": played.decisions % 2 == 0}
            played.decisions += 1
            reply = client.post(f"{url}/decision", json=body)
        else:
            reply = client.post(
                f"{url}/actions", json=chooser(response, store.get(played.battle_id).state)
            )
        assert reply.status_code == 200, reply.text
        response = reply.json()
    played.final = response
    return played, played.decisions


@pytest.mark.parametrize(
    "case",
    [
        ("open_plain", 7, "build_fire"),
        ("narrow_halls", 11, "build_trapper"),
        ("ruined_fort", 5, "build_tank"),
    ],
)
def test_prompt_and_off_modes_replay_identically(
    client: TestClient, library: ContentLibrary, tmp_path: Path, case: tuple[str, int, str]
) -> None:
    map_id, seed, hero = case
    create = {"map_id": map_id, "seed": seed, "hero_build": hero}
    for mode in ("prompt", "off"):
        played, decisions = _play_with_modes(client, library, create, mode)
        assert played.final["awaiting"] == "ended"
        if mode == "off":
            assert decisions == 0
        raw = client.get(f"/api/battles/{played.battle_id}/log").text
        log = BattleLog.model_validate_json(raw)
        assert any(s.type == "set_reaction_mode" for s in log.actions)
        run = replay(log.setup, log.seed, log.actions)
        assert state_to_json(run.state) == state_to_json(log.final_state)
        assert EVENT_LIST_ADAPTER.dump_json(run.events) == EVENT_LIST_ADAPTER.dump_json(log.events)  # type: ignore[arg-type]
        path = tmp_path / f"{map_id}_{mode}.json"
        path.write_text(raw, encoding="utf-8")
        out = io.StringIO()
        assert cmd_replay(path, out) == 0 and "重播驗證通過" in out.getvalue()


def test_prompt_mode_produces_decisions_somewhere(
    client: TestClient, library: ContentLibrary
) -> None:
    total = 0
    for map_id, seed, hero in [
        ("open_plain", 7, "build_fire"),
        ("narrow_halls", 11, "build_trapper"),
        ("ruined_fort", 5, "build_tank"),
    ]:
        total += _play_with_modes(
            client, library, {"map_id": map_id, "seed": seed, "hero_build": hero}, "prompt"
        )[1]
    assert total > 0


# ---------------------------------------------------------------------------
# 環境預告
# ---------------------------------------------------------------------------


def _fire_field() -> BattleState:
    """火 (0, 0)；油 (1, 0)、(2, 0)；草叢 (0, 1)；油桶 (3, 0)（與引擎預告測試相同的場地）。"""
    m = make_map(
        "000000\n000000\n000000",
        surfaces=[(0, 0, "fire"), (1, 0, "oil"), (2, 0, "oil")],
        objects=[(0, 1, "grass"), (3, 0, "oil_barrel")],
        ally=[(5, 2)],
        enemy=[(4, 2)],
    )
    return make_state(
        m,
        [
            spawn(Team.ALLY, (5, 2), no_reactions("hero_fighter", max_hp=500)),
            spawn(Team.ENEMY, (4, 2), no_reactions("bandit", max_hp=500)),
        ],
    )


def _finish_round(state: BattleState) -> list[Any]:
    start = state.round
    events: list[Any] = []
    while state.round == start and not state.ended:
        assert state.active_unit is not None
        result = resolve(state, EndTurn(unit_id=state.active_unit))
        state, events = result.state, events + result.events
    began = next(i for i, e in enumerate(events) if e.type == "environment_started")
    ended = next(i for i, e in enumerate(events) if e.type == "environment_ended")
    return events[began : ended + 1]


def _xy(pos: dict[str, int] | None) -> tuple[int | None, int | None]:
    return (None, None) if pos is None else (pos["x"], pos["y"])


def _signature(changes: list[dict[str, Any]]) -> set[tuple[str, int | None, int | None]]:
    return {(c["kind"], *_xy(c["pos"])) for c in changes}


def test_response_telegraph_matches_the_next_environment_round(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    session.state = _fire_field()
    session.pending = None
    reply = client.get(_url(battle))
    assert reply.status_code == 200
    forecast = reply.json()["telegraph"]
    assert forecast["round"] == 1
    assert forecast["changes"] and all(c["text"] for c in forecast["changes"])
    actual = [e for e in _finish_round(_fire_field()) if e.type in _KIND]
    expected = {(_KIND[e.type], e.pos.x, e.pos.y) for e in actual}
    assert _signature(forecast["changes"]) == expected
    assert ("surface", 1, 0) in expected and ("object_ignited", 0, 1) in expected
    # 與引擎的 telegraph 一致，且不改變工作階段
    assert len(forecast["changes"]) == len(telegraph(_fire_field()).changes)
    assert session.state.tile(1, 0).surface.value == "oil"


_KIND = {
    "surface_changed": "surface",
    "terrain_changed": "terrain",
    "object_destroyed": "object_destroyed",
    "object_ignited": "object_ignited",
    "object_exploded": "object_exploded",
    "unit_spawned": "unit_spawned",
}


def test_telegraph_burning_and_text_and_no_leaks(client: TestClient) -> None:
    battle = _create(client)
    assert set(battle["telegraph"]) == {"round", "changes", "burning", "upcoming"}
    text = json.dumps(battle["telegraph"], ensure_ascii=False)
    assert "rng_state" not in text and "seed" not in text


def test_telegraph_ignores_the_enemys_hidden_traps(
    client: TestClient, library: ContentLibrary
) -> None:
    from trpg.engine.state import TrapState  # noqa: PLC0415
    from trpg.shared.types import Pos  # noqa: PLC0415

    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    state = session.state.clone()
    enemy = next(u for u in state.units_sorted() if u.team is Team.ENEMY)
    rules = session.state.ruleset
    skill_id = next(s for s in library.skills if rules.skill_def(s).trap is not None)
    trap = TrapState(
        owner_id=enemy.id,
        team=Team.ENEMY,
        pos=Pos(x=0, y=0),
        skill_id=skill_id,
        remaining=3,
        attributes=(),
    )
    state.traps = [trap]
    session.state = state
    data = client.get(_url(battle)).json()
    assert data["view"]["traps"] == []
    assert trap.skill_id not in json.dumps(data)


# ---------------------------------------------------------------------------
# 隊友指令的忽略原因、連鎖預覽、技能卡片
# ---------------------------------------------------------------------------


def test_orders_ignored_reports_orders_that_cannot_run(client: TestClient) -> None:
    battle = _create(client)
    assert battle["orders_ignored"] == []
    target = next(u["id"] for u in battle["view"]["units"] if u["team"] == "enemy")
    body = {"team_orders": [{"kind": "focus_target", "target": target}], "unit_orders": {}}
    ok = client.put(_url(battle, "/orders"), json=body)
    assert ok.status_code == 200 and ok.json()["orders"]["team_orders"][0]["target"] == target
    assert ok.json()["orders_ignored"] == []
    # 目標倒下後指令無法執行：側欄要能顯示原因
    session = store_of(client).get(battle["battle_id"])
    state = session.state.clone()
    state.units[target].hp = 0
    state.units[target].downed = True
    session.state = state
    ignored = client.get(_url(battle)).json()["orders_ignored"]
    assert ignored and ignored[0]["scope"] == "team" and "已倒下" in ignored[0]["reason"]
    cleared = client.put(_url(battle, "/orders"), json={"team_orders": [], "unit_orders": {}})
    assert cleared.json()["orders"]["team_orders"] == []


def test_preview_lists_filtered_chain_events_with_text(client: TestClient) -> None:
    battle = _create(client)
    seen = 0
    for action in battle["legal_actions"]:
        if action["type"] not in {"attack", "use_skill", "move"}:
            continue
        data = client.post(_url(battle, "/preview"), json=action).json()
        for key in ("min_events", "max_events"):
            assert isinstance(data[key], list)
            assert all("seq" in e and "type" in e for e in data[key])
            assert "rng_state" not in json.dumps(data[key]) and '"seed"' not in json.dumps(
                data[key]
            )
        seen += len(data["max_events"])
        if action["type"] == "attack":
            assert any(e.get("text") for e in data["max_events"])
            assert len(data["max_events"]) >= len(data["min_events"]) > 0
    assert seen > 0


def test_skill_cards_never_say_ap_none(client: TestClient, library: ContentLibrary) -> None:
    passives = [s for s in library.skills.values() if s.ap_cost is None and not s.is_activatable]
    assert passives
    for skill in passives:
        card = client.get(f"/api/skills/{skill.id}").json()
        assert not any("None" in part for part in card["cost"])
        assert not any(part.startswith("AP") for part in card["cost"])
