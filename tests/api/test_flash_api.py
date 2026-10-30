"""Phase 3W-5：閃現的 API（預覽與每類數量、出題與選擇、重閃、溶掉、傳承只在營火、戰鬥中擋下、
LLM Mock 來源）。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.engine.helpers import library as _load_library
from trpg.api.app import create_app
from trpg.api.llm_source import MockLlmProvider
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.roguelite import auto_play
from trpg.roguelite.state import CampfireNode, GearOfferNode, RunState

START = {"build": "build_fire", "seed": 6}
# 每打贏一場的靈感點（取 content 的值，不寫死）
INSIGHT_PER_WIN = _load_library().flash.rules.insight_per_win


@pytest.fixture
def client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(library, save_dir=tmp_path / "saves", llm=MockLlmProvider())
    with TestClient(app) as c:
        yield c


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code in (200, 201), reply.text
    data: dict[str, Any] = reply.json()
    return data


def _store(client: TestClient) -> RunStore:
    runs = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(runs, RunStore)
    return runs


def _at_gear(client: TestClient, **create: Any) -> tuple[str, RunState]:
    """開一輪並用 AI 打完第一場，停在裝備三選一（有 1 點靈感、技能先上場用過）。"""
    run_id = _ok(client.post("/api/runs", json={**START, **create}))["run_id"]
    store = _store(client)
    session = store.get(run_id)
    run, _ = auto_play(
        store.library, session.run, stop=lambda r, _b: isinstance(r.node, GearOfferNode)
    )
    session.run = run
    return run_id, run


def _ready(body: dict[str, Any]) -> str:
    return str(next(f["skill_id"] for f in body["hero"]["flash"] if f["can_flash"]))


def test_the_hero_reports_insight_rules_and_flash_state(client: TestClient) -> None:
    run_id, _ = _at_gear(client)
    body = _ok(client.get(f"/api/runs/{run_id}"))
    hero = body["hero"]
    assert hero["insight"] == INSIGHT_PER_WIN
    rules = hero["flash_rules"]
    assert (rules["open_cost"], rules["open_options"]) == (1, 4)
    assert (rules["focused_cost"], rules["focused_options"]) == (2, 3)
    assert (rules["max_flashes"], rules["major_flash"], rules["insight_per_win"]) == (
        5,
        3,
        INSIGHT_PER_WIN,
    )
    owned = [c["id"] for c in hero["skills"]] + [c["id"] for c in hero["bench"]]
    assert [f["skill_id"] for f in hero["flash"]] == owned
    flash = next(f for f in hero["flash"] if f["can_flash"])
    assert flash["used"] and flash["flashes"] == 0 and flash["records"] == []
    assert flash["flash_problem_zh"] is None and flash["dissolve_refund"] == 0
    assert body["pending_flash"] is None
    assert "skill_points" not in hero and "evolutions" not in hero


def test_preview_lists_category_counts_and_problems(client: TestClient) -> None:
    run_id, _ = _at_gear(client)
    body = _ok(client.get(f"/api/runs/{run_id}"))
    skill = _ready(body)
    preview = _ok(client.post(f"/api/runs/{run_id}/flash-preview", json={"skill": skill}))
    assert preview["problem_zh"] is None and preview["nth"] == 1 and not preview["major"]
    assert preview["categories"] and all(c["name_zh"] for c in preview["categories"])
    assert all(0 <= c["count"] <= 3 for c in preview["categories"])
    bad = _ok(client.post(f"/api/runs/{run_id}/flash-preview", json={"skill": "skill_nobody"}))
    assert bad["problem_zh"] and bad["categories"] == []
    # 預覽不改狀態
    assert _ok(client.get(f"/api/runs/{run_id}"))["hero"]["insight"] == INSIGHT_PER_WIN


def test_flash_then_pick_over_the_api(client: TestClient) -> None:
    run_id, _ = _at_gear(client)
    url = f"/api/runs/{run_id}/choice"
    skill = _ready(_ok(client.get(f"/api/runs/{run_id}")))
    opened = _ok(client.post(url, json={"kind": "flash", "skill": skill}))
    pending = opened["pending_flash"]
    assert pending["skill_id"] == skill and pending["cost"] == 1 and pending["slot"] is None
    assert len(pending["options"]) == 4
    assert opened["hero"]["insight"] == INSIGHT_PER_WIN - 1
    option = pending["options"][0]
    assert option["card"]["id"] and option["summary_zh"] and option["category_zh"]
    # 生成的選項技能卡查得到
    assert _ok(client.get(f"/api/skills/{option['card']['id']}"))["id"] == option["card"]["id"]
    # 待選時別的選擇 409、不能開戰
    assert client.post(url, json={"kind": "gear_pick", "pick": None}).status_code == 409
    picked = _ok(client.post(url, json={"kind": "flash_pick", "pick": 0}))
    assert picked["pending_flash"] is None and picked["node"]["kind"] == "gear_offer"
    new_id = option["card"]["id"]
    state = next(f for f in picked["hero"]["flash"] if f["skill_id"] == new_id)
    assert state["flashes"] == 1 and not state["used"] and state["spent"] == 1
    assert state["records"][0]["nth"] == 1 and state["records"][0]["summary_zh"]
    assert not state["can_flash"] and state["flash_problem_zh"]
    # 沒點了（明確把點數設為 0，不依賴每勝點數）
    session = _store(client).get(run_id)
    session.run = session.run.model_copy(update={"insight": 0})
    other = _ready(picked)
    assert client.post(url, json={"kind": "flash", "skill": other}).status_code == 422


def test_reflash_dissolve_and_inherit_only_at_the_campfire(client: TestClient) -> None:
    run_id, _ = _at_gear(client)
    url = f"/api/runs/{run_id}/choice"
    skill = _ready(_ok(client.get(f"/api/runs/{run_id}")))
    _ok(client.post(url, json={"kind": "flash", "skill": skill}))
    states = _ok(client.post(url, json={"kind": "flash_pick", "pick": 0}))["hero"]["flash"]
    flashed = next(f["skill_id"] for f in states if f["flashes"] == 1)
    for body in (
        {"kind": "flash", "skill": flashed, "slot": 1},
        {"kind": "dissolve", "skill": flashed},
        {"kind": "inherit", "skill": flashed, "source": flashed, "records": [1]},
    ):
        assert client.post(url, json=body).status_code == 409
    session = _store(client).get(run_id)
    session.run = session.run.model_copy(
        update={"node": CampfireNode(after_battle=3), "insight": 4}
    )
    reflash = _ok(client.post(url, json={"kind": "flash", "skill": flashed, "slot": 1}))
    assert reflash["pending_flash"]["slot"] == 1 and reflash["hero"]["insight"] == 3
    done = _ok(client.post(url, json={"kind": "flash_pick", "pick": 0}))
    again = next(f for f in done["hero"]["flash"] if f["flashes"] == 1)
    assert again["records"][0]["reflashes"] == 1 and again["spent"] == 2
    gone = _ok(client.post(url, json={"kind": "dissolve", "skill": again["skill_id"]}))
    assert gone["hero"]["insight"] == 3 + 1  # 花了 2 點，退 1
    assert all(f["skill_id"] != again["skill_id"] for f in gone["hero"]["flash"])


def test_the_backend_sends_reflash_slots_and_inherit_rules(client: TestClient) -> None:
    """3W-R2：可重閃的欄、可帶走的變化、傳承目標與不能傳承的原因由後端下發（前端不自己推）。"""
    run_id, _ = _at_gear(client)
    url = f"/api/runs/{run_id}/choice"
    skill = _ready(_ok(client.get(f"/api/runs/{run_id}")))
    _ok(client.post(url, json={"kind": "flash", "skill": skill}))
    hero = _ok(client.post(url, json={"kind": "flash_pick", "pick": 0}))["hero"]
    assert hero["flash_rules"]["max_carry"] == hero["flash_rules"]["major_flash"] - 1 == 2
    flashed = next(f for f in hero["flash"] if f["flashes"] == 1)
    assert flashed["reflash_slots"] == [{"slot": 1, "transform_hint": False}]
    assert flashed["carryable"] == [1] and not flashed["inherit_target"]
    assert flashed["inherit_problem_zh"] is None
    fresh = [f for f in hero["flash"] if f["flashes"] == 0]
    assert fresh and all(f["inherit_target"] and f["reflash_slots"] == [] for f in fresh)
    assert all(f["carryable"] == [] and f["inherit_problem_zh"] for f in fresh)


def test_no_flash_while_a_battle_is_in_progress(client: TestClient) -> None:
    run_id = _ok(client.post("/api/runs", json=START))["run_id"]
    _ok(client.post(f"/api/runs/{run_id}/battle"))
    session = _store(client).get(run_id)
    session.run = session.run.model_copy(update={"insight": 3})
    skill = session.run.hero.skills[0]
    reply = client.post(f"/api/runs/{run_id}/choice", json={"kind": "flash", "skill": skill})
    assert reply.status_code == 409


def test_llm_runs_ask_the_mock_for_flash_variations(client: TestClient) -> None:
    run_id, _ = _at_gear(client, llm=True)
    session = _store(client).get(run_id)
    assert session.run.llm and session.flash_source is not None
    url = f"/api/runs/{run_id}/choice"
    skill = _ready(_ok(client.get(f"/api/runs/{run_id}")))
    _ok(client.post(url, json={"kind": "flash", "skill": skill}))
    log = _store(client).get(run_id).run.flash_llm_log
    assert len(log) == 1 and log[0].source in ("llm", "partial")
