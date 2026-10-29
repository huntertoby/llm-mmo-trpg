"""``/api/runs``：roguelite 一輪的 API（Phase 3-5a）。"""

from __future__ import annotations

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
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.roguelite import next_node

BUILD, SEED = "build_fire", 0
"""回歸範本 build（開發用的開局路徑，Phase 3-24b2 起玩家介面不提供）。"""
START = {"weapon": "fire_staff", "keywords": ["ignite", "marked"]}
"""一般開局（Phase 3-24b2）：起始武器 ＋ 2 個關鍵字。"""


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


def _create(client: TestClient, **over: Any) -> dict[str, Any]:
    body = {**START, "seed": SEED, **over}
    reply = client.post("/api/runs", json=body)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _unit(battle: dict[str, Any], unit_id: str) -> dict[str, Any]:
    found: dict[str, Any] = next(u for u in battle["view"]["units"] if u["id"] == unit_id)
    return found


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _play_battle(
    client: TestClient, library: ContentLibrary, battle: dict[str, Any], limit: int | None = None
) -> dict[str, Any]:
    """以效用 AI 為主角下指令，打到結束（或送出 ``limit`` 個請求）；回傳最後的戰鬥回應。"""
    chooser = utility_chooser(UtilityAI(library.ai_profiles))
    url = f"/api/battles/{battle['battle_id']}"
    sent = 0
    while battle["awaiting"] in ("action", "decision") and (limit is None or sent < limit):
        if battle["awaiting"] == "decision":
            battle = _ok(client.post(f"{url}/decision", json={"accept": True}))
        else:
            state = store_of(client).get(battle["battle_id"]).state
            battle = _ok(client.post(f"{url}/actions", json=chooser(battle, state)))
        sent += 1
    return battle


def test_create_run_returns_hero_plan_and_first_battle(runs_client: TestClient) -> None:
    run = _create(runs_client, attributes={"int": 3, "wis": 1})
    assert run["node"] == {
        "kind": "battle",
        "battle_index": 1,
        "boss": False,
        "level": None,
        "points": None,
        "tier_up": None,
        "after_battle": None,
        "offer": None,
        "victory": None,
        "gear": None,
    }
    hero = run["hero"]
    assert hero["attributes"]["int"] == 13 and hero["attributes"]["wis"] == 11
    assert hero["level"] == 1 and hero["xp_next"] == 100
    assert hero["hp"] == hero["max_hp"] and hero["source_max"] == 3
    assert [c["id"] for c in hero["skills"]]
    assert hero["weapon_name_zh"] != "" and hero["weapon_class"] in {"melee", "ranged", "focus"}
    assert len(run["plan"]) == 6 and run["plan"][-1]["boss"]
    assert run["battle_id"] is None


def test_run_plan_carries_each_battles_objective(runs_client: TestClient) -> None:
    """Phase 3-22：計畫列出每場的勝利條件（一般戰鬥至少 1 撤離、1 守點；Boss 全滅）。"""
    plan = _create(runs_client)["plan"]
    kinds = [p["objective"]["kind"] for p in plan]
    assert kinds.count("escape") >= 1 and kinds.count("defend") >= 1
    assert kinds[-1] == "eliminate" and plan[-1]["objective"]["tiles"] == []
    for p in plan:
        if p["objective"]["kind"] != "eliminate":
            assert p["objective"]["rounds"] and p["objective"]["tiles"]


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"build": "build_nobody", "seed": 1}, 422),
        ({"build": BUILD, "seed": 1, "attributes": {"str": 1}}, 422),
        ({"build": BUILD, "seed": -1}, 422),
        ({**START, "seed": 1, "attributes": {"str": 1}}, 422),
        ({"weapon": "fire_staff", "keywords": ["ignite"], "seed": 1}, 422),
        ({"weapon": "fire_staff", "keywords": ["ignite", "ignite"], "seed": 1}, 422),
        ({"weapon": "fire_staff", "keywords": ["ignite", "nope"], "seed": 1}, 422),
        ({"weapon": "nope", "keywords": ["ignite", "marked"], "seed": 1}, 422),
        ({"weapon": "fire_staff", "seed": 1}, 422),
        ({**START, "build": BUILD, "seed": 1}, 422),
        ({"dev_pack": "dev_nobody", "seed": 1}, 422),
        ({"seed": 1}, 422),
    ],
)
def test_create_run_rejects_bad_input(
    runs_client: TestClient, body: dict[str, Any], status: int
) -> None:
    assert runs_client.post("/api/runs", json=body).status_code == status


