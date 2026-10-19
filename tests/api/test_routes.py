"""每個端點的正常與錯誤情況（Phase 3-2 4.4／4.5）：404／400／409／422／500。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.api.app import create_app
from trpg.content.library import ContentLibrary
from trpg.engine.runner import BattleLog
from trpg.engine.state import state_to_json
from trpg.shared.types import UnitId

CREATE = {"map_id": "open_plain", "seed": 7, "hero_build": "build_fire"}


def _create(client: TestClient, **extra: Any) -> dict[str, Any]:
    reply = client.post("/api/battles", json={**CREATE, **extra})
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _url(battle: dict[str, Any], suffix: str = "") -> str:
    return f"/api/battles/{battle['battle_id']}{suffix}"


def _end_turn(battle: dict[str, Any]) -> dict[str, Any]:
    return {"type": "end_turn", "unit_id": battle["hero_id"]}


def _until(
    client: TestClient, battle: dict[str, Any], awaiting: str, limit: int = 500
) -> dict[str, Any]:
    """主角一律結束回合（詢問一律接受），直到 ``awaiting``。"""
    current = battle
    for _ in range(limit):
        if current["awaiting"] == awaiting:
            return current
        if current["awaiting"] == "decision":
            reply = client.post(_url(battle, "/decision"), json={"accept": True})
        else:
            reply = client.post(_url(battle, "/actions"), json=_end_turn(battle))
        assert reply.status_code == 200, reply.text
        current = reply.json()
    raise AssertionError(f"沒有等到 {awaiting}")


# ---------------------------------------------------------------------------
# 內容
# ---------------------------------------------------------------------------


def test_maps_lists_the_ten_playable_maps(client: TestClient) -> None:
    reply = client.get("/api/maps")
    assert reply.status_code == 200
    maps = reply.json()
    assert len(maps) == 10
    assert {"id", "name_zh", "archetype", "width", "height"} == set(maps[0])
    assert all(not m["id"].startswith("test_") for m in maps)
    assert [m["id"] for m in maps] == sorted(m["id"] for m in maps)


def test_builds_lists_every_build(client: TestClient, library: ContentLibrary) -> None:
    builds = client.get("/api/builds").json()
    assert [b["id"] for b in builds] == [b.id for b in library.builds.builds]
    assert builds[0]["name_zh"] and builds[0]["skills"]


def test_skill_card_has_text_and_codes(client: TestClient) -> None:
    card = client.get("/api/skills/skill_bear_trap").json()
    assert card["name_zh"] == "捕獸夾"
    assert card["skeleton"] == "trap"
    assert card["rarity_id"] and card["kind_id"] == "active"
    assert card["scaling_attrs"] == ["dex"]
    assert card["effects"]


def test_unknown_skill_is_404(client: TestClient) -> None:
    reply = client.get("/api/skills/skill_nope")
    assert reply.status_code == 404
    assert "skill_nope" in reply.json()["detail"]


# ---------------------------------------------------------------------------
# 建立與讀取
# ---------------------------------------------------------------------------


def test_create_advances_to_the_hero_and_includes_the_opening(client: TestClient) -> None:
    battle = _create(client)
    assert battle["awaiting"] == "action"
    assert battle["hero_id"] == "unit_0001"
    assert battle["view"]["active_unit"] == battle["hero_id"]
    assert battle["pending"] is None and battle["outcome"] is None
    opening = battle["steps"][0]
    assert opening["actor_id"] is None and opening["step"] is None
    assert opening["events"][0]["type"] == "battle_started"
    assert opening["events"][0]["text"].startswith("戰鬥開始：")
    assert any(a["type"] == "end_turn" for a in battle["legal_actions"])
    assert all(a["unit_id"] == battle["hero_id"] for a in battle["legal_actions"])
    # 預設補隊友：build 英雄 ＋ 2 名標準隊友
    allies = [u for u in battle["view"]["units"] if u["team"] == "ally"]
    assert [u["template_id"] for u in allies] == [
        "build_fire",
        "sim_companion_fighter",
        "sim_companion_archer",
    ]


def test_create_with_explicit_ally_builds(client: TestClient) -> None:
    battle = _create(client, ally_builds=["build_tank"], max_rounds=5)
    allies = [u["template_id"] for u in battle["view"]["units"] if u["team"] == "ally"]
    assert allies == ["build_fire", "build_tank"]
    assert battle["view"]["max_rounds"] == 5


@pytest.mark.parametrize(
    "body",
    [
        {**CREATE, "map_id": "nowhere"},
        {**CREATE, "map_id": "test_flat_6x6"},  # 沒有預設遭遇
        {**CREATE, "hero_build": "build_nope"},
        {**CREATE, "ally_builds": ["build_tank", "build_nope"]},
        {**CREATE, "seed": -1},
        {**CREATE, "seed": 2**64},
        {**CREATE, "max_rounds": 0},
        {"map_id": "open_plain", "seed": 7},  # 缺 hero_build
        {**CREATE, "extra": 1},
    ],
)
def test_bad_create_requests_are_422(client: TestClient, body: dict[str, Any]) -> None:
    reply = client.post("/api/battles", json=body)
    assert reply.status_code == 422, reply.text


def test_get_returns_the_current_state_without_steps(client: TestClient) -> None:
    battle = _create(client)
    again = client.get(_url(battle)).json()
    assert again["steps"] == []
    assert again["view"] == battle["view"]
    assert again["legal_actions"] == battle["legal_actions"]


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("get", "", None),
        ("post", "/actions", {"type": "end_turn", "unit_id": "unit_0001"}),
        ("post", "/decision", {"accept": True}),
        ("post", "/preview", {"type": "end_turn", "unit_id": "unit_0001"}),
        ("put", "/orders", {}),
        ("get", "/log", None),
    ],
)
def test_unknown_battle_is_404(
    client: TestClient, method: str, suffix: str, body: dict[str, Any] | None
) -> None:
    kwargs = {} if body is None else {"json": body}
    reply = getattr(client, method)(f"/api/battles/nope{suffix}", **kwargs)
    assert reply.status_code == 404
    assert "nope" in reply.json()["detail"]


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


def test_a_legal_action_advances_to_the_next_hero_turn(client: TestClient) -> None:
    battle = _create(client)
    reply = client.post(_url(battle, "/actions"), json=_end_turn(battle))
    assert reply.status_code == 200
    data = reply.json()
    assert data["steps"][0]["actor_id"] == battle["hero_id"]
    assert data["steps"][0]["step"]["type"] == "end_turn"
    assert len(data["steps"]) > 1  # 其他單位由 AI 自動行動
    assert data["awaiting"] in {"action", "ended"}
    assert {s["actor_id"] for s in data["steps"][1:]} - {battle["hero_id"]}


def test_an_illegal_action_is_400_and_changes_nothing(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    before = (state_to_json(session.state), len(session.steps))
    hero = battle["hero_id"]
    reply = client.post(
        _url(battle, "/actions"), json={"type": "attack", "unit_id": hero, "target_id": hero}
    )
    assert reply.status_code == 400
    assert reply.json()["detail"]
    assert (state_to_json(session.state), len(session.steps)) == before


def test_an_action_for_another_unit_is_400(client: TestClient) -> None:
    battle = _create(client)
    reply = client.post(_url(battle, "/actions"), json={"type": "end_turn", "unit_id": "unit_0002"})
    assert reply.status_code == 400
    assert "只能操控主角" in reply.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [
        {"type": "fly", "unit_id": "unit_0001"},
        {"type": "attack", "unit_id": "unit_0001"},  # 沒有目標
        {"type": "move", "unit_id": "unit_0001", "path": []},
        {"unit_id": "unit_0001"},
    ],
)
def test_a_malformed_action_is_422(client: TestClient, body: dict[str, Any]) -> None:
    battle = _create(client)
    assert client.post(_url(battle, "/actions"), json=body).status_code == 422


def test_actions_and_decisions_after_the_end_are_409(client: TestClient) -> None:
    battle = _until(client, _create(client, max_rounds=1), "ended")
    assert battle["outcome"] is not None and battle["outcome"]["round"] == 1
    assert battle["legal_actions"] == []
    for suffix, body in (
        ("/actions", _end_turn(battle)),
        ("/decision", {"accept": True}),
        ("/preview", _end_turn(battle)),
        ("/orders", {}),
    ):
        method = client.put if suffix == "/orders" else client.post
        reply = method(_url(battle, suffix), json=body)
        assert reply.status_code == 409, suffix
        assert reply.json()["detail"] == "戰鬥已結束"


def test_a_decision_while_waiting_for_an_action_is_409(client: TestClient) -> None:
    battle = _create(client)
    reply = client.post(_url(battle, "/decision"), json={"accept": True})
    assert reply.status_code == 409
    assert client.post(_url(battle, "/decision"), json={"accept": "maybe"}).status_code == 422


def test_waiting_for_a_decision_rejects_actions_with_409(prompt_client: TestClient) -> None:
    battle = _until(prompt_client, _create(prompt_client, hero_build="build_tank"), "decision")
    pending = battle["pending"]
    assert pending["unit_id"] == battle["hero_id"] and pending["kind"] == "reaction"
    assert battle["legal_actions"] == []
    assert set(pending) == {
        "kind",
        "unit_id",
        "reaction",
        "trigger_unit_id",
        "skill_id",
        "trigger_event_seq",
        "stamina_cost",
        "mana_cost",
        "hp_cost_permille",
    }
    for suffix in ("/actions", "/preview"):
        reply = prompt_client.post(_url(battle, suffix), json=_end_turn(battle))
        assert reply.status_code == 409
    answered = prompt_client.post(_url(battle, "/decision"), json={"accept": False})
    assert answered.status_code == 200
    first = answered.json()["steps"][0]
    assert first["step"] == {"type": "decision", "unit_id": battle["hero_id"], "accept": False}


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def test_preview_returns_the_numbers_and_does_not_change_the_session(client: TestClient) -> None:
    battle = _create(client)
    session = store_of(client).get(battle["battle_id"])
    before = (state_to_json(session.state), len(session.steps), len(session.events))
    actions = battle["legal_actions"]
    attack = next(a for a in actions if a["type"] in {"attack", "use_skill"})
    reply = client.post(_url(battle, "/preview"), json=attack)
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert set(data) == {
        "action",
        "hit_permille",
        "crit_permille",
        "damage",
        "affected_tiles",
        "affected_units",
        "certain",
        "possible",
        "cover",
        "notes",
        "targets",
        "healed",
        "min_events",
        "max_events",
    }
    assert data["action"] == attack
    move = next(a for a in actions if a["type"] == "move")
    moved = client.post(_url(battle, "/preview"), json=move)
    assert moved.status_code == 200
    assert moved.json()["hit_permille"] is None
    assert (state_to_json(session.state), len(session.steps), len(session.events)) == before
    assert client.get(_url(battle)).json()["view"] == battle["view"]


def test_preview_errors(client: TestClient) -> None:
    battle = _create(client)
    hero = battle["hero_id"]
    bad = {"type": "attack", "unit_id": hero, "target_id": hero}
    assert client.post(_url(battle, "/preview"), json=bad).status_code == 400
    other = {"type": "end_turn", "unit_id": "unit_0002"}
    assert client.post(_url(battle, "/preview"), json=other).status_code == 400
    assert client.post(_url(battle, "/preview"), json={"type": "x"}).status_code == 422


# ---------------------------------------------------------------------------
# 戰術指令
# ---------------------------------------------------------------------------


def _enemy_id(battle: dict[str, Any]) -> str:
    return str(next(u["id"] for u in battle["view"]["units"] if u["team"] == "enemy"))


def _ally_ids(battle: dict[str, Any]) -> list[str]:
    return [u["id"] for u in battle["view"]["units"] if u["team"] == "ally"]


def test_focus_order_is_applied_and_logged(client: TestClient) -> None:
    battle = _create(client)
    target = _enemy_id(battle)
    orders = {"team_orders": [{"kind": "focus_target", "target": target}]}
    reply = client.put(_url(battle, "/orders"), json=orders)
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert data["orders"]["team_orders"] == [{"kind": "focus_target", "target": target}]
    assert data["steps"] == []
    # 下一次我方 AI 決策即生效：效用 AI 讀到的指令
    session = store_of(client).get(battle["battle_id"])
    companion = UnitId(_ally_ids(battle)[1])
    assert session.policy.ai.orders is not None
    (order,) = session.policy.ai.orders(session.state, companion)
    assert order.kind == "focus_target"
    log = BattleLog.model_validate_json(client.get(_url(battle, "/log")).text)
    assert len(log.orders) == 1
    record = log.orders[0]
    assert record.round == battle["view"]["round"]
    assert record.orders.team_orders[0].kind == "focus_target"
    # 空集合 ＝ 取消
    cleared_reply = client.put(_url(battle, "/orders"), json={})
    assert cleared_reply.status_code == 200, cleared_reply.text
    cleared = cleared_reply.json()
    assert cleared["orders"] == {"team_orders": [], "unit_orders": {}}
    log = BattleLog.model_validate_json(client.get(_url(battle, "/log")).text)
    assert [len(r.orders.team_orders) for r in log.orders] == [1, 0]


@pytest.mark.parametrize(
    "make",
    [
        lambda b: {"team_orders": [{"kind": "focus_target", "target": _ally_ids(b)[1]}]},
        lambda b: {"team_orders": [{"kind": "protect", "ward": _enemy_id(b)}]},
        lambda b: {"team_orders": [{"kind": "retreat_to", "at": [99, 99]}]},
        lambda b: {"unit_orders": {b["hero_id"]: [{"kind": "use_environment"}]}},
        lambda b: {"unit_orders": {_enemy_id(b): [{"kind": "use_environment"}]}},
        lambda b: {"unit_orders": {"unit_9999": [{"kind": "use_environment"}]}},
        lambda b: {"team_orders": [{"kind": "use_environment"}, {"kind": "use_environment"}]},
        lambda b: {"team_orders": [{"kind": "dance"}]},
    ],
)
def test_invalid_orders_are_422(client: TestClient, make: Any) -> None:
    battle = _create(client)
    reply = client.put(_url(battle, "/orders"), json=make(battle))
    assert reply.status_code == 422, reply.text
    assert client.get(_url(battle)).json()["orders"] == {"team_orders": [], "unit_orders": {}}


def test_a_semantic_order_error_has_a_chinese_reason(client: TestClient) -> None:
    battle = _create(client)
    ally = _ally_ids(battle)[1]
    reply = client.put(
        _url(battle, "/orders"), json={"team_orders": [{"kind": "focus_target", "target": ally}]}
    )
    assert reply.json()["detail"] == f"目標 {ally} 不是敵人"


# ---------------------------------------------------------------------------
# 紀錄與推進上限
# ---------------------------------------------------------------------------


def test_log_has_the_cli_format(client: TestClient) -> None:
    battle = _create(client)
    client.post(_url(battle, "/actions"), json=_end_turn(battle))
    reply = client.get(_url(battle, "/log"))
    assert reply.status_code == 200
    log = BattleLog.model_validate_json(reply.text)
    assert log.format.startswith("trpg-battle-log/")
    assert log.seed == CREATE["seed"]
    session = store_of(client).get(battle["battle_id"])
    assert log.actions == session.steps
    assert any(a.type == "end_turn" and a.unit_id == battle["hero_id"] for a in log.actions)


def test_exceeding_the_auto_advance_limit_is_500_and_keeps_the_session(
    library: ContentLibrary,
) -> None:
    with TestClient(create_app(library, max_auto_steps=0)) as client:
        reply = client.post("/api/battles", json=CREATE)
        if reply.status_code == 201:  # 主角先攻：建立時不用推進，結束回合時才超過
            battle = reply.json()
            reply = client.post(_url(battle, "/actions"), json=_end_turn(battle))
        assert reply.status_code == 500
        body = reply.json()
        assert "超過 0 個動作" in body["detail"]
        kept = client.get(f"/api/battles/{body['battle_id']}")
        assert kept.status_code == 200
        assert kept.json()["awaiting"] == "stalled"
        assert client.get(f"/api/battles/{body['battle_id']}/log").status_code == 200
        hero = kept.json()["hero_id"]
        stuck = client.post(
            f"/api/battles/{body['battle_id']}/actions", json={"type": "end_turn", "unit_id": hero}
        )
        assert stuck.status_code == 409
