"""Phase 3-26a：技能點與技能等級的 API（花點、重配、換裝、技能卡的等級、戰鬥中的等級）。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.roguelite import RunState, auto_play, new_run
from trpg.roguelite.auto import AutoStop
from trpg.roguelite.state import BattleNode, CampfireNode, LevelUpNode

BUILD = "build_fire"


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(library, save_dir=tmp_path / "saves")) as c:
        yield c


def _runs(client: TestClient) -> RunStore:
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    return runs


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code == 200, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _session_at(client: TestClient, library: ContentLibrary, kind: type[object]) -> str:
    """開一輪、直接把狀態換成 AI 代打到第一個 ``kind`` 節點的樣子（API 之外的準備）。"""
    created = client.post("/api/runs", json={"build": BUILD, "seed": 0})
    assert created.status_code == 201, created.text
    run_id: str = created.json()["run_id"]

    def stop(run: RunState, battle: Any) -> bool:
        return isinstance(run.node, kind)

    stopper: AutoStop = stop
    run, _ = auto_play(library, new_run(library, BUILD, 0), stop=stopper)
    _runs(client).get(run_id).run = run
    return run_id


def test_the_hero_reports_points_levels_and_growth_rules(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id = _session_at(client, library, LevelUpNode)
    hero = _ok(client.get(f"/api/runs/{run_id}"))["hero"]
    assert hero["skill_points"] == 2
    assert hero["skill_growth"] == {
        "max_level": 5,
        "upgrade_cost": 1,
        "points_per_level": 2,
        "trait_level": 5,
        "evolve_level": 3,
        "evolve_uses": 3,
    }
    first = next(c for c in hero["skills"] if c["growth"] is not None)
    assert first["growth"]["level"] == 1 and first["growth"]["next_level"] == 2
    assert "+10%" in first["growth"]["next_text"] and first["growth"]["cost"] == 1
    passive = [c for c in hero["skills"] if c["kind_id"] != "active"]
    assert all(c["growth"] is None for c in passive)  # 只有主動技能能升級


def test_spend_points_over_the_api_updates_cards_and_stays_on_the_node(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id = _session_at(client, library, LevelUpNode)
    hero = _ok(client.get(f"/api/runs/{run_id}"))["hero"]
    skill = next(c["id"] for c in hero["skills"] if c["growth"] is not None)
    reply = _ok(
        client.post(f"/api/runs/{run_id}/choice", json={"kind": "spend", "levels": {skill: 2}})
    )
    assert reply["node"]["kind"] == "level_up"
    card = next(c for c in reply["hero"]["skills"] if c["id"] == skill)
    assert card["growth"]["level"] == 2 and card["growth"]["bonus_permille"] == 100
    assert "Lv.2" in card["growth"]["current_text"] and reply["hero"]["skill_points"] == 1
    bad = client.post(f"/api/runs/{run_id}/choice", json={"kind": "spend", "levels": {skill: 3}})
    # 3-26b：3 級是分歧進化，這一輪還沒用夠次數（顯示原因）
    assert bad.status_code == 422 and "要在這一輪用過 3 次" in bad.json()["detail"]
    assert card["growth"]["blocked_text"] == bad.json()["detail"]


def test_campfire_respec_and_loadout_over_the_api(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id = _session_at(client, library, CampfireNode)
    run = _runs(client).get(run_id).run
    assert run.skill_levels  # AI 代打升過級
    refunded = _ok(client.post(f"/api/runs/{run_id}/choice", json={"kind": "respec"}))
    assert refunded["hero"]["skill_points"] == 4
    assert all(c["growth"] is None or c["growth"]["level"] == 1 for c in refunded["hero"]["skills"])
    kept = [s["id"] for s in refunded["hero"]["skills"]][1:]
    swapped = _ok(
        client.post(f"/api/runs/{run_id}/choice", json={"kind": "loadout", "skills": kept})
    )
    assert [c["id"] for c in swapped["hero"]["skills"]] == kept
    assert len(swapped["hero"]["bench"]) >= 1
    assert swapped["node"]["kind"] == "campfire"
    # 重配與換裝只能在營火
    other = _session_at(client, library, LevelUpNode)
    for body in ({"kind": "respec"}, {"kind": "loadout", "skills": []}):
        assert client.post(f"/api/runs/{other}/choice", json=body).status_code == 409


def test_no_spending_while_a_battle_is_in_progress(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id = _session_at(client, library, BattleNode)
    _ok(client.post(f"/api/runs/{run_id}/battle"))
    reply = client.post(f"/api/runs/{run_id}/choice", json={"kind": "spend", "levels": {}})
    assert reply.status_code == 409


def test_the_battle_view_lists_the_heros_skill_levels(
    client: TestClient, library: ContentLibrary
) -> None:
    run_id = _session_at(client, library, CampfireNode)
    run = _runs(client).get(run_id).run
    leveled = next(iter(run.skill_levels))
    started = _ok(client.post(f"/api/runs/{run_id}/choice", json={"kind": "leave"}))
    assert started["node"]["kind"] == "battle"
    battle = _ok(client.post(f"/api/runs/{run_id}/battle"))["battle"]
    mine = next(u for u in battle["view"]["units"] if u["id"] == "unit_0001")
    assert mine["skill_levels"][leveled] == run.skill_levels[leveled]
    other = next(u for u in battle["view"]["units"] if u["team"] == "enemy")
    assert other["skill_levels"] == {}