def test_unknown_run_is_404(runs_client: TestClient) -> None:
    assert runs_client.get("/api/runs/nope").status_code == 404
    assert runs_client.post("/api/runs/load", json={"run_id": "nope"}).status_code == 404


def test_battle_starts_once_and_resumes(runs_client: TestClient) -> None:
    run = _create(runs_client)
    session = _runs(runs_client).get(run["run_id"])
    session.run = session.run.model_copy(update={"hp": 33, "mana": 2, "source": 0})
    url = f"/api/runs/{run['run_id']}"
    first = _ok(runs_client.post(f"{url}/battle"))
    battle_id = first["battle"]["battle_id"]
    assert first["run"]["battle_id"] == battle_id
    assert first["battle"]["awaiting"] == "action"
    opening = {"view": first["battle"]["initial_view"]}
    hero = _unit(opening, first["battle"]["hero_id"])
    assert (hero["hp"], hero["mana"], hero["source"]) == (33, 2, 1)  # 帶入一輪的值，源力保底 1
    again = _ok(runs_client.post(f"{url}/battle"))
    assert again["battle"]["battle_id"] == battle_id
    assert again["battle"]["steps"] == []
    assert runs_client.post(f"{url}/choice", json={"kind": "leave"}).status_code == 409


def test_finished_battle_writes_back_and_levels_up(
    runs_client: TestClient, library: ContentLibrary
) -> None:
    run = _create(runs_client)
    url = f"/api/runs/{run['run_id']}"
    started = _ok(runs_client.post(f"{url}/battle"))
    final = _play_battle(runs_client, library, started["battle"])
    assert final["awaiting"] == "ended" and final["outcome"]["winner"] == "ally"
    hero_view = _unit(final, final["hero_id"])
    # 先裝備三選一（Phase 3K-2），還沒升級
    offered = _ok(runs_client.get(url))
    assert offered["battle_id"] is None and offered["node"]["kind"] == "gear_offer"
    gear = offered["node"]["gear"]
    assert gear["after_battle"] == 1 and len(gear["candidates"]) == 3
    assert len({c["item"]["slot_type"] for c in gear["candidates"]}) == 3
    assert all(
        c["slot"] and c["slot_zh"] and c["item"]["points"] is not None for c in gear["candidates"]
    )
    assert (
        offered["hero"]["level"] == 1
        and runs_client.post(f"{url}/choice", json={"kind": "leave"}).status_code == 409
    )
    assert all(slot["item"] is None for slot in offered["hero"]["equipment"][1:])
    taken = _ok(runs_client.post(f"{url}/choice", json={"kind": "gear_pick", "pick": 0}))
    worn = [s["item"] for s in taken["hero"]["equipment"] if s["item"] is not None]
    assert gear["candidates"][0]["item"]["id"] in [i["id"] for i in worn]
    # 回到沒選裝備的狀態再打一次，驗證跳過：重新讀檔（自動存檔在選擇之前不存在）所以直接用同一輪
    after = taken
    assert after["battle_id"] is None
    level_gain = library.ruleset.core.level_hp_bonus(  # 升到 2 級，目前 HP 同步增加
        library.roguelite.start.heroes["focus"].max_hp, 2
    )
    assert after["hero"]["hp"] == max(hero_view["hp"], 1) + level_gain
    assert after["history"][0]["won"] and after["history"][0]["index"] == 1
    node = after["node"]
    assert node["kind"] == "level_up" and node["points"] == 2
    offer = node["offer"]
    assert len(offer["candidates"]) == 3
    assert [t["kind"] for t in offer["tags"]] == ["deepen", "bridge", "new"]
    assert [t["label_zh"] for t in offer["tags"]] == ["加深", "橋接", "新方向"]
    # 生成技能的卡片也查得到
    generated = offer["candidates"][0]["id"]
    assert _ok(runs_client.get(f"/api/skills/{generated}"))["id"] == generated
    assert runs_client.post(f"{url}/choice", json={"kind": "leave"}).status_code == 409
    bad = {"kind": "level_up", "attributes": {"int": 1}, "pick": None}
    assert runs_client.post(f"{url}/choice", json=bad).status_code == 422
    pick = {"kind": "level_up", "attributes": {"int": 2}, "pick": 0, "replace": None}
    reply = runs_client.post(f"{url}/choice", json=pick)
    if reply.status_code == 422:  # 欄位滿：換掉第一個同種技能以外的情況改為跳過
        reply = runs_client.post(f"{url}/choice", json={**pick, "pick": None})
    chosen = _ok(reply)
    assert chosen["hero"]["attributes"]["int"] == after["hero"]["attributes"]["int"] + 2
    assert chosen["hero"]["level"] == 2
    assert chosen["node"]["kind"] == "battle" and chosen["node"]["battle_index"] == 2


