"""``/api/world``：大世界的 API（Phase 5A-5；``docs/phases/Phase5計畫.md`` 10.3、10.6）。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import MAX_REQUESTS, utility_chooser
from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.world.replay import replay
from trpg.world.save import loads_char, loads_log, loads_world

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


class Clock:
    def __init__(self) -> None:
        self.now = NOON

    def __call__(self) -> int:
        self.now += 7
        return self.now


@pytest.fixture(scope="module")
def ambush(library: ContentLibrary) -> ContentLibrary:
    """每一步都遇敵（城鎮與傳送點除外）。"""
    return with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    """不會遇敵。"""
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


def _client(library: ContentLibrary, saves: Path) -> TestClient:
    app = create_app(library, save_dir=saves)
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = Clock()
    return TestClient(app)


@pytest.fixture
def saves(tmp_path: Path) -> Path:
    return tmp_path / "saves"


@pytest.fixture
def calm_client(calm: ContentLibrary, saves: Path) -> Iterator[TestClient]:
    with _client(calm, saves) as c:
        yield c


@pytest.fixture
def ambush_client(ambush: ContentLibrary, saves: Path) -> Iterator[TestClient]:
    with _client(ambush, saves) as c:
        yield c


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _create(client: TestClient, **over: Any) -> dict[str, Any]:
    return _ok(client.post("/api/world/characters", json={**START, **over}), 201)


def _act(client: TestClient, cid: str, **action: Any) -> dict[str, Any]:
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=action))


def _loc(view: dict[str, Any], location: str) -> dict[str, Any]:
    found: dict[str, Any] = next(x for x in view["map"]["locations"] if x["id"] == location)
    return found


def _ids(view: dict[str, Any]) -> set[str]:
    return {x["id"] for x in view["map"]["locations"]}


# ---------------------------------------------------------------------------
# 建立與讀取
# ---------------------------------------------------------------------------


def test_create_character_in_town(calm_client: TestClient) -> None:
    view = _create(calm_client)
    char = view["character"]
    assert char["name"] == "阿霧"
    assert char["level"] == 1
    assert char["hp"] == char["max_hp"] > 0
    assert char["supplies"] == 5
    assert len(char["skills"]) == 2
    assert view["here"]["location"] == "mist_ferry"
    assert view["here"]["can_rest"] is True
    assert view["encounter"] is None
    assert _loc(view, "mist_ferry")["current"] is True
    assert _loc(view, "ferry_steps")["adjacent"] is True
    assert _loc(view, "ferry_steps")["blocked_zh"] is None
    assert _loc(view, "ashen_ferry")["blocked_zh"] == "還沒開放"
    listed: list[dict[str, Any]] = calm_client.get("/api/world/characters").json()
    assert [c["character_id"] for c in listed] == [char["character_id"]]
    assert listed[0]["location_name_zh"] == "霧渡鎮"


@pytest.mark.parametrize(
    "over",
    [
        {"name": "   "},
        {"name": "一二三四五六七八九十十一十二"},
        {"keywords": ["ignite"]},
        {"weapon": "nope"},
    ],
)
def test_create_rejects_bad_input(calm_client: TestClient, over: dict[str, Any]) -> None:
    reply = calm_client.post("/api/world/characters", json={**START, **over})
    assert reply.status_code == 422, reply.text


def test_unknown_character_is_404(calm_client: TestClient) -> None:
    assert calm_client.get("/api/world/characters/cdeadbeef").status_code == 404
    assert calm_client.get("/api/world/characters/..%2Fx").status_code == 404


def test_hidden_locations_are_not_sent(calm_client: TestClient) -> None:
    view = _create(calm_client)
    assert {"crane_cliff", "elixir_cave"}.isdisjoint(_ids(view))
    for a, b in view["map"]["edges"]:
        assert {a, b} <= _ids(view)


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------


def test_travel_to_neighbour(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    view = _act(calm_client, cid, kind="travel", to="ferry_steps")
    assert view["here"]["location"] == "ferry_steps"
    assert any("渡口石階" in e for e in view["events"])
    hasty = _act(calm_client, cid, kind="travel", to="bamboo_path", hasten=True)
    assert hasty["character"]["supplies"] == 4
    reply = calm_client.post(
        f"/api/world/characters/{cid}/actions", json={"kind": "travel", "to": "cloud_summit"}
    )
    assert reply.status_code == 422
    assert "相鄰" in reply.json()["detail"]


def test_fight_action_is_not_accepted(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    reply = calm_client.post(
        f"/api/world/characters/{cid}/actions", json={"kind": "fight", "steps": []}
    )
    assert reply.status_code == 422


def test_camp_and_rest(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    town = _ok(calm_client.get(f"/api/world/characters/{cid}"))
    assert town["here"]["camp_problem_zh"] is not None
    _act(calm_client, cid, kind="travel", to="hunter_hut")  # 村落可以紮營
    camp = _act(calm_client, cid, kind="camp")
    assert camp["here"]["camped"] is True
    assert camp["here"]["can_loadout"] is True
    assert camp["character"]["supplies"] == 4
    _act(calm_client, cid, kind="travel", to="mist_ferry")
    rested = _act(calm_client, cid, kind="rest")
    assert rested["character"]["supplies"] == 5
    assert any("休息" in e for e in rested["events"])


def test_loadout_in_town(calm_client: TestClient) -> None:
    view = _create(calm_client)
    cid = view["character"]["character_id"]
    first, second = (s["id"] for s in view["character"]["skills"])
    changed = _act(calm_client, cid, kind="loadout", skills=[first])
    assert [s["id"] for s in changed["character"]["skills"]] == [first]
    assert [s["id"] for s in changed["character"]["bench"]] == [second]
    _act(calm_client, cid, kind="travel", to="ferry_steps")
    reply = calm_client.post(
        f"/api/world/characters/{cid}/actions", json={"kind": "loadout", "skills": [first, second]}
    )
    assert reply.status_code == 422


# ---------------------------------------------------------------------------
# 遭遇與戰鬥
# ---------------------------------------------------------------------------


def test_encounter_lineup_and_retreat(ambush_client: TestClient) -> None:
    cid = _create(ambush_client)["character"]["character_id"]
    met = _act(ambush_client, cid, kind="travel", to="ferry_steps")
    encounter = met["encounter"]
    assert encounter is not None
    assert encounter["location"] == "ferry_steps"
    assert encounter["enemies"]
    assert encounter["retreat_to_zh"] == "霧渡鎮"
    assert encounter["in_battle"] is False
    assert _loc(met, "bamboo_path")["blocked_zh"] == "先處理眼前的遭遇"
    back = _act(ambush_client, cid, kind="retreat")
    assert back["encounter"] is None
    assert back["here"]["location"] == "mist_ferry"


def test_battle_without_encounter_is_409(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    assert calm_client.post(f"/api/world/characters/{cid}/battle").status_code == 409


def _finish_battle(client: TestClient, battle: dict[str, Any], library: ContentLibrary) -> None:
    """主角交給效用 AI，打到結束（反應詢問一律接受）。"""
    store = client.app.state.store  # type: ignore[attr-defined]
    assert isinstance(store, SessionStore)
    chooser = utility_chooser(UtilityAI(library.ai_profiles))
    url = f"/api/battles/{battle['battle_id']}"
    response = battle
    for _ in range(MAX_REQUESTS):
        if response["awaiting"] == "ended":
            return
        if response["awaiting"] == "decision":
            reply = client.post(f"{url}/decision", json={"accept": True})
        else:
            action = chooser(response, store.get(battle["battle_id"]).state)
            reply = client.post(f"{url}/actions", json=action)
        response = _ok(reply)
    raise AssertionError("戰鬥沒有在請求上限內結束")  # pragma: no cover


def test_battle_writes_back_to_world(
    ambush_client: TestClient, ambush: ContentLibrary, saves: Path
) -> None:
    cid = _create(ambush_client)["character"]["character_id"]
    initial = loads_char((saves / "world" / "chars" / f"{cid}.json").read_text(encoding="utf-8"))
    world0 = loads_world((saves / "world" / "world.json").read_text(encoding="utf-8"))
    _act(ambush_client, cid, kind="travel", to="ferry_steps")
    opened = _ok(ambush_client.post(f"/api/world/characters/{cid}/battle"))
    battle = opened["battle"]
    assert opened["world"]["battle_id"] == battle["battle_id"]
    assert opened["world"]["encounter"]["in_battle"] is True
    again = _ok(ambush_client.post(f"/api/world/characters/{cid}/battle"))
    assert again["battle"]["battle_id"] == battle["battle_id"]
    busy = ambush_client.post(f"/api/world/characters/{cid}/actions", json={"kind": "retreat"})
    assert busy.status_code == 409
    _finish_battle(ambush_client, battle, ambush)
    after = _ok(ambush_client.get(f"/api/world/characters/{cid}"))
    assert after["battle_id"] is None
    assert after["encounter"] is None
    won = any("打贏" in e for e in after["events"])
    lost = any("戰鬥失敗" in e for e in after["events"])
    assert won != lost
    if won:
        assert after["character"]["xp"] in (100, 300)  # 一般 1 份、精英 3 份（種子隨機）
        assert after["here"]["location"] == "ferry_steps"
    else:
        assert after["here"]["location"] == "mist_ferry"
        assert after["character"]["fatigued"] is True
    log = loads_log((saves / "world" / "log.jsonl").read_text(encoding="utf-8"))
    assert [e.action.kind for e in log] == ["travel", "fight"]
    replayed = replay(ambush, world0, {cid: initial}, log)
    saved = loads_char((saves / "world" / "chars" / f"{cid}.json").read_text(encoding="utf-8"))
    assert replayed.characters[cid] == saved


def test_reload_from_disk(calm: ContentLibrary, saves: Path) -> None:
    with _client(calm, saves) as first:
        cid = _create(first)["character"]["character_id"]
        _act(first, cid, kind="travel", to="hunter_hut")
    with _client(calm, saves) as second:
        view = _ok(second.get(f"/api/world/characters/{cid}"))
        assert view["here"]["location"] == "hunter_hut"
        _act(second, cid, kind="travel", to="mist_ferry")
    log = loads_log((saves / "world" / "log.jsonl").read_text(encoding="utf-8"))
    # 走到觸發事件時會多一筆說書人旁白（narrate，5B-5）
    assert [e.seq for e in log] == list(range(1, len(log) + 1))
    assert [e.action.kind for e in log if e.action.kind != "narrate"] == ["travel", "travel"]
