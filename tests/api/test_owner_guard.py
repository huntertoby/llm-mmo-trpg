"""戰鬥與一輪的擁有者檢查（Phase 6S-1；``docs/phases/Phase6計畫.md`` 第 1 節 6S-1 列）。

表格測試：每個帶 ``battle_id``／``run_id``／``character_id`` 的入口 ×（開發模式開／關）×
（自己／別人／未登入）。

- 開發模式關：自己的照常；別人的 404，訊息和真的不存在一樣（不透露存在與否）；未登入 401。
- 開發模式開：照舊不檢查（大世界端點帶了別人的 token 本來就 404，維持現狀）。

請求的順序是別人 → 未登入 → 自己：擋不住時別人的請求會先改到自己的戰鬥，測試照樣抓得到。
測試裡的密碼一律用 ``secrets`` 當場產生。
"""

from __future__ import annotations

import itertools
import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON
from trpg.api.app import create_app
from trpg.api.runs import RunStore
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.server import accounts
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore

RUN = {"seed": 1, "weapon": "fire_staff", "keywords": ["ignite", "marked"]}
BATTLE = {
    "map_id": "open_plain",
    "seed": 7,
    "weapon": "fire_staff",
    "keywords": ["ignite", "marked"],
}
CHAR = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}
END_TURN = {"type": "end_turn"}
VIEWERS = ("other", "anon", "self")
_TEST_SCRYPT_N = 2**4

BATTLE_ROUTES: tuple[tuple[str, str, Any], ...] = (
    ("GET", "/api/battles/{b}", None),
    ("GET", "/api/battles/{b}/history", None),
    ("POST", "/api/battles/{b}/preview", END_TURN),
    ("POST", "/api/battles/{b}/path-preview", {"dest": {"x": 0, "y": 0}}),
    ("GET", "/api/battles/{b}/summons/s1/command-options", None),
    ("GET", "/api/battles/{b}/summons/s1/infuse-options", None),
    ("GET", "/api/battles/{b}/skill-reasons", None),
    ("GET", "/api/battles/{b}/hero-cards", None),
    ("GET", "/api/battles/{b}/log", None),
    ("PUT", "/api/battles/{b}/orders", {}),
    ("POST", "/api/battles/{b}/decision", {"accept": True}),
    ("POST", "/api/battles/{b}/actions", END_TURN),
    ("GET", "/api/skills/no_such_skill?battle_id={b}", None),
)
RUN_ROUTES: tuple[tuple[str, str, Any], ...] = (
    ("GET", "/api/runs/{r}", None),
    ("POST", "/api/runs/{r}/allocation-preview", {"attributes": {}}),
    ("POST", "/api/runs/{r}/flash-preview", {"skill": "no_such_skill"}),
    ("POST", "/api/runs/{r}/save", None),
    ("POST", "/api/runs/{r}/choice", {"kind": "leave"}),
    ("POST", "/api/runs/{r}/battle", None),
)
WORLD_ROUTES: tuple[tuple[str, str, Any], ...] = (
    ("GET", "/api/world/characters/{c}", None),
    ("POST", "/api/world/characters/{c}/flash-preview", {"skill": "no_such_skill"}),
    ("POST", "/api/world/characters/{c}/allocation-preview", {"attributes": {}}),
    ("POST", "/api/world/characters/{c}/battle", None),
)


@dataclass
class Env:
    client: TestClient
    dev: bool
    tokens: dict[str, dict[str, str]]

    def headers(self, who: str) -> dict[str, str]:
        return self.tokens["alice" if who == "self" else "bob"] if who != "anon" else {}

    def ok(self, reply: Any, status: int = 200) -> dict[str, Any]:
        assert reply.status_code == status, reply.text
        data: dict[str, Any] = reply.json()
        return data