def test_save_mid_battle_load_and_continue_matches(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    run = _create(runs_client)
    url = f"/api/runs/{run['run_id']}"
    battle = _ok(runs_client.post(f"{url}/battle"))["battle"]
    battle = _play_battle(runs_client, library, battle, limit=2)
    assert battle["awaiting"] == "action"
    saved = _ok(runs_client.post(f"{url}/save"))
    assert saved == {
        "run_id": run["run_id"],
        "file": f"run-{run['run_id']}.json",
        "format": "trpg-run/13",
        "in_battle": True,
    }
    assert (save_dir / saved["file"]).is_file()
    listed: list[dict[str, Any]] = runs_client.get("/api/runs/saves").json()
    assert [s["run_id"] for s in listed] == [run["run_id"]]
    assert listed[0]["in_battle"]
    snapshot = (save_dir / saved["file"]).read_bytes()
    # 原本的一輪打完（自動存檔會覆寫存檔，所以先留一份存檔當下的檔案）
    original = _play_battle(runs_client, library, battle)
    (save_dir / saved["file"]).write_bytes(snapshot)
    # 讀檔：重播到存檔當下，戰場與存檔時相同
    loaded = _ok(runs_client.post("/api/runs/load", json={"run_id": run["run_id"]}))
    assert loaded["battle_id"] not in (None, battle["battle_id"])
    resumed = _ok(runs_client.post(f"{url}/battle"))["battle"]
    assert resumed["battle_id"] == loaded["battle_id"]
    assert resumed["view"] == battle["view"]
    assert resumed["legal_actions"] == battle["legal_actions"]
    finished = _play_battle(runs_client, library, resumed)
    assert finished["view"] == original["view"]
    assert finished["outcome"] == original["outcome"]


def test_corrupt_save_is_422(runs_client: TestClient, save_dir: Path) -> None:
    save_dir.mkdir(parents=True)
    (save_dir / "run-bad.json").write_text('{"format": "trpg-run/0"}', encoding="utf-8")
    reply = runs_client.post("/api/runs/load", json={"run_id": "bad"})
    assert reply.status_code == 422
    assert "trpg-run/13" in reply.json()["detail"]
    assert runs_client.get("/api/runs/saves").json() == []


def test_campfire_choices_over_the_api(runs_client: TestClient) -> None:
    run = _create(runs_client)
    runs = _runs(runs_client)
    session = runs.get(run["run_id"])
    session.run = next_node(
        runs.library, session.run.model_copy(update={"battles_done": 3, "hp": 1})
    )
    url = f"/api/runs/{run['run_id']}"
    offer = _ok(runs_client.get(url))  # 第 3 場後先是完整技能三選一（3W-5），再到營火
    assert offer["node"]["kind"] == "complete_offer" and offer["node"]["after_battle"] == 3
    assert offer["node"]["offer"]["reason"] == "complete"
    assert len(offer["node"]["offer"]["candidates"]) == 3
    assert runs_client.post(f"{url}/choice", json={"kind": "leave"}).status_code == 409
    camp = _ok(runs_client.post(f"{url}/choice", json={"kind": "complete_pick", "pick": None}))
    assert camp["node"]["kind"] == "campfire" and camp["node"]["after_battle"] == 3
    assert camp["hero"]["hp"] == camp["hero"]["max_hp"]
    left = _ok(runs_client.post(f"{url}/choice", json={"kind": "leave"}))
    assert left["node"] == {**left["node"], "kind": "battle", "battle_index": 4}


def _rewrite_save(save_dir: Path, run_id: str, **fields: Any) -> None:
    """改寫存檔的頂層欄位（值為 ``None`` 表示移除該欄位）。"""
    path = save_dir / f"run-{run_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in fields.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    path.write_text(json.dumps(data), encoding="utf-8")


def _save_mid_battle(client: TestClient, library: ContentLibrary) -> str:
    run = _create(client)
    url = f"/api/runs/{run['run_id']}"
    battle = _ok(client.post(f"{url}/battle"))["battle"]
    _play_battle(client, library, battle, limit=2)
    _ok(client.post(f"{url}/save"))
    return str(run["run_id"])


def test_mid_battle_save_with_a_changed_ruleset_hash_restarts_that_battle(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    """內容檔改過的戰鬥中存檔和引擎版本不符一樣：捨棄那場戰鬥、回到該戰鬥節點開頭，提示一次。"""
    run_id = _save_mid_battle(runs_client, library)
    assert json.loads((save_dir / f"run-{run_id}.json").read_text(encoding="utf-8"))["ruleset_hash"]
    _rewrite_save(save_dir, run_id, ruleset_hash="0" * 64)
    loaded = _ok(runs_client.post("/api/runs/load", json={"run_id": run_id}))
    assert loaded["battle_id"] is None and loaded["node"]["kind"] == "battle"
    assert loaded["load_notice"] == "內容檔已更新，這場戰鬥從開頭重新開始。"
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    assert battle["view"]["round"] == 1


def test_mid_battle_save_from_an_old_engine_restarts_that_battle(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    """3W-R1：引擎版本不符的戰鬥中存檔捨棄那場戰鬥、回到該戰鬥節點開頭，讀檔回應帶提示一次。"""
    run_id = _save_mid_battle(runs_client, library)
    _rewrite_save(save_dir, run_id, engine="trpg-battle-log/1")
    loaded = _ok(runs_client.post("/api/runs/load", json={"run_id": run_id}))
    assert loaded["battle_id"] is None and loaded["node"]["kind"] == "battle"
    assert loaded["load_notice"] == "這場戰鬥的紀錄格式已更新，從這場的開頭重新開始。"
    assert _ok(runs_client.get(f"/api/runs/{run_id}"))["load_notice"] is None
    battle = _ok(runs_client.post(f"/api/runs/{run_id}/battle"))["battle"]
    assert battle["view"]["round"] == 1  # 從頭開打


def test_old_mid_battle_save_without_hash_restarts_that_battle(
    runs_client: TestClient, library: ContentLibrary, save_dir: Path
) -> None:
    run_id = _save_mid_battle(runs_client, library)
    _rewrite_save(save_dir, run_id, ruleset_hash=None)
    loaded = _ok(runs_client.post("/api/runs/load", json={"run_id": run_id}))
    assert loaded["battle_id"] is None and loaded["node"]["kind"] == "battle"
    assert loaded["load_notice"] == "內容檔已更新，這場戰鬥從開頭重新開始。"


def test_between_battles_save_ignores_the_hash(runs_client: TestClient, save_dir: Path) -> None:
    run = _create(runs_client)
    saved = _ok(runs_client.post(f"/api/runs/{run['run_id']}/save"))
    assert saved["in_battle"] is False
    _rewrite_save(save_dir, run["run_id"], ruleset_hash="f" * 64)
    assert runs_client.post("/api/runs/load", json={"run_id": run["run_id"]}).status_code == 200
    _rewrite_save(save_dir, run["run_id"], ruleset_hash=None)  # 舊存檔沒有此欄位
    loaded = _ok(runs_client.post("/api/runs/load", json={"run_id": run["run_id"]}))
    assert loaded["node"]["kind"] == "battle"


def test_rules_and_hero_expose_the_hp_per_constitution_point(
    runs_client: TestClient, library: ContentLibrary
) -> None:
    """Phase 3-7：前端的「＋N HP」預覽用的係數來自 core.yaml。"""
    core = library.ruleset.core
    assert runs_client.get("/api/runs/rules").json()["hp_per_con_point"] == core.hp_per_con_point
    hero = _create(runs_client)["hero"]
    assert (hero["hp_per_con_point"], hero["hp_con_base"]) == (
        core.hp_per_con_point,
        core.hp_con_base,
    )
    assert hero["max_hp"] == hero["hp"]


def test_hero_exposes_the_attribute_perks_generated_from_the_data(
    runs_client: TestClient, library: ContentLibrary
) -> None:
    """Phase 3H-1：面板的常駐數值說明由 core.yaml 的 attribute_perks 產生，階數依主角的屬性。"""
    perks = library.ruleset.core.attribute_perks
    hero = _create(runs_client)["hero"]
    shown = hero["attribute_perks"]
    assert len(shown) == len(perks.perks) == 6
    by_attr = {p["attr"]: p for p in shown if p["attr"] in ("str", "wil")}
    for attr in ("str", "wil"):
        tier = perks.tier(hero["attributes"][attr])
        assert by_attr[attr]["tier"] == tier
        assert (by_attr[attr]["now_zh"] is None) == (tier == 0)
        assert by_attr[attr]["next_at"] == perks.base + perks.step * (tier + 1)
    assert all(p["per_tier_zh"].endswith("／階") and "{n}" not in p["per_tier_zh"] for p in shown)


def test_a_run_can_start_with_a_race_and_the_battle_view_shows_it(runs_client: TestClient) -> None:
    """種族（Phase 3R-2）：`race` 隨一輪保存，戰鬥視圖的主角帶 `race`（種族技、次數、被動）。"""
    run = _create(runs_client, race="elf")
    assert _runs(runs_client).get(run["run_id"]).run.hero.race == "elf"
    started = _ok(runs_client.post(f"/api/runs/{run['run_id']}/battle"))["battle"]
    units = started["view"]["units"]
    hero = next(u for u in units if u["id"] == started["hero_id"])
    assert hero["race"]["id"] == "elf"
    assert hero["race"]["skill_name_zh"] == "林隱"
    assert hero["race"]["skill_uses_left"] == hero["race"]["skill_uses_max"] == 2
    assert hero["race"]["passive_name_zh"] == "林間視野"
    assert all(u["race"] is None for u in units if u["team"] == "enemy")


def test_a_run_rejects_unknown_races(runs_client: TestClient) -> None:
    reply = runs_client.post("/api/runs", json={**START, "seed": SEED, "race": "elfin"})
    assert reply.status_code == 422 and "未知的種族" in reply.text
