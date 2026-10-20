"""Phase 3-6：一輪的自動存檔、重新整理、戰鬥紀錄還原、開局規則，以及網頁與 CLI 的一致性
（``docs/phases/Phase3計畫.md`` 8.1～8.4）。存檔一律寫在暫存資料夾。"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.api.helpers import utility_chooser
from trpg.api.app import create_app
from trpg.api.runs import RunStore
from trpg.cli.battle import cmd_replay
from trpg.cli.run import cmd_run_auto
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import BattleLog, replay
from trpg.engine.state import state_to_json
from trpg.roguelite import auto_choice, auto_play, load_save, restore_battle
from trpg.roguelite.state import BattleNode

BUILD, SEED = "build_fire", 0


@pytest.fixture
def save_dir(tmp_path: Path) -> Path:
    return tmp_path / "saves"


@pytest.fixture
def runs_client(library: ContentLibrary, save_dir: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=save_dir)) as c:
        yield c


def _runs(client: TestClient) -> RunStore:
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    return runs


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _create(client: TestClient, **over: Any) -> dict[str, Any]:
    reply = client.post("/api/runs", json={"build": BUILD, "seed": SEED, **over})
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _file(save_dir: Path, run_id: str) -> Path:
    return save_dir / f"run-{run_id}.json"


def _assert_file_matches_memory(client: TestClient, save_dir: Path, run_id: str) -> None:
    """存檔檔案讀回來，與伺服器記憶體裡的一輪（含進行中的戰鬥）一致。"""
    session = _runs(client).get(run_id)
    saved = load_save(_file(save_dir, run_id))
    assert saved.run == session.run
    if session.battle is None:
        assert saved.battle is None
        return
    assert saved.battle is not None
    assert saved.battle.steps == session.battle.steps
    assert saved.battle.orders == session.battle.order_log
    assert saved.battle.seed == session.battle.seed


def _step(client: TestClient, library: ContentLibrary, battle: dict[str, Any]) -> dict[str, Any]:
    chooser = utility_chooser(UtilityAI(library.ai_profiles))
    url = f"/api/battles/{battle['battle_id']}"
    if battle["awaiting"] == "decision":
        return _ok(client.post(f"{url}/decision", json={"accept": True}))
    state = store_of(client).get(battle["battle_id"]).state
    return _ok(client.post(f"{url}/actions", json=chooser(battle, state)))


def _steps_in_memory(client: TestClient, run_id: str) -> int:
    battle = _runs(client).get(run_id).battle
    assert battle is not None
    return len(battle.steps)


# ---------------------------------------------------------------------------
# 8.1 自動存檔
# ---------------------------------------------------------------------------


def test_every_battle_action_autosaves(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    run = _create(runs_client)
    run_id = run["run_id"]
    assert _file(save_dir, run_id).is_file()  # 開局就有存檔
    _assert_file_matches_memory(runs_client, save_dir, run_id)
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    _assert_file_matches_memory(runs_client, save_dir, run_id)
    for _ in range(3):  # 種子 0 的第一場在第 4 個動作結束
        assert battle["awaiting"] == "action"
        before = _steps_in_memory(runs_client, run_id)
        battle = _step(runs_client, library, battle)
        assert _steps_in_memory(runs_client, run_id) > before
        _assert_file_matches_memory(runs_client, save_dir, run_id)
        assert load_save(_file(save_dir, run_id)).battle is not None


def test_every_node_change_autosaves(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    """打完一整輪：戰鬥結束、升級、營火、結束，每一次節點改變後存檔都是最新。"""
    run = _create(runs_client)
    run_id = run["run_id"]
    seen: set[str] = set()
    for _ in range(80):
        session = _runs(runs_client).get(run_id)
        if session.run.ended:
            break
        node = session.run.node
        seen.add(node.kind)
        done_before = len(session.run.history)
        if isinstance(node, BattleNode):
            battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
            while battle["awaiting"] in ("action", "decision"):
                battle = _step(runs_client, library, battle)
            # 戰鬥打完的當下（還沒有任何一輪的請求）檔案就已經結算到下一個節點
            saved = load_save(_file(save_dir, run_id))
            assert saved.battle is None
            assert len(saved.run.history) == done_before + 1
        else:
            choice = auto_choice(library, session.run)
            _ok(runs_client.post(f"/api/runs/{run_id}/choice", json=choice.model_dump(mode="json")))
        _assert_file_matches_memory(runs_client, save_dir, run_id)
    assert _runs(runs_client).get(run_id).run.ended
    assert {"battle", "level_up"} <= seen
    assert load_save(_file(save_dir, run_id)).run.node.kind == "ended"
    listed = runs_client.get("/api/runs/saves").json()
    assert listed[0]["node"] == "ended" and listed[0]["victory"] in (True, False)


def test_autosave_failure_does_not_break_the_game(library: ContentLibrary, tmp_path: Path) -> None:
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")  # 存檔資料夾的位置被檔案佔住 → 寫不進去
    with TestClient(create_app(library, save_dir=blocker / "saves")) as client:
        run = _create(client)
        assert _ok(client.post(f"/api/runs/{run['run_id']}/battle"))["battle"]["awaiting"]


def test_standalone_battles_do_not_autosave(runs_client: TestClient, save_dir: Path) -> None:
    created = runs_client.post(
        "/api/battles", json={"map_id": "open_plain", "hero_build": BUILD, "seed": 1}
    )
    assert created.status_code == 201, created.text
    battle = created.json()
    action = next(a for a in battle["legal_actions"] if a["type"] != "end_turn")
    reply = runs_client.post(f"/api/battles/{battle['battle_id']}/actions", json=action)
    assert reply.status_code == 200, reply.text
    assert not save_dir.exists() or not list(save_dir.iterdir())


# ---------------------------------------------------------------------------
# 8.1 重新整理與戰鬥紀錄還原
# ---------------------------------------------------------------------------


def test_get_run_keeps_the_in_memory_battle_and_steps(
    runs_client: TestClient, library: ContentLibrary
) -> None:
    """重新整理先 GET：伺服器記憶體裡的戰鬥與步驟都還在（不像讀檔會換成新的戰鬥）。"""
    run = _create(runs_client)
    run_id = run["run_id"]
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    battle = _step(runs_client, library, battle)
    got = _ok(runs_client.get(f"/api/runs/{run_id}"))
    assert got["battle_id"] == battle["battle_id"]
    again = _ok(runs_client.get(f"/api/battles/{battle['battle_id']}"))
    assert again["view"] == battle["view"] and again["legal_actions"] == battle["legal_actions"]
    resumed = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    assert resumed["battle_id"] == battle["battle_id"]
    assert resumed["view"] == battle["view"]


def _texts(steps: list[dict[str, Any]]) -> list[str]:
    return [e["text"] for s in steps for e in s["events"] if "text" in e]


def test_history_restores_the_battle_log_after_load(
    runs_client: TestClient, library: ContentLibrary
) -> None:
    run = _create(runs_client)
    run_id = run["run_id"]
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    streamed = _texts(battle["steps"])
    for _ in range(3):
        battle = _step(runs_client, library, battle)
        streamed += _texts(battle["steps"])
    history = _ok(runs_client.get(f"/api/battles/{battle['battle_id']}/history"))
    live = _texts(history["steps"])
    assert live and live == streamed  # 歷史 ＝ 一路收到的事件
    loaded = _ok(runs_client.post("/api/runs/load", json={"run_id": run_id}))
    assert loaded["battle_id"] != battle["battle_id"]
    restored = _ok(runs_client.get(f"/api/battles/{loaded['battle_id']}/history"))
    assert _texts(restored["steps"]) == live


# ---------------------------------------------------------------------------
# 8.2 小修
# ---------------------------------------------------------------------------


def test_rules_endpoint_gives_start_points(
    runs_client: TestClient, library: ContentLibrary
) -> None:
    rules = _ok(runs_client.get("/api/runs/rules"))
    assert rules == {
        "start_points": library.roguelite.start_free_points,
        "base_attribute": library.roguelite.base_attribute,
    }


def test_builds_give_hp_mana_and_weapon(runs_client: TestClient, library: ContentLibrary) -> None:
    builds: list[dict[str, Any]] = runs_client.get("/api/builds").json()
    assert len(builds) == len(library.builds.builds)
    for out, b in zip(builds, library.builds.builds, strict=True):
        weapon = library.weapons[b.hero.weapon]
        assert out["max_hp"] == b.hero.max_hp > 0
        assert out["max_mana"] == b.hero.max_mana
        assert out["weapon"] == b.hero.weapon and out["weapon_name_zh"] == weapon.name_zh


def test_save_list_has_build_name_and_victory(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    run = _create(runs_client)
    entry = runs_client.get("/api/runs/saves").json()[0]
    expected = next(b.name_zh for b in library.builds.builds if b.id == BUILD)
    assert entry["build_name_zh"] == expected and entry["victory"] is None
    path = _file(save_dir, run["run_id"])
    data = json.loads(path.read_text(encoding="utf-8"))
    data["run"]["node"] = {"kind": "ended", "victory": False}
    path.write_text(json.dumps(data), encoding="utf-8")
    entry = runs_client.get("/api/runs/saves").json()[0]
    assert entry["node"] == "ended" and entry["victory"] is False


# ---------------------------------------------------------------------------
# 8.3 網頁與 CLI 一致
# ---------------------------------------------------------------------------


def test_api_battle_log_replays_with_the_cli(
    runs_client: TestClient, library: ContentLibrary, tmp_path: Path
) -> None:
    run = _create(runs_client)
    run_id = run["run_id"]
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    while battle["awaiting"] in ("action", "decision"):
        battle = _step(runs_client, library, battle)
    log_text = runs_client.get(f"/api/battles/{battle['battle_id']}/log").text
    path = tmp_path / "battle.json"
    path.write_text(log_text, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0 and "重播驗證通過" in out.getvalue()
    log = BattleLog.model_validate_json(log_text)
    replayed = replay(log.setup, log.seed, log.actions)
    digest = hashlib.sha256(state_to_json(replayed.state).encode("utf-8")).hexdigest()
    record = _ok(runs_client.get(f"/api/runs/{run_id}"))["history"][0]
    assert digest == record["state_digest"]


def test_api_load_and_cli_auto_from_finish_identically(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path, tmp_path: Path
) -> None:
    run = _create(runs_client)
    run_id = run["run_id"]
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    for _ in range(2):
        battle = _step(runs_client, library, battle)
    start = tmp_path / "start.json"
    start.write_bytes(_file(save_dir, run_id).read_bytes())  # 戰鬥中的存檔
    # CLI：trpg run auto --from
    cli_dir = tmp_path / "cli"
    assert cmd_run_auto(library, io.StringIO(), from_path=start, save_dir=cli_dir) == 0
    cli_final = load_save(cli_dir / f"run-{run_id}.json").run
    assert cli_final.ended
    saved = load_save(start)
    direct, _ = auto_play(library, saved.run, restore_battle(library, saved))
    assert direct == cli_final
    # API：讀檔後由「效用 AI 主角」打到結束（戰鬥走網頁動作，節點走選擇端點）
    _ok(runs_client.post("/api/runs/load", json={"run_id": run_id}))
    for _ in range(80):
        session = _runs(runs_client).get(run_id)
        if session.run.ended:
            break
        if isinstance(session.run.node, BattleNode):
            battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
            while battle["awaiting"] in ("action", "decision"):
                battle = _step(runs_client, library, battle)
        else:
            choice = auto_choice(library, session.run)
            _ok(runs_client.post(f"/api/runs/{run_id}/choice", json=choice.model_dump(mode="json")))
    api_final = load_save(_file(save_dir, run_id)).run
    assert api_final == cli_final
    assert [h.state_digest for h in api_final.history] == [
        h.state_digest for h in cli_final.history
    ]