@pytest.fixture(scope="module", params=[False, True], ids=["dev_off", "dev_on"])
def server(
    request: pytest.FixtureRequest, ambush: ContentLibrary, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[tuple[TestClient, bool]]:
    dev = bool(request.param)
    saves = tmp_path_factory.mktemp("saves")
    app = create_app(ambush, save_dir=Path(saves), accounts=AccountSettings(dev_mode=dev))
    world = app.state.world
    assert isinstance(world, WorldStore)
    world.clock = lambda: NOON
    with TestClient(app) as client:
        yield client, dev


_NAMES = itertools.count()


@pytest.fixture
def env(server: tuple[TestClient, bool], monkeypatch: pytest.MonkeyPatch) -> Env:
    """每個測試一組新的 alice、bob（角色上限按帳號算，不互相佔位）。

    這裡驗的是擁有者檢查，不是密碼：只在這個檔案用較小的 scrypt 成本（PERF-4）。
    正式參數的註冊、登入流程由 ``tests/server/test_accounts.py`` 的
    ``test_login_and_authenticate`` 涵蓋。"""
    monkeypatch.setattr(accounts, "SCRYPT_N", _TEST_SCRYPT_N)
    client, dev = server
    store = client.app.state.accounts  # type: ignore[attr-defined]
    assert isinstance(store, AccountStore)
    tokens = {}
    n = next(_NAMES)
    for name in ("alice", "bob"):
        pw = secrets.token_urlsafe(12)
        store.create(f"{name}{n}", pw)
        reply = client.post("/api/auth/login", json={"username": f"{name}{n}", "password": pw})
        assert reply.status_code == 200, reply.text
        tokens[name] = {"Authorization": f"Bearer {reply.json()['token']}"}
    return Env(client, dev, tokens)


def _world_character(env: Env) -> str:
    alice = env.headers("self")
    made = env.ok(env.client.post("/api/world/characters", json=CHAR, headers=alice), 201)
    cid: str = made["character"]["character_id"]
    moved = env.client.post(
        f"/api/world/characters/{cid}/actions",
        json={"kind": "travel", "to": "ferry_steps"},
        headers=alice,
    )
    env.ok(moved)
    return cid


def _battle_of(env: Env, source: str) -> str:
    """alice 的一場戰鬥：自由戰鬥、一輪的戰鬥或大世界的戰鬥。"""
    alice = env.headers("self")
    if source == "free":
        data = env.ok(env.client.post("/api/battles", json=BATTLE, headers=alice), 201)
        return str(data["battle_id"])
    if source == "run":
        run = env.ok(env.client.post("/api/runs", json=RUN, headers=alice), 201)
        data = env.ok(env.client.post(f"/api/runs/{run['run_id']}/battle", headers=alice))
        return str(data["battle"]["battle_id"])
    cid = _world_character(env)
    data = env.ok(env.client.post(f"/api/world/characters/{cid}/battle", headers=alice))
    return str(data["battle"]["battle_id"])


def _check(env: Env, who: str, reply: Any, missing: str, *, world: bool = False) -> None:
    detail = str(reply.json().get("detail", "")) if reply.content else ""
    hidden = reply.status_code == 404 and detail.startswith(missing)
    if env.dev:
        if world and who == "other":  # 大世界：帶了別人的 token 本來就 404（5E-1，維持現狀）
            assert hidden, reply.text
            return
        assert reply.status_code not in (401, 403) and not hidden, (who, reply.text)
        return
    if who == "anon":
        assert reply.status_code == 401, reply.text
    elif who == "other":
        assert hidden, reply.text
    else:
        assert reply.status_code not in (401, 403) and not hidden, reply.text


def _send(env: Env, who: str, method: str, path: str, body: Any) -> Any:
    return env.client.request(method, path, json=body, headers=env.headers(who))


@pytest.mark.parametrize("source", ["free", "run", "world"])
@pytest.mark.parametrize(("method", "path", "body"), BATTLE_ROUTES)
def test_battle_routes_only_answer_the_owner(
    env: Env, source: str, method: str, path: str, body: Any
) -> None:
    battle_id = _battle_of(env, source)
    url = path.format(b=battle_id)
    if body is END_TURN:  # 結束回合要帶主角的 unit_id 才通過 schema（別人的請求也要合法才測得到）
        hero = env.ok(env.client.get(f"/api/battles/{battle_id}", headers=env.headers("self")))
        body = {**END_TURN, "unit_id": hero["hero_id"]}
    for who in VIEWERS:
        _check(env, who, _send(env, who, method, url, body), f"找不到戰鬥 {battle_id}")


@pytest.mark.parametrize(("method", "path", "body"), RUN_ROUTES)
def test_run_routes_only_answer_the_owner(env: Env, method: str, path: str, body: Any) -> None:
    run = env.ok(env.client.post("/api/runs", json=RUN, headers=env.headers("self")), 201)
    run_id = run["run_id"]
    url = path.format(r=run_id)
    for who in VIEWERS:
        _check(env, who, _send(env, who, method, url, body), f"找不到一輪 {run_id}")


@pytest.mark.parametrize(("method", "path", "body"), WORLD_ROUTES)
def test_world_routes_only_answer_the_owner(env: Env, method: str, path: str, body: Any) -> None:
    cid = _world_character(env)
    url = path.format(c=cid)
    for who in VIEWERS:
        reply = _send(env, who, method, url, body)
        _check(env, who, reply, f"找不到角色 {cid}", world=True)


def test_owner_reads_own_battle_and_run(env: Env) -> None:
    """自己的照常 200（開發模式開關都一樣）。"""
    alice = env.headers("self")
    run = env.ok(env.client.post("/api/runs", json=RUN, headers=alice), 201)
    assert env.ok(env.client.get(f"/api/runs/{run['run_id']}", headers=alice))["run_id"]
    battle_id = _battle_of(env, "free")
    assert env.ok(env.client.get(f"/api/battles/{battle_id}", headers=alice))["battle_id"]


def test_other_and_missing_ids_look_the_same(env: Env) -> None:
    """開發模式關：別人的與不存在的回同樣的狀態碼與訊息格式。"""
    if env.dev:
        pytest.skip("開發模式開照舊不檢查")
    bob = env.headers("other")
    battle_id = _battle_of(env, "free")
    theirs = env.client.get(f"/api/battles/{battle_id}", headers=bob)
    nothing = env.client.get("/api/battles/b_missing", headers=bob)
    assert theirs.status_code == nothing.status_code == 404
    assert theirs.json()["detail"] == f"找不到戰鬥 {battle_id}"
    assert nothing.json()["detail"] == "找不到戰鬥 b_missing"


def test_generated_skill_cards_only_from_own_runs(env: Env, library: ContentLibrary) -> None:
    """``/api/skills/{id}`` 查各輪的生成技能：開發模式關只查自己的一輪（別人、未登入 404）。"""
    run = env.ok(env.client.post("/api/runs", json=RUN, headers=env.headers("self")), 201)
    runs = env.client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    session = runs.get(run["run_id"])
    base = next(iter(library.skills.values()))
    secret = base.model_copy(update={"id": "gen_6s1_secret"})
    session.run = session.run.model_copy(
        update={"generated_skills": (*session.run.generated_skills, secret)}
    )
    for who in VIEWERS:
        reply = env.client.get("/api/skills/gen_6s1_secret", headers=env.headers(who))
        if env.dev or who == "self":
            assert reply.status_code == 200, (who, reply.text)
        else:
            assert reply.status_code == 404, (who, reply.text)
